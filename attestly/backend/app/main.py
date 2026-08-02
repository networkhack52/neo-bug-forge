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
from fastapi.responses import JSONResponse, StreamingResponse

from . import __version__, billing, config, db, engine, export, parsing


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
    }


@app.get("/v1/plans")
def plans() -> dict:
    return {"plans": config.TIERS}


# --------------------------------------------------------------------------
# Signup / me
# --------------------------------------------------------------------------
@app.post("/v1/signup")
def signup(body: dict) -> dict:
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    org = db.create_org(name=name, email=body.get("email"))
    return {"org_id": org["id"], "api_token": org["api_token"], "tier": org["tier"]}


@app.get("/v1/me")
def me(org: dict = Depends(require_org)) -> dict:
    return usage_view(org)


# --------------------------------------------------------------------------
# Answer Bank
# --------------------------------------------------------------------------
@app.get("/v1/answers")
def get_answers(org: dict = Depends(require_org)) -> dict:
    return {"answers": db.list_answers(org["id"])}


@app.post("/v1/answers")
def create_answer(body: dict, org: dict = Depends(require_org)) -> dict:
    q, a = (body.get("question") or "").strip(), (body.get("answer") or "").strip()
    if not q or not a:
        raise HTTPException(status_code=400, detail="question and answer are required")
    if db.count_answers(org["id"]) >= config.TIERS[org["tier"]]["bank_limit"]:
        raise HTTPException(status_code=402, detail="Answer Bank limit reached for your plan")
    return db.add_answer(org["id"], q, a, body.get("category", "general"), body.get("source", "manual"))


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
# Questionnaires
# --------------------------------------------------------------------------
@app.post("/v1/questionnaires")
async def upload_questionnaire(
    file: UploadFile = File(...), org: dict = Depends(require_org)
) -> dict:
    data = await file.read()
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

    qid = db.create_questionnaire(org["id"], file.filename or "Questionnaire", file.filename or "", n_questions)
    for eq in parsed.questions:
        db.add_item(qid, eq.row_index, eq.question)

    engine.answer_questionnaire(org["id"], qid)
    db.increment_usage(org["id"], n_questions)

    items = db.list_items(qid)
    reused = sum(1 for it in items if it["match_type"] == "reuse")
    return {
        "questionnaire_id": qid,
        "total_questions": n_questions,
        "reused_from_bank": reused,
        "drafted": n_questions - reused,
        "items": items,
    }


@app.get("/v1/questionnaires")
def list_questionnaires(org: dict = Depends(require_org)) -> dict:
    return {"questionnaires": db.list_questionnaires(org["id"])}


@app.get("/v1/questionnaires/{qid}")
def get_questionnaire(qid: int, org: dict = Depends(require_org)) -> dict:
    q = db.get_questionnaire(qid, org["id"])
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    return {"questionnaire": q, "items": db.list_items(qid)}


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
    from rapidfuzz import fuzz

    return fuzz.token_set_ratio(a, b) >= 95


@app.get("/v1/questionnaires/{qid}/export")
def export_questionnaire(qid: int, org: dict = Depends(require_org)) -> StreamingResponse:
    q = db.get_questionnaire(qid, org["id"])
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    items = db.list_items(qid)
    data = export.export_simple(q["name"], items)
    db.set_questionnaire_status(qid, "exported")
    filename = (q["name"].rsplit(".", 1)[0] or "responses") + "_answers.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --------------------------------------------------------------------------
# Billing
# --------------------------------------------------------------------------
@app.post("/v1/billing/checkout")
def checkout(body: dict, org: dict = Depends(require_org)) -> dict:
    tier = (body.get("tier") or "").strip()
    try:
        return billing.create_checkout(org, tier)
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
