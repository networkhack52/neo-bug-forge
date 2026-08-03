from app import assessment
from app.report import render


def test_weak_company_scores_low_and_flags_gaps():
    a = assessment.score_company("Weak Co", {}, monthly_questionnaires=6)
    assert a.score < 40
    assert a.grade in ("D", "F")
    assert all(f.ok is False for f in a.findings)
    # cost model reflects volume
    assert a.annual_time_cost > 0
    assert a.hours_saved_per_month > 0


def test_strong_company_scores_high():
    signals = {k: True for k in assessment.SIGNALS}
    a = assessment.score_company("Strong Co", signals)
    assert a.score == 100
    assert a.grade == "A"


def test_partial_score_is_weighted():
    # Only the two heaviest signals present -> mid score, not zero, not full.
    signals = {"has_soc2": True, "has_answer_library": True}
    a = assessment.score_company("Mid Co", signals)
    assert 30 < a.score < 60


def test_live_sample_auto_answers_standard_questions():
    a = assessment.score_company("Demo Co", {})
    a = assessment.with_live_sample(a)
    assert a.autoanswer_rate is not None
    assert a.autoanswer_rate >= 50  # standard security Qs hit the starter bank
    assert len(a.sample) > 0


def test_report_renders_self_contained_html():
    a = assessment.score_company("Acme Inc", {"has_soc2": True}, monthly_questionnaires=5)
    a = assessment.with_live_sample(a)
    doc = render(a, cta_url="https://example.com/app")
    assert doc.startswith("<!doctype html>")
    assert "Acme Inc" in doc
    assert "Readiness" in doc
    assert "https://example.com/app" in doc
    assert "<script" not in doc.lower()  # no external/js dependencies
