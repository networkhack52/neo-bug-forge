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


def test_usage_cost_uses_model_price():
    # 1M input @ $1 + 1M output @ $5 = $6.00 for haiku.
    usage = {"input_tokens": 1_000_000, "cached_input_tokens": 0,
             "output_tokens": 1_000_000, "model": "claude-haiku-4-5-20251001"}
    assert drafting.usage_cost(usage) == 6.0
    # Cached input is billed at the discounted rate.
    cached = {"input_tokens": 0, "cached_input_tokens": 1_000_000,
              "output_tokens": 0, "model": "claude-haiku-4-5-20251001"}
    assert drafting.usage_cost(cached) == 0.10


def test_verify_model_is_configurable():
    from app import config
    assert config.VERIFY_MODEL  # own config value, defaults to the draft model


def test_prompt_cache_shapes_system_field(monkeypatch):
    from app import config
    monkeypatch.setattr(config, "PROMPT_CACHE_ENABLED", False)
    assert drafting._system("hi") == "hi"  # plain string when off (default)
    monkeypatch.setattr(config, "PROMPT_CACHE_ENABLED", True)
    blocks = drafting._system("hi")
    assert blocks == [{"type": "text", "text": "hi", "cache_control": {"type": "ephemeral"}}]


def test_offline_draft_no_context_refuses():
    d = drafting.draft_answer("What is your annual revenue?", [])
    assert d.needs_review is True
    assert d.answer == drafting.NO_EVIDENCE


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
