"""Funnel instrumentation (Brief 3, Task 4).

The six events are recorded in our own table; the internal page rolls them up.
These check the events fire where they should, the country header is captured,
run_completed carries wall-clock + row count, and the internal page is guarded.
"""
import io
import time
import uuid

from openpyxl import Workbook

from app import config, db, main


def _wb(rows):
    w = Workbook()
    s = w.active
    for r in rows:
        s.append(r)
    b = io.BytesIO()
    w.save(b)
    return b.getvalue()


def test_signup_records_event_with_country(client):
    email = f"e-{uuid.uuid4().hex[:8]}@evco.example"
    r = client.post("/v1/signup", json={"name": "Ev", "email": email, "password": "pw12345678"},
                    headers={"CF-IPCountry": "gb"})
    assert r.status_code == 200
    since = time.time() - 60
    assert db.event_counts_since(since)["signup_completed"] >= 1
    split = {row["country"]: row["n"] for row in db.event_country_split_since(since)}
    assert split.get("GB", 0) >= 1


def test_run_and_export_events_and_wall_clock(client):
    email = f"e-{uuid.uuid4().hex[:8]}@evco2.example"
    tok = client.post("/v1/signup", json={"name": "Ev", "email": email, "password": "pw12345678"}).json()["api_token"]
    H = {"Authorization": f"Bearer {tok}"}
    qs = [f"Do you enforce control {i}?" for i in range(3)]
    client.post("/v1/answers/bulk", headers=H,
                json={"answers": [{"question": q, "answer": "Yes, we do."} for q in qs]})
    qid = client.post("/v1/questionnaires", headers=H,
                      files={"file": ("q.xlsx", _wb([["Question", "Answer"]] + [[q, ""] for q in qs]),
                                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                      ).json()["questionnaire_id"]
    client.post(f"/v1/questionnaires/{qid}/run", headers=H, json={"exclude": []})

    # Wait for the durable run to finish.
    for _ in range(80):
        if not client.get(f"/v1/questionnaires/{qid}", headers=H).json()["progress"]["running"]:
            break
        time.sleep(0.1)

    client.get(f"/v1/questionnaires/{qid}/export", headers=H)

    since = time.time() - 120
    counts = db.event_counts_since(since)
    assert counts["run_started"] >= 1
    assert counts["run_completed"] >= 1
    assert counts["export_downloaded"] >= 1

    # run_completed carries wall-clock seconds and the row count.
    import json as _json
    with db.cursor() as cur:
        row = cur.execute(
            "SELECT props FROM analytics_events WHERE name='run_completed' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    props = _json.loads(dict(row)["props"])
    assert props["wall_seconds"] >= 0
    assert props["rows"] == 3


def test_sample_flag_records_sample_event(client):
    email = f"e-{uuid.uuid4().hex[:8]}@evco3.example"
    tok = client.post("/v1/signup", json={"name": "Ev", "email": email, "password": "pw12345678"}).json()["api_token"]
    H = {"Authorization": f"Bearer {tok}"}
    qid = client.post("/v1/questionnaires", headers=H,
                      files={"file": ("q.xlsx", _wb([["Question", "Answer"], ["Do you do the thing?", ""]]),
                                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                      ).json()["questionnaire_id"]
    before = db.event_counts_since(time.time() - 120)["sample_run_started"]
    client.post(f"/v1/questionnaires/{qid}/run", headers=H, json={"exclude": [], "sample": True})
    assert db.event_counts_since(time.time() - 120)["sample_run_started"] == before + 1


def test_internal_page_is_guarded(client, monkeypatch):
    # No admin token -> disabled entirely.
    monkeypatch.setattr(config, "ADMIN_TOKEN", "")
    assert client.get("/internal").status_code == 404
    assert client.get("/internal?key=whatever").status_code == 404

    monkeypatch.setattr(config, "ADMIN_TOKEN", "s3cret")
    assert client.get("/internal?key=wrong").status_code == 404
    ok = client.get("/internal?key=s3cret")
    assert ok.status_code == 200
    assert "Internal metrics" in ok.text
    js = client.get("/v1/internal/metrics?key=s3cret")
    assert js.status_code == 200
    assert set(db.EVENT_NAMES) <= set(js.json()["counts"].keys())


def test_internal_page_accepts_header_token_and_survives_bad_input(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "s3cret")
    # Header token works, keeping the secret out of the URL / access logs.
    assert client.get("/internal", headers={"X-Admin-Token": "s3cret"}).status_code == 200
    assert client.get("/v1/internal/metrics", headers={"X-Admin-Token": "s3cret"}).status_code == 200
    # Wrong header is a 404, not a reveal.
    assert client.get("/internal", headers={"X-Admin-Token": "nope"}).status_code == 404
    # A non-ASCII key in the URL must be a clean 404, never a 500 from compare_digest.
    assert client.get("/internal?key=café").status_code == 404


def test_median_big_run_only_counts_over_100_rows():
    since = time.time() - 60
    db.record_event("run_completed", props={"rows": 50, "wall_seconds": 10})
    db.record_event("run_completed", props={"rows": 120, "wall_seconds": 40})
    db.record_event("run_completed", props={"rows": 200, "wall_seconds": 60})
    vals = db.run_completed_wall_seconds_since(since, min_rows=100)
    assert sorted(vals) == [40.0, 60.0]  # the 50-row run is excluded
