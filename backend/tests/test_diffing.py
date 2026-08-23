from app import diffing


def test_flags_polarity_flip():
    assert diffing.materially_differs("Yes, we do this.", "No, we do not.") is not None


def test_flags_frequency_change():
    assert diffing.materially_differs("Access reviews run monthly.",
                                      "Access reviews run quarterly.") is not None


def test_flags_number_and_period_change():
    assert diffing.materially_differs("We retain logs for 90 days.",
                                      "We retain logs for 30 days.") is not None


def test_flags_named_technology_change():
    assert diffing.materially_differs("Data is encrypted with AES-256.",
                                      "Data is encrypted with AES-128.") is not None


def test_hyphenated_and_spaced_units_are_equal():
    # "72-hour" and "72 hours" mean the same thing — not a contradiction.
    assert diffing.materially_differs(
        "we will notify you within 72 hours of confirmation",
        "notification consistent with the 72-hour framework",
    ) is None


def test_ignores_pure_wording_changes():
    assert diffing.materially_differs("We enforce MFA for all staff.",
                                      "MFA is required for every employee.") is None
    assert diffing.materially_differs("We are ISO 27001 certified.",
                                      "We hold ISO 27001 certification.") is None
    assert diffing.materially_differs("Yes, TLS 1.2+ everywhere.",
                                      "Yes, we use TLS 1.2 in transit.") is None


def test_empty_inputs_never_flag():
    assert diffing.materially_differs("", "anything") is None
    assert diffing.materially_differs("anything", "") is None


def test_engine_flags_contradiction_on_drafted_answer(monkeypatch):
    import json
    import uuid

    from app import db, engine, retrieval
    from app.drafting import Draft

    org = db.create_org(name="Co", email=f"c-{uuid.uuid4().hex[:8]}@contra.example")
    oid = org["id"]
    prior = db.add_answer(oid, "How often do you review user access?",
                          "We review user access quarterly.")
    qid = db.create_questionnaire(oid, "q", "q.xlsx", 1)
    iid = db.add_item(qid, 0, "How often is user access reviewed?")

    # Force a fresh draft (skip verbatim reuse) that differs on frequency.
    monkeypatch.setattr(retrieval, "best_reusable", lambda m: None)
    monkeypatch.setattr(engine, "draft_answer", lambda q, ctx, docs=None: Draft(
        answer="We review user access monthly.", confidence=80.0, needs_review=False,
        match_type="drafted", choice="",
        citations=[{"title": "prior", "text": "x", "kind": "library"}],
    ))

    bank = db.list_answers(oid)
    engine.answer_question(oid, iid, "How often is user access reviewed?", bank)

    contra = json.loads(db.get_item(iid)["contradiction"] or "{}")
    assert contra, "expected a contradiction flag"
    assert contra["answer_id"] == prior["id"]
    assert "frequency" in contra["reason"]
