"""Trust-document ingestion: SOC 2 reports, security policies, etc.

Uploaded documents are extracted to plain text, split into overlapping
passages, embedded (when a Voyage key is configured), and stored. At answer
time the most relevant passages are handed to Claude as citable ``document``
blocks, so answers can cite the *exact span* of a SOC 2 report — the strongest
possible "this isn't hallucinated" proof for a reviewing CTO.

Retrieval degrades to a lexical passage match when embeddings are disabled, so
grounding still works offline.
"""
from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass

import datetime as _dt
import time as _time

from . import dates, db, embeddings, fuzzy

# Passage sizing: big enough to carry a full control statement, small enough
# that a citation points at something specific.
CHUNK_CHARS = 900
CHUNK_OVERLAP = 150
# How many document passages to ground each drafted answer in. A fixed global
# top-5 does not scale with the corpus: with one document the right chunk is
# almost always in the window, but with several documents the specific chunk for
# a question gets crowded out, so the model abstains on facts the docs clearly
# state (observed on the Meridian coverage run: "encrypted at rest" grounded with
# 1 doc, abstained with 4). Raised to 8, and paired with a per-document cap below
# so no single verbose document can fill the window.
MAX_GROUND_CHUNKS = int(os.environ.get("ATTESTLY_DOC_TOP_K", "8"))
# Cap on passages taken from any ONE document before the global top-k is applied.
# Guarantees every uploaded document contributes its best passages, so a query's
# supporting chunk is a candidate even when other documents are wordier.
DOC_PER_DOC_CHUNKS = int(os.environ.get("ATTESTLY_DOC_PER_DOC", "3"))


@dataclass
class DocMatch:
    chunk_id: int
    doc_name: str
    text: str
    score: float
    source_date: float | None = None   # epoch of the document's surfaced date
    date_basis: str = ""               # 'stated' | 'file' | ''


def extract_text(filename: str, data: bytes) -> tuple[str, str]:
    """Return (plain_text, kind). Supports PDF and utf-8 text/markdown."""
    name = (filename or "").lower()
    if name.endswith(".pdf") or data[:5] == b"%PDF-":
        return _extract_pdf(data), "pdf"
    return data.decode("utf-8", errors="replace"), "text"


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    return "\n".join(parts)


def _pdf_meta_date(data: bytes) -> float | None:
    """A PDF's own modification/creation date from its metadata, as epoch.

    PDF dates look like ``D:20250314120000Z``. Used as the file date when the
    document doesn't state a review date in its text."""
    try:
        from pypdf import PdfReader

        meta = PdfReader(io.BytesIO(data)).metadata or {}
        for key in ("/ModDate", "/CreationDate"):
            raw = meta.get(key)
            if not raw:
                continue
            m = re.search(r"(\d{4})(\d{2})(\d{2})", str(raw))
            if m:
                y, mo, d = (int(g) for g in m.groups())
                try:
                    return _dt.datetime(y, mo, d, tzinfo=_dt.timezone.utc).timestamp()
                except ValueError:
                    continue
    except Exception:
        pass
    return None


def source_dates(kind: str, data: bytes, text: str) -> dict:
    """Resolve the date we surface for a document. Prefer a review/effective date
    stated in the text; fall back to the file's own date (PDF metadata) or the
    upload time. Returns stored fields for `create_document`."""
    stated = dates.parse_stated_date(text)
    file_date = _pdf_meta_date(data) if kind == "pdf" else None
    if file_date is None:
        file_date = _time.time()  # upload time is the best "file date" we have
    if stated is not None:
        return {"stated_date": stated, "file_date": file_date,
                "source_date": stated, "date_basis": "stated"}
    return {"stated_date": None, "file_date": file_date,
            "source_date": file_date, "date_basis": "file"}


def _normalise(text: str) -> str:
    # Collapse the ragged whitespace PDF extraction produces.
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split into overlapping passages, preferring paragraph boundaries."""
    text = _normalise(text)
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paragraphs:
        if len(buf) + len(p) + 2 <= size:
            buf = f"{buf}\n\n{p}" if buf else p
        else:
            if buf:
                chunks.append(buf)
            # A single oversized paragraph is hard-split with overlap.
            if len(p) > size:
                start = 0
                while start < len(p):
                    chunks.append(p[start : start + size])
                    start += size - overlap
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


def ingest(org_id: int, filename: str, data: bytes) -> dict:
    """Extract, chunk, embed, and store a document. Returns its summary row."""
    text, kind = extract_text(filename, data)
    passages = chunk_text(text)
    if not passages:
        raise ValueError("No extractable text found in the document")

    vectors = embeddings.embed_texts(passages, input_type="document")
    chunks: list[tuple[str, bytes | None]] = []
    for i, passage in enumerate(passages):
        blob = embeddings.to_blob(vectors[i]) if vectors and i < len(vectors) else None
        chunks.append((passage, blob))

    return db.create_document(
        org_id, filename or "document", kind, len(text), chunks,
        dates=source_dates(kind, data, text),
    )


def search(org_id: int, question: str, k: int = MAX_GROUND_CHUNKS,
           query_vec: list[float] | None = None) -> list[DocMatch]:
    """Top document passages relevant to a question (semantic, else lexical).

    Pass ``query_vec`` to reuse an already-computed query embedding."""
    rows = db.list_chunks(org_id)
    if not rows:
        return []
    if query_vec is None:
        query_vec = embeddings.embed_one(question, input_type="query")
    scored: list[tuple[float, dict]] = []
    for r in rows:
        if query_vec:
            vec = embeddings.from_blob(r.get("embedding"))
            score = embeddings.cosine(query_vec, vec) * 100 if vec else 0.0
        else:
            # Lexical fallback: does the question's wording appear in the passage?
            score = fuzzy.partial_ratio(question, r["text"])
        scored.append((score, r))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    # Per-document cap first, so one wordy document can't fill the whole window and
    # crowd out the passage that actually answers the question; then take the
    # global top-k from what each document contributed.
    per_doc = max(1, DOC_PER_DOC_CHUNKS)
    taken_per_doc: dict[str, int] = {}
    candidates: list[tuple[float, dict]] = []
    for score, r in scored:
        if score <= 0:
            continue
        doc = r["doc_name"]
        if taken_per_doc.get(doc, 0) >= per_doc:
            continue
        taken_per_doc[doc] = taken_per_doc.get(doc, 0) + 1
        candidates.append((score, r))
    out: list[DocMatch] = []
    for score, r in candidates[:k]:
        out.append(DocMatch(
            chunk_id=r["id"], doc_name=r["doc_name"], text=r["text"], score=float(score),
            source_date=r.get("doc_source_date"), date_basis=r.get("doc_date_basis") or "",
        ))
    return out
