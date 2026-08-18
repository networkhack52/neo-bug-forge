"""SQLite persistence layer.

Uses the stdlib ``sqlite3`` module (no ORM) so the codebase runs with zero
extra dependencies. In production the same schema maps cleanly onto the
existing Supabase/Postgres instance; swap ``connect()`` for a psycopg pool.
"""
from __future__ import annotations

import re
import sqlite3
import time
from contextlib import contextmanager
from typing import Iterator, Optional

from . import config, tokens

# When True, storage is Postgres (via DATABASE_URL); otherwise local SQLite.
PG = config.USE_POSTGRES

SCHEMA = """
CREATE TABLE IF NOT EXISTS orgs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT,
    password_hash TEXT,
    api_token     TEXT NOT NULL UNIQUE,
    tier          TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id TEXT,
    period_start  REAL NOT NULL,
    questions_used INTEGER NOT NULL DEFAULT 0,
    created_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS answers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id       INTEGER NOT NULL REFERENCES orgs(id),
    question     TEXT NOT NULL,
    answer       TEXT NOT NULL,
    category     TEXT DEFAULT 'general',
    source       TEXT DEFAULT 'manual',
    status       TEXT NOT NULL DEFAULT 'approved',   -- approved | draft
    times_reused INTEGER NOT NULL DEFAULT 0,
    embedding    BLOB,                                -- float32 question vector (optional)
    change_log   TEXT DEFAULT '[]',                   -- JSON list of {date, note, from, to} when the answer changed (T2)
    created_at   REAL NOT NULL,
    updated_at   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_answers_org ON answers(org_id, status);

CREATE TABLE IF NOT EXISTS questionnaires (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id       INTEGER NOT NULL REFERENCES orgs(id),
    name         TEXT NOT NULL,
    source_filename TEXT,
    status       TEXT NOT NULL DEFAULT 'processing', -- processing | ready | exported
    total_questions INTEGER NOT NULL DEFAULT 0,
    answered_questions INTEGER NOT NULL DEFAULT 0,
    source_bytes BLOB,                    -- original upload, for write-back export
    source_kind  TEXT DEFAULT 'xlsx',     -- xlsx | csv
    sheet_name   TEXT,                     -- worksheet the questions were read from
    question_col INTEGER,                  -- 1-based column layout captured at parse time
    answer_col   INTEGER,
    detail_col   INTEGER,
    framework    TEXT DEFAULT '',           -- detected format: SIG | SIG Lite | CAIQ | CAIQ Lite | VSAQ | Custom
    created_at   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_q_org ON questionnaires(org_id);

CREATE TABLE IF NOT EXISTS questionnaire_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    questionnaire_id INTEGER NOT NULL REFERENCES questionnaires(id),
    row_index       INTEGER NOT NULL,
    excel_row       INTEGER NOT NULL DEFAULT 0, -- 1-based source row, for write-back
    question        TEXT NOT NULL,
    answer          TEXT DEFAULT '',
    confidence      REAL DEFAULT 0,
    match_type      TEXT DEFAULT 'none',   -- reuse | drafted | fallback | none
    matched_answer_id INTEGER,
    needs_review    INTEGER NOT NULL DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'pending', -- pending | approved
    choice          TEXT DEFAULT '',       -- Yes | No | Partially | Not Applicable | ''
    citations       TEXT DEFAULT '[]',     -- JSON list of source questions the model cited
    verification    TEXT DEFAULT 'skipped',-- supported | unsupported | skipped
    locked          INTEGER NOT NULL DEFAULT 0, -- 1 = over quota, not answered
    excluded        INTEGER NOT NULL DEFAULT 0, -- 1 = out of scope, exported as N/A (triage)
    exclusion_reason TEXT DEFAULT '',       -- why it was excluded (also the N/A justification)
    remediation_date TEXT DEFAULT '',       -- for a 'No': planned fix date (YYYY-MM-DD)
    no_plan         INTEGER NOT NULL DEFAULT 0, -- for a 'No': user acknowledged there is no plan
    na_reason       TEXT DEFAULT '',        -- one-line justification for a user-set Not Applicable
    contradiction   TEXT DEFAULT '',        -- JSON: prior library answer this differs from (T2), '' when none
    created_at      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS domain_allowances (
    domain          TEXT PRIMARY KEY,          -- normalised email domain
    onboarding_used INTEGER NOT NULL DEFAULT 0,-- answers drawn from the 150 pool
    created_at      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id              INTEGER NOT NULL,
    questionnaire_id    INTEGER,
    item_id             INTEGER,
    model               TEXT,
    input_tokens        INTEGER NOT NULL DEFAULT 0,
    cached_input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens       INTEGER NOT NULL DEFAULT 0,
    cost_usd            REAL NOT NULL DEFAULT 0,
    created_at          REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_org ON usage_events(org_id);
CREATE INDEX IF NOT EXISTS idx_usage_qid ON usage_events(questionnaire_id);
CREATE INDEX IF NOT EXISTS idx_items_q ON questionnaire_items(questionnaire_id);

CREATE TABLE IF NOT EXISTS password_resets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id      INTEGER NOT NULL REFERENCES orgs(id),
    token_hash  TEXT NOT NULL,             -- SHA-256 of the raw reset token
    expires_at  REAL NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0,
    created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_resets_hash ON password_resets(token_hash);

CREATE TABLE IF NOT EXISTS documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id       INTEGER NOT NULL REFERENCES orgs(id),
    name         TEXT NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'pdf',   -- pdf | text
    char_count   INTEGER NOT NULL DEFAULT 0,
    chunk_count  INTEGER NOT NULL DEFAULT 0,
    stated_date  REAL,                          -- review/effective date parsed from the text (epoch)
    file_date    REAL,                          -- upload/file date (epoch)
    source_date  REAL,                          -- the date we actually surface (stated if parsed, else file)
    date_basis   TEXT DEFAULT '',               -- 'stated' | 'file' — which one source_date came from
    created_at   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_docs_org ON documents(org_id);

CREATE TABLE IF NOT EXISTS document_chunks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  INTEGER NOT NULL REFERENCES documents(id),
    org_id       INTEGER NOT NULL REFERENCES orgs(id),
    ordinal      INTEGER NOT NULL,
    text         TEXT NOT NULL,
    embedding    BLOB,
    created_at   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_org ON document_chunks(org_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);
"""

