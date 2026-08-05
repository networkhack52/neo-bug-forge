import io
import uuid

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app

client = TestClient(app)


def _token():
    # Unique email per call — signup now enforces one account per email.
    email = f"t-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/v1/signup", json={"name": "Test Co", "email": email, "password": "supersecret"})
    assert r.status_code == 200, r.text
    return r.json()["api_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _questionnaire_bytes():
    wb = Workbook()
    ws = wb.active
    ws.append(["Question", "Answer"])
    ws.append(["Do you enforce MFA for all employees?", ""])
    ws.append(["Is data encrypted in transit?", ""])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_seed_starter_loads_and_is_idempotent():
    token = _token()
    r1 = client.post("/v1/answers/seed_starter", headers=_auth(token)).json()
    assert r1["created"] > 20            # the bundled starter set
    assert r1["bank_size"] == r1["created"]
    # Second call adds nothing (everything already present / deduped).
    r2 = client.post("/v1/answers/seed_starter", headers=_auth(token)).json()
    assert r2["created"] == 0
    assert r2["skipped"] >= r1["created"]


def test_oversized_upload_is_rejected(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1024)  # 1 KB cap for the test
    token = _token()
    big = b"x" * 2048
    r = client.post("/v1/documents", headers=_auth(token),
                    files={"file": ("big.txt", big, "text/plain")})
    assert r.status_code == 413


def test_auth_required():
    assert client.get("/v1/me").status_code == 401
    assert client.get("/v1/me", headers=_auth("bogus")).status_code == 401


def test_signup_requires_email_and_password():
    assert client.post("/v1/signup", json={"name": "X", "email": "bad", "password": "supersecret"}).status_code == 400
    assert client.post("/v1/signup", json={"name": "X", "email": "a@b.com", "password": "short"}).status_code == 400


def test_signup_dedupes_email_and_login_returns_same_org():
    email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    r1 = client.post("/v1/signup", json={"name": "Acme", "email": email, "password": "supersecret"})
    assert r1.status_code == 200
    org_id = r1.json()["org_id"]
    # Second signup with the same email is rejected.
    assert client.post("/v1/signup", json={"name": "Acme2", "email": email, "password": "supersecret"}).status_code == 409
    # Login with the right password returns the SAME org (and its data/token).
    ok = client.post("/v1/login", json={"email": email, "password": "supersecret"})
    assert ok.status_code == 200
    assert ok.json()["org_id"] == org_id
    # Wrong password is rejected.
    assert client.post("/v1/login", json={"email": email, "password": "nope"}).status_code == 401
    # Unknown email is rejected the same way.
    assert client.post("/v1/login", json={"email": "ghost@example.com", "password": "x"}).status_code == 401


def test_full_flow_signup_bank_upload_export():
    token = _token()

    # New org starts on free tier with empty bank.
    me = client.get("/v1/me", headers=_auth(token)).json()
    assert me["tier"] == "free"
    assert me["bank_size"] == 0

    # Seed the bank with the two answers the questionnaire will ask.
    client.post("/v1/answers", headers=_auth(token), json={
        "question": "Do you enforce multi-factor authentication (MFA) for all employees?",
        "answer": "Yes, MFA is enforced for all employees.",
    })
    client.post("/v1/answers", headers=_auth(token), json={
        "question": "Is data encrypted in transit?",
        "answer": "Yes, TLS 1.2+ everywhere.",
    })

    # Upload a questionnaire -> auto-answered.
    files = {"file": ("q.xlsx", _questionnaire_bytes(),
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = client.post("/v1/questionnaires", headers=_auth(token), files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_questions"] == 2
    assert body["reused_from_bank"] >= 1   # at least the verbatim MFA question

    qid = body["questionnaire_id"]

    # Usage was metered.
    me = client.get("/v1/me", headers=_auth(token)).json()
    assert me["questions_used"] == 2

    # Export returns a real xlsx.
    r = client.get(f"/v1/questionnaires/{qid}/export", headers=_auth(token))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(r.content) > 0


def test_free_tier_question_limit_enforced():
    token = _token()
    # Build a questionnaire with 30 questions (> free limit of 25).
    wb = Workbook()
    ws = wb.active
    ws.append(["Question", "Answer"])
    for i in range(30):
        ws.append([f"Do you support control number {i}?", ""])
    buf = io.BytesIO()
    wb.save(buf)
    files = {"file": ("big.xlsx", buf.getvalue(),
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = client.post("/v1/questionnaires", headers=_auth(token), files=files)
    assert r.status_code == 402  # over plan allowance


def test_simulated_upgrade_changes_tier():
    token = _token()
    r = client.post("/v1/billing/checkout", headers=_auth(token), json={"tier": "starter"})
    assert r.status_code == 200
    assert r.json()["simulated"] is True
    r = client.post("/v1/billing/confirm", headers=_auth(token), json={"tier": "starter"})
    assert r.status_code == 200
    assert r.json()["tier"] == "starter"
    assert r.json()["question_limit"] == 750


def test_annual_checkout_charges_yearly_price():
    token = _token()
    r = client.post("/v1/billing/checkout", headers=_auth(token),
                    json={"tier": "growth", "interval": "year"})
    assert r.status_code == 200
    body = r.json()
    assert body["interval"] == "year"
    assert body["amount"] == 2490  # 10 x $249, 2 months free


def test_invalid_interval_rejected():
    token = _token()
    r = client.post("/v1/billing/checkout", headers=_auth(token),
                    json={"tier": "starter", "interval": "weekly"})
    assert r.status_code == 400
