"""Attestly HTTP API (FastAPI).

Self-serve: an org signs up, gets an API token, builds an Answer Bank, then
uploads questionnaires that come back auto-answered. Metering enforces plan
limits; billing is self-serve via Stripe Checkout.
"""
from __future__ import annotations

import io

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from . import __version__, assessment as assess, billing, config, db, documents, engine, export, parsing, passwords
from .report import render as render_report


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


# Also initialise at import so TestClient (no lifespan) and scripts work.
db.init_db()

app = FastAPI(title="Attestly API", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return {
        "org_id": org["id"],
        "name": org["name"],
        "tier": org["tier"],
        "tier_name": tier["name"],
        "questions_used": org["questions_used"],
        "question_limit": tier["question_limit"],
        "questions_remaining": max(tier["question_limit"] - org["questions_used"], 0),
        "bank_limit": tier["bank_limit"],
        "bank_size": db.count_answers(org["id"]),
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
    }


@app.get("/v1/plans")
def plans() -> dict:
    return {"plans": config.TIERS}


# --------------------------------------------------------------------------
# Readiness assessment (public — lead magnet / outbound asset)
# --------------------------------------------------------------------------
@app.post("/v1/assessment")
def assessment_json(body: dict) -> dict:
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
def assessment_report(body: dict) -> HTMLResponse:
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
def signup(body: dict) -> dict:
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not name:
        raise HTTPException(status_code=400, detail="Company name is required")
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="A valid work email is required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.get_org_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists — log in instead")
    org = db.create_org(name=name, email=email, password_hash=passwords.hash_password(password))
    return {"org_id": org["id"], "api_token": org["api_token"], "tier": org["tier"]}


@app.post("/v1/login")
def login(body: dict) -> dict:
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    org = db.get_org_by_email(email)
    # Same error whether the email or the password is wrong (no account enumeration).
    if not org or not org.get("password_hash") or not passwords.verify_password(password, org["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"org_id": org["id"], "api_token": org["api_token"], "tier": org["tier"]}


@app.get("/v1/me")
def me(org: dict = Depends(require_org)) -> dict:
    return usage_view(org)


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
async def upload_document(file: UploadFile = File(...), org: dict = Depends(require_org)) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty file")
    _reject_if_oversized(data)
    try:
        doc = documents.ingest(org["id"], file.filename or "document", data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"document": doc}


@app.delete("/v1/documents/{doc_id}")
def delete_document(doc_id: int, org: dict = Depends(require_org)) -> dict:
    if not db.delete_document(org["id"], doc_id):
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


# --------------------------------------------------------------------------
# Questionnaires
# --------------------------------------------------------------------------
@app.post("/v1/questionnaires")
async def upload_questionnaire(
    file: UploadFile = File(...), org: dict = Depends(require_org)
) -> dict:
    data = await file.read()
    _reject_if_oversized(data)
    parsed = parsing.parse(file.filename or "upload.xlsx", data)
    if not parsed.questions:
        raise HTTPException(status_code=422, detail="No questions detected in the file")

    # Metering: enforce the plan's question allowance.
    tier = config.TIERS[org["tier"]]
    remaining = tier["question_limit"] - org["questions_used"]
    if remaining <= 0:
        raise HTTPException(status_code=402, detail="Monthly question limit reached — upgrade your plan")
    n_questions = len(parsed.questions)
    if n_questions > remaining:
        raise HTTPException(
            status_code=402,
            detail=f"This questionnaire has {n_questions} questions but only {remaining} "
            f"remain on your plan this period.",
        )

    qid = db.create_questionnaire(
        org["id"], file.filename or "Questionnaire", file.filename or "", n_questions,
        source_bytes=data, source_kind=parsed.kind, sheet_name=parsed.sheet_name,
        question_col=parsed.question_col, answer_col=parsed.answer_col,
        detail_col=parsed.detail_col,
    )
    for eq in parsed.questions:
        db.add_item(qid, eq.row_index, eq.question, excel_row=eq.excel_row)

    engine.answer_questionnaire(org["id"], qid)
    db.increment_usage(org["id"], n_questions)

    items = db.list_items(qid)
    reused = sum(1 for it in items if it["match_type"] == "reuse")
    return {
        "questionnaire_id": qid,
        "total_questions": n_questions,
        "reused_from_bank": reused,
        "drafted": n_questions - reused,
        "can_export_original": parsed.answer_col is not None,
        "source_kind": parsed.kind,
        "items": items,
    }


@app.get("/v1/questionnaires")
def list_questionnaires(org: dict = Depends(require_org)) -> dict:
    return {"questionnaires": [public_questionnaire(q) for q in db.list_questionnaires(org["id"])]}


@app.get("/v1/questionnaires/{qid}")
def get_questionnaire(qid: int, org: dict = Depends(require_org)) -> dict:
    q = db.get_questionnaire(qid, org["id"])
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    return {"questionnaire": public_questionnaire(q), "items": db.list_items(qid)}


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
    result = billing.handle_webhook(payload, stripe_signature)
    return JSONResponse(result)
