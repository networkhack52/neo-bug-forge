"""Tests for api.py — request/response contracts and helper logic.

The Anthropic client and Supabase database layer are never called for real;
network-touching paths are either mocked or avoided. These focus on the pure
helpers and FastAPI validation, including a regression test for the code-fence
stripping bug (``str.strip`` treating its argument as a character set).
"""

import json

import anthropic
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

import api
from api import (
    app,
    strip_code_fences,
    build_prompt,
    run_fix,
    verify_api_key,
    FixRequest,
    ReadRequest,
)


# ─── strip_code_fences (regression for the character-set bug) ──────────────────

class TestStripCodeFences:
    def test_plain_text_unchanged(self):
        assert strip_code_fences('{"a": 1}') == '{"a": 1}'

    def test_strips_json_fence(self):
        assert strip_code_fences('```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_strips_bare_fence(self):
        assert strip_code_fences('```\n{"a": 1}\n```') == '{"a": 1}'

    def test_strips_language_fence(self):
        assert strip_code_fences('```python\nprint(1)\n```') == 'print(1)'

    def test_surrounding_whitespace_removed(self):
        assert strip_code_fences('\n\n  {"a": 1}  \n') == '{"a": 1}'

    def test_content_starting_with_json_word_is_not_corrupted(self):
        # The old lstrip("```json") ate leading j/s/o/n chars. This is the bug.
        raw = 'json.loads(x)'
        assert strip_code_fences(raw) == 'json.loads(x)'

    def test_content_starting_with_stripped_letters_preserved(self):
        # 's', 'o', 'n', 'j' are all in the old character set — must survive now.
        assert strip_code_fences('son of a function') == 'son of a function'

    def test_fixed_code_json_survives_round_trip(self):
        payload = {"fixed_code": "json.dumps(obj)", "explanation": "ok"}
        raw = "```json\n" + json.dumps(payload) + "\n```"
        assert json.loads(strip_code_fences(raw)) == payload


# ─── build_prompt ──────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_small_file_requests_unified_diff(self):
        prompt = build_prompt("x = 1", "err", "python")
        assert "unified diff" in prompt

    def test_large_file_omits_diff(self):
        big = "a = 1\n" * 1000  # > 3000 chars
        prompt = build_prompt(big, "err", "python")
        assert "unified diff" not in prompt

    def test_includes_code_and_error(self):
        prompt = build_prompt("MY_CODE_MARKER", "MY_ERROR_MARKER", "go")
        assert "MY_CODE_MARKER" in prompt
        assert "MY_ERROR_MARKER" in prompt

    def test_blank_error_shows_placeholder(self):
        prompt = build_prompt("x = 1", "", "python")
        assert "(none provided)" in prompt

    def test_blank_language_autodetects(self):
        prompt = build_prompt("x = 1", "err", "")
        assert "auto-detect" in prompt


# ─── run_fix (with a fake Anthropic client) ────────────────────────────────────

class _FakeContentBlock:
    def __init__(self, text):
        self.text = text


class _FakeMessage:
    def __init__(self, text):
        self.content = [_FakeContentBlock(text)]


class _FakeMessages:
    def __init__(self, text=None, exc=None):
        self._text = text
        self._exc = exc

    def create(self, **kwargs):
        if self._exc:
            raise self._exc
        return _FakeMessage(self._text)


class _FakeAnthropic:
    def __init__(self, text=None, exc=None, **kwargs):
        self.messages = _FakeMessages(text=text, exc=exc)


def _patch_client(monkeypatch, text=None, exc=None):
    monkeypatch.setattr(
        api.anthropic, "Anthropic",
        lambda **kwargs: _FakeAnthropic(text=text, exc=exc),
    )


VALID_FIX = {
    "fixed_code": "x = 1",
    "explanation": "set x to 1",
    "root_cause": "logic_error",
    "confidence": 90,
    "diff": "- x\n+ x = 1",
    "test_case": "assert x == 1",
}


class TestRunFix:
    def test_parses_valid_fenced_response(self, monkeypatch):
        _patch_client(monkeypatch, text="```json\n" + json.dumps(VALID_FIX) + "\n```")
        result = run_fix("x", "err", "python")
        assert result["fixed_code"] == "x = 1"
        assert result["confidence"] == 90

    def test_non_json_response_raises_value_error(self, monkeypatch):
        _patch_client(monkeypatch, text="I cannot help with that")
        with pytest.raises(ValueError, match="non-JSON"):
            run_fix("x", "err", "python")

    def test_missing_field_raises_value_error(self, monkeypatch):
        incomplete = dict(VALID_FIX)
        del incomplete["test_case"]
        _patch_client(monkeypatch, text=json.dumps(incomplete))
        with pytest.raises(ValueError, match="test_case"):
            run_fix("x", "err", "python")

    def test_rate_limit_maps_to_runtime_error(self, monkeypatch, fake_response):
        exc = anthropic.RateLimitError("slow down", response=fake_response(429), body=None)
        _patch_client(monkeypatch, exc=exc)
        with pytest.raises(RuntimeError, match="rate limit"):
            run_fix("x", "err", "python")

    def test_auth_error_maps_to_value_error(self, monkeypatch, fake_response):
        exc = anthropic.AuthenticationError("bad", response=fake_response(401), body=None)
        _patch_client(monkeypatch, exc=exc)
        with pytest.raises(ValueError, match="invalid"):
            run_fix("x", "err", "python")

    def test_missing_server_key_raises(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        with pytest.raises(ValueError, match="not configured"):
            run_fix("x", "err", "python")


# ─── Pydantic request validation ───────────────────────────────────────────────

class TestRequestValidation:
    def test_fix_request_rejects_blank_code(self):
        with pytest.raises(ValidationError):
            FixRequest(broken_code="   ", error_message="e", language="python")

    def test_fix_request_rejects_empty_code(self):
        with pytest.raises(ValidationError):
            FixRequest(broken_code="", error_message="e", language="python")

    def test_fix_request_accepts_valid_payload(self):
        req = FixRequest(broken_code="x = 1", error_message="e", language="python")
        assert req.broken_code == "x = 1"

    def test_fix_request_enforces_max_length(self):
        with pytest.raises(ValidationError):
            FixRequest(broken_code="a" * 50_001)

    def test_read_request_rejects_blank_code(self):
        with pytest.raises(ValidationError):
            ReadRequest(code="   ")


# ─── verify_api_key format gate ────────────────────────────────────────────────

class TestVerifyApiKey:
    def test_rejects_wrong_prefix(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(x_api_key="sk_1234567890123456789012345")
        assert exc_info.value.status_code == 401

    def test_rejects_too_short_key(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(x_api_key="nbf_short")
        assert exc_info.value.status_code == 401


# ─── Endpoint smoke tests (no external calls) ──────────────────────────────────

class TestEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "timestamp" in body

    def test_root_endpoint_lists_endpoints(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Neo Bug Forge API"

    def test_public_fix_rejects_blank_body(self, client):
        resp = client.post("/v1/fix/public", json={"broken_code": "   "})
        assert resp.status_code == 422

    def test_authenticated_fix_requires_api_key_header(self, client):
        resp = client.post("/v1/fix", json={"broken_code": "x = 1"})
        assert resp.status_code == 422  # missing required X-API-Key header


# ─── /v1/keys — plaintext-storage & rotation security ──────────────────────────
# A minimal fake of the Supabase query builder, recording what create_key writes.

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, store):
        self._store = store
        self._op = None

    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._store["inserted"].append(payload)
        return self

    def update(self, payload):
        self._op = "update"
        self._store["updated"].append(payload)
        return self

    def eq(self, *a, **k):
        return self

    def single(self):
        return self

    def execute(self):
        # Only select's return value is consumed by create_key.
        return _FakeResult(self._store["existing"] if self._op == "select" else None)


class _FakeDB:
    def __init__(self, store):
        self._store = store

    def table(self, _name):
        return _FakeTable(self._store)


class TestCreateKeySecurity:
    """POST /v1/keys must never persist plaintext, and must rotate on repeat."""

    def _patch_db(self, monkeypatch, existing):
        import database
        store = {"existing": existing, "inserted": [], "updated": []}
        monkeypatch.setattr(database, "get_db", lambda: _FakeDB(store))
        return store

    def test_creation_does_not_store_raw_key(self, monkeypatch):
        store = self._patch_db(monkeypatch, existing=[])
        client = TestClient(app)
        resp = client.post("/v1/keys", json={"email": "new@example.com"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["api_key"].startswith("nbf_")
        assert body["message"] == "API key created."
        # The whole point: exactly one insert, and it must NOT carry raw_key.
        assert len(store["inserted"]) == 1
        payload = store["inserted"][0]
        assert "raw_key" not in payload
        assert "key_hash" in payload
        assert payload["key_hash"] != body["api_key"]  # hash stored, not plaintext

    def test_repeat_request_rotates_and_preserves_tier_and_usage(self, monkeypatch):
        from database import hash_key
        old_key = "nbf_oldkey_plaintext"
        existing_row = {
            "id": "row-1", "tier": "pro", "fixes_limit": 500,
            "fixes_used": 42, "key_hash": hash_key(old_key),
        }
        store = self._patch_db(monkeypatch, existing=[existing_row])
        client = TestClient(app)
        resp = client.post("/v1/keys", json={"email": "existing@example.com"})
        assert resp.status_code == 200
        body = resp.json()

        assert body["message"] == "New key generated (previous key revoked)."
        # Tier and usage are carried over unchanged.
        assert body["tier"] == "pro"
        assert body["fixes_limit"] == 500
        assert body["fixes_used"] == 42
        # Rotation = update in place (no new row), and ONLY key_hash changes.
        assert len(store["inserted"]) == 0
        assert len(store["updated"]) == 1
        assert store["updated"][0] == {"key_hash": hash_key(body["api_key"])}
        # The old key can no longer authenticate.
        assert hash_key(body["api_key"]) != hash_key(old_key)


# ─── Cloudflare origin-secret middleware ───────────────────────────────────────

class TestOriginSecret:
    """When ORIGIN_SECRET is set, only requests carrying the matching header
    (i.e. proxied through Cloudflare) are allowed; direct-to-origin is rejected."""

    def _client(self):
        return TestClient(app)

    def test_no_enforcement_when_secret_unset(self, monkeypatch):
        monkeypatch.setattr(api, "ORIGIN_SECRET", "")
        resp = self._client().get("/")
        assert resp.status_code == 200

    def test_missing_header_rejected_when_secret_set(self, monkeypatch):
        monkeypatch.setattr(api, "ORIGIN_SECRET", "s3cret")
        resp = self._client().get("/")
        assert resp.status_code == 403
        assert "Direct origin access" in resp.json()["error"]

    def test_wrong_header_rejected(self, monkeypatch):
        monkeypatch.setattr(api, "ORIGIN_SECRET", "s3cret")
        resp = self._client().get("/", headers={"X-Origin-Secret": "nope"})
        assert resp.status_code == 403

    def test_correct_header_allowed(self, monkeypatch):
        monkeypatch.setattr(api, "ORIGIN_SECRET", "s3cret")
        resp = self._client().get("/", headers={"X-Origin-Secret": "s3cret"})
        assert resp.status_code == 200

    def test_health_exempt_even_without_header(self, monkeypatch):
        # Render's liveness probe hits the origin directly, not via Cloudflare.
        monkeypatch.setattr(api, "ORIGIN_SECRET", "s3cret")
        resp = self._client().get("/health")
        assert resp.status_code == 200