# Columns added after v1 — applied idempotently for existing databases.
_MIGRATIONS = {
    "questionnaire_items": {
        "choice": "TEXT DEFAULT ''",
        "citations": "TEXT DEFAULT '[]'",
        "verification": "TEXT DEFAULT 'skipped'",
        "excel_row": "INTEGER NOT NULL DEFAULT 0",
        "locked": "INTEGER NOT NULL DEFAULT 0",
        "excluded": "INTEGER NOT NULL DEFAULT 0",
        "exclusion_reason": "TEXT DEFAULT ''",
        "remediation_date": "TEXT DEFAULT ''",
        "no_plan": "INTEGER NOT NULL DEFAULT 0",
        "na_reason": "TEXT DEFAULT ''",
        "contradiction": "TEXT DEFAULT ''",
    },
    "questionnaires": {
        "source_bytes": "BLOB",
        "source_kind": "TEXT DEFAULT 'xlsx'",
        "sheet_name": "TEXT",
        "question_col": "INTEGER",
        "answer_col": "INTEGER",
        "detail_col": "INTEGER",
        "framework": "TEXT DEFAULT ''",
    },
    "documents": {
        "stated_date": "REAL",
        "file_date": "REAL",
        "source_date": "REAL",
        "date_basis": "TEXT DEFAULT ''",
    },
    "answers": {
        "embedding": "BLOB",
        "change_log": "TEXT DEFAULT '[]'",
    },
    "orgs": {
        "password_hash": "TEXT",
    },
}


def _pg_connect():
    import psycopg
    from psycopg.rows import dict_row

    kwargs = {"row_factory": dict_row}
    # Enforce TLS to the database unless the URL already sets an sslmode.
    if "sslmode" not in config.DATABASE_URL:
        kwargs["sslmode"] = "require"
    return psycopg.connect(config.DATABASE_URL, **kwargs)


