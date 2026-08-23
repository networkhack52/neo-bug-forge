"""The curated static onboarding sample (Brief 3, Task 2)."""
import time
import uuid

from app import db, sample


def test_sample_is_the_curated_eight_with_the_right_mix():
    items = sample.sample_items()
    assert len(items) == 8

    clean = [i for i in items if i["match_type"] == "reuse" and i["choice"] == "Yes"
             and i["citations"] and not any(c.get("stale") for c in i["citations"])]
    stale = [i for i in items if any(c.get("stale") for c in i["citations"])]
    abstain = [i for i in items if i["match_type"] == "fallback" and not i["citations"]]
    negative = [i for i in items if i["choice"] == "No"]

    assert len(clean) == 4, "4 clean cited answers"
    assert len(stale) == 1, "1 stale source"
    assert len(abstain) == 2, "2 honest abstentions"
    assert len(negative) == 1, "1 substantive negative"

    # Every grounded answer carries a readable quote; abstentions carry none.
    for i in items:
        for c in i["citations"]:
            assert c.get("text"), "citation must have a verbatim quote"
    # The negative is substantive, not a bare 'No'.
    assert len(negative[0]["answer"]) > 20


def test_sample_endpoint_serves_it_and_records_event(client):
    tok = client.post("/v1/signup",
                      json={"name": "S", "email": f"s-{uuid.uuid4().hex[:8]}@samco.example",
                            "password": "pw12345678"}).json()["api_token"]
    r = client.get("/v1/sample", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["sample"] is True
    assert len(body["items"]) == 8
    assert db.event_counts_since(time.time() - 60)["sample_run_started"] >= 1


def test_sample_makes_no_model_call(client, monkeypatch):
    # Serving the sample must never hit the drafting layer (it's precomputed).
    from app import drafting

    def _boom(*a, **k):
        raise AssertionError("sample must not call the model")

    monkeypatch.setattr(drafting, "draft_answer", _boom)
    tok = client.post("/v1/signup",
                      json={"name": "S", "email": f"s-{uuid.uuid4().hex[:8]}@samco2.example",
                            "password": "pw12345678"}).json()["api_token"]
    r = client.get("/v1/sample", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
