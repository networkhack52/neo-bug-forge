import uuid

from fastapi.testclient import TestClient

from app import config, ratelimit
from app.main import app

client = TestClient(app)


def test_allow_enforces_limit_and_resets_window(monkeypatch):
    ratelimit.reset()
    # 3 allowed, 4th blocked within the window.
    assert [ratelimit.allow("b", "1.1.1.1", 3, 100) for _ in range(4)] == [True, True, True, False]
    # A different IP has its own bucket.
    assert ratelimit.allow("b", "2.2.2.2", 3, 100) is True
    # Window elapsed -> allowed again.
    t = [1000.0]
    monkeypatch.setattr(ratelimit.time, "time", lambda: t[0])
    ratelimit.reset()
    assert ratelimit.allow("b", "1.1.1.1", 1, 10) is True
    assert ratelimit.allow("b", "1.1.1.1", 1, 10) is False
    t[0] += 11
    assert ratelimit.allow("b", "1.1.1.1", 1, 10) is True


def test_login_endpoint_rate_limited(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(config, "RL_LOGIN", (5, 300))
    ratelimit.reset()
    body = {"email": f"nobody-{uuid.uuid4().hex}@example.com", "password": "whatever"}
    codes = [client.post("/v1/login", json=body).status_code for _ in range(6)]
    # First 5 are normal auth failures (401); the 6th is throttled (429).
    assert codes[:5] == [401, 401, 401, 401, 401]
    assert codes[5] == 429
    ratelimit.reset()


def test_signup_endpoint_rate_limited(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(config, "RL_SIGNUP", (2, 3600))
    ratelimit.reset()
    def _signup():
        return client.post("/v1/signup", json={
            "name": "RL Co", "email": f"rl-{uuid.uuid4().hex}@example.com", "password": "supersecret",
        }).status_code
    assert _signup() == 200
    assert _signup() == 200
    assert _signup() == 429   # 3rd within the hour is blocked
    ratelimit.reset()
