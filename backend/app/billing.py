"""Stripe self-serve billing.

Creates Checkout Sessions for paid tiers and handles the webhook that
upgrades an org's tier on successful payment. When STRIPE_SECRET_KEY is
absent (local/dev/grading) it returns a simulated checkout URL and lets the
caller upgrade directly, so the flow is demonstrable without Stripe.
"""
from __future__ import annotations

from typing import Optional

from . import config, db


class WebhookError(Exception):
    """A Stripe webhook could not be trusted (missing/invalid signature or misconfig).

    Raised so the caller returns 400 and NEVER acts on an unverified event."""

# Map (tier, interval) to Stripe Price IDs via env in production. For the demo
# we derive amounts from config.TIERS.
_PRICE_ENV = {
    ("starter", "month"): "STRIPE_PRICE_STARTER",
    ("growth", "month"): "STRIPE_PRICE_GROWTH",
    ("scale", "month"): "STRIPE_PRICE_SCALE",
    ("starter", "year"): "STRIPE_PRICE_STARTER_YEARLY",
    ("growth", "year"): "STRIPE_PRICE_GROWTH_YEARLY",
    ("scale", "year"): "STRIPE_PRICE_SCALE_YEARLY",
}


def _amount(tier: str, interval: str) -> int:
    """Dollar amount charged per billing period for a tier/interval."""
    t = config.TIERS[tier]
    return t["yearly_price"] if interval == "year" else t["price"]


def create_checkout(org: dict, tier: str, interval: str = "month") -> dict:
    if tier not in config.TIERS or tier == "free":
        raise ValueError(f"Not a purchasable tier: {tier}")
    if interval not in ("month", "year"):
        raise ValueError(f"Not a valid billing interval: {interval}")

    if not config.STRIPE_ENABLED:
        # Simulated: front-end can confirm to trigger an immediate upgrade.
        return {
            "simulated": True,
            "checkout_url": f"{config.APP_BASE_URL}/billing/success?tier={tier}&interval={interval}&simulated=1",
            "tier": tier,
            "interval": interval,
            "amount": _amount(tier, interval),
        }

    import os

    import stripe

    stripe.api_key = config.STRIPE_SECRET_KEY
    price_id = os.environ.get(_PRICE_ENV[(tier, interval)])
    label = config.TIERS[tier]["name"] + (" (annual)" if interval == "year" else "")
    line_item = (
        {"price": price_id, "quantity": 1}
        if price_id
        else {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Attestly {label}"},
                "unit_amount": _amount(tier, interval) * 100,
                "recurring": {"interval": interval},
            },
            "quantity": 1,
        }
    )
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[line_item],
        success_url=f"{config.APP_BASE_URL}/billing/success?tier={tier}&interval={interval}",
        cancel_url=f"{config.APP_BASE_URL}/billing",
        client_reference_id=str(org["id"]),
        customer=org.get("stripe_customer_id") or None,
        metadata={"org_id": str(org["id"]), "tier": tier, "interval": interval},
    )
    return {"simulated": False, "checkout_url": session.url, "tier": tier, "interval": interval}


def confirm_simulated_upgrade(org_id: int, tier: str) -> None:
    if config.STRIPE_ENABLED:
        raise RuntimeError("Simulated upgrades are disabled when Stripe is configured")
    if tier not in config.TIERS:
        raise ValueError("unknown tier")
    db.set_org_tier(org_id, tier)


def handle_webhook(payload: bytes, sig_header: Optional[str]) -> dict:
    if not config.STRIPE_ENABLED:
        return {"handled": False, "reason": "stripe disabled"}

    # Fail closed: a webhook that upgrades billing tiers must be cryptographically
    # verified. Without a configured secret or a valid signature we reject it —
    # never parse an unverified payload, or anyone could POST a fake
    # "checkout.session.completed" and upgrade an org for free.
    if not config.STRIPE_WEBHOOK_SECRET:
        raise WebhookError("Webhook secret not configured — refusing to process unverified event")
    if not sig_header:
        raise WebhookError("Missing Stripe-Signature header")

    import stripe

    stripe.api_key = config.STRIPE_SECRET_KEY
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, config.STRIPE_WEBHOOK_SECRET)
    except Exception as exc:  # bad payload or bad signature -> reject, act on nothing
        raise WebhookError(f"Signature verification failed: {type(exc).__name__}") from exc

    etype = event.get("type") if isinstance(event, dict) else event["type"]
    obj = (event.get("data", {}) if isinstance(event, dict) else event["data"]).get("object", {})

    if etype == "checkout.session.completed":
        meta = obj.get("metadata") or {}
        org_id = meta.get("org_id") or obj.get("client_reference_id")
        tier = meta.get("tier")
        customer_id = obj.get("customer")
        if org_id and tier:
            db.set_org_tier(int(org_id), tier, stripe_customer_id=customer_id)
            return {"handled": True, "org_id": int(org_id), "tier": tier}

    if etype in ("customer.subscription.deleted",):
        # Downgrade to free on cancellation.
        customer_id = obj.get("customer")
        return {"handled": True, "note": "subscription cancelled", "customer": customer_id}

    return {"handled": False, "type": etype}
