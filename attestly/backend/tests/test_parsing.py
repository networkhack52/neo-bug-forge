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


def test_detects_question_column_and_skips_headers_and_sections():
    rows = [
        ["Section", "Question", "Answer"],
        ["Access", "", ""],  # section row, no question
        ["AC-1", "Do you enforce MFA for all employees?", ""],
        ["AC-2", "Is customer data encrypted at rest?", ""],
        ["", "", ""],  # blank
        ["EN-1", "Please describe your key management process.", ""],
    ]
    result = parsing.parse_xlsx(_wb_bytes(rows))
    questions = [q.question for q in result.questions]
    assert "Do you enforce MFA for all employees?" in questions
    assert "Is customer data encrypted at rest?" in questions
    assert len(questions) == 3
    # question col is 2 (1-based) -> the "Question" column
    assert result.question_col == 2
    assert result.answer_col == 3


def test_csv_parsing():
    csv_bytes = (
        "Question,Response\n"
        "Do you encrypt data in transit?,\n"
        "How long are audit logs retained?,\n"
    ).encode()
    result = parsing.parse_csv(csv_bytes)
    assert len(result.questions) == 2
    assert result.questions[0].question.startswith("Do you encrypt")


def test_no_questions_returns_empty():
    rows = [["a", "b"], ["1", "2"], ["3", "4"]]
    result = parsing.parse_xlsx(_wb_bytes(rows))
    assert result.questions == []
