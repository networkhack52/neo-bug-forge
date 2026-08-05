"""Semantic embeddings for retrieval — Voyage AI, stored as SQLite BLOBs.

Deliberately *not* a vector database. Security-questionnaire banks are small
(hundreds to low-thousands of entries per org), so brute-force cosine over
float32 blobs in SQLite is instant and adds no infrastructure — the app still
installs clean on Windows with no services to run.

Everything is gated by ``config.EMBEDDINGS_ENABLED``: with no Voyage key the
embedding calls are skipped and callers fall back to the lexical matcher, so
the whole pipeline still runs offline.
"""
from __future__ import annotations

import array
import math

import httpx

from . import config

# Voyage returns 1024-dim vectors for voyage-3.5-lite; we don't hardcode the
# dimension — blobs are self-describing (len(bytes) / 4 floats).
_FLOAT = "f"  # 4-byte float32


def to_blob(vec: list[float]) -> bytes:
    return array.array(_FLOAT, vec).tobytes()


def from_blob(blob) -> list[float]:
    if not blob:
        return []
    # Postgres (psycopg) may hand back a memoryview for BYTEA; normalise to bytes.
    if not isinstance(blob, (bytes, bytearray)):
        blob = bytes(blob)
    a = array.array(_FLOAT)
    a.frombytes(blob)
    return list(a)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embed_texts(texts: list[str], input_type: str | None = None) -> list[list[float]] | None:
    """Embed a batch. Returns None (never raises) when disabled or on failure.

    ``input_type`` lets Voyage optimise asymmetric search: pass "document" for
    stored answers/chunks and "query" for the incoming question.
    """
    if not config.EMBEDDINGS_ENABLED or not texts:
        return None
    payload: dict = {"model": config.VOYAGE_MODEL, "input": texts}
    if input_type:
        payload["input_type"] = input_type
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{config.VOYAGE_BASE_URL}/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {config.VOYAGE_API_KEY}",
                    "content-type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
        # Preserve input order (Voyage returns an "index" per item).
        ordered = sorted(data, key=lambda d: d.get("index", 0))
        return [d.get("embedding", []) for d in ordered]
    except Exception:
        return None


def embed_one(text: str, input_type: str | None = None) -> list[float]:
    out = embed_texts([text], input_type=input_type)
    return out[0] if out else []
