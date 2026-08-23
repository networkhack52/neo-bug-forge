"""Attestly HTTP API (FastAPI).

Self-serve: an org signs up, gets an API token, builds an Answer Bank, then
uploads questionnaires that come back auto-answered. Metering enforces plan
limits; billing is self-serve via Stripe Checkout.
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import logging
import secrets
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from . import (
    __version__, assessment as assess, billing, config, db, documents, email as email_svc,
    engine, export, parsing, passwords, ratelimit, runner, tokens, triage,
)
from .report import render as render_report

_spend_log = logging.getLogger("attestly.spend")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    # Finish any run that was in flight when the process last stopped (deploy,
    # crash, restart). Best-effort: a resume failure must never block boot.
    try:
        runner.resume_interrupted()
    except Exception:
        logging.getLogger("attestly.runner").exception("startup resume failed")
    yield


# Also initialise at import so TestClient (no lifespan) and scripts work.
db.init_db()

app = FastAPI(title="Attestly API", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Defense-in-depth headers on every API response."""
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return resp


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
def require_org(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    org = db.get_org_by_token(token)
    if not org:
        raise HTTPException(status_code=401, detail="Invalid token")
    return db.roll_period_if_needed(org)


def rate_limit(request: Request, bucket: str, rule: tuple) -> None:
    """Raise 429 if the caller's IP exceeds `rule` = (limit, window_seconds)."""
    if not config.RATE_LIMIT_ENABLED:
        return
    limit, window = rule
    if not ratelimit.allow(bucket, ratelimit.client_ip(request), limit, window):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down and try again shortly.",
            headers={"Retry-After": str(window)},
        )


def rate_limit_request_and_account(request: Request, bucket: str, org_id: int, rule: tuple) -> None:
    """Rate limit an authenticated action by BOTH client IP and account."""
    rate_limit(request, bucket, rule)
    if not config.RATE_LIMIT_ENABLED:
        return
    limit, window = rule
    if not ratelimit.allow(f"{bucket}:acct", f"org:{org_id}", limit, window):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down and try again shortly.",
            headers={"Retry-After": str(window)},
        )


def _month_start_epoch() -> float:
    now = _dt.datetime.now(_dt.timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()


def _free_tier_drafting_paused() -> bool:
    """True when free-tier model spend this month has hit the cap. Logs thresholds."""
    cap = config.FREE_TIER_MONTHLY_SPEND_CAP_USD
    if cap <= 0:
        return False
    spent = db.free_tier_spend_since(_month_start_epoch())
    pct = spent / cap
    if pct >= 1.0:
        _spend_log.error("Free-tier spend cap REACHED: $%.2f / $%.2f. Free drafting paused.", spent, cap)
        return True
    if pct >= 0.8:
        _spend_log.warning("Free-tier spend at %.0f%%: $%.2f / $%.2f", pct * 100, spent, cap)
    elif pct >= 0.5:
        _spend_log.warning("Free-tier spend at %.0f%%: $%.2f / $%.2f", pct * 100, spent, cap)
    return False


def _client_country(request: Request) -> str:
    """Client country (ISO alpha-2) from a fronting CDN's header, '' if none.
    Cloudflare (CF-IPCountry) / Vercel (X-Vercel-IP-Country) set these when the
    API is behind them; direct-to-origin traffic has no country and stores ''."""
    for h in config.COUNTRY_HEADERS:
        v = (request.headers.get(h) or "").strip()
        if v and v.upper() not in ("XX", "T1"):  # CF placeholders for unknown/Tor
            return v[:2].upper()
    return ""


def _event(name: str, org_id=None, country: str = "", **props) -> None:
    """Record a funnel event, best-effort: analytics must never break a request."""
    try:
        db.record_event(name, org_id=org_id, country=country, props=props or {})
    except Exception:
        logging.getLogger("attestly.events").exception("failed to record %s", name)


def _reject_if_oversized(data: bytes) -> None:
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {config.MAX_UPLOAD_MB} MB).",
        )


def public_answer(a: dict) -> dict:
    """Drop the stored embedding BLOB before returning an answer over the API."""
    return {k: v for k, v in a.items() if k != "embedding"}


def public_questionnaire(q: dict) -> dict:
    """Strip the stored source BLOB and expose a write-back availability flag."""
    out = {k: v for k, v in q.items() if k != "source_bytes"}
    out["can_export_original"] = export.can_export_original(q)
    return out


