"""
database.py - Supabase helpers for Neo Bug Forge API
"""

import os
import hashlib
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def get_db() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase credentials are not configured.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def lookup_api_key(api_key: str) -> dict | None:
    try:
        db = get_db()
        result = (
            db.table("api_keys")
            .select("*")
            .eq("key_hash", hash_key(api_key))
            .eq("is_active", True)
            .single()
            .execute()
        )
        return result.data
    except Exception as e:
        print(f"[DB ERROR] lookup_api_key failed: {e}")
        return None


def check_and_increment_quota(key_id: str, tier: str, fixes_limit: int) -> tuple[bool, int]:
    if tier == "team":
        return True, 999999
    db = get_db()
    row = (
        db.table("api_keys")
        .select("fixes_used")
        .eq("id", key_id)
        .single()
        .execute()
        .data
    )
    if not row:
        return False, 0
    fixes_used = row["fixes_used"]
    if fixes_used >= fixes_limit:
        return False, 0
    db.table("api_keys").update({
        "fixes_used":   fixes_used + 1,
        "last_used_at": "now()",
    }).eq("id", key_id).execute()
    return True, fixes_limit - (fixes_used + 1)


def save_fix(fix_id: str, key_id: str | None, body: dict, result: dict, tokens: int):
    db = get_db()
    db.table("fixes").insert({
        "fix_id":      fix_id,
        "key_id":      key_id,
        "language":    body.get("language") or "auto",
        "confidence":  result.get("confidence"),
        "tokens_used": tokens,
        "broken_code": body.get("broken_code"),
        "fixed_code":  result.get("fixed_code"),
        "explanation": result.get("explanation"),
        "root_cause":  result.get("root_cause"),
        "diff":        result.get("diff"),
        "test_case":   result.get("test_case"),
    }).execute()
    if key_id:
        row = (
            db.table("api_keys")
            .select("tokens_used")
            .eq("id", key_id)
            .single()
            .execute()
            .data
        )
        if row:
            db.table("api_keys").update({
                "tokens_used": row["tokens_used"] + tokens
            }).eq("id", key_id).execute()


def get_fix_by_id(fix_id: str) -> dict | None:
    try:
        db = get_db()
        result = (
            db.table("fixes")
            .select("*")
            .eq("fix_id", fix_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None
