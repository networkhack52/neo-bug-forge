from app import db, documents, drafting


def test_extract_text_detects_kind():
    text, kind = documents.extract_text("policy.txt", b"We encrypt all data at rest with AES-256.")
    assert kind == "text"
    assert "AES-256" in text


def test_chunk_text_splits_large_input():
    para = "This is a control statement. " * 60  # ~1740 chars
    chunks = documents.chunk_text(para, size=500, overlap=100)
    assert len(chunks) >= 3
    assert all(len(c) <= 600 for c in chunks)


def test_ingest_and_lexical_search(monkeypatch):
    # Embeddings disabled -> search falls back to lexical passage matching.
    db.init_db()
    org = db.create_org("Doc Co")
    body = (
        "Access Control Policy\n\n"
        "All employees must use multi-factor authentication to access production systems.\n\n"
        "Data Retention\n\n"
        "Audit logs are retained for 400 days in an immutable store.\n"
    ).encode()
    doc = documents.ingest(org["id"], "security_policy.txt", body)
    assert doc["chunk_count"] >= 1

    hits = documents.search(org["id"], "How long are audit logs kept?")
    assert hits, "expected a lexical passage match"
    assert any("retained for 400 days" in h.text for h in hits)
    assert hits[0].doc_name == "security_policy.txt"


def test_delete_document_is_scoped():
    db.init_db()
    org = db.create_org("Del Co")
    doc = documents.ingest(org["id"], "p.txt", b"We run background checks on all staff.")
    assert db.delete_document(org["id"], doc["id"]) is True
    assert db.delete_document(org["id"], doc["id"]) is False  # already gone
    assert documents.search(org["id"], "background checks") == []


def test_collect_citations_captures_span_and_kind():
    sources = [
        {"title": "Do you encrypt data at rest?", "kind": "library", "data": "Yes, AES-256."},
        {"title": "SOC2_2024.pdf", "kind": "document", "data": "All data is encrypted at rest using AES-256."},
    ]
    blocks = [{
        "type": "text",
        "text": "We encrypt at rest.",
        "citations": [
            {"document_index": 1, "document_title": "SOC2_2024.pdf",
             "cited_text": "encrypted at rest using AES-256"},
        ],
    }]
    cites = drafting._collect_citations(blocks, sources)
    assert cites == [{
        "title": "SOC2_2024.pdf",
        "text": "encrypted at rest using AES-256",
        "kind": "document",
    }]
