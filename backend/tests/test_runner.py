"""Durable background runs (Brief 3, Task 1).

These prove the two acceptance properties that make a run survivable:
  1. Quota consumed == answers produced, charged per completed answer (not per
     run), so a run that stops half-way has already paid for exactly what it
     produced — never a whole run at once, never zero.
  2. An interrupted run (status 'running' with rows still pending) is resumed
     and only the remaining rows are answered — no double answering, no double
     charge.
"""
import time
import uuid

from app import config, db, engine, retrieval, runner
from app.drafting import Draft


def _org():
    # Unique domain per org: the onboarding pool is shared per-domain, so tests
    # must not collide on it.
    slug = uuid.uuid4().hex[:8]
    return db.create_org(name="Co", email=f"c-{slug}@run-{slug}.example")


def _stub_reuse(monkeypatch):
    """Make every question resolve as a free 'reuse' answer, deterministically,
    with no model call — so the test exercises charging/durability, not the LLM."""
    monkeypatch.setattr(retrieval, "best_reusable",
                        lambda matches: retrieval.Match(
                            answer_id=1, question="q", answer="Yes, we do.",
                            score=99.0, category="general"))
    monkeypatch.setattr(db, "bump_reuse", lambda *_a, **_k: None)


def _wait_done(qid, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        if not runner.is_running(qid):
            return
        time.sleep(0.02)
    raise AssertionError("run did not finish in time")


def test_run_charges_quota_per_answer_and_totals_match(monkeypatch):
    _stub_reuse(monkeypatch)
    org = _org()
    oid = org["id"]
    domain = db.email_domain(org["email"])
    qid = db.create_questionnaire(oid, "q", "q.xlsx", 5)
    for i in range(5):
        db.add_item(qid, i, f"Do you do control {i}?")

    started = runner.start_run(oid, qid, allow_draft=True, block_message="",
                               use_onboarding=True, domain=domain)
    assert started
    _wait_done(qid)

    items = db.list_items(qid)
    produced = sum(1 for it in items if it["match_type"] == "reuse")
    assert produced == 5
    # Charged per answer to the onboarding pool — exactly the number produced.
    assert db.domain_onboarding_used(domain) == 5
    q = db.get_questionnaire(qid, oid)
    assert q["status"] == "ready"
    assert q["answered_questions"] == 5


def test_resume_finishes_only_the_remaining_rows(monkeypatch):
    _stub_reuse(monkeypatch)
    org = _org()
    oid = org["id"]
    domain = db.email_domain(org["email"])
    qid = db.create_questionnaire(oid, "q", "q.xlsx", 4)
    ids = [db.add_item(qid, i, f"Do you do control {i}?") for i in range(4)]

    # Simulate a process that died mid-run: two rows already answered+charged,
    # the questionnaire still marked 'running', the other two rows pending.
    for iid in ids[:2]:
        db.update_item(iid, answer="Yes, we do.", confidence=99.0, match_type="reuse",
                       matched_answer_id=1, needs_review=False, choice="Yes")
    db.charge_one_answer(oid, domain, True)
    db.charge_one_answer(oid, domain, True)
    db.set_questionnaire_status(qid, "running")

    resumed = runner.resume_interrupted()
    assert resumed >= 1
    _wait_done(qid)

    items = db.list_items(qid)
    assert sum(1 for it in items if it["match_type"] == "reuse") == 4
    # Only the two remaining rows were charged on resume -> 4 total, not 6.
    assert db.domain_onboarding_used(domain) == 4
    assert db.get_questionnaire(qid, oid)["status"] == "ready"


def test_charge_one_answer_falls_through_to_period_when_onboarding_exhausted():
    org = _org()
    oid = org["id"]
    domain = db.email_domain(org["email"])
    # Drain the onboarding pool for this domain.
    db.consume_domain_onboarding(domain, config.ONBOARDING_ALLOWANCE)
    bucket = db.charge_one_answer(oid, domain, use_onboarding=True)
    assert bucket == "period"
    assert db.get_org(oid)["questions_used"] == 1


def test_double_start_is_rejected(monkeypatch):
    # A run already active for a questionnaire can't be started twice.
    _stub_reuse(monkeypatch)
    org = _org()
    oid = org["id"]
    qid = db.create_questionnaire(oid, "q", "q.xlsx", 1)
    db.add_item(qid, 0, "Do you do the thing?")
    assert runner._claim(qid) is True
    try:
        assert runner.start_run(oid, qid, True, "", True, "runco.example") is False
    finally:
        runner._release(qid)
