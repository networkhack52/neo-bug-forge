import io

from openpyxl import Workbook

from app import parsing


def _wb_bytes(rows):
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_only_real_questions_are_extracted_from_a_messy_sheet():
    rows = [
        ["Question", "Answer"],
        ["Vendor Security Assessment 2025", ""],                 # title
        ["1. Access Control", ""],                               # section header
        ["Please answer all questions in this section.", ""],    # instruction
        ["Do you enforce MFA for all employees?", ""],           # REAL question
        ["The organization maintains a documented access control policy.", ""],  # control statement
        ["2. Encryption", ""],                                   # section header
        ["Is data encrypted at rest?", ""],                      # REAL question
        ["Confidential - Acme Corp - Page 1 of 3", ""],          # footer
        ["© 2025 Acme Corp. All rights reserved.", ""],          # boilerplate
    ]
    result = parsing.parse_xlsx(_wb_bytes(rows))
    got = [q.question for q in result.questions]
    assert got == [
        "Do you enforce MFA for all employees?",
        "The organization maintains a documented access control policy.",
        "Is data encrypted at rest?",
    ], got


def test_section_titles_and_footers_score_zero():
    for noise in ["Access Control", "ENCRYPTION", "Section 3: Governance",
                  "Page 2 of 10", "© 2025 Acme", "Instructions", "Overview",
                  "Please complete the following table.", "For each control, provide evidence.",
                  "This document is confidential and proprietary."]:
        assert parsing._question_score(noise) == 0.0, noise


def test_real_questions_and_control_statements_score_positive():
    for q in ["Do you enforce MFA for all employees?",
              "Is data encrypted at rest?",
              "Describe your incident response process.",
              "The organization maintains a documented data classification policy.",
              "We encrypt all customer data at rest and in transit."]:
        assert parsing._question_score(q) > 0.0, q


def test_csv_messy_sheet_extracts_only_questions():
    csv_text = (
        "Question,Answer\n"
        "Information Security Questionnaire,\n"          # title
        "Domain: Access Management,\n"                   # section
        "Do you review user access periodically?,\n"     # REAL
        "Please see the guidance notes above.,\n"        # instruction
        "Are audit logs retained?,\n"                    # REAL
        "Page 1,\n"                                      # footer
    )
    result = parsing.parse_csv(csv_text.encode())
    got = [q.question for q in result.questions]
    assert got == ["Do you review user access periodically?", "Are audit logs retained?"], got
