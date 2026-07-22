"""Unit tests for bug_fixer.py — the pure, deterministic core logic.

These cover the parts most likely to break silently and hardest to notice in
production: parsing untrusted LLM output, language detection, cost math,
history persistence, and the retry/backoff wrapper.
"""

import json
import time

import anthropic
import pytest

import bug_fixer
from bug_fixer import (
    parse_response,
    detect_language,
    calculate_cost,
    load_history,
    save_to_history,
    call_with_retry,
    PRICING,
    MODEL,
    MAX_HISTORY,
)


# ─── parse_response ────────────────────────────────────────────────────────────

class TestParseResponse:
    def test_plain_json(self):
        raw = '{"fixed_code": "x = 1", "explanation": "set x"}'
        result = parse_response(raw)
        assert result["fixed_code"] == "x = 1"
        assert result["explanation"] == "set x"

    def test_json_with_surrounding_whitespace(self):
        raw = '\n\n  {"fixed_code": "a", "explanation": "b"}  \n'
        assert parse_response(raw)["fixed_code"] == "a"

    def test_markdown_fenced_json(self):
        raw = '```json\n{"fixed_code": "a", "explanation": "b"}\n```'
        assert parse_response(raw)["explanation"] == "b"

    def test_bare_triple_backtick_fence(self):
        raw = '```\n{"fixed_code": "a", "explanation": "b"}\n```'
        assert parse_response(raw)["fixed_code"] == "a"

    def test_fence_without_closing_backticks(self):
        # Exercises the `end = len(lines)` branch (no trailing ``` line).
        raw = '```json\n{"fixed_code": "a", "explanation": "b"}'
        assert parse_response(raw)["fixed_code"] == "a"

    def test_prose_wrapped_json_uses_regex_fallback(self):
        raw = 'Sure! Here is your fix:\n{"fixed_code": "a", "explanation": "b"}\nHope that helps.'
        assert parse_response(raw)["explanation"] == "b"

    def test_malformed_json_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_response("this is not json at all")

    def test_broken_json_object_raises_value_error(self):
        # Looks like an object to the regex but is not valid JSON.
        with pytest.raises(ValueError):
            parse_response('{"fixed_code": "a", "explanation": }')

    def test_missing_fixed_code_key_raises(self):
        with pytest.raises(ValueError, match="fixed_code"):
            parse_response('{"explanation": "b"}')

    def test_missing_explanation_key_raises(self):
        with pytest.raises(ValueError, match="explanation"):
            parse_response('{"fixed_code": "a"}')


# ─── detect_language ───────────────────────────────────────────────────────────

class TestDetectLanguage:
    def test_hint_alias_expands_shorthand(self):
        assert detect_language("anything", hint="py") == "Python"
        assert detect_language("anything", hint="js") == "JavaScript"
        assert detect_language("anything", hint="ts") == "TypeScript"

    def test_hint_alias_is_case_insensitive(self):
        assert detect_language("anything", hint="PY") == "Python"

    def test_unknown_hint_is_capitalized(self):
        assert detect_language("anything", hint="elixir") == "Elixir"

    def test_detects_python_from_signatures(self):
        code = "def foo():\n    import os\n    print('hi')\n    self.x = None"
        assert detect_language(code) == "Python"

    def test_detects_javascript_from_signatures(self):
        code = "function f() { console.log('x'); const y = () => undefined; }"
        assert detect_language(code) == "JavaScript"

    def test_unrecognized_code_returns_unknown(self):
        assert detect_language("!!!@@@###") == "Unknown"

    def test_empty_code_returns_unknown(self):
        assert detect_language("") == "Unknown"


# ─── calculate_cost ────────────────────────────────────────────────────────────

