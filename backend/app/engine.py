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
from .drafting import draft_answer, infer_choice, usage_cost


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
    usage: dict | None = None  # token usage for a drafted answer (None = no model cost)


# Shown when drafting is gated behind a trust-document upload (free tier, no docs).
BLOCKED_ANSWER = "Add a SOC 2 or policy in Trust Documents so Attestly can draft this answer."


def answer_question(
    org_id: int, item_id: int, question: str, bank: list[dict], allow_draft: bool = True,
    block_message: str = BLOCKED_ANSWER,
) -> AnsweredItem:
    # Embed the query once and reuse it for both bank ranking and doc search
    # (avoids a second identical embedding call per drafted question).
    query_vec = embeddings.embed_one(question, input_type="query")
    matches = retrieval.rank(question, bank, query_vec=query_vec)
    reusable = retrieval.best_reusable(matches)

    if reusable is None and not allow_draft:
        # Drafting is gated (no trust document, or free-tier spend cap). Don't
        # spend a model call — surface why. Blocked items are not charged.
        result = AnsweredItem(
            item_id=item_id,
            question=question,
            answer=block_message,
            confidence=0.0,
            match_type="blocked",
            matched_answer_id=None,
            needs_review=True,
            choice="",
            citations=[],
            verification="skipped",
        )
    elif reusable is not None:
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
            usage=d.usage,
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


def answer_questionnaire(
    org_id: int, questionnaire_id: int, allow_draft: bool = True,
    block_message: str = BLOCKED_ANSWER,
) -> list[AnsweredItem]:
    bank = db.list_answers(org_id, status="approved")
    # Locked items are over the plan's quota — leave them unanswered for the
    # upgrade prompt; only spend model calls (and quota) on the rest.
    items = [it for it in db.list_items(questionnaire_id) if not it.get("locked")]
    out: list[AnsweredItem | None] = [None] * len(items)

    # Answer questions concurrently — each drafted one makes several sequential
    # API calls, so parallelism cuts wall time roughly by the worker count.
    workers = max(1, min(config.ANSWER_CONCURRENCY, len(items)))
    if workers == 1 or len(items) <= 1:
        for i, it in enumerate(items):
            out[i] = answer_question(org_id, it["id"], it["question"], bank, allow_draft, block_message)
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {
                ex.submit(answer_question, org_id, it["id"], it["question"], bank,
                          allow_draft, block_message): i
                for i, it in enumerate(items)
            }
            for fut in as_completed(futures):
                out[futures[fut]] = fut.result()

    # Record token/cost usage per drafted answer (post-join, so no concurrent
    # writes). Reused and blocked items have no model cost.
    for it in out:
        if it and it.usage and it.usage.get("input_tokens", 0) > 0:
            db.record_usage(org_id, questionnaire_id, it.item_id, it.usage, usage_cost(it.usage))

    db.set_answered_count(questionnaire_id, len(out))
    db.set_questionnaire_status(questionnaire_id, "ready")
    return out  # type: ignore[return-value]
