from app import backfill_embeddings, config, db, documents, embeddings, retrieval


def test_blob_roundtrip_and_cosine():
    v = [0.1, -0.2, 0.3, 0.4]
    blob = embeddings.to_blob(v)
    back = embeddings.from_blob(blob)
    assert len(back) == 4
    assert all(abs(a - b) < 1e-6 for a, b in zip(v, back))
    # cosine of a vector with itself is 1; with orthogonal is 0.
    assert abs(embeddings.cosine(v, v) - 1.0) < 1e-6
    assert abs(embeddings.cosine([1, 0], [0, 1])) < 1e-6
    assert embeddings.from_blob(None) == []
    assert embeddings.cosine([], [1, 2]) == 0.0


def test_embed_disabled_returns_none(monkeypatch):
    monkeypatch.setattr(config, "EMBEDDINGS_ENABLED", False)
    assert embeddings.embed_texts(["hello"]) is None
    assert embeddings.embed_one("hello") == []


def test_rank_blends_semantic_when_enabled(monkeypatch):
    # Two library entries; the query shares NO surface words with the intended
    # match, so lexical alone would miss it. A stubbed embedder makes the
    # semantic layer pick it, proving the blend raises recall.
    bank = [
        {"id": 1, "question": "In which region does customer data reside?",
         "answer": "EU (Frankfurt).", "category": "data", "embedding": embeddings.to_blob([1.0, 0.0, 0.0])},
        {"id": 2, "question": "Do you run background checks on staff?",
         "answer": "Yes.", "category": "hr", "embedding": embeddings.to_blob([0.0, 1.0, 0.0])},
    ]
    monkeypatch.setattr(config, "EMBEDDINGS_ENABLED", True)

    def fake_embed_one(text, input_type=None):
        # Query aligns with entry 1's vector.
        return [1.0, 0.0, 0.0]

    monkeypatch.setattr(embeddings, "embed_one", fake_embed_one)
    matches = retrieval.rank("Where is my data stored geographically?", bank, limit=2)
    assert matches[0].answer_id == 1
    assert matches[0].score >= 90  # cosine 1.0 * SEMANTIC_WEIGHT


def test_backfill_embeds_missing_rows(monkeypatch):
    db.init_db()
    org = db.create_org("Backfill Co")
    # Create rows while embeddings are OFF -> stored with NULL embedding.
    monkeypatch.setattr(config, "EMBEDDINGS_ENABLED", False)
    db.add_answer(org["id"], "Do you encrypt data at rest?", "Yes, AES-256.")
    documents.ingest(org["id"], "policy.txt", b"Access requires MFA via Okta for all systems.")
    assert db.rows_missing_embeddings("answers", "question")
    assert db.rows_missing_embeddings("document_chunks", "text")

    # Turn embeddings ON with a deterministic stub, then backfill.
    monkeypatch.setattr(config, "EMBEDDINGS_ENABLED", True)
    monkeypatch.setattr(
        embeddings, "embed_texts",
        lambda texts, input_type=None: [[0.1, 0.2, 0.3] for _ in texts],
    )
    n = backfill_embeddings.backfill()
    assert n >= 2
    # Every row now has an embedding.
    assert db.rows_missing_embeddings("answers", "question") == []
    assert db.rows_missing_embeddings("document_chunks", "text") == []


def test_backfill_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(config, "EMBEDDINGS_ENABLED", False)
    assert backfill_embeddings.backfill() == 0
