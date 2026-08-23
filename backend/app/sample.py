"""The curated 8-question onboarding sample.

Hand-picked and PRECOMPUTED — no model call, no quota, fully deterministic — so a
first-time visitor sees exactly what the product does in seconds, every time. The
set is chosen to show the whole spectrum on purpose:

  - 4 clean answers, each with a short readable quote from a fresh source,
  - 1 answer whose source is stale (over 12 months old — the freshness flag),
  - 2 honest abstentions (the docs don't cover it, so we do NOT guess 'No'),
  - 1 substantive negative (a real 'No' with the reason, not a bare 'No').

The frontend reveals these with a fake-paced stream so it feels live. Shapes
match a questionnaire item closely enough for the review UI to render them.
"""
from __future__ import annotations

# Citations are structured like real ones: {title, text, kind, date, stale}.
# `date` is an ISO date the reviewer sees; `stale` drives the freshness warning.
SAMPLE_ITEMS: list[dict] = [
    {
        "id": "s1", "row_index": 0,
        "question": "Is customer data encrypted at rest?",
        "answer": "Yes. All customer data is encrypted at rest using AES-256.",
        "choice": "Yes", "confidence": 96, "match_type": "reuse",
        "verification": "supported", "needs_review": False,
        "citations": [{
            "title": "SOC 2 Type II Report 2025", "kind": "document",
            "text": "All customer data is encrypted at rest using AES-256 and in transit using TLS 1.2 or higher.",
            "date": "2025-02-10", "date_basis": "stated", "stale": False,
        }],
    },
    {
        "id": "s2", "row_index": 1,
        "question": "Do you enforce multi-factor authentication for employees?",
        "answer": "Yes. MFA is enforced for all employee access to production systems.",
        "choice": "Yes", "confidence": 95, "match_type": "reuse",
        "verification": "supported", "needs_review": False,
        "citations": [{
            "title": "Access Control Policy", "kind": "document",
            "text": "Multi-factor authentication is enforced for all employee access to production systems and administrative consoles.",
            "date": "2025-01-15", "date_basis": "stated", "stale": False,
        }],
    },
    {
        "id": "s3", "row_index": 2,
        "question": "Do you perform independent penetration testing at least annually?",
        "answer": "Yes. An independent third party performs penetration testing at least annually.",
        "choice": "Yes", "confidence": 94, "match_type": "reuse",
        "verification": "supported", "needs_review": False,
        "citations": [{
            "title": "SOC 2 Type II Report 2025", "kind": "document",
            "text": "An independent third party performs network and application penetration testing at least annually; findings are tracked to remediation.",
            "date": "2025-02-10", "date_basis": "stated", "stale": False,
        }],
    },
    {
        "id": "s4", "row_index": 3,
        "question": "Are backups performed and tested for recoverability?",
        "answer": "Yes. Backups run daily and are tested quarterly for restorability.",
        "choice": "Yes", "confidence": 93, "match_type": "reuse",
        "verification": "supported", "needs_review": False,
        "citations": [{
            "title": "Business Continuity & Backup Policy", "kind": "document",
            "text": "Backups are performed daily, encrypted, and tested for restorability on a quarterly basis.",
            "date": "2025-03-01", "date_basis": "stated", "stale": False,
        }],
    },
    {
        # Stale: correct answer, but the cited source is over 12 months old.
        "id": "s5", "row_index": 4,
        "question": "Do you maintain and test an incident response plan?",
        "answer": "Yes. The incident response plan is reviewed and tested annually.",
        "choice": "Yes", "confidence": 88, "match_type": "reuse",
        "verification": "supported", "needs_review": False,
        "citations": [{
            "title": "Incident Response Plan", "kind": "document",
            "text": "The incident response plan is reviewed and tested annually, including a tabletop exercise with the security team.",
            "date": "2023-04-01", "date_basis": "stated", "stale": True,
        }],
    },
    {
        # Abstention: the documents don't mention ISO 27001 — do NOT answer 'No'.
        "id": "s6", "row_index": 5,
        "question": "Are you certified under ISO/IEC 27001?",
        "answer": "No supporting evidence found in the uploaded documents. Needs owner review.",
        "choice": "", "confidence": 0, "match_type": "fallback",
        "verification": "skipped", "needs_review": True, "citations": [],
    },
    {
        # Abstention: FedRAMP not covered by the sample docs.
        "id": "s7", "row_index": 6,
        "question": "Do you hold a FedRAMP authorization (ATO)?",
        "answer": "No supporting evidence found in the uploaded documents. Needs owner review.",
        "choice": "", "confidence": 0, "match_type": "fallback",
        "verification": "skipped", "needs_review": True, "citations": [],
    },
    {
        # Substantive negative: an honest 'No' with the reason — not a bare 'No'.
        "id": "s8", "row_index": 7,
        "question": "Do you offer a single-tenant, dedicated deployment?",
        "answer": ("No. The platform runs on shared multi-tenant infrastructure with logical "
                   "isolation per customer; a dedicated single-tenant deployment is not offered."),
        "choice": "No", "confidence": 91, "match_type": "reuse",
        "verification": "supported", "needs_review": False,
        "citations": [{
            "title": "System Architecture Overview", "kind": "document",
            "text": "The platform is deployed as a shared, multi-tenant service; tenant data is logically isolated at the application and database layers.",
            "date": "2025-02-20", "date_basis": "stated", "stale": False,
        }],
    },
]


def sample_items() -> list[dict]:
    """A fresh copy so a caller can't mutate the canonical set. Each item carries
    the read-only fields the review UI needs; the rest default on the client."""
    import copy

    return copy.deepcopy(SAMPLE_ITEMS)
