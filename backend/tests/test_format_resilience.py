"""Format resilience over HTTP (Brief 3, Task 3): multi-sheet detection, the
confirm-before-quota metadata, a column-override re-parse, and RTL notes."""
import io
import uuid

from openpyxl import Workbook


def _tok(client):
    return client.post("/v1/signup",
                       json={"name": "F", "email": f"f-{uuid.uuid4().hex[:8]}@fmtco.example",
                             "password": "pw12345678"}).json()["api_token"]


def _wb(sheets):
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets:
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def _upload(client, H, data, filename="q.xlsx"):
    return client.post("/v1/questionnaires", headers=H,
                       files={"file": (filename, data,
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})


def test_confirm_screen_metadata_and_multi_sheet(client):
    H = {"Authorization": f"Bearer {_tok(client)}"}
    data = _wb([
        ("Cover", [["Vendor Security Questionnaire"], ["Confidential"]]),
        ("Controls", [["#", "Question", "Response"],
                      ["1", "Do you encrypt data at rest?", ""],
                      ["2", "Is MFA enforced for all staff?", ""]]),
    ])
    r = _upload(client, H, data).json()
    assert r["sheet_name"] == "Controls"
    assert {s["name"] for s in r["sheets"]} == {"Cover", "Controls"}
    assert r["question_col"] == 2
    assert len(r["first_questions"]) == 2
    assert any(c["index"] == 2 for c in r["columns"])


def test_column_override_reparse_endpoint(client):
    H = {"Authorization": f"Bearer {_tok(client)}"}
    data = _wb([("Controls", [["Ref", "Question"],
                              ["A1", "Do you encrypt data at rest?"],
                              ["A2", "Is MFA enforced?"]])])
    up = _upload(client, H, data).json()
    qid = up["questionnaire_id"]
    assert up["question_col"] == 2

    # Force column 1 ('Ref') -> no questions detected there.
    r = client.post(f"/v1/questionnaires/{qid}/reparse", headers=H,
                    json={"question_col": 1})
    assert r.status_code == 422  # nothing parseable in that column

    # Switch back to column 2 -> two questions, items replaced (not duplicated).
    r2 = client.post(f"/v1/questionnaires/{qid}/reparse", headers=H,
                     json={"question_col": 2}).json()
    assert r2["question_col"] == 2
    assert r2["total_questions"] == 2
    assert len(r2["items"]) == 2


def test_rtl_bilingual_is_flagged(client):
    H = {"Authorization": f"Bearer {_tok(client)}"}
    data = _wb([("Sheet1", [["Question", "Answer"],
                            ["Do you encrypt data? هل تقومون بالتشفير؟", ""]])])
    r = _upload(client, H, data).json()
    assert r["rtl"] is True
    assert "ar" in r["languages"]
