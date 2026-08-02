"""Seed a demo org and load the starter Answer Bank.

Run:  python -m app.seed
Prints the demo org's API token.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config, db

STARTER = Path(__file__).resolve().parent.parent / "sample_data" / "starter_answer_bank.json"


def seed_demo(name: str = "Acme SaaS (demo)", tier: str = "growth") -> dict:
    db.init_db()
    org = db.create_org(name=name, email="demo@example.com", tier=tier)
    load_starter_bank(org["id"])
    return org


def load_starter_bank(org_id: int) -> int:
    entries = json.loads(STARTER.read_text(encoding="utf-8"))
    n = 0
    for e in entries:
        db.add_answer(org_id, e["question"], e["answer"], e.get("category", "general"), source="starter")
        n += 1
    return n


if __name__ == "__main__":
    org = seed_demo()
    size = db.count_answers(org["id"])
    print("=" * 60)
    print("Attestly demo org created")
    print(f"  org_id     : {org['id']}")
    print(f"  name       : {org['name']}")
    print(f"  tier       : {org['tier']}")
    print(f"  API token  : {org['api_token']}")
    print(f"  Answer Bank: {size} approved answers loaded")
    print(f"  LLM enabled: {config.LLM_ENABLED}  (drafting uses Claude when a key is set)")
    print("=" * 60)
