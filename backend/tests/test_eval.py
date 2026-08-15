import json
from collections import Counter

from app import eval as ev
from app.drafting import NO_EVIDENCE, Draft


def test_eval_dataset_is_well_formed():
    qs = json.loads(ev.QUESTIONS.read_text(encoding="utf-8"))
    assert len(qs) == 50
    counts = Counter(q["label"] for q in qs)
    assert counts["supported"] == 20
    assert counts["unsupported"] == 20
    assert counts["ambiguous"] == 10
    assert len({q["id"] for q in qs}) == 50  # ids are unique


def test_eval_docs_chunk_into_citable_passages():
    chunks = ev._chunks()
    assert len(chunks) >= 5
    assert all(c.doc_name and c.text for c in chunks)


def test_asserts_control_classifier():
    yes = Draft(answer="Yes. We enforce it.", confidence=90.0, needs_review=False,
                match_type="drafted", choice="Yes")
    assert ev._asserts_control(yes) is True
    # Abstention is never a false assertion.
    abstain = Draft(answer=NO_EVIDENCE, confidence=0.0, needs_review=True,
                    match_type="drafted", choice="")
    assert ev._asserts_control(abstain) is False
    # A flagged Yes (needs_review) is not a confident assertion.
    flagged = Draft(answer="Yes, probably.", confidence=55.0, needs_review=True,
                    match_type="drafted", choice="Yes")
    assert ev._asserts_control(flagged) is False