def connect():
    if PG:
        return _pg_connect()
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


class _Cursor:
    """Thin wrapper so the same SQL (with ? placeholders) runs on SQLite or PG.

    Translates ? -> %s for Postgres and exposes ``insert()`` which returns the new
    row id on both backends (RETURNING id on PG, lastrowid on SQLite).
    """

    def __init__(self, raw):
        self._raw = raw

    @staticmethod
    def _sql(sql: str) -> str:
        return sql.replace("?", "%s") if PG else sql

    def execute(self, sql: str, params=()):
        self._raw.execute(self._sql(sql), params)
        return self

    def executemany(self, sql: str, seq):
        self._raw.executemany(self._sql(sql), seq)
        return self

    def insert(self, sql: str, params=()) -> int:
        if PG:
            self._raw.execute(self._sql(sql) + " RETURNING id", params)
            return int(self._raw.fetchone()["id"])
        self._raw.execute(sql, params)
        return int(self._raw.lastrowid)

    def fetchone(self):
        return self._raw.fetchone()

    def fetchall(self):
        return self._raw.fetchall()


@contextmanager
def cursor() -> Iterator[_Cursor]:
    conn = connect()
    try:
        cur = conn.cursor()
        yield _Cursor(cur)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# SQLite -> Postgres DDL: identity columns, byte and float types.
def _to_pg_ddl(sql: str) -> str:
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
    sql = re.sub(r"\bBLOB\b", "BYTEA", sql)
    sql = re.sub(r"\bREAL\b", "DOUBLE PRECISION", sql)
    return sql


def init_db() -> None:
    conn = connect()
    try:
        if PG:
            with conn.cursor() as cur:
                for stmt in _to_pg_ddl(SCHEMA).split(";"):
                    if stmt.strip():
                        cur.execute(stmt)
                # Postgres supports ADD COLUMN IF NOT EXISTS — idempotent migrations.
                for table, columns in _MIGRATIONS.items():
                    for name, decl in columns.items():
                        cur.execute(
                            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {_to_pg_ddl(decl)}"
                        )
            conn.commit()
        else:
            conn.executescript(SCHEMA)
            for table, columns in _MIGRATIONS.items():
                existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
                for name, decl in columns.items():
                    if name not in existing:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
            conn.commit()
    finally:
        conn.close()
    _migrate_plaintext_tokens()


def _migrate_plaintext_tokens() -> None:
    """One-time, idempotent: hash any legacy plaintext API tokens in place.

    Old rows stored the raw token; hashing the stored value means a client's
    existing token still authenticates (its SHA-256 now matches). Hashes are 64
    hex chars, raw tokens ~36, so the length filter makes this a safe no-op on
    already-migrated databases. A hiccup here must never stop the app booting."""
    try:
        with cursor() as cur:
            rows = cur.execute("SELECT id, api_token FROM orgs WHERE length(api_token) < 60").fetchall()
            for r in rows:
                cur.execute(
                    "UPDATE orgs SET api_token = ? WHERE id = ?",
                    (tokens.hash_token(r["api_token"]), r["id"]),
                )
    except Exception:
        pass  # non-fatal: worst case, affected clients just log in again


# --------------------------------------------------------------------------
# Orgs
# --------------------------------------------------------------------------
def create_org(name: str, email: Optional[str] = None, tier: str = config.DEFAULT_TIER,
               password_hash: Optional[str] = None) -> dict:
    raw_token = tokens.new_token()
    now = time.time()
    with cursor() as cur:
        org_id = cur.insert(
            "INSERT INTO orgs (name, email, password_hash, api_token, tier, period_start, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, email, password_hash, tokens.hash_token(raw_token), tier, now, now),
        )
    org = get_org(org_id)  # stored value is the hash
    org["api_token"] = raw_token  # return the usable token once; only its hash is persisted
    return org  # type: ignore[return-value]


