import hashlib
import hmac
import time

import pytest

from app import billing, config, db

FORGED = '{"type":"checkout.session.completed","data":{"object":{"metadata":{"org_id":"%d","tier":"scale"}}}}'


def _org():
    db.init_db()
    return db.create_org("Webhook Co", email=None, password_hash="x")


def _stripe_sig(payload: bytes, secret: str, t: int | None = None) -> str:
    """Build a valid Stripe-Signature header (t=<ts>,v1=<hmac>)."""
    t = t or int(time.time())
    signed = f"{t}.".encode() + payload
    mac = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={t},v1={mac}"


def test_disabled_stripe_ignores_forged_event(monkeypatch):
    # Dev/default: Stripe off -> webhook is a no-op, never upgrades.
    monkeypatch.setattr(config, "STRIPE_ENABLED", False)
    org = _org()
    res = billing.handle_webhook((FORGED % org["id"]).encode(), None)
    assert res["handled"] is False
    assert db.get_org(org["id"])["tier"] == "free"


def test_enabled_stripe_rejects_unsigned_forgery(monkeypatch):
    # The core fix: an unsigned forged event must NOT upgrade the org.
    monkeypatch.setattr(config, "STRIPE_ENABLED", True)
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    org = _org()
    with pytest.raises(billing.WebhookError):
        billing.handle_webhook((FORGED % org["id"]).encode(), None)
    assert db.get_org(org["id"])["tier"] == "free"


def test_enabled_stripe_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(config, "STRIPE_ENABLED", True)
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "sk_test_x")
    org = _org()
    with pytest.raises(billing.WebhookError):
        billing.handle_webhook((FORGED % org["id"]).encode(), "t=123,v1=deadbeef")
    assert db.get_org(org["id"])["tier"] == "free"


def test_enabled_stripe_refuses_when_secret_missing(monkeypatch):
    monkeypatch.setattr(config, "STRIPE_ENABLED", True)
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "")
    org = _org()
    with pytest.raises(billing.WebhookError):
        billing.handle_webhook((FORGED % org["id"]).encode(), "t=123,v1=deadbeef")
    assert db.get_org(org["id"])["tier"] == "free"


def test_enabled_stripe_accepts_valid_signature(monkeypatch):
    # A properly signed event still works (we didn't break real webhooks).
    secret = "whsec_test"
    monkeypatch.setattr(config, "STRIPE_ENABLED", True)
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", secret)
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "sk_test_x")
    org = _org()
    payload = ('{"type":"checkout.session.completed","data":{"object":'
               '{"metadata":{"org_id":"%d","tier":"growth"}}}}' % org["id"]).encode()
    res = billing.handle_webhook(payload, _stripe_sig(payload, secret))
    assert res["handled"] is True
    assert db.get_org(org["id"])["tier"] == "growth"
