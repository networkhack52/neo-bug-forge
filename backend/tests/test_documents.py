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


def test_search_gives_each_document_a_fair_share(monkeypatch):
    # Regression for the coverage-run finding: with several documents, a query's
    # supporting passage must not be crowded out of the window by one wordy doc.
    monkeypatch.setattr(documents, "MAX_GROUND_CHUNKS", 6)
    monkeypatch.setattr(documents, "DOC_PER_DOC_CHUNKS", 2)
    db.init_db()
    org = db.create_org("Corpus Co")
    # One long, encryption-heavy document (many passages mentioning "encrypt").
    big = "\n\n".join(
        f"Section {i}: We encrypt data and manage encryption keys carefully. Encryption is applied broadly."
        for i in range(12)
    ).encode()
    documents.ingest(org["id"], "big_encryption_policy.txt", big)
    # A separate short document that holds the specific fact being asked about.
    documents.ingest(
        org["id"], "incident_policy.txt",
        b"Incident Response\n\nWe notify affected customers within 72 hours of a confirmed breach.",
    )
    hits = documents.search(org["id"], "Do you notify customers of a breach within 72 hours?")
    names = {h.doc_name for h in hits}
    # The wordy document must not monopolise the window; the incident doc's passage
    # (the actual answer) is retrieved.
    assert "incident_policy.txt" in names, names
    assert sum(1 for h in hits if h.doc_name == "big_encryption_policy.txt") <= 2
    assert any("72 hours" in h.text for h in hits)


def test_delete_document_is_scoped():
    db.init_db()
    org = db.create_org("Del Co")
    doc = documents.ingest(org["id"], "p.txt", b"We run background checks on all staff.")
    assert db.delete_document(org["id"], doc["id"]) is True
    assert db.delete_document(org["id"], doc["id"]) is False  # already gone
    assert documents.search(org["id"], "background checks") == []


class _Doc:
    def __init__(self, name, text=""):
        self.doc_name = name
        self.text = text


def test_parse_citations_maps_source_and_kind():
    docs = [_Doc("SOC2_2024.pdf")]
    raw = [
        {"source": "SOC2_2024.pdf", "quote": "encrypted at rest using AES-256"},
        {"source": "Do you encrypt data at rest?", "quote": "Yes, AES-256."},
    ]
    cites = drafting._parse_citations(raw, docs)
    assert cites[0] == {"title": "SOC2_2024.pdf",
                        "text": "encrypted at rest using AES-256", "kind": "document"}
    assert cites[1]["kind"] == "library"


def test_parse_citations_handles_junk():
    assert drafting._parse_citations(None, []) == []
    assert drafting._parse_citations("nope", []) == []
    assert drafting._parse_citations([{"source": "", "quote": ""}, "x"], []) == []


def test_strip_cite_tags_removes_inline_markup():
    dirty = 'We encrypt at rest. <cite index="1-2">AES-256</cite> everywhere.'
    assert drafting._strip_cite_tags(dirty) == "We encrypt at rest. AES-256 everywhere."
