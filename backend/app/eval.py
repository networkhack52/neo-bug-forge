"""Answer-quality eval: measure the FALSE CONFIDENCE rate.

Runs a fixed, labelled set of questions against a known document set and reports
how often the model asserts a control the documents do NOT support. Also reports
model cost, so quality and COGS are read together.

Decision rule (per the dev brief): if false confidence > 3%, move the verify
step to a stronger model (set ATTESTLY_VERIFY_MODEL). Until then, haiku-only.

Run (needs ANTHROPIC_API_KEY, and VOYAGE_API_KEY if you want semantic doc search):

    python -m app.eval

Exits non-zero if false confidence exceeds the threshold, so it can gate a
release if you ever wire it into CI with a key.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from . import config, documents, embeddings, fuzzy
from .drafting import CHOICES, NO_EVIDENCE, draft_answer, usage_cost

import os

EVAL_DIR = Path(__file__).resolve().parent.parent / "eval"
# Paths are overridable so the frozen 60 stays runnable next to the 150:
#   ATTESTLY_EVAL_DOCS=eval/attestly_eval_docs_60.md \
#   ATTESTLY_EVAL_QUESTIONS=eval/eval_questions_60.json python -m app.eval
DOCS = Path(os.environ.get("ATTESTLY_EVAL_DOCS", "")) if os.environ.get("ATTESTLY_EVAL_DOCS") \
    else EVAL_DIR / "attestly_eval_docs.md"
QUESTIONS = Path(os.environ.get("ATTESTLY_EVAL_QUESTIONS", "")) if os.environ.get("ATTESTLY_EVAL_QUESTIONS") \
    else EVAL_DIR / "eval_questions.json"
THRESHOLD = 0.03  # 3% false confidence -> upgrade the verify model


@dataclass
class _Doc:
    doc_name: str
    text: str


def _chunks() -> list[_Doc]:
    """Split the fixture into topical passages the model can cite."""
    raw = DOCS.read_text(encoding="utf-8")
    parts = [p.strip() for p in raw.split("\n\n") if p.strip() and not p.startswith("# ")]
    return [_Doc("attestly_eval_docs.md", p) for p in parts]


# Top passages handed to the model per question. Matches production's default so
# the eval tests the REAL pipeline: the right control has to be *retrieved* out of
# the whole corpus, not just be present somewhere in it. Override to widen/narrow.
TOP_K = int(os.environ.get("ATTESTLY_EVAL_TOP_K", str(documents.MAX_GROUND_CHUNKS)))


def _retrieve(query: str, docs: list[_Doc], vectors, k: int) -> list[_Doc]:
    """Rank the corpus for a question and return the top-k passages, the same way
    documents.search does: semantic cosine when embeddings are on, else lexical.

    k <= 0 means "hand the model the whole corpus" — isolates MODEL judgment from
    retrieval (comparable to the frozen 60), useful when embeddings aren't set."""
    if k <= 0:
        return list(docs)
    if vectors:
        qv = embeddings.embed_one(query, input_type="query")
        scored = [((embeddings.cosine(qv, vectors[i]) * 100) if qv else 0.0, d)
                  for i, d in enumerate(docs)]
    else:
        scored = [(fuzzy.partial_ratio(query, d.text), d) for d in docs]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [d for s, d in scored[:k] if s > 0]


def _asserts_control(d) -> bool:
    """The model confidently claims 'Yes' to the control (asserts it exists / agrees)."""
    return d.choice == "Yes" and not d.needs_review and d.answer != NO_EVIDENCE


def _answered_confidently(d) -> bool:
    return not d.needs_review and d.answer != NO_EVIDENCE and d.choice in CHOICES


def _abstained(d) -> bool:
    return not _answered_confidently(d)


def _is_false_confidence(label: str, d) -> bool:
    """A dangerous over-claim, defined per category:

    - unsupported: the docs are SILENT, so any confident Yes/No is unfounded
      (absence is not evidence). Only abstaining is correct.
    - contradicted: near-miss evidence exists with a different specific, so a
      confident 'Yes' to the question's figure is the over-claim. A grounded 'No'
      (the real value) or an abstention is fine.
    """
    if label == "unsupported":
        return not _abstained(d)
    if label == "contradicted":
        return _asserts_control(d)
    return False