def usage_view(org: dict) -> dict:
    tier = config.TIERS[org["tier"]]
    is_free = org["tier"] == "free"
    period_remaining = max(tier["question_limit"] - org["questions_used"], 0)
    onboarding_remaining = (
        max(0, config.ONBOARDING_ALLOWANCE - db.domain_onboarding_used(db.email_domain(org.get("email"))))
        if is_free else 0
    )
    return {
        "org_id": org["id"],
        "name": org["name"],
        "tier": org["tier"],
        "tier_name": tier["name"],
        "questions_used": org["questions_used"],
        "question_limit": tier["question_limit"],
        "questions_remaining": period_remaining,
        # Total answers this account can run right now (onboarding pool + period).
        "onboarding_remaining": onboarding_remaining,
        "answers_remaining": onboarding_remaining + period_remaining,
        "bank_limit": tier["bank_limit"],
        "bank_size": db.count_answers(org["id"]),
        "doc_count": db.count_documents(org["id"]),
    }


# --------------------------------------------------------------------------
# Health / plans
# --------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "llm_enabled": config.LLM_ENABLED,
        "stripe_enabled": config.STRIPE_ENABLED,
        "embeddings_enabled": config.EMBEDDINGS_ENABLED,
        "storage": "postgres" if config.USE_POSTGRES else "sqlite",
    }


@app.get("/v1/plans")
def plans() -> dict:
    return {"plans": config.TIERS}


# --------------------------------------------------------------------------
# Readiness assessment (public — lead magnet / outbound asset)
# --------------------------------------------------------------------------
@app.post("/v1/assessment")
def assessment_json(body: dict, request: Request) -> dict:
    rate_limit(request, "assessment", config.RL_ASSESSMENT)
    company = (body.get("company") or "Your company").strip()
    signals = body.get("signals") or {}
    volume = int(body.get("monthly_questionnaires", 4) or 4)
    a = assess.score_company(company, signals, monthly_questionnaires=volume)
    if body.get("include_sample", True):
        a = assess.with_live_sample(a)
    return {
        "company": a.company,
        "score": a.score,
        "grade": a.grade,
        "grade_summary": a.grade_summary,
        "findings": [
            {"label": f.label, "ok": f.ok, "weight": f.weight, "note": f.note} for f in a.findings
        ],
        "monthly_questionnaires": a.monthly_questionnaires,
        "hours_saved_per_month": a.hours_saved_per_month,
        "annual_time_cost": a.annual_time_cost,
        "autoanswer_rate": a.autoanswer_rate,
        "sample": a.sample,
    }


@app.post("/v1/assessment/report")
def assessment_report(body: dict, request: Request) -> HTMLResponse:
    rate_limit(request, "assessment", config.RL_ASSESSMENT)
    company = (body.get("company") or "Your company").strip()
    signals = body.get("signals") or {}
    volume = int(body.get("monthly_questionnaires", 4) or 4)
    a = assess.score_company(company, signals, monthly_questionnaires=volume)
    if body.get("include_sample", True):
        a = assess.with_live_sample(a)
    return HTMLResponse(render_report(a, cta_url=body.get("cta_url", config.APP_BASE_URL)))


# --------------------------------------------------------------------------
# Signup / me
# --------------------------------------------------------------------------
@app.post("/v1/signup")
def signup(body: dict, request: Request) -> dict:
    rate_limit(request, "signup", config.RL_SIGNUP)
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not name:
        raise HTTPException(status_code=400, detail="Company name is required")
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="A valid work email is required")
    _domain = db.email_domain(email)
    if _domain in config.DISPOSABLE_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail="Disposable email addresses aren't supported. Please use a real inbox.",
        )
    if config.REQUIRE_WORK_EMAIL and _domain in config.FREE_CONSUMER_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail="Please sign up with your work email.",
        )
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.get_org_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists — log in instead")
    org = db.create_org(name=name, email=email, password_hash=passwords.hash_password(password))
    _event("signup_completed", org_id=org["id"], country=_client_country(request), domain=_domain)
    return {"org_id": org["id"], "api_token": org["api_token"], "tier": org["tier"]}


