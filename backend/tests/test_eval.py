import json
from collections import Counter

from app import eval as ev
from app.drafting import NO_EVIDENCE, Draft


def test_eval_dataset_is_well_formed():
    qs = json.loads(ev.QUESTIONS.read_text(encoding="utf-8"))
    assert len(qs) == 150
    counts = Counter(q["label"] for q in qs)
    assert counts["supported"] == 50
    assert counts["unsupported"] == 40
    assert counts["contradicted"] == 35
    assert counts["ambiguous"] == 25
    assert len({q["id"] for q in qs}) == 150            # ids unique
    assert len({q["question"].lower() for q in qs}) == 150  # no duplicate questions


def test_frozen_60_regression_suite_is_intact():
    frozen = ev.EVAL_DIR / "eval_questions_60.json"
    qs = json.loads(frozen.read_text(encoding="utf-8"))
    counts = Counter(q["label"] for q in qs)
    assert len(qs) == 60
    assert counts == {"supported": 20, "unsupported": 20, "contradicted": 10, "ambiguous": 10}


def test_eval_docs_chunk_into_citable_passages():
    chunks = ev._chunks()
    assert len(chunks) >= 40  # realistic corpus: SOC 2 report + policies
    assert all(c.doc_name and c.text for c in chunks)


def test_retrieve_returns_top_k_and_all_when_zero():
    docs = ev._chunks()
    top = ev._retrieve("Do you encrypt data at rest?", docs, None, 3)
    assert 0 < len(top) <= 3
    # k <= 0 hands the model the whole corpus (model-judgment mode).
    assert len(ev._retrieve("anything", docs, None, 0)) == len(docs)


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


def test_false_confidence_definition_per_category():
    confident_no = Draft(answer="No. We are not.", confidence=90.0, needs_review=False,
                         match_type="drafted", choice="No")
    abstain = Draft(answer=NO_EVIDENCE, confidence=0.0, needs_review=True,
                    match_type="drafted", choice="")
    confident_yes = Draft(answer="Yes.", confidence=90.0, needs_review=False,
                          match_type="drafted", choice="Yes")
    # Unsupported: a confident "No" from silence IS false confidence; abstain is safe.
    assert ev._is_false_confidence("unsupported", confident_no) is True
    assert ev._is_false_confidence("unsupported", abstain) is False
    # Contradicted: confirming the wrong specific (Yes) is false confidence; a
    # grounded "No" (the real value) or abstain is fine.
    assert ev._is_false_confidence("contradicted", confident_yes) is True
    assert ev._is_false_confidence("contradicted", confident_no) is False
    assert ev._is_false_confidence("contradicted", abstain) is False
