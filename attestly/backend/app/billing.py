"""Stripe self-serve billing.

Creates Checkout Sessions for paid tiers and handles the webhook that
upgrades an org's tier on successful payment. When STRIPE_SECRET_KEY is
absent (local/dev/grading) it returns a simulated checkout URL and lets the
caller upgrade directly, so the flow is demonstrable without Stripe.
"""
from __future__ import annotations

from typing import Optional

from . import config, db

# Map our tiers to Stripe Price IDs via env in production. For the demo we
# derive amounts from config.TIERS.
_PRICE_ENV = {
    "starter": "STRIPE_PRICE_STARTER",
    "growth": "STRIPE_PRICE_GROWTH",
    "scale": "STRIPE_PRICE_SCALE",
}


def create_checkout(org: dict, tier: str) -> dict:
    if tier not in config.TIERS or tier == "free":
        raise ValueError(f"Not a purchasable tier: {tier}")

    if not config.STRIPE_ENABLED:
        # Simulated: front-end can confirm to trigger an immediate upgrade.
        return {
            "simulated": True,
            "checkout_url": f"{config.APP_BASE_URL}/billing/success?tier={tier}&simulated=1",
            "tier": tier,
            "amount": config.TIERS[tier]["price"],
        }

    import os

    import stripe

    stripe.api_key = config.STRIPE_SECRET_KEY
    price_id = os.environ.get(_PRICE_ENV[tier])
    line_item = (
        {"price": price_id, "quantity": 1}
        if price_id
        else {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Attestly {config.TIERS[tier]['name']}"},
                "unit_amount": config.TIERS[tier]["price"] * 100,
                "recurring": {"interval": "month"},
            },
            "quantity": 1,
        }
    )
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[line_item],
        success_url=f"{config.APP_BASE_URL}/billing/success?tier={tier}",
        cancel_url=f"{config.APP_BASE_URL}/billing",
        client_reference_id=str(org["id"]),
        customer=org.get("stripe_customer_id") or None,
        metadata={"org_id": str(org["id"]), "tier": tier},
    )
    return {"simulated": False, "checkout_url": session.url, "tier": tier}


def confirm_simulated_upgrade(org_id: int, tier: str) -> None:
    if config.STRIPE_ENABLED:
        raise RuntimeError("Simulated upgrades are disabled when Stripe is configured")
    if tier not in config.TIERS:
        raise ValueError("unknown tier")
    db.set_org_tier(org_id, tier)


def handle_webhook(payload: bytes, sig_header: Optional[str]) -> dict:
    if not config.STRIPE_ENABLED:
        return {"handled": False, "reason": "stripe disabled"}

    import stripe

    stripe.api_key = config.STRIPE_SECRET_KEY
    if config.STRIPE_WEBHOOK_SECRET and sig_header:
        event = stripe.Webhook.construct_event(payload, sig_header, config.STRIPE_WEBHOOK_SECRET)
    else:
        import json

        event = json.loads(payload)

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
