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

from . import config
from .drafting import CHOICES, NO_EVIDENCE, draft_answer, usage_cost

EVAL_DIR = Path(__file__).resolve().parent.parent / "eval"
DOCS = EVAL_DIR / "attestly_eval_docs.md"
QUESTIONS = EVAL_DIR / "eval_questions.json"
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


def _asserts_control(d) -> bool:
    """The model confidently claims the control exists (the dangerous case)."""
    return d.choice == "Yes" and not d.needs_review and d.answer != NO_EVIDENCE


def _answered_confidently(d) -> bool:
    return not d.needs_review and d.answer != NO_EVIDENCE and d.choice in CHOICES


def run() -> int:
    if not config.LLM_ENABLED:
        print("ANTHROPIC_API_KEY is not set — the eval needs the live model. Aborting.")
        return 2

    docs = _chunks()
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    by_label = {"supported": [], "unsupported": [], "ambiguous": []}

    total_cost = 0.0
    false_confidence = []  # unsupported questions we asserted anyway
    print(f"Running {len(questions)} questions against {len(docs)} passages "
          f"(draft={config.ANTHROPIC_MODEL}, verify={config.VERIFY_MODEL})\n")

    for q in questions:
        d = draft_answer(q["question"], [], docs)
        total_cost += usage_cost(d.usage)
        stance = "assert" if _asserts_control(d) else ("answer" if _answered_confidently(d) else "abstain")
        by_label[q["label"]].append((q, d, stance))
        if q["label"] == "unsupported" and _asserts_control(d):
            false_confidence.append(q)
        flag = "  <-- FALSE CONFIDENCE" if (q["label"] == "unsupported" and _asserts_control(d)) else ""
        print(f"  [{q['label'][:5]:5}] {q['id']}  {stance:7}  {q['question'][:60]}{flag}")

    n = len(questions)
    fc_rate = len(false_confidence) / n
    supported_cov = sum(1 for _, d, _ in by_label["supported"] if _answered_confidently(d))
    ambiguous_flagged = sum(1 for _, d, s in by_label["ambiguous"] if s == "abstain")

    print("\n" + "=" * 60)
    print(f"FALSE CONFIDENCE: {len(false_confidence)}/{n} = {fc_rate:.1%}  "
          f"(threshold {THRESHOLD:.0%})")
    print(f"Supported coverage: {supported_cov}/{len(by_label['supported'])} answered confidently")
    print(f"Ambiguous flagged:  {ambiguous_flagged}/{len(by_label['ambiguous'])} abstained/flagged")
    print(f"Model cost: ${total_cost:.4f} total, ${total_cost / n:.5f} per answer")
    if false_confidence:
        print("Asserted despite no support: " + ", ".join(q["id"] for q in false_confidence))
    print("=" * 60)

    if fc_rate > THRESHOLD:
        print(f"\nRESULT: FAIL — false confidence {fc_rate:.1%} exceeds {THRESHOLD:.0%}. "
              f"Move verify to a stronger model (set ATTESTLY_VERIFY_MODEL).")
        return 1
    print(f"\nRESULT: PASS — false confidence {fc_rate:.1%} within {THRESHOLD:.0%}. Haiku-only stands.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
