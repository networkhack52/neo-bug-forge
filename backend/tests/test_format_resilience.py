"""Format resilience over HTTP (Brief 3, Task 3): multi-sheet detection, the
confirm-before-quota metadata, a column-override re-parse, and RTL notes."""
import io
import uuid

from openpyxl import Workbook

from app import config, db, ratelimit


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


def test_cannot_exclude_another_tenants_items(client):
    # Security regression: the exclude list on an answer run must only affect the
    # caller's own questionnaire rows, never arbitrary item ids from other orgs.
    victim = {"Authorization": f"Bearer {_tok(client)}"}
    vdata = _wb([("S", [["Question", "Answer"], ["Do you encrypt data at rest?", ""]])])
    vitems = _upload(client, victim, vdata).json()["items"]
    victim_item_id = vitems[0]["id"]

    attacker = {"Authorization": f"Bearer {_tok(client)}"}
    adata = _wb([("S", [["Question", "Answer"], ["Do you enforce MFA?", ""]])])
    aqid = _upload(client, attacker, adata).json()["questionnaire_id"]

    # Attacker runs their OWN questionnaire but tries to exclude the victim's row.
    r = client.post(f"/v1/questionnaires/{aqid}/answer", headers=attacker,
                    json={"exclude": [{"id": victim_item_id, "reason": "pwned"}]})
    assert r.status_code == 200

    # The victim's item is untouched: not excluded, no injected reason.
    victim_item = db.get_item(victim_item_id)
    assert victim_item["excluded"] == 0
    assert victim_item["exclusion_reason"] == ""


def test_reparse_is_rate_limited(client, monkeypatch):
    # Security regression: re-parsing a stored workbook is CPU work and must be
    # rate limited (it shares the 'upload' bucket) so it can't be spammed.
    H = {"Authorization": f"Bearer {_tok(client)}"}
    data = _wb([("S", [["Ref", "Question"], ["A1", "Do you encrypt data at rest?"]])])
    qid = _upload(client, H, data).json()["questionnaire_id"]

    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(config, "RL_UPLOAD", (2, 3600))
    ratelimit.reset()
    try:
        codes = [client.post(f"/v1/questionnaires/{qid}/reparse", headers=H,
                             json={"question_col": 2}).status_code for _ in range(3)]
        assert codes == [200, 200, 429]
    finally:
        ratelimit.reset()
