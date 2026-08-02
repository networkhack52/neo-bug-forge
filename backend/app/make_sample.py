"""Generate a realistic sample vendor security questionnaire (.xlsx).

Mixes questions that overlap the starter bank near-verbatim (should be
reused) with reworded and net-new questions (should be drafted), plus
section headers and blank rows to exercise the parser.

Run:  python -m app.make_sample  ->  sample_data/sample_questionnaire.xlsx
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

OUT = Path(__file__).resolve().parent.parent / "sample_data" / "sample_questionnaire.xlsx"

ROWS = [
    ("Section", "Question", "Vendor Response"),
    ("Access Control", "", ""),
    ("AC-1", "Do you enforce multi-factor authentication (MFA) for all employees?", ""),
    ("AC-2", "Is access granted based on the principle of least privilege?", ""),
    ("AC-3", "How is privileged administrative access controlled and reviewed?", ""),
    ("Encryption", "", ""),
    ("EN-1", "Is customer data encrypted at rest?", ""),
    ("EN-2", "Do you encrypt data while it is transmitted over networks?", ""),
    ("EN-3", "Describe how cryptographic keys are stored and rotated.", ""),
    ("Compliance", "", ""),
    ("CO-1", "Do you hold a current SOC 2 Type II report?", ""),
    ("CO-2", "Are you compliant with the GDPR for personal data you process?", ""),
    ("CO-3", "Will you execute a Data Processing Agreement?", ""),
    ("Data", "", ""),
    ("DA-1", "Do you use our data to train any AI or machine learning models?", ""),
    ("DA-2", "How long is customer data retained after the contract ends?", ""),
    ("DA-3", "In which geographic regions is customer data stored?", ""),
    ("Operations", "", ""),
    ("OP-1", "Do you conduct independent penetration testing at least annually?", ""),
    ("OP-2", "Do you maintain audit logs, and for how long are they retained?", ""),
    ("OP-3", "What is your target service availability / uptime?", ""),
    ("IR-1", "Do you have a documented incident response plan?", ""),
    ("IR-2", "Will you notify us if our data is involved in a security breach?", ""),
    # Net-new questions unlikely to have an exact bank match -> drafted.
    ("MI-1", "Do you offer a customer-facing status page for incidents and uptime?", ""),
    ("MI-2", "Can we configure single sign-on (SSO) via SAML for our users?", ""),
]


def build() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Security Questionnaire"
    for r in ROWS:
        ws.append(list(r))
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 70
    ws.column_dimensions["C"].width = 60
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote sample questionnaire -> {path}")
