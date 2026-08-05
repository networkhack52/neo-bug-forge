"""One-shot: embed every answer/document passage that has no vector yet.

Run this once after you first set ``VOYAGE_API_KEY`` so your *existing* Answer
Library and trust documents become semantically searchable — new entries embed
automatically on write, this catches everything created before the key existed.

    python -m app.backfill_embeddings

Safe to re-run: it only touches rows whose embedding is still NULL. Does nothing
(and says so) when no Voyage key is configured.
"""
from __future__ import annotations

from . import config, db, embeddings

BATCH = 100  # Voyage accepts batches; 100 keeps each request comfortably small.

_TABLES = [
    ("answers", "question", "answers"),
    ("document_chunks", "text", "document passages"),
]


def backfill() -> int:
    """Embed all NULL-embedding rows. Returns the number of rows updated."""
    db.init_db()
    if not config.EMBEDDINGS_ENABLED:
        print("VOYAGE_API_KEY is not set — nothing to embed. Set it and re-run.")
        return 0

    total = 0
    for table, text_col, label in _TABLES:
        rows = db.rows_missing_embeddings(table, text_col)
        if not rows:
            print(f"{label}: up to date (nothing to backfill).")
            continue
        print(f"{label}: embedding {len(rows)} row(s)…")
        updates: list = []
        for start in range(0, len(rows), BATCH):
            chunk = rows[start : start + BATCH]
            vecs = embeddings.embed_texts([r["text"] for r in chunk], input_type="document")
            if not vecs:
                print("  embedding request failed — stopping (already-done rows are saved).")
                break
            for r, v in zip(chunk, vecs):
                updates.append((r["id"], embeddings.to_blob(v)))
            print(f"  {min(start + BATCH, len(rows))}/{len(rows)}")
        db.set_embeddings_batch(table, updates)
        total += len(updates)

    print(f"Done. Backfilled {total} embedding(s).")
    return total


if __name__ == "__main__":
    backfill()