def run() -> int:
    if not config.LLM_ENABLED:
        print("ANTHROPIC_API_KEY is not set — the eval needs the live model. Aborting.")
        return 2

    docs = _chunks()
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    by_label: dict[str, list] = {}

    # Pre-embed the corpus once, so each question retrieves its top-K against the
    # whole set — this is what makes a large corpus a real test: the right control
    # must be RETRIEVED, not merely present.
    mode = "semantic" if config.EMBEDDINGS_ENABLED else "lexical"
    vectors = embeddings.embed_texts([d.text for d in docs], input_type="document") \
        if config.EMBEDDINGS_ENABLED else None
    retrieval_desc = "all passages (no retrieval)" if TOP_K <= 0 else f"top-{TOP_K} {mode} retrieval"

    total_cost = 0.0
    false_confidence = []
    failures = []  # questions where the model call errored and fell back
    print(f"Running {len(questions)} questions against {len(docs)} passages, "
          f"{retrieval_desc} "
          f"(draft={config.ANTHROPIC_MODEL}, verify={config.VERIFY_MODEL})\n")
    if TOP_K > 0 and not config.EMBEDDINGS_ENABLED:
        print("  NOTE: lexical retrieval (no VOYAGE_API_KEY). For the realistic end-to-end\n"
              "  number, set VOYAGE_API_KEY (semantic, matches production grounding), or set\n"
              "  ATTESTLY_EVAL_TOP_K=0 to measure model judgment against the whole corpus.\n")

    for q in questions:
        retrieved = _retrieve(q["question"], docs, vectors, TOP_K)
        d = draft_answer(q["question"], [], retrieved)
        total_cost += usage_cost(d.usage)
        if "model call failed" in d.answer:
            failures.append((q, d.answer.split("model call failed:", 1)[-1].strip(" ]")))
        stance = "assert" if _asserts_control(d) else ("answer" if _answered_confidently(d) else "abstain")
        by_label.setdefault(q["label"], []).append((q, d, stance))
        fc = _is_false_confidence(q["label"], d)
        if fc:
            false_confidence.append(q)
        print(f"  [{q['label'][:6]:6}] {q['id']}  {stance:7}  {q['question'][:58]}"
              f"{'  <-- FALSE CONFIDENCE' if fc else ''}")

    n = len(questions)
    fc_rate = len(false_confidence) / n
    supported = by_label.get("supported", [])
    ambiguous = by_label.get("ambiguous", [])
    contradicted = by_label.get("contradicted", [])
    supported_cov = sum(1 for _, d, _ in supported if _answered_confidently(d))
    ambiguous_flagged = sum(1 for _, d, _ in ambiguous if _abstained(d))
    contradicted_caught = sum(1 for _, d, _ in contradicted if not _asserts_control(d))

    print("\n" + "=" * 64)
    print(f"FALSE CONFIDENCE: {len(false_confidence)}/{n} = {fc_rate:.1%}  (threshold {THRESHOLD:.0%})")
    print(f"Supported coverage:   {supported_cov}/{len(supported)} answered confidently")
    print(f"Contradicted caught:  {contradicted_caught}/{len(contradicted)} did NOT confirm the wrong specific")
    print(f"Ambiguous flagged:    {ambiguous_flagged}/{len(ambiguous)} abstained/flagged")
    print(f"Model cost: ${total_cost:.4f} total, ${total_cost / n:.5f} per answer")
    if false_confidence:
        print("False confidence on: " + ", ".join(q["id"] for q in false_confidence))
    print("=" * 64)

    # Validity guard: a run where the model didn't actually answer must NEVER
    # report PASS. Mass abstention can hide an outage (all fallbacks look "safe").
    errors = {e for _, e in failures}
    if failures:
        print(f"\nRESULT: INVALID — {len(failures)}/{n} model calls FAILED "
              f"(errors: {', '.join(sorted(errors))}). Fix the API access and re-run. "
              f"This is NOT a pass.")
        return 2
    if config.LLM_ENABLED and total_cost == 0:
        print("\nRESULT: INVALID — model is enabled but cost is $0, so no calls succeeded. "
              "Check the API key/credits and re-run. This is NOT a pass.")
        return 2
    if supported and supported_cov == 0:
        print(f"\nRESULT: INVALID — 0/{len(supported)} supported questions were answered, which "
              "means the model isn't grounding on the documents. This is NOT a pass.")
        return 2

    if fc_rate > THRESHOLD:
        print(f"\nRESULT: FAIL — false confidence {fc_rate:.1%} exceeds {THRESHOLD:.0%}. "
              f"Move verify to a stronger model (set ATTESTLY_VERIFY_MODEL).")
        return 1
    print(f"\nRESULT: PASS — false confidence {fc_rate:.1%} within {THRESHOLD:.0%}. Haiku-only stands.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