def rotate_token(org_id: int) -> str:
    """Issue a fresh token (invalidating the old one). Returns the raw token once."""
    raw_token = tokens.new_token()
    with cursor() as cur:
        cur.execute("UPDATE orgs SET api_token = ? WHERE id = ?", (tokens.hash_token(raw_token), org_id))
    return raw_token


def get_org(org_id: int) -> Optional[dict]:
    with cursor() as cur:
        row = cur.execute("SELECT * FROM orgs WHERE id = ?", (org_id,)).fetchone()
    return dict(row) if row else None


def get_org_by_token(token: str) -> Optional[dict]:
    with cursor() as cur:
        row = cur.execute(
            "SELECT * FROM orgs WHERE api_token = ?", (tokens.hash_token(token),)
        ).fetchone()
    return dict(row) if row else None


def get_org_by_email(email: str) -> Optional[dict]:
    with cursor() as cur:
        row = cur.execute(
            "SELECT * FROM orgs WHERE email = ? ORDER BY id LIMIT 1", (email.strip().lower(),)
        ).fetchone()
    return dict(row) if row else None


def set_org_tier(org_id: int, tier: str, stripe_customer_id: Optional[str] = None) -> None:
    with cursor() as cur:
        if stripe_customer_id:
            cur.execute(
                "UPDATE orgs SET tier = ?, stripe_customer_id = ? WHERE id = ?",
                (tier, stripe_customer_id, org_id),
            )
        else:
            cur.execute("UPDATE orgs SET tier = ? WHERE id = ?", (tier, org_id))


def set_org_password(org_id: int, password_hash: str) -> None:
    with cursor() as cur:
        cur.execute("UPDATE orgs SET password_hash = ? WHERE id = ?", (password_hash, org_id))


# --------------------------------------------------------------------------
# Password resets
# --------------------------------------------------------------------------
def create_password_reset(org_id: int, token_hash: str, expires_at: float) -> int:
    """Store a single-use reset token (hash only) and invalidate any prior ones
    for this org, so at most one live reset link exists per account."""
    now = time.time()
    with cursor() as cur:
        cur.execute("UPDATE password_resets SET used = 1 WHERE org_id = ? AND used = 0", (org_id,))
        return cur.insert(
            "INSERT INTO password_resets (org_id, token_hash, expires_at, used, created_at) "
            "VALUES (?, ?, ?, 0, ?)",
            (org_id, token_hash, expires_at, now),
        )


def get_valid_password_reset(token_hash: str) -> Optional[dict]:
    """Return the reset row if it exists, is unused, and hasn't expired."""
    with cursor() as cur:
        row = cur.execute(
            "SELECT * FROM password_resets WHERE token_hash = ? AND used = 0 AND expires_at > ? "
            "ORDER BY id DESC LIMIT 1",
            (token_hash, time.time()),
        ).fetchone()
    return dict(row) if row else None


def consume_password_reset(reset_id: int) -> None:
    with cursor() as cur:
        cur.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (reset_id,))


def roll_period_if_needed(org: dict) -> dict:
    """Reset the 30-day metering window if it has elapsed."""
    if time.time() - org["period_start"] >= 30 * 86400:
        with cursor() as cur:
            cur.execute(
                "UPDATE orgs SET period_start = ?, questions_used = 0 WHERE id = ?",
                (time.time(), org["id"]),
            )
        return get_org(org["id"])  # type: ignore[return-value]
    return org


def increment_usage(org_id: int, n: int) -> None:
    with cursor() as cur:
        cur.execute(
            "UPDATE orgs SET questions_used = questions_used + ? WHERE id = ?",
            (n, org_id),
        )


def email_domain(email: Optional[str]) -> str:
    """Normalised domain part of an email, or '' if not parseable."""
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[1].strip().lower()


def domain_onboarding_used(domain: str) -> int:
    """Answers already drawn from a domain's one-time onboarding pool."""
    if not domain:
        return 0
    with cursor() as cur:
        row = cur.execute(
            "SELECT onboarding_used FROM domain_allowances WHERE domain = ?", (domain,)
        ).fetchone()
    return int(dict(row)["onboarding_used"]) if row else 0


