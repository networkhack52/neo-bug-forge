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

from . import db, embeddings, fuzzy

# Passage sizing: big enough to carry a full control statement, small enough
# that a citation points at something specific.
CHUNK_CHARS = 900
CHUNK_OVERLAP = 150
MAX_GROUND_CHUNKS = int(os.environ.get("ATTESTLY_DOC_TOP_K", "3"))


@dataclass
class DocMatch:
    chunk_id: int
    doc_name: str
    text: str
    score: float


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

    return db.create_document(org_id, filename or "document", kind, len(text), chunks)


def search(org_id: int, question: str, k: int = MAX_GROUND_CHUNKS) -> list[DocMatch]:
    """Top document passages relevant to a question (semantic, else lexical)."""
    rows = db.list_chunks(org_id)
    if not rows:
        return []
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
    out: list[DocMatch] = []
    for score, r in scored[:k]:
        if score <= 0:
            continue
        out.append(DocMatch(chunk_id=r["id"], doc_name=r["doc_name"], text=r["text"], score=float(score)))
    return out
