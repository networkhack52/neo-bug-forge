"""Generate a shareable readiness-assessment report for a prospect.

Example:
  python -m app.make_assessment "Acme Robotics" \
      --soc2 --trust-page --volume 6 --owner --out acme.html

Every readiness flag defaults to OFF (the weak/needs-help case). Pass a flag to
mark it present. The output is a self-contained HTML file you can email.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .assessment import score_company, with_live_sample
from .report import render


def main() -> None:
    p = argparse.ArgumentParser(description="Generate a security-questionnaire readiness report.")
    p.add_argument("company")
    p.add_argument("--soc2", action="store_true", help="Holds SOC 2 / ISO 27001")
    p.add_argument("--trust-page", action="store_true", help="Has a public trust/security page")
    p.add_argument("--answer-library", action="store_true", help="Maintains a reusable answer library")
    p.add_argument("--framework", action="store_true", help="Has a completed SIG or CAIQ")
    p.add_argument("--owner", action="store_true", help="Has a named questionnaire owner")
    p.add_argument("--fast", action="store_true", help="Typically responds within 3 business days")
    p.add_argument("--headroom", action="store_true", help="Current volume is manageable")
    p.add_argument("--volume", type=int, default=4, help="Questionnaires per month (default 4)")
    p.add_argument("--no-sample", action="store_true", help="Skip the live auto-answer proof section")
    p.add_argument("--cta", default="https://app.example.com", help="CTA link in the report")
    p.add_argument("--out", default=None, help="Output HTML path")
    args = p.parse_args()

    signals = {
        "has_soc2": args.soc2,
        "has_trust_page": args.trust_page,
        "has_answer_library": args.answer_library,
        "has_completed_framework": args.framework,
        "dedicated_owner": args.owner,
        "fast_response": args.fast,
        "low_volume_headroom": args.headroom,
    }
    assessment = score_company(args.company, signals, monthly_questionnaires=args.volume)
    if not args.no_sample:
        assessment = with_live_sample(assessment)

    out = Path(args.out or f"assessment_{args.company.lower().replace(' ', '_')}.html")
    out.write_text(render(assessment, cta_url=args.cta), encoding="utf-8")
    print(f"Score: {assessment.score}/100 (grade {assessment.grade}) — {assessment.grade_summary}")
    if assessment.autoanswer_rate is not None:
        print(f"Live sample auto-answer rate: {assessment.autoanswer_rate}%")
    print(f"Report written -> {out.resolve()}")


if __name__ == "__main__":
    main()