def consume_domain_onboarding(domain: str, n: int) -> None:
    """Draw n answers from a domain's onboarding pool (upsert, additive)."""
    if not domain or n <= 0:
        return
    now = time.time()
    with cursor() as cur:
        if PG:
            cur.execute(
                "INSERT INTO domain_allowances (domain, onboarding_used, created_at) "
                "VALUES (?, ?, ?) ON CONFLICT (domain) DO UPDATE SET "
                "onboarding_used = domain_allowances.onboarding_used + ?",
                (domain, n, now, n),
            )
        else:
            cur.execute(
                "INSERT INTO domain_allowances (domain, onboarding_used, created_at) "
                "VALUES (?, ?, ?) ON CONFLICT (domain) DO UPDATE SET "
                "onboarding_used = onboarding_used + ?",
                (domain, n, now, n),
            )


def lock_items(item_ids: list[int]) -> None:
    """Mark items as locked (over quota, not answered)."""
    if not item_ids:
        return
    with cursor() as cur:
        for iid in item_ids:
            cur.execute("UPDATE questionnaire_items SET locked = 1 WHERE id = ?", (iid,))


def record_usage(org_id: int, questionnaire_id: Optional[int], item_id: Optional[int],
                 usage: dict, cost: float) -> None:
    """Log token usage + computed cost for one drafted answer."""
    with cursor() as cur:
        cur.execute(
            "INSERT INTO usage_events (org_id, questionnaire_id, item_id, model, input_tokens, "
            "cached_input_tokens, output_tokens, cost_usd, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (org_id, questionnaire_id, item_id, usage.get("model", ""),
             int(usage.get("input_tokens", 0)), int(usage.get("cached_input_tokens", 0)),
             int(usage.get("output_tokens", 0)), float(cost), time.time()),
        )


_COST_COLS = (
    "COUNT(*) AS answers, COALESCE(SUM(input_tokens),0) AS input_tokens, "
    "COALESCE(SUM(cached_input_tokens),0) AS cached_input_tokens, "
    "COALESCE(SUM(output_tokens),0) AS output_tokens, "
    "COALESCE(SUM(cost_usd),0) AS cost_usd"
)


def cost_summary(org_id: int) -> dict:
    with cursor() as cur:
        row = cur.execute(
            f"SELECT {_COST_COLS} FROM usage_events WHERE org_id = ?", (org_id,)
        ).fetchone()
    return dict(row)


def cost_for_questionnaire(questionnaire_id: int) -> dict:
    with cursor() as cur:
        row = cur.execute(
            f"SELECT {_COST_COLS} FROM usage_events WHERE questionnaire_id = ?", (questionnaire_id,)
        ).fetchone()
    return dict(row)


def free_tier_spend_since(since_epoch: float) -> float:
    """Total model spend by free-tier orgs since a timestamp (for the spend cap)."""
    with cursor() as cur:
        row = cur.execute(
            "SELECT COALESCE(SUM(u.cost_usd),0) AS c FROM usage_events u "
            "JOIN orgs o ON o.id = u.org_id "
            "WHERE o.tier = 'free' AND u.created_at >= ?",
            (since_epoch,),
        ).fetchone()
    return float(dict(row)["c"])


# --------------------------------------------------------------------------
# Answer Bank
# --------------------------------------------------------------------------
def add_answer(
    org_id: int,
    question: str,
    answer: str,
    category: str = "general",
    source: str = "manual",
    status: str = "approved",
) -> dict:
    now = time.time()
    # Best-effort semantic vector for the question (None when embeddings are off).
    from . import embeddings

    vec = embeddings.embed_one(question.strip(), input_type="document")
    blob = embeddings.to_blob(vec) if vec else None
    with cursor() as cur:
        aid = cur.insert(
            "INSERT INTO answers (org_id, question, answer, category, source, status, "
            "embedding, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (org_id, question.strip(), answer.strip(), category, source, status, blob, now, now),
        )
        row = cur.execute("SELECT * FROM answers WHERE id = ?", (aid,)).fetchone()
    return dict(row)


