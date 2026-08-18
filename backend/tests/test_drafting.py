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


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeClient:
    """Captures the request payloads and returns canned draft+verify responses."""

    def __init__(self, sent, responses):
        self._sent = sent
        self._responses = responses

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, headers=None, json=None):
        self._sent.append(json)
        return _FakeResp(self._responses[min(len(self._sent) - 1, len(self._responses) - 1)])


def _capture_llm(monkeypatch):
    """Run draft_answer against a fake Anthropic that records every request."""
    import datetime as dt

    from app import config, documents

    monkeypatch.setattr(config, "LLM_ENABLED", True)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    sent = []
    draft_json = {"content": [{"type": "text", "text":
        '{"choice":"Yes","answer":"We encrypt customer data at rest.","confidence":85,'
        '"needs_review":false,"citations":[{"source":"Old_Security_Policy.pdf",'
        '"quote":"data is encrypted at rest with AES-256"}]}'}], "usage": {}}
    verify_json = {"content": [{"type": "text",
        "text": '{"supported": true, "unsupported_claims": []}'}], "usage": {}}
    monkeypatch.setattr(drafting.httpx, "Client",
                        lambda *a, **k: _FakeClient(sent, [draft_json, verify_json]))

    old = dt.datetime(2019, 1, 1, tzinfo=dt.timezone.utc).timestamp()  # deliberately stale
    doc = documents.DocMatch(chunk_id=1, doc_name="Old_Security_Policy.pdf",
                             text="Our data is encrypted at rest with AES-256.", score=90.0,
                             source_date=old, date_basis="stated")
    d = drafting.draft_answer("Is data encrypted at rest?", [], [doc])
    return d, sent


def test_draft_and_verify_are_temperature_zero(monkeypatch):
    d, sent = _capture_llm(monkeypatch)
    assert len(sent) == 2                       # draft + verify
    assert sent[0]["temperature"] == 0          # deterministic drafting
    assert sent[1]["temperature"] == 0          # deterministic verify


def test_source_freshness_never_reaches_the_model(monkeypatch):
    """The design invariant: a document's date/staleness is information for the
    reader, never an input to the support decision. It must not appear in the
    draft OR verify request the model sees."""
    d, sent = _capture_llm(monkeypatch)
    import json as _json

    draft_body = _json.dumps(sent[0]).lower()
    verify_body = _json.dumps(sent[1]).lower()
    for body in (draft_body, verify_body):
        assert "2019" not in body               # the source date
        assert "stale" not in body
        assert "date_basis" not in body
        assert "reviewed" not in body

    # But freshness IS computed and attached for the reader/export.
    cite = d.citations[0]
    assert cite["date"] == "2019-01-01"
    assert cite["stale"] is True


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
