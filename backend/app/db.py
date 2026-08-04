"""SQLite persistence layer.

Uses the stdlib ``sqlite3`` module (no ORM) so the codebase runs with zero
extra dependencies. In production the same schema maps cleanly onto the
existing Supabase/Postgres instance; swap ``connect()`` for a psycopg pool.
"""
from __future__ import annotations

import secrets
import sqlite3
import time
from contextlib import contextmanager
from typing import Iterator, Optional

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS orgs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT,
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
    created_at      REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_q ON questionnaire_items(questionnaire_id);

CREATE TABLE IF NOT EXISTS documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id       INTEGER NOT NULL REFERENCES orgs(id),
    name         TEXT NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'pdf',   -- pdf | text
    char_count   INTEGER NOT NULL DEFAULT 0,
    chunk_count  INTEGER NOT NULL DEFAULT 0,
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
    },
    "questionnaires": {
        "source_bytes": "BLOB",
        "source_kind": "TEXT DEFAULT 'xlsx'",
        "sheet_name": "TEXT",
        "question_col": "INTEGER",
        "answer_col": "INTEGER",
        "detail_col": "INTEGER",
    },
    "answers": {
        "embedding": "BLOB",
    },
}


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def cursor() -> Iterator[sqlite3.Cursor]:
    conn = connect()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        # Idempotent column migrations for pre-existing databases.
        for table, columns in _MIGRATIONS.items():
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            for name, decl in columns.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Orgs
# --------------------------------------------------------------------------
def create_org(name: str, email: Optional[str] = None, tier: str = config.DEFAULT_TIER) -> dict:
    token = "atl_" + secrets.token_urlsafe(24)
    now = time.time()
    with cursor() as cur:
        cur.execute(
            "INSERT INTO orgs (name, email, api_token, tier, period_start, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, token, tier, now, now),
        )
        org_id = cur.lastrowid
    return get_org(org_id)  # type: ignore[return-value]


def get_org(org_id: int) -> Optional[dict]:
    with cursor() as cur:
        row = cur.execute("SELECT * FROM orgs WHERE id = ?", (org_id,)).fetchone()
    return dict(row) if row else None


def get_org_by_token(token: str) -> Optional[dict]:
    with cursor() as cur:
        row = cur.execute("SELECT * FROM orgs WHERE api_token = ?", (token,)).fetchone()
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
        cur.execute(
            "INSERT INTO answers (org_id, question, answer, category, source, status, "
            "embedding, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (org_id, question.strip(), answer.strip(), category, source, status, blob, now, now),
        )
        aid = cur.lastrowid
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
        cur.execute(
            "INSERT INTO questionnaires (org_id, name, source_filename, total_questions, "
            "source_bytes, source_kind, sheet_name, question_col, answer_col, detail_col, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (org_id, name, source_filename, total, source_bytes, source_kind, sheet_name,
             question_col, answer_col, detail_col, time.time()),
        )
        return int(cur.lastrowid)


def add_item(questionnaire_id: int, row_index: int, question: str, excel_row: int = 0) -> int:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO questionnaire_items (questionnaire_id, row_index, excel_row, question, "
            "created_at) VALUES (?, ?, ?, ?, ?)",
            (questionnaire_id, row_index, excel_row, question.strip(), time.time()),
        )
        return int(cur.lastrowid)


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
                    chunks: list[tuple[str, Optional[bytes]]]) -> dict:
    """Insert a document and its (text, embedding) chunks in one transaction."""
    now = time.time()
    with cursor() as cur:
        cur.execute(
            "INSERT INTO documents (org_id, name, kind, char_count, chunk_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (org_id, name, kind, char_count, len(chunks), now),
        )
        doc_id = int(cur.lastrowid)
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
            "SELECT id, name, kind, char_count, chunk_count, created_at FROM documents "
            "WHERE org_id = ? ORDER BY created_at DESC",
            (org_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_chunks(org_id: int) -> list[dict]:
    """All chunks for an org, with their document name — for grounding search."""
    with cursor() as cur:
        rows = cur.execute(
            "SELECT c.id, c.text, c.embedding, c.ordinal, d.name AS doc_name "
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