def set_answer_embedding(answer_id: int, blob: bytes) -> None:
    with cursor() as cur:
        cur.execute("UPDATE answers SET embedding = ? WHERE id = ?", (blob, answer_id))


def answers_missing_embeddings(org_id: int, limit: int = 200) -> list[dict]:
    with cursor() as cur:
        rows = cur.execute(
            "SELECT id, question FROM answers WHERE org_id = ? AND embedding IS NULL LIMIT ?",
            (org_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def set_chunk_embedding(chunk_id: int, blob: bytes) -> None:
    with cursor() as cur:
        cur.execute("UPDATE document_chunks SET embedding = ? WHERE id = ?", (blob, chunk_id))


def rows_missing_embeddings(table: str, text_col: str) -> list[dict]:
    """All rows (across orgs) in ``table`` whose embedding is NULL.

    ``table``/``text_col`` are code-controlled constants — never user input."""
    assert table in ("answers", "document_chunks")
    assert text_col in ("question", "text")
    with cursor() as cur:
        rows = cur.execute(
            f"SELECT id, {text_col} AS text FROM {table} WHERE embedding IS NULL ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def set_embeddings_batch(table: str, pairs: list) -> None:
    """Bulk-write (id, blob) embedding pairs in one transaction."""
    assert table in ("answers", "document_chunks")
    if not pairs:
        return
    with cursor() as cur:
        cur.executemany(
            f"UPDATE {table} SET embedding = ? WHERE id = ?",
            [(blob, row_id) for row_id, blob in pairs],
        )


def list_answers(org_id: int, status: str = "approved") -> list[dict]:
    with cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM answers WHERE org_id = ? AND status = ? ORDER BY updated_at DESC",
            (org_id, status),
        ).fetchall()
    return [dict(r) for r in rows]


def count_answers(org_id: int, status: str = "approved") -> int:
    with cursor() as cur:
        row = cur.execute(
            "SELECT COUNT(*) AS c FROM answers WHERE org_id = ? AND status = ?",
            (org_id, status),
        ).fetchone()
    return int(row["c"])


def bump_reuse(answer_id: int) -> None:
    with cursor() as cur:
        cur.execute(
            "UPDATE answers SET times_reused = times_reused + 1, updated_at = ? WHERE id = ?",
            (time.time(), answer_id),
        )


# --------------------------------------------------------------------------
# Questionnaires + items
# --------------------------------------------------------------------------
def create_questionnaire(
    org_id: int,
    name: str,
    source_filename: str,
    total: int,
    source_bytes: Optional[bytes] = None,
    source_kind: str = "xlsx",
    sheet_name: Optional[str] = None,
    question_col: Optional[int] = None,
    answer_col: Optional[int] = None,
    detail_col: Optional[int] = None,
) -> int:
    with cursor() as cur:
        return cur.insert(
            "INSERT INTO questionnaires (org_id, name, source_filename, total_questions, "
            "source_bytes, source_kind, sheet_name, question_col, answer_col, detail_col, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (org_id, name, source_filename, total, source_bytes, source_kind, sheet_name,
             question_col, answer_col, detail_col, time.time()),
        )


def add_item(questionnaire_id: int, row_index: int, question: str, excel_row: int = 0) -> int:
    with cursor() as cur:
        return cur.insert(
            "INSERT INTO questionnaire_items (questionnaire_id, row_index, excel_row, question, "
            "created_at) VALUES (?, ?, ?, ?, ?)",
            (questionnaire_id, row_index, excel_row, question.strip(), time.time()),
        )


def update_item(
    item_id: int,
    answer: str,
    confidence: float,
    match_type: str,
    matched_answer_id: Optional[int],
    needs_review: bool,
    choice: str = "",
    citations: Optional[list] = None,
    verification: str = "skipped",
) -> None:
    import json as _json

    with cursor() as cur:
        cur.execute(
            "UPDATE questionnaire_items SET answer = ?, confidence = ?, match_type = ?, "
            "matched_answer_id = ?, needs_review = ?, choice = ?, citations = ?, "
            "verification = ? WHERE id = ?",
            (answer, confidence, match_type, matched_answer_id, int(needs_review),
             choice, _json.dumps(citations or []), verification, item_id),
        )


def get_questionnaire(qid: int, org_id: int) -> Optional[dict]:
    with cursor() as cur:
        row = cur.execute(
            "SELECT * FROM questionnaires WHERE id = ? AND org_id = ?", (qid, org_id)
        ).fetchone()
    return dict(row) if row else None


def list_questionnaires(org_id: int) -> list[dict]:
    with cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM questionnaires WHERE org_id = ? ORDER BY created_at DESC", (org_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def list_items(questionnaire_id: int) -> list[dict]:
    with cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM questionnaire_items WHERE questionnaire_id = ? ORDER BY row_index",
            (questionnaire_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_item(item_id: int) -> Optional[dict]:
    with cursor() as cur:
        row = cur.execute("SELECT * FROM questionnaire_items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def approve_item(item_id: int, answer: str) -> None:
    with cursor() as cur:
        cur.execute(
            "UPDATE questionnaire_items SET answer = ?, status = 'approved', needs_review = 0 WHERE id = ?",
            (answer, item_id),
        )


def set_questionnaire_status(qid: int, status: str) -> None:
    with cursor() as cur:
        cur.execute("UPDATE questionnaires SET status = ? WHERE id = ?", (status, qid))


def set_answered_count(qid: int, n: int) -> None:
    with cursor() as cur:
        cur.execute("UPDATE questionnaires SET answered_questions = ? WHERE id = ?", (n, qid))


# --------------------------------------------------------------------------
# Trust documents (SOC 2, policies) + chunks
# --------------------------------------------------------------------------
def create_document(org_id: int, name: str, kind: str, char_count: int,
                    chunks: list[tuple[str, Optional[bytes]]],
                    dates: Optional[dict] = None) -> dict:
    """Insert a document and its (text, embedding) chunks in one transaction.

    ``dates`` carries the resolved source date fields (see documents.source_dates)."""
    now = time.time()
    d = dates or {}
    with cursor() as cur:
        doc_id = cur.insert(
            "INSERT INTO documents (org_id, name, kind, char_count, chunk_count, "
            "stated_date, file_date, source_date, date_basis, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (org_id, name, kind, char_count, len(chunks),
             d.get("stated_date"), d.get("file_date"), d.get("source_date"),
             d.get("date_basis", ""), now),
        )
        for ordinal, (text, blob) in enumerate(chunks):
            cur.execute(
                "INSERT INTO document_chunks (document_id, org_id, ordinal, text, embedding, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (doc_id, org_id, ordinal, text, blob, now),
            )
        row = cur.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return dict(row)


def list_documents(org_id: int) -> list[dict]:
    with cursor() as cur:
        rows = cur.execute(
            "SELECT id, name, kind, char_count, chunk_count, stated_date, file_date, "
            "source_date, date_basis, created_at FROM documents "
            "WHERE org_id = ? ORDER BY created_at DESC",
            (org_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def count_documents(org_id: int) -> int:
    with cursor() as cur:
        row = cur.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE org_id = ?", (org_id,)
        ).fetchone()
    return int(dict(row)["n"]) if row else 0


def list_chunks(org_id: int) -> list[dict]:
    """All chunks for an org, with their document name — for grounding search."""
    with cursor() as cur:
        rows = cur.execute(
            "SELECT c.id, c.text, c.embedding, c.ordinal, d.name AS doc_name, "
            "d.source_date AS doc_source_date, d.date_basis AS doc_date_basis "
            "FROM document_chunks c JOIN documents d ON d.id = c.document_id "
            "WHERE c.org_id = ?",
            (org_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_document(org_id: int, doc_id: int) -> bool:
    with cursor() as cur:
        owned = cur.execute(
            "SELECT 1 FROM documents WHERE id = ? AND org_id = ?", (doc_id, org_id)
        ).fetchone()
        if not owned:
            return False
        cur.execute("DELETE FROM document_chunks WHERE document_id = ? AND org_id = ?", (doc_id, org_id))
        cur.execute("DELETE FROM documents WHERE id = ? AND org_id = ?", (doc_id, org_id))
    return True
