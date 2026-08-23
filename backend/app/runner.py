"""Durable questionnaire runs.

A run is a BACKGROUND job, not a request. The browser starts it and then polls
the questionnaire for progress, so closing the tab (or a mid-run deploy) never
stops the work: the answering happens in an in-process worker pool, each answer
is persisted to the database the moment it lands, and quota is charged per
completed answer — never a whole run at once. If the process restarts while a
run is in flight, ``resume_interrupted`` finds it (status ``running`` with rows
still pending) and finishes only what's left.

The pool is bounded by ``config.RUN_WORKERS`` (runs at once) and the global
``MAX_CONCURRENT_MODEL_CALLS`` semaphore in ``drafting`` (API calls across all
runs). Fix the architecture first; raise those before touching machine size.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from . import config, db, engine

_log = logging.getLogger("attestly.runner")

# One shared pool for the whole process. Daemon threads so a shutdown doesn't
# hang on an in-flight run (the DB already holds every answer produced so far,
# and startup resume finishes the remainder).
_EXECUTOR = ThreadPoolExecutor(
    max_workers=max(1, config.RUN_WORKERS), thread_name_prefix="attestly-run"
)

# Guards against submitting the same questionnaire twice (double-click, or a
# resume racing a fresh start). A run holds its qid here for its lifetime.
_active: set[int] = set()
_active_lock = threading.Lock()


def _claim(qid: int) -> bool:
    with _active_lock:
        if qid in _active:
            return False
        _active.add(qid)
        return True


def _release(qid: int) -> None:
    with _active_lock:
        _active.discard(qid)


def is_running(qid: int) -> bool:
    with _active_lock:
        return qid in _active


def _do_run(org_id: int, qid: int, allow_draft: bool, block_message: str,
            use_onboarding: bool, domain: str) -> None:
    """Answer every pending row, charging quota as each answer lands. Runs on a
    worker thread. The engine generator sets the final answered-count and marks
    the questionnaire ``ready`` when it drains; we only add per-answer charging
    and keep the live progress count moving so a poll sees rows accrue."""
    try:
        produced = 0
        for ai in engine.stream_answer_questionnaire(org_id, qid, allow_draft, block_message):
            if ai and ai.match_type in ("reuse", "drafted", "fallback"):
                db.charge_one_answer(org_id, domain, use_onboarding)
                produced += 1
                # Live progress for pollers (the engine sets the authoritative
                # cumulative total when the run drains).
                db.set_answered_count(qid, _answered_count(qid))
        _log.info("run %s finished: %s answers produced", qid, produced)
    except Exception:  # never let a worker die silently — leave the run resumable
        _log.exception("run %s failed; leaving pending rows for resume", qid)
        # Reset to 'running' so startup resume (or a manual retry) picks up the
        # remaining rows; the engine only flips to 'ready' on a clean drain.
        try:
            db.set_questionnaire_status(qid, "running")
        except Exception:
            _log.exception("run %s: could not reset status after failure", qid)
    finally:
        _release(qid)


def _answered_count(qid: int) -> int:
    return sum(
        1 for it in db.list_items(qid)
        if it["match_type"] in ("reuse", "drafted", "fallback")
        and not it["locked"] and not it["excluded"]
    )


def start_run(org_id: int, qid: int, allow_draft: bool, block_message: str,
              use_onboarding: bool, domain: str) -> bool:
    """Mark the questionnaire ``running`` and submit the background job. Returns
    False (and does nothing) if a run for this questionnaire is already active."""
    if not _claim(qid):
        return False
    db.set_questionnaire_status(qid, "running")
    try:
        _EXECUTOR.submit(
            _do_run, org_id, qid, allow_draft, block_message, use_onboarding, domain
        )
    except Exception:
        _release(qid)
        raise
    return True


def resume_interrupted() -> int:
    """Re-submit runs that were in flight when the process last stopped. Called
    once at startup. Recomputes the quota gate from the org so a resumed run
    charges and blocks exactly as a fresh one would. Returns how many resumed."""
    resumed = 0
    for q in db.running_questionnaires():
        qid, org_id = q["id"], q["org_id"]
        # Nothing left to do -> just close it out instead of resubmitting.
        pending = [
            it for it in db.list_items(qid)
            if not it.get("locked") and not it.get("excluded")
            and (it.get("match_type") or "none") in ("none", "blocked")
        ]
        if not pending:
            db.set_questionnaire_status(qid, "ready")
            continue
        is_free = q.get("org_tier") == "free"
        domain = db.email_domain(q.get("org_email"))
        allow_draft, block_message = _gate_for_resume(org_id, is_free)
        if start_run(org_id, qid, allow_draft, block_message, is_free, domain):
            resumed += 1
    if resumed:
        _log.info("resumed %s interrupted run(s) at startup", resumed)
    return resumed


def _gate_for_resume(org_id: int, is_free: bool) -> tuple[bool, str]:
    """Resolve the drafting gate for a resumed run without the request context."""
    no_docs = is_free and db.count_documents(org_id) == 0
    if no_docs:
        return False, engine.BLOCKED_ANSWER
    return True, engine.BLOCKED_ANSWER
