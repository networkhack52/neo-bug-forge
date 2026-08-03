"""Security-Questionnaire Readiness Assessment.

The engine behind assessment-based selling: given a handful of signals about a
prospect, produce a 0-100 readiness score, a letter grade, specific findings,
and a quantified cost-of-inaction — plus (optionally) a live sample of how many
standard questions the product can auto-answer from the starter bank.

Used two ways:
  * Outbound now: generate a branded report to send a prospect (make_assessment).
  * Inbound later: the same logic powers a public self-serve "readiness score"
    lead-magnet tool (see GO_TO_MARKET.md).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import retrieval

STARTER = Path(__file__).resolve().parent.parent / "sample_data" / "starter_answer_bank.json"

# Each signal: (weight, human label, remediation shown when the answer is weak).
# Booleans are True = good. Larger weight = bigger impact on the score.
SIGNALS = {
    "has_soc2": (22, "Holds SOC 2 / ISO 27001",
                 "Buyers ask for a report you can produce on day one; without it, every "
                 "questionnaire turns into a fire drill."),
    "has_trust_page": (10, "Public trust / security page",
                       "A trust page deflects many questions before they are ever sent."),
    "has_answer_library": (20, "Maintains a reusable answer library",
                           "Re-typing the same answers is the #1 time sink; a reusable "
                           "library is where 80% of the speed-up comes from."),
    "has_completed_framework": (12, "Has a completed SIG or CAIQ on file",
                                "A completed standard questionnaire becomes the template for "
                                "answering the next one fast."),
    "dedicated_owner": (8, "A named owner for questionnaires",
                        "When no one owns it, questionnaires bounce between sales, security "
                        "and engineering and stall."),
    "fast_response": (18, "Typically responds within 3 business days",
                      "78% of buyers pick whoever responds first; slow turnaround silently "
                      "loses deals."),
    "low_volume_headroom": (10, "Volume is manageable for the current process",
                            "Rising questionnaire volume breaks manual processes exactly when "
                            "you are trying to close bigger deals."),
}

GRADE_BANDS = [
    (85, "A", "Questionnaire-ready — small gaps to close."),
    (70, "B", "Mostly ready — a few gaps are costing you time and deals."),
    (55, "C", "At risk — questionnaires are slowing your sales cycle."),
    (40, "D", "High risk — you are likely losing deals to slow responses."),
    (0, "F", "Critical — every enterprise questionnaire is a fire drill."),
]


@dataclass
class Finding:
    label: str
    ok: bool
    weight: int
    note: str


@dataclass
class Assessment:
    company: str
    score: int
    grade: str
    grade_summary: str
    findings: list[Finding] = field(default_factory=list)
    monthly_questionnaires: int = 4
    hours_saved_per_month: float = 0.0
    annual_time_cost: float = 0.0
    autoanswer_rate: float | None = None
    sample: list[dict] = field(default_factory=list)


# Cost model constants (conservative; cited in the report).
HOURS_PER_QUESTIONNAIRE = 12.0        # a 100-question DDQ first draft ≈ 4-5h; multi-team back-and-forth pushes it higher
LOADED_HOURLY_RATE = 75.0             # blended loaded cost of the people who answer
TOOL_TIME_REDUCTION = 0.70           # portion of answering time removed once a reusable bank exists


def grade_for(score: int) -> tuple[str, str]:
    for threshold, letter, summary in GRADE_BANDS:
        if score >= threshold:
            return letter, summary
    return "F", GRADE_BANDS[-1][2]


def score_company(company: str, signals: dict, monthly_questionnaires: int = 4) -> Assessment:
    findings: list[Finding] = []
    earned = 0
    total = 0
    for key, (weight, label, note) in SIGNALS.items():
        total += weight
        ok = bool(signals.get(key, False))
        if ok:
            earned += weight
        findings.append(Finding(label=label, ok=ok, weight=weight, note=note))

    score = round(earned / total * 100) if total else 0
    grade, summary = grade_for(score)

    # Cost of inaction: current time spent vs. time recoverable with a reusable bank.
    monthly_hours = monthly_questionnaires * HOURS_PER_QUESTIONNAIRE
    hours_saved = monthly_hours * TOOL_TIME_REDUCTION
    annual_time_cost = monthly_hours * 12 * LOADED_HOURLY_RATE

    return Assessment(
        company=company,
        score=score,
        grade=grade,
        grade_summary=summary,
        findings=findings,
        monthly_questionnaires=monthly_questionnaires,
        hours_saved_per_month=round(hours_saved, 1),
        annual_time_cost=round(annual_time_cost, 2),
    )


def with_live_sample(assessment: Assessment, sample_questions: list[str] | None = None) -> Assessment:
    """Attach a live auto-answer demo using the starter bank (the 'proof')."""
    bank = json.loads(STARTER.read_text(encoding="utf-8"))
    # give bank entries ids for the ranker
    for i, b in enumerate(bank):
        b["id"] = i
    questions = sample_questions or [
        "Do you enforce MFA for all staff?",
        "Is customer data encrypted at rest and in transit?",
        "Do you have a SOC 2 Type II report?",
        "How long do you retain data after contract termination?",
        "Do you conduct annual penetration testing?",
        "Will you notify us of a data breach, and how quickly?",
        # Deliberately company-specific — the generic starter bank won't cover
        # these, so the proof shows a realistic (not suspiciously perfect) rate.
        "Do you support SCIM user provisioning for our identity provider?",
        "Can you provide a completed HECVAT for higher-education procurement?",
    ]
    # "Auto-answered" in the proof means a genuinely strong match the product
    # would confidently reuse/draft — not a weak context hit.
    SAMPLE_MATCH_THRESHOLD = 70.0
    answered = 0
    sample: list[dict] = []
    for q in questions:
        matches = retrieval.rank(q, bank)
        top = matches[0] if matches else None
        hit = bool(top and top.score >= SAMPLE_MATCH_THRESHOLD)
        if hit:
            answered += 1
        sample.append({
            "question": q,
            "matched": hit,
            "answer": top.answer if hit else "",
            "confidence": round(top.score, 0) if top else 0,
        })
    assessment.autoanswer_rate = round(answered / len(questions) * 100) if questions else 0
    assessment.sample = sample
    return assessment