@app.post("/v1/login")
def login(body: dict, request: Request) -> dict:
    rate_limit(request, "login", config.RL_LOGIN)
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    org = db.get_org_by_email(email)
    # Same error whether the email or the password is wrong (no account enumeration).
    if not org or not org.get("password_hash") or not passwords.verify_password(password, org["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    # Only the token hash is stored, so we can't return the old token — mint a
    # fresh one for this login (invalidates any previously issued token).
    raw_token = db.rotate_token(org["id"])
    return {"org_id": org["id"], "api_token": raw_token, "tier": org["tier"]}


@app.post("/v1/password/forgot")
def password_forgot(body: dict, request: Request) -> dict:
    """Start a password reset. Always returns 200 with the same message whether
    or not the email exists, so it can't be used to enumerate accounts."""
    rate_limit(request, "password_forgot", config.RL_PASSWORD_FORGOT)
    email = (body.get("email") or "").strip().lower()
    generic = {"message": "If an account exists for that email, a reset link is on its way."}
    if "@" not in email:
        return generic
    org = db.get_org_by_email(email)
    if not org:
        return generic
    raw = tokens.PREFIX + secrets.token_urlsafe(32)
    db.create_password_reset(
        org["id"], tokens.hash_token(raw), time.time() + config.PASSWORD_RESET_TTL_SECONDS
    )
    reset_url = f"{config.APP_BASE_URL.rstrip('/')}/?reset={raw}"
    sent = email_svc.send_password_reset(email, reset_url)
    if not sent:
        # No email provider configured (or send failed): log the link so the
        # flow is still completable in dev. The link is a secret — this only
        # reaches whoever can read the server log, not the user's inbox.
        _spend_log.warning("Password reset for %s (email not sent): %s", email, reset_url)
    return generic


@app.post("/v1/password/reset")
def password_reset(body: dict, request: Request) -> dict:
    """Complete a password reset with the token from the emailed link."""
    rate_limit(request, "password_reset", config.RL_LOGIN)
    token = (body.get("token") or "").strip()
    new_password = body.get("password") or ""
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    row = db.get_valid_password_reset(tokens.hash_token(token)) if token else None
    if not row:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired. Request a new one.")
    db.consume_password_reset(row["id"])
    db.set_org_password(row["org_id"], passwords.hash_password(new_password))
    # A reset is also our lever against a compromised account: rotate the API
    # token so any previously issued token stops working, and return a fresh one
    # so the user is signed straight in.
    raw_token = db.rotate_token(row["org_id"])
    org = db.get_org(row["org_id"])
    return {"org_id": org["id"], "api_token": raw_token, "tier": org["tier"]}


@app.get("/v1/me")
def me(org: dict = Depends(require_org)) -> dict:
    return usage_view(org)


@app.post("/v1/token/rotate")
def rotate_token_endpoint(org: dict = Depends(require_org)) -> dict:
    """Revoke the current API token and issue a new one (e.g. if it leaked)."""
    return {"api_token": db.rotate_token(org["id"])}


@app.delete("/v1/account")
def delete_account(org: dict = Depends(require_org)) -> dict:
    """Right-to-delete: permanently remove this account and ALL of its data
    (questionnaires, documents, answer library, usage). Irreversible."""
    db.delete_org_data(org["id"])
    return {"deleted": True}


# --------------------------------------------------------------------------
# Answer Bank
# --------------------------------------------------------------------------
@app.get("/v1/answers")
def get_answers(org: dict = Depends(require_org)) -> dict:
    return {"answers": [public_answer(a) for a in db.list_answers(org["id"])]}


@app.post("/v1/answers")
def create_answer(body: dict, org: dict = Depends(require_org)) -> dict:
    q, a = (body.get("question") or "").strip(), (body.get("answer") or "").strip()
    if not q or not a:
        raise HTTPException(status_code=400, detail="question and answer are required")
    if db.count_answers(org["id"]) >= config.TIERS[org["tier"]]["bank_limit"]:
        raise HTTPException(status_code=402, detail="Answer Library limit reached for your plan")
    return public_answer(db.add_answer(org["id"], q, a, body.get("category", "general"), body.get("source", "manual")))


@app.post("/v1/answers/seed_starter")
def seed_starter(org: dict = Depends(require_org)) -> dict:
    """One-click: load the bundled 37-answer starter Library, deduped."""
    from . import seed

    limit = config.TIERS[org["tier"]]["bank_limit"]
    existing = db.list_answers(org["id"])
    seen = [b["question"] for b in existing]
    created = skipped = 0
    for e in seed.starter_entries():
        if db.count_answers(org["id"]) >= limit:
            break
        q = (e.get("question") or "").strip()
        a = (e.get("answer") or "").strip()
        if not q or not a:
            continue
        if any(retrieval_close(q, prev) for prev in seen):
            skipped += 1
            continue
        db.add_answer(org["id"], q, a, e.get("category", "general"), source="starter")
        seen.append(q)  # dedup within this batch too
        created += 1
    return {"created": created, "skipped": skipped, "bank_size": db.count_answers(org["id"])}


@app.post("/v1/answers/bulk")
def bulk_answers(body: dict, org: dict = Depends(require_org)) -> dict:
    rows = body.get("answers") or []
    created = 0
    limit = config.TIERS[org["tier"]]["bank_limit"]
    for row in rows:
        if db.count_answers(org["id"]) >= limit:
            break
        q, a = (row.get("question") or "").strip(), (row.get("answer") or "").strip()
        if q and a:
            db.add_answer(org["id"], q, a, row.get("category", "general"), row.get("source", "import"))
            created += 1
    return {"created": created, "bank_size": db.count_answers(org["id"])}


# --------------------------------------------------------------------------
# Trust documents (SOC 2, policies) — grounding sources for drafted answers
# --------------------------------------------------------------------------
@app.get("/v1/documents")
def get_documents(org: dict = Depends(require_org)) -> dict:
    return {
        "documents": db.list_documents(org["id"]),
        "embeddings_enabled": config.EMBEDDINGS_ENABLED,
    }


@app.post("/v1/documents")
async def upload_document(
    request: Request, file: UploadFile = File(...), org: dict = Depends(require_org)
) -> dict:
    rate_limit_request_and_account(request, "upload", org["id"], config.RL_UPLOAD)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty file")
    _reject_if_oversized(data)
    try:
        doc = documents.ingest(org["id"], file.filename or "document", data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    _event("source_doc_uploaded", org_id=org["id"], kind=doc.get("kind", ""),
           chunks=doc.get("chunk_count", 0))
    return {"document": doc}


@app.delete("/v1/documents/{doc_id}")
def delete_document(doc_id: int, org: dict = Depends(require_org)) -> dict:
    if not db.delete_document(org["id"], doc_id):
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


# --------------------------------------------------------------------------
# Questionnaires
# --------------------------------------------------------------------------
def _quota_state(org: dict) -> dict:
    """This account's answer allowance right now (onboarding pool + period)."""
    tier = config.TIERS[org["tier"]]
    is_free = org["tier"] == "free"
    domain = db.email_domain(org.get("email"))
    onboarding_remaining = (
        max(0, config.ONBOARDING_ALLOWANCE - db.domain_onboarding_used(domain)) if is_free else 0
    )
    period_remaining = max(0, tier["question_limit"] - org["questions_used"])
    return {
        "is_free": is_free,
        "domain": domain,
        "onboarding_remaining": onboarding_remaining,
        "period_remaining": period_remaining,
        "total_remaining": onboarding_remaining + period_remaining,
    }


@app.post("/v1/questionnaires")
async def upload_questionnaire(
    request: Request, file: UploadFile = File(...), org: dict = Depends(require_org)
) -> dict:
    """Triage step: parse and scope the questionnaire WITHOUT answering. Detects
    the framework, counts questions, shows how many the library already covers
    and how much quota the rest will use, and suggests out-of-scope rows to
    exclude. No model call, no quota consumed — answering happens on confirm via
    POST /v1/questionnaires/{id}/answer."""
    rate_limit_request_and_account(request, "upload", org["id"], config.RL_UPLOAD)
    data = await file.read()
    _reject_if_oversized(data)
    parsed = parsing.parse(file.filename or "upload.xlsx", data)
    if not parsed.questions:
        raise HTTPException(status_code=422, detail="No questions detected in the file")

    framework = triage.detect_framework(file.filename or "", parsed.questions)
    n_questions = len(parsed.questions)

    qid = db.create_questionnaire(
        org["id"], file.filename or "Questionnaire", file.filename or "", n_questions,
        source_bytes=data, source_kind=parsed.kind, sheet_name=parsed.sheet_name,
        question_col=parsed.question_col, answer_col=parsed.answer_col,
        detail_col=parsed.detail_col, framework=framework,
    )
    for eq in parsed.questions:
        db.add_item(qid, eq.row_index, eq.question, excel_row=eq.excel_row)

    # Coverage + out-of-scope: no model calls (library ranking + heuristics only).
    covered = triage.coverage_flags(org["id"], parsed.questions)
    suggestions = triage.out_of_scope_suggestions(org["id"], parsed.questions)
    covered_count = sum(covered)

    q = _quota_state(org)
    items = db.list_items(qid)
    # Attach the triage hints to each item (row order matches parsed.questions).
    for it, eq, is_covered in zip(items, parsed.questions, covered):
        it["covered"] = bool(is_covered)
        reason = suggestions.get(eq.row_index)
        it["suggested_exclude"] = reason is not None
        it["suggested_reason"] = reason or ""

    is_free = q["is_free"]
    no_docs = is_free and db.count_documents(org["id"]) == 0
    spend_paused = is_free and _free_tier_drafting_paused()

    # Answers the non-covered rows would consume (covered rows reuse for free).
    to_draft = n_questions - covered_count
    return {
        "questionnaire_id": qid,
        "phase": "triage",
        "framework": framework,
        "total_questions": n_questions,
        "library_covered": covered_count,
        "will_use_quota": to_draft,
        "suggested_exclusions": [it["id"] for it in items if it.get("suggested_exclude")],
        "onboarding_remaining": q["onboarding_remaining"],
        "period_remaining": q["period_remaining"],
        "answers_remaining": q["total_remaining"],
        "no_docs": no_docs,
        "spend_paused": spend_paused,
        "can_export_original": parsed.answer_col is not None,
        "source_kind": parsed.kind,
        "items": items,
    }


def _prepare_answer_run(qid: int, body: dict, org: dict) -> dict:
    """Shared setup for both the batch and streaming answer endpoints: apply
    exclusions, lock the over-quota overflow among unanswered rows, and resolve
    the drafting gate. Returns the run context."""
    exclude_ids = set()
    for ex in body.get("exclude") or []:
        iid = ex.get("id")
        if iid is None:
            continue
        db.set_item_exclusion(int(iid), True, (ex.get("reason") or "").strip())
        exclude_ids.add(int(iid))

    state = _quota_state(org)
    ordered = db.list_items(qid)
    unanswered = [
        it for it in ordered
        if it["id"] not in exclude_ids and not it.get("excluded") and not it.get("locked")
        and (it.get("match_type") or "none") in ("none", "blocked")
    ]
    over = unanswered[state["total_remaining"]:] if state["total_remaining"] < len(unanswered) else []
    db.lock_items([it["id"] for it in over])

    is_free = state["is_free"]
    spend_paused = is_free and _free_tier_drafting_paused()
    no_docs = is_free and db.count_documents(org["id"]) == 0
    allow_draft = not (no_docs or spend_paused)
    block_message = engine.BLOCKED_ANSWER
    if spend_paused:
        block_message = ("Free capacity for this month has been reached. Upgrade to keep drafting, "
                         "or try again next month.")
    # Rows we'll actually answer this run (after locking) — for a progress total.
    to_answer = len(unanswered) - len(over)
    return {"state": state, "allow_draft": allow_draft, "block_message": block_message,
            "spend_paused": spend_paused, "to_answer": to_answer}


def _finalize_answer_run(qid: int, q: dict, org: dict, ctx: dict, produced: list) -> dict:
    """Charge only this run's produced answers, then build the response summary."""
    state = ctx["state"]
    new_answered = sum(1 for it in produced if it.match_type in ("reuse", "drafted", "fallback"))
    from_onboarding = min(new_answered, state["onboarding_remaining"])
    db.consume_domain_onboarding(state["domain"], from_onboarding)
    if new_answered - from_onboarding > 0:
        db.increment_usage(org["id"], new_answered - from_onboarding)

    items = db.list_items(qid)
    reused = sum(1 for it in items if it["match_type"] == "reuse" and not it["locked"] and not it["excluded"])
    drafted = sum(1 for it in items if it["match_type"] in ("drafted", "fallback") and not it["locked"] and not it["excluded"])
    return {
        "questionnaire_id": qid,
        "phase": "answered",
        "framework": q.get("framework", ""),
        "total_questions": q.get("total_questions", len(items)),
        "answered": reused + drafted,
        "locked": sum(1 for it in items if it["locked"]),
        "blocked": sum(1 for it in items if it["match_type"] == "blocked"),
        "excluded": sum(1 for it in items if it["excluded"]),
        "reused_from_bank": reused,
        "drafted": drafted,
        "spend_paused": ctx["spend_paused"],
        "cost_usd": db.cost_for_questionnaire(qid)["cost_usd"],
        "can_export_original": bool(q.get("answer_col")),
        "source_kind": q.get("source_kind", "xlsx"),
        "items": items,
    }


@app.post("/v1/questionnaires/{qid}/answer")
def answer_questionnaire_endpoint(
    qid: int, body: dict, request: Request, org: dict = Depends(require_org)
) -> dict:
    """Answer a triaged questionnaire in one shot. Applies exclusions, partial-
    answers up to the remaining quota, locks the rest, and charges ONLY the
    answers produced in this run."""
    rate_limit_request_and_account(request, "answer", org["id"], config.RL_ANSWER)
    q = db.get_questionnaire(qid, org["id"])
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    ctx = _prepare_answer_run(qid, body, org)
    produced = engine.answer_questionnaire(
        org["id"], qid, allow_draft=ctx["allow_draft"], block_message=ctx["block_message"]
    )
    return _finalize_answer_run(qid, q, org, ctx, produced)


@app.post("/v1/questionnaires/{qid}/answer/stream")
def answer_questionnaire_stream(
    qid: int, body: dict, request: Request, org: dict = Depends(require_org)
) -> StreamingResponse:
    """Same as /answer, but streams NDJSON so the UI can show answers landing one
    by one: a `start` line, an `item` line per answer as it's ready, then a
    `done` line carrying the final summary."""
    rate_limit_request_and_account(request, "answer", org["id"], config.RL_ANSWER)
    q = db.get_questionnaire(qid, org["id"])
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    ctx = _prepare_answer_run(qid, body, org)

    def gen():
        yield json.dumps({"type": "start", "to_answer": ctx["to_answer"]}) + "\n"
        produced = []
        for ai in engine.stream_answer_questionnaire(
            org["id"], qid, allow_draft=ctx["allow_draft"], block_message=ctx["block_message"]
        ):
            produced.append(ai)
            item = db.get_item(ai.item_id) or {}
            yield json.dumps({"type": "item", "item": item}) + "\n"
        summary = _finalize_answer_run(qid, q, org, ctx, produced)
        yield json.dumps({"type": "done", "summary": summary}) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.post("/v1/questionnaires/{qid}/run")
def start_questionnaire_run(
    qid: int, body: dict, request: Request, org: dict = Depends(require_org)
) -> dict:
    """Start a DURABLE background run and return immediately. Answering happens in
    an in-process worker; each answer is persisted and charged the moment it lands,
    so closing the tab (or a deploy) never loses work. The client polls
    GET /v1/questionnaires/{id} for progress, and the run is re-openable from its
    URL. Applies exclusions and locks the over-quota overflow before starting."""
    rate_limit_request_and_account(request, "answer", org["id"], config.RL_ANSWER)
    q = db.get_questionnaire(qid, org["id"])
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    if runner.is_running(qid):
        items = db.list_items(qid)
        return {"questionnaire_id": qid, "phase": "running", "already_running": True,
                "progress": _run_progress(q, items)}

    ctx = _prepare_answer_run(qid, body, org)
    state = ctx["state"]
    started = runner.start_run(
        org["id"], qid, ctx["allow_draft"], ctx["block_message"],
        use_onboarding=state["is_free"], domain=state["domain"],
    )
    if started:
        # The sample is the top of the onboarding funnel, so it's its own event.
        ev = "sample_run_started" if body.get("sample") else "run_started"
        _event(ev, org_id=org["id"], questionnaire_id=qid, to_answer=ctx["to_answer"])
    q = db.get_questionnaire(qid, org["id"]) or q
    items = db.list_items(qid)
    return {
        "questionnaire_id": qid,
        "phase": "running",
        "started": started,
        "to_answer": ctx["to_answer"],
        "spend_paused": ctx["spend_paused"],
        "progress": _run_progress(q, items),
    }


def _run_progress(q: dict, items: list) -> dict:
    """Live per-row rollup for the poll: how many rows are answered, blocked,
    locked, excluded, or still pending, plus whether the run is finished."""
    answered = sum(1 for it in items
                   if it["match_type"] in ("reuse", "drafted", "fallback")
                   and not it["locked"] and not it["excluded"])
    blocked = sum(1 for it in items if it["match_type"] == "blocked")
    locked = sum(1 for it in items if it["locked"])
    excluded = sum(1 for it in items if it["excluded"])
    pending = sum(1 for it in items
                  if (it["match_type"] or "none") in ("none", "blocked")
                  and not it["locked"] and not it["excluded"])
    running = runner.is_running(q["id"]) or q.get("status") == "running"
    return {
        "status": q.get("status"),
        "running": running,
        "done": not running and q.get("status") in ("ready", "exported"),
        "total": len(items),
        "answered": answered,
        "blocked": blocked,
        "locked": locked,
        "excluded": excluded,
        "pending": pending,
    }


@app.get("/v1/usage/cost")
def usage_cost_view(org: dict = Depends(require_org)) -> dict:
    """This account's model spend: answers, tokens (with cached split), and USD."""
    return db.cost_summary(org["id"])


# --------------------------------------------------------------------------
# Internal analytics page (guarded by ATTESTLY_ADMIN_TOKEN)
# --------------------------------------------------------------------------
def _median(values: list) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _internal_metrics(days: int = 30) -> dict:
    since = time.time() - days * 86400
    wall = db.run_completed_wall_seconds_since(since, min_rows=100)
    med = _median(wall)
    return {
        "window_days": days,
        "counts": db.event_counts_since(since),
        "countries": db.event_country_split_since(since),
        "big_run_median_seconds": round(med, 1) if med is not None else None,
        "big_run_sample": len(wall),
    }


def _require_admin(key: str) -> None:
    """Gate the internal page. Disabled entirely (404) when no admin token is set,
    so it's never world-readable by default; wrong key is also 404 (no reveal)."""
    if not config.ADMIN_TOKEN or not key or not secrets.compare_digest(key, config.ADMIN_TOKEN):
        raise HTTPException(status_code=404, detail="Not found")


@app.get("/v1/internal/metrics")
def internal_metrics(key: str = "", days: int = 30) -> dict:
    _require_admin(key)
    return _internal_metrics(max(1, min(days, 365)))


@app.get("/internal", response_class=HTMLResponse)
def internal_page(key: str = "", days: int = 30) -> HTMLResponse:
    _require_admin(key)
    m = _internal_metrics(max(1, min(days, 365)))
    return HTMLResponse(_render_internal_html(m, key))


def _render_internal_html(m: dict, key: str) -> str:
    import html as _html

    c = m["counts"]
    order = [
        ("sample_run_started", "Sample runs started"),
        ("signup_completed", "Signups completed"),
        ("source_doc_uploaded", "Source docs uploaded"),
        ("run_started", "Runs started"),
        ("run_completed", "Runs completed"),
        ("export_downloaded", "Exports downloaded"),
    ]
    rows = "".join(
        f"<tr><td>{_html.escape(label)}</td><td class='n'>{c.get(k, 0)}</td></tr>"
        for k, label in order
    )
    if m["countries"]:
        countries = "".join(
            f"<tr><td>{_html.escape(str(r['country']))}</td><td class='n'>{r['n']}</td></tr>"
            for r in m["countries"]
        )
    else:
        countries = "<tr><td colspan='2' class='muted'>No signups in this window.</td></tr>"
    med = m["big_run_median_seconds"]
    med_txt = f"{med:.0f}s" if med is not None else "n/a"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Attestly internal metrics</title>
<style>
  body{{font:15px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
       margin:0;background:#0b1220;color:#e8eefc;padding:32px}}
  .wrap{{max-width:760px;margin:0 auto}}
  h1{{font-size:20px;margin:0 0 4px}}
  .muted{{color:#8ea0c0}} .small{{font-size:13px}}
  .cards{{display:flex;gap:16px;flex-wrap:wrap;margin:24px 0}}
  .card{{background:#131d33;border:1px solid #23324f;border-radius:12px;padding:18px 20px;flex:1;min-width:220px}}
  table{{width:100%;border-collapse:collapse}}
  th{{text-align:left;color:#8ea0c0;font-weight:600;font-size:13px;padding:6px 0;border-bottom:1px solid #23324f}}
  td{{padding:8px 0;border-bottom:1px solid #1a2740}}
  td.n{{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}}
  .big{{font-size:30px;font-weight:700}}
</style></head><body><div class="wrap">
<h1>Internal metrics</h1>
<div class="muted small">Trailing {m['window_days']} days. Own data, no third party.</div>
<div class="cards">
  <div class="card"><div class="muted small">Median wall-clock, runs &gt;100 rows</div>
    <div class="big">{med_txt}</div>
    <div class="muted small">{m['big_run_sample']} run(s) in window</div></div>
</div>
<div class="cards">
  <div class="card"><table><thead><tr><th>Event</th><th class="n">Count</th></tr></thead>
    <tbody>{rows}</tbody></table></div>
  <div class="card"><table><thead><tr><th>Signups by country</th><th class="n">Count</th></tr></thead>
    <tbody>{countries}</tbody></table></div>
</div>
<div class="muted small">Country is read from the CDN edge header (CF-IPCountry / X-Vercel-IP-Country);
'Unknown' when the API is reached directly, without a country-aware proxy in front.</div>
</div></body></html>"""


@app.get("/v1/questionnaires")
def list_questionnaires(org: dict = Depends(require_org)) -> dict:
    return {"questionnaires": [public_questionnaire(q) for q in db.list_questionnaires(org["id"])]}


@app.get("/v1/questionnaires/{qid}")
def get_questionnaire(qid: int, org: dict = Depends(require_org)) -> dict:
    q = db.get_questionnaire(qid, org["id"])
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    items = db.list_items(qid)
    return {"questionnaire": public_questionnaire(q), "items": items,
            "progress": _run_progress(q, items)}


@app.post("/v1/items/{item_id}/approve")
def approve_item(item_id: int, body: dict, org: dict = Depends(require_org)) -> dict:
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    q = db.get_questionnaire(item["questionnaire_id"], org["id"])
    if not q:
        raise HTTPException(status_code=403, detail="Not your item")

    final_answer = (body.get("answer") or item["answer"]).strip()
    db.approve_item(item_id, final_answer)

    # Compounding moat: approved answers flow back into the Bank (deduped by
    # near-exact question match).
    added = False
    if final_answer and body.get("save_to_bank", True):
        bank = db.list_answers(org["id"])
        already = any(
            retrieval_close(item["question"], b["question"]) for b in bank
        )
        if not already and db.count_answers(org["id"]) < config.TIERS[org["tier"]]["bank_limit"]:
            db.add_answer(org["id"], item["question"], final_answer, source="questionnaire")
            added = True
    return {"approved": True, "saved_to_bank": added}


def _require_item(item_id: int, org: dict) -> dict:
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not db.get_questionnaire(item["questionnaire_id"], org["id"]):
        raise HTTPException(status_code=403, detail="Not your item")
    return item


@app.post("/v1/items/{item_id}/remediation")
def set_item_remediation(item_id: int, body: dict, org: dict = Depends(require_org)) -> dict:
    """Attach what a negative ('No') or 'N/A' answer needs before it can export:
    a remediation date, an explicit no-plan acknowledgement, or an N/A reason."""
    _require_item(item_id, org)
    db.set_item_remediation(
        item_id,
        remediation_date=(body.get("remediation_date") or "").strip(),
        no_plan=bool(body.get("no_plan")),
        na_reason=(body.get("na_reason") or "").strip(),
    )
    return {"ok": True}


@app.post("/v1/items/{item_id}/resolve_contradiction")
def resolve_contradiction(item_id: int, body: dict, org: dict = Depends(require_org)) -> dict:
    """Resolve a flagged contradiction between a drafted answer and the approved
    library answer for the same question. keep='new' updates the library to the
    new answer (with a dated change note); keep='prior' reverts the item to the
    library answer. Either way the flag clears."""
    import json as _json

    item = _require_item(item_id, org)
    try:
        data = _json.loads(item.get("contradiction") or "{}")
    except (ValueError, TypeError):
        data = {}
    if not data:
        return {"resolved": True}  # nothing to do

    keep = (body.get("keep") or "new").strip().lower()
    answer_id = data.get("answer_id")
    if keep == "prior":
        prior = data.get("prior_answer") or ""
        db.set_item_answer_text(item_id, prior, engine.infer_choice(prior))
    else:  # keep the new answer -> update the library entry so it's now current
        if answer_id and db.get_answer(answer_id):
            note = body.get("note") or "Updated from a questionnaire answer"
            db.update_answer(answer_id, item.get("answer") or data.get("new_answer") or "", note)
    db.set_item_contradiction(item_id, None)
    return {"resolved": True, "kept": keep}


def retrieval_close(a: str, b: str) -> bool:
    from . import fuzzy

    return fuzzy.token_set_ratio(a, b) >= 95


@app.get("/v1/questionnaires/{qid}/export")
def export_questionnaire(
    qid: int, original: bool = False, org: dict = Depends(require_org)
) -> StreamingResponse:
    q = db.get_questionnaire(qid, org["id"])
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    items = db.list_items(qid)

    # A negative ('No') needs a remediation date or an explicit no-plan
    # acknowledgement, and an 'N/A' needs a reason, before it can leave the tool
    # — no export contains a bare 'No' or 'N/A'.
    issues = export.gate_issues(items)
    if issues:
        return JSONResponse(
            status_code=409,
            content={
                "detail": (f"{len(issues)} row(s) need a remediation date or a reason before "
                           "you can export. Add them on the flagged rows, then export again."),
                "unresolved": issues,
            },
        )
    base = q["name"].rsplit(".", 1)[0] or "responses"

    # "Filled original" returns the customer's own template with cells filled;
    # falls back to the clean workbook when we didn't capture the source.
    if original and export.can_export_original(q):
        data = export.export_original(q, items)
        if (q.get("source_kind") or "xlsx").lower() == "csv":
            media_type, filename = "text/csv", f"{base}_filled.csv"
        else:
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{base}_filled.xlsx"
    else:
        data = export.export_simple(q["name"], items)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{base}_answers.xlsx"

    db.set_questionnaire_status(qid, "exported")
    _event("export_downloaded", org_id=org["id"], questionnaire_id=qid,
           original=bool(original and export.can_export_original(q)))
    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --------------------------------------------------------------------------
# Billing
# --------------------------------------------------------------------------
@app.post("/v1/billing/checkout")
def checkout(body: dict, org: dict = Depends(require_org)) -> dict:
    tier = (body.get("tier") or "").strip()
    interval = (body.get("interval") or "month").strip()
    try:
        return billing.create_checkout(org, tier, interval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/billing/confirm")
def confirm(body: dict, org: dict = Depends(require_org)) -> dict:
    """Confirm a *simulated* upgrade (Stripe-disabled environments only)."""
    tier = (body.get("tier") or "").strip()
    try:
        billing.confirm_simulated_upgrade(org["id"], tier)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return usage_view(db.get_org(org["id"]))


@app.post("/v1/stripe/webhook")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None)) -> JSONResponse:
    payload = await request.body()
    try:
        result = billing.handle_webhook(payload, stripe_signature)
    except billing.WebhookError as e:
        # Untrusted event — reject and do nothing.
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(result)
