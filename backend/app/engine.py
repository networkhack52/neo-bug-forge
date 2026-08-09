"""Answering engine: the core value loop.

For each question:
  1. Rank the org's Answer Bank (lexical/fuzzy).
  2. If the top match is confident -> reuse verbatim (free, instant, consistent).
  3. Else -> draft with Claude, grounded in the closest prior answers.
Every approved answer flows back into the Bank, so accuracy and reuse-rate
compound per customer — that is the retention moat.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from . import config, db, documents, embeddings, retrieval
from .drafting import draft_answer, infer_choice


@dataclass
class AnsweredItem:
    item_id: int
    question: str
    answer: str
    confidence: float
    match_type: str
    matched_answer_id: int | None
    needs_review: bool
    choice: str = ""
    citations: list[dict] = field(default_factory=list)
    verification: str = "skipped"


def answer_question(org_id: int, item_id: int, question: str, bank: list[dict]) -> AnsweredItem:
    # Embed the query once and reuse it for both bank ranking and doc search
    # (avoids a second identical embedding call per drafted question).
    query_vec = embeddings.embed_one(question, input_type="query")
    matches = retrieval.rank(question, bank, query_vec=query_vec)
    reusable = retrieval.best_reusable(matches)

    if reusable is not None:
        db.bump_reuse(reusable.answer_id)
        result = AnsweredItem(
            item_id=item_id,
            question=question,
            answer=reusable.answer,
            confidence=reusable.score,
            match_type="reuse",
            matched_answer_id=reusable.answer_id,
            needs_review=False,
            choice=infer_choice(reusable.answer),
            # A reused answer is its own source.
            citations=[{"title": reusable.question, "text": reusable.answer, "kind": "library"}],
            verification="supported",
        )
    else:
        ctx = retrieval.context_matches(matches)
        docs = documents.search(org_id, question, query_vec=query_vec)
        d = draft_answer(question, ctx, docs)
        result = AnsweredItem(
            item_id=item_id,
            question=question,
            answer=d.answer,
            confidence=d.confidence,
            match_type=d.match_type,
            matched_answer_id=ctx[0].answer_id if ctx else None,
            needs_review=d.needs_review,
            choice=d.choice,
            citations=d.citations,
            verification=d.verification,
        )

    db.update_item(
        item_id,
        answer=result.answer,
        confidence=result.confidence,
        match_type=result.match_type,
        matched_answer_id=result.matched_answer_id,
        needs_review=result.needs_review,
        choice=result.choice,
        citations=result.citations,
        verification=result.verification,
    )
    return result


def answer_questionnaire(org_id: int, questionnaire_id: int) -> list[AnsweredItem]:
    bank = db.list_answers(org_id, status="approved")
    items = db.list_items(questionnaire_id)
    out: list[AnsweredItem | None] = [None] * len(items)

    # Answer questions concurrently — each drafted one makes several sequential
    # API calls, so parallelism cuts wall time roughly by the worker count.
    workers = max(1, min(config.ANSWER_CONCURRENCY, len(items)))
    if workers == 1 or len(items) <= 1:
        for i, it in enumerate(items):
            out[i] = answer_question(org_id, it["id"], it["question"], bank)
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {
                ex.submit(answer_question, org_id, it["id"], it["question"], bank): i
                for i, it in enumerate(items)
            }
            for fut in as_completed(futures):
                out[futures[fut]] = fut.result()

    db.set_answered_count(questionnaire_id, len(out))
    db.set_questionnaire_status(questionnaire_id, "ready")
    return out  # type: ignore[return-value]