class TestCalculateCost:
    def test_known_model_sonnet(self):
        # 1M input @ $3 + 1M output @ $15 = $18
        cost = calculate_cost(1_000_000, 1_000_000, "claude-sonnet-4-20250514")
        assert cost == pytest.approx(18.0)

    def test_haiku_pricing(self):
        cost = calculate_cost(1_000_000, 0, "claude-haiku-4-5-20251001")
        assert cost == pytest.approx(0.80)

    def test_zero_tokens_is_zero(self):
        assert calculate_cost(0, 0, "claude-sonnet-4-20250514") == 0.0

    def test_unknown_model_falls_back_to_sonnet_pricing(self):
        unknown = calculate_cost(1_000_000, 1_000_000, "made-up-model")
        sonnet = calculate_cost(1_000_000, 1_000_000, "claude-sonnet-4-20250514")
        assert unknown == sonnet

    def test_result_is_rounded_to_six_places(self):
        cost = calculate_cost(1, 1, "claude-sonnet-4-20250514")
        assert cost == round(cost, 6)


# ─── load_history / save_to_history ────────────────────────────────────────────

class TestHistory:
    @pytest.fixture(autouse=True)
    def isolate_history_file(self, tmp_path, monkeypatch):
        # Redirect the module-level HISTORY_FILE to a temp path per test.
        monkeypatch.setattr(bug_fixer, "HISTORY_FILE", tmp_path / "history.json")

    def test_load_missing_file_returns_empty_list(self):
        assert load_history() == []

    def test_load_corrupt_file_returns_empty_list(self):
        bug_fixer.HISTORY_FILE.write_text("{not valid json", encoding="utf-8")
        assert load_history() == []

    def test_save_then_load_roundtrip(self):
        entry = {"timestamp": "t", "language": "Python", "success": True}
        save_to_history(entry)
        loaded = load_history()
        assert loaded == [entry]

    def test_history_is_capped_at_max_history(self):
        for i in range(MAX_HISTORY + 5):
            save_to_history({"i": i})
        loaded = load_history()
        assert len(loaded) == MAX_HISTORY
        # Only the most recent MAX_HISTORY entries are kept.
        assert loaded[0]["i"] == 5
        assert loaded[-1]["i"] == MAX_HISTORY + 4


# ─── call_with_retry ───────────────────────────────────────────────────────────

class _FakeMessages:
    def __init__(self, behaviors):
        # behaviors: list of either an exception instance (raised) or a value (returned)
        self._behaviors = list(behaviors)
        self.calls = 0

    def create(self, **kwargs):
        behavior = self._behaviors[self.calls]
        self.calls += 1
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


class _FakeClient:
    def __init__(self, behaviors):
        self.messages = _FakeMessages(behaviors)


class TestCallWithRetry:
    @pytest.fixture(autouse=True)
    def no_sleep(self, monkeypatch):
        # Keep the exponential backoff from actually sleeping.
        monkeypatch.setattr(time, "sleep", lambda _s: None)

    def _rate_limit(self, fake_response):
        return anthropic.RateLimitError("rate limited", response=fake_response(429), body=None)

    def test_returns_message_on_first_success(self):
        sentinel = object()
        client = _FakeClient([sentinel])
        assert call_with_retry(client, "prompt") is sentinel
        assert client.messages.calls == 1

    def test_retries_then_succeeds(self, fake_response):
        sentinel = object()
        client = _FakeClient([self._rate_limit(fake_response), sentinel])
        assert call_with_retry(client, "prompt") is sentinel
        assert client.messages.calls == 2

    def test_raises_after_exhausting_retries(self, fake_response):
        errors = [self._rate_limit(fake_response) for _ in range(3)]
        client = _FakeClient(errors)
        with pytest.raises(anthropic.RateLimitError):
            call_with_retry(client, "prompt", max_retries=3)
        assert client.messages.calls == 3

    def test_authentication_error_maps_to_runtime_error_without_retry(self, fake_response):
        err = anthropic.AuthenticationError("bad key", response=fake_response(401), body=None)
        client = _FakeClient([err])
        with pytest.raises(RuntimeError, match="Authentication failed"):
            call_with_retry(client, "prompt")
        assert client.messages.calls == 1  # not retried

    def test_connection_error_maps_to_runtime_error(self):
        request = anthropic.APIConnectionError(
            request=__import__("httpx").Request("POST", "https://api.anthropic.com")
        )
        client = _FakeClient([request])
        with pytest.raises(RuntimeError, match="Could not reach"):
            call_with_retry(client, "prompt")
