"""End-to-end demo of the Attestly pipeline — no server, no frontend needed.

  python run_demo.py

Steps:
  1. Seed a demo org + load the 36-answer starter bank.
  2. Generate a realistic 20-question vendor questionnaire (.xlsx).
  3. Parse it, auto-answer every question (reuse-from-bank or Claude draft).
  4. Print a per-question report + summary stats.
  5. Export a filled .xlsx and (optionally) approve answers back into the bank.

Runs fully offline: with no ANTHROPIC_API_KEY, unmatched questions use the
flagged fallback drafter, so the whole flow still completes.
"""
from __future__ import annotations

import os
import tempfile

# Use an isolated throwaway DB so repeated demo runs stay clean.
os.environ.setdefault("ATTESTLY_DB_PATH", os.path.join(tempfile.gettempdir(), "attestly_demo.db"))
if os.path.exists(os.environ["ATTESTLY_DB_PATH"]):
    os.remove(os.environ["ATTESTLY_DB_PATH"])

from app import config, db, engine, export  # noqa: E402
from app.make_sample import build as build_sample  # noqa: E402
from app.parsing import parse  # noqa: E402
from app.seed import seed_demo  # noqa: E402


def main() -> None:
    print("\n=== Attestly end-to-end demo ===")
    print(f"LLM drafting: {'ON (Claude)' if config.LLM_ENABLED else 'OFF (offline fallback)'}\n")

    org = seed_demo()
    bank_size = db.count_answers(org["id"])
    print(f"1. Seeded org '{org['name']}' with {bank_size} approved answers in the Answer Library.")

    sample_path = build_sample()
    data = sample_path.read_bytes()
    parsed = parse(sample_path.name, data)
    print(f"2. Parsed '{sample_path.name}': detected {len(parsed.questions)} questions "
          f"(question col {parsed.question_col}).\n")

    qid = db.create_questionnaire(org["id"], sample_path.name, sample_path.name, len(parsed.questions))
    for eq in parsed.questions:
        db.add_item(qid, eq.row_index, eq.question)

    results = engine.answer_questionnaire(org["id"], qid)

    print("3. Auto-answered questions:\n")
    for i, r in enumerate(results, 1):
        flag = "  ⚠ REVIEW" if r.needs_review else ""
        tag = {"reuse": "REUSED ", "drafted": "DRAFTED", "fallback": "FALLBCK"}.get(r.match_type, r.match_type)
        print(f"  {i:2d}. [{tag} {r.confidence:5.1f}%]{flag}  {r.question}")
        snippet = r.answer.replace("\n", " ")
        print(f"      -> {snippet[:110]}{'...' if len(snippet) > 110 else ''}\n")

    reused = sum(1 for r in results if r.match_type == "reuse")
    drafted = sum(1 for r in results if r.match_type == "drafted")
    fallback = sum(1 for r in results if r.match_type == "fallback")
    review = sum(1 for r in results if r.needs_review)
    total = len(results)

    print("4. Summary")
    print(f"   total questions     : {total}")
    print(f"   reused from bank    : {reused}  ({reused/total*100:.0f}%)  <- instant, $0 API cost")
    print(f"   drafted by Claude   : {drafted}")
    print(f"   offline fallback    : {fallback}")
    print(f"   flagged for review  : {review}")

    items = db.list_items(qid)
    out = export.export_simple(sample_path.name, items)
    out_path = sample_path.parent / "sample_questionnaire_ANSWERED.xlsx"
    out_path.write_bytes(out)
    print(f"\n5. Exported filled questionnaire -> {out_path}")

    # Show the compounding effect: approve everything back into the bank.
    for it in items:
        db.approve_item(it["id"], it["answer"])
        if it["match_type"] != "reuse":
            from app.main import retrieval_close
            if not any(retrieval_close(it["question"], b["question"]) for b in db.list_answers(org["id"])):
                db.add_answer(org["id"], it["question"], it["answer"], source="questionnaire")
    print(f"   Answer Library grew from {bank_size} -> {db.count_answers(org['id'])} "
          f"(next questionnaire reuses more, costs less).")
    print("\n=== demo complete ===\n")


if __name__ == "__main__":
    main()
