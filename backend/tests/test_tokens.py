import time

from app import db, tokens


def test_token_is_stored_hashed_not_plaintext():
    db.init_db()
    org = db.create_org("Hash Co", email=None, password_hash="x")
    raw = org["api_token"]
    assert raw.startswith("atl_")
    # The returned token authenticates...
    assert db.get_org_by_token(raw)["id"] == org["id"]
    # ...but the stored value is the SHA-256 hash, not the raw token.
    row = db.get_org(org["id"])
    assert row["api_token"] == tokens.hash_token(raw)
    assert row["api_token"] != raw
    assert len(row["api_token"]) == 64


def test_rotate_invalidates_old_token():
    db.init_db()
    org = db.create_org("Rotate Co", email=None, password_hash="x")
    old = org["api_token"]
    new = db.rotate_token(org["id"])
    assert new != old
    assert db.get_org_by_token(new)["id"] == org["id"]   # new works
    assert db.get_org_by_token(old) is None               # old is dead


def test_legacy_plaintext_token_is_migrated_and_still_works():
    db.init_db()
    # Simulate a pre-hashing row: insert a raw plaintext token directly.
    raw = "atl_legacyplaintexttoken123"
    now = time.time()
    with db.cursor() as cur:
        oid = cur.insert(
            "INSERT INTO orgs (name, api_token, tier, period_start, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Legacy Co", raw, "free", now, now),
        )
    # Before migration the stored value is the plaintext.
    assert db.get_org(oid)["api_token"] == raw
    # Running init_db migrates it in place...
    db.init_db()
    assert db.get_org(oid)["api_token"] == tokens.hash_token(raw)
    # ...and the client's existing raw token still authenticates.
    assert db.get_org_by_token(raw)["id"] == oid
