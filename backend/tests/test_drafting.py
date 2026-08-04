from app import db, drafting
from app.retrieval import Match


def _ctx(score=80.0):
    return [Match(answer_id=1, question="Do you encrypt data at rest?",
                  answer="Yes, AES-256.", category="encryption", score=score)]


def test_offline_draft_is_flagged_and_uncited():
    # No ANTHROPIC_API_KEY in tests -> deterministic fallback.
    d = drafting.draft_answer("Is data encrypted at rest?", _ctx(85))
    assert d.match_type == "fallback"
    assert d.needs_review is True
    assert d.citations == []
    assert d.verification == "skipped"
    # The nearest answer starts with "Yes" -> compliance status is inferred.
    assert d.choice == "Yes"


def test_choice_helpers_map_to_enum():
    assert drafting.normalize_choice("compliant") == "Yes"
    assert drafting.normalize_choice("non-compliant") == "No"
    assert drafting.normalize_choice("Partial") == "Partially"
    assert drafting.normalize_choice("n/a") == "Not Applicable"
    assert drafting.normalize_choice("maybe") == ""
    assert drafting.infer_choice("No, we do not sell data.") == "No"
    assert drafting.infer_choice("Not applicable — we don't process cards.") == "Not Applicable"
    assert drafting.infer_choice("It depends.") == ""


def test_offline_draft_no_context_refuses():
    d = drafting.draft_answer("What is your annual revenue?", [])
    assert d.needs_review is True
    assert "No approved answer" in d.answer


def test_hardened_prompt_has_grounding_and_injection_rules():
    p = drafting.SYSTEM_PROMPT.lower()
    assert "only from the provided context" in p
    assert "never invent" in p
    assert "untrusted data" in p          # prompt-injection defense
    assert "confidence rubric" in p


def test_migration_is_idempotent_and_persists_citations():
    db.init_db()
    db.init_db()  # second call must not error (columns already added)
    org = db.create_org("Trust Co")
    qid = db.create_questionnaire(org["id"], "q", "q.xlsx", 1)
    item_id = db.add_item(qid, 0, "Do you encrypt data at rest?")
    db.update_item(item_id, answer="Yes.", confidence=92, match_type="drafted",
                   matched_answer_id=None, needs_review=False,
                   citations=["Do you encrypt data at rest?"], verification="supported")
    row = db.get_item(item_id)
    assert row["citations"] == '["Do you encrypt data at rest?"]'
    assert row["verification"] == "supported"
