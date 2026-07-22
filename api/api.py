"""
api.py  —  Neo Bug Forge REST API
===================================
Production-ready FastAPI microservice.

Endpoints:
  POST /v1/fix          → fix a bug (requires X-API-Key header)
  POST /v1/fix/public   → fix a bug (no auth, 10 req/day per IP)
  GET  /v1/fix/{fix_id} → retrieve a previous fix by ID
  GET  /health          → liveness probe
  GET  /                → API info + quick-start

Run locally:
  pip install -r requirements.txt
  cp .env.example .env   # fill in your keys
  uvicorn api:app --reload --port 8000

Deploy to Railway:
  railway login && railway up
"""

import os
import json
import time
import hashlib
import hmac
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Literal
from contextlib import asynccontextmanager

import httpx
import stripe
import anthropic
from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_SECRET_KEY    = os.environ.get("API_SECRET_KEY", "dev-secret-change-in-prod")
ENVIRONMENT       = os.environ.get("ENVIRONMENT", "development")
SUPABASE_URL      = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY      = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
STRIPE_SECRET_KEY    = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_PRO  = os.environ.get("STRIPE_PRICE_PRO", "")   # price_xxx for Pro $12/mo
STRIPE_PRICE_TEAM = os.environ.get("STRIPE_PRICE_TEAM", "")  # price_xxx for Team $49/mo
ADMIN_EMAIL       = os.environ.get("ADMIN_EMAIL", "ya7308312@gmail.com")
MODEL             = "claude-haiku-4-5-20251001"
MAX_TOKENS        = 16000

from database import lookup_api_key, check_and_increment_quota, save_fix, get_fix_by_id

# ─── Rate limiter ─────────────────────────────────────────────────────────────
# Render (and most PaaS) sit behind a reverse proxy. get_remote_address returns
# the internal proxy IP, meaning ALL users share one bucket. Use X-Forwarded-For
# so each real user gets their own rate-limit counter.
def get_real_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

limiter = Limiter(key_func=get_real_ip)

# ─── Pydantic models ──────────────────────────────────────────────────────────

class FixRequest(BaseModel):
    broken_code:   str = Field(..., min_length=1, max_length=50_000)
    error_message: str = Field("",  max_length=5_000)
    language:      str = Field("",  max_length=50)

    @field_validator("broken_code")
    @classmethod
    def code_not_blank(cls, v):
        if not v.strip():
            raise ValueError("broken_code must not be blank")
        return v


class FixResponse(BaseModel):
    fix_id:      str
    fixed_code:  str
    explanation: str
    root_cause:  str
    confidence:  int
    diff:        str
    test_case:   str
    language:    str
    created_at:  str
    share_url:   str


class HealthResponse(BaseModel):
    status:               str
    environment:          str
    timestamp:            str
    anthropic_configured: bool


class ReadRequest(BaseModel):
    code:     str = Field(..., min_length=1, max_length=50_000)
    language: str = Field("", max_length=50)

    @field_validator("code")
    @classmethod
    def code_not_blank(cls, v):
        if not v.strip():
            raise ValueError("code must not be blank")
        return v


class ReadResponse(BaseModel):
    summary:          str
    what_it_does:     str
    potential_issues: list[str]
    complexity:       str   # "low" | "medium" | "high"
    language:         str


# ─── App lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not ANTHROPIC_API_KEY:
        print("[!] WARNING: ANTHROPIC_API_KEY not set")
    else:
        print(f"[+] Anthropic configured ({ANTHROPIC_API_KEY[:12]}...)")
    print(f"[+] Neo Bug Forge API [{ENVIRONMENT}] ready")
    yield
    print("Neo Bug Forge API shutting down.")


app = FastAPI(
    title="Neo Bug Forge API",
    description="AI-powered code bug fixer. Paste broken code → get fixed code, diff, and test case.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = ["*"] if ENVIRONMENT == "development" else [
    "https://neo-bug-forge-web.vercel.app",
    "https://www.neobugforge.io",
    "https://app.neobugforge.io",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─── Auth ─────────────────────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> dict:
    if not x_api_key.startswith("nbf_") or len(x_api_key) < 20:
        raise HTTPException(status_code=401, detail="Invalid API key format.")
    key_row = lookup_api_key(x_api_key)
    if not key_row:
        raise HTTPException(status_code=401, detail="API key not found or inactive.")
    return key_row


async def verify_supabase_token(authorization: str) -> dict:
    """Verify a Supabase JWT by calling the Supabase auth API."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required.")
    token = authorization.removeprefix("Bearer ").strip()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_KEY},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired Supabase token.")
    return resp.json()  # contains id, email, etc.

# ─── Response helpers ─────────────────────────────────────────────────────────

def strip_code_fences(raw: str) -> str:
    """Remove a leading ```/```json fence and a trailing ``` fence from a model
    response, then strip surrounding whitespace.

    Uses prefix/suffix removal rather than ``str.strip("```json")``, which treats
    its argument as a *set of characters* and would eat any leading ``j``/``s``/
    ``o``/``n``/backtick or trailing backtick that legitimately belongs to the
    content (e.g. code beginning with ``json.loads(...)``).
    """
    text = raw.strip()
    if text.startswith("```"):
        # Drop the opening fence line (```, ```json, ```python, …).
        newline = text.find("\n")
        text = text[newline + 1:] if newline != -1 else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ─── Prompt ───────────────────────────────────────────────────────────────────

def build_prompt(code: str, error: str, language: str) -> str:
    # Skip diff for large files to stay within token limits
    large_file = len(code) > 3000
    if large_file:
        json_shape = """{
  "fixed_code":  "<complete corrected code>",
  "explanation": "<TEACH, don't just describe. 3-6 sentences: name the underlying concept, explain WHY a developer hits this (the mental-model gap behind it), and what to watch for next time. If more than one legitimate fix exists, say so and explain how to choose between them.>",
  "root_cause":  "<one of: null_reference|type_mismatch|off_by_one|async_race|scope_error|logic_error|syntax_error|import_error|index_error|other>",
  "confidence":  <integer 0-100>,
  "diff":        "",
  "test_case":   "<minimal unit test in the same language>"
}"""
    else:
        json_shape = """{
  "fixed_code":  "<complete corrected code>",
  "explanation": "<TEACH, don't just describe. 3-6 sentences: name the underlying concept, explain WHY a developer hits this (the mental-model gap behind it), and what to watch for next time. If more than one legitimate fix exists, say so and explain how to choose between them.>",
  "root_cause":  "<one of: null_reference|type_mismatch|off_by_one|async_race|scope_error|logic_error|syntax_error|import_error|index_error|other>",
  "confidence":  <integer 0-100>,
  "diff":        "<unified diff, --- original, +++ fixed>",
  "test_case":   "<minimal unit test in the same language>"
}"""

    return f"""You are a patient, expert programming teacher and debugger specializing in {language or "multiple languages"}. You don't just repair code — you make sure the developer UNDERSTANDS why it broke, so they can avoid the whole class of bug next time.

A developer has submitted broken code and its error message.

Tasks:
1. Identify the exact root cause.
2. Fix the code without changing original intent or logic.
3. IMPORTANT — if the bug can be legitimately fixed in more than one way (for example, changing the caller vs. changing the function itself), pick the fix that best preserves the apparent intent, and explicitly say in the explanation that an alternative exists and how to decide between them. Never silently choose for the developer when the choice depends on what they meant.
4. Generate a minimal unit test that would have caught this bug. Begin the test with a one-line comment stating what it catches and why, so the developer learns what makes a good regression test.
5. Return ONLY a raw JSON object — no markdown, no extra text.

ACCURACY RULES (critical — a confident falsehood is worse than saying nothing):
- State only language behavior you are CERTAIN of. If unsure exactly how something behaves at runtime, describe it generally or omit it — never invent a mechanism to sound thorough.
- Never reference code elements that are not present. Do not mention docstrings, comments, type hints, variables, or functions that do not literally appear in the submitted code.
- Describe what an operation DOES (e.g. "raises TypeError because integers are not iterable"), not an imagined internal process.
- If a claim would need verification to be safe to teach, leave it out. Completeness never outranks correctness.
- Verify any arithmetic in your test assertions before writing them.

Required JSON shape (all fields mandatory):
{json_shape}

--- LANGUAGE: {language or "auto-detect"} ---

--- BROKEN CODE ---
{code}

--- ERROR MESSAGE ---
{error or "(none provided)"}

Respond with raw JSON only."""


def run_fix(code: str, error: str, language: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured on the server.")

    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": build_prompt(code, error, language)}],
        )
    except anthropic.AuthenticationError:
        raise ValueError("Server API key is invalid.")
    except anthropic.RateLimitError:
        raise RuntimeError("Upstream rate limit hit. Try again shortly.")
    except anthropic.APIConnectionError:
        raise RuntimeError("Could not reach Claude API.")
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Claude API error {e.status_code}: {e.message}")

    raw = strip_code_fences(message.content[0].text)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned non-JSON: {raw[:200]}") from exc

    for key in ("fixed_code", "explanation", "root_cause", "confidence", "diff", "test_case"):
        if key not in result:
            raise ValueError(f"Response missing field: {key}")

    return result

def build_read_prompt(code: str, language: str) -> str:
    return f"""You are a patient, expert programming teacher explaining {language or "code"} to a developer who wants to genuinely UNDERSTAND it — not just get a summary. Your goal is that after reading, they could confidently write similar code themselves and recognize this pattern next time. Return ONLY a raw JSON object — no markdown, no extra text.

Teaching principles:
- Explain the WHY, not just the WHAT. Name the underlying concept and teach the category, not only this instance.
- Call out any non-obvious language behavior a learner would miss (e.g. which exceptions a built-in can raise, why a construct is used, what a keyword actually does under the hood).
- Write in plain, concrete English for a motivated junior developer. Never condescending, never hand-wavy.

ACCURACY RULES (critical — a confident falsehood is worse than saying nothing):
- State only language behavior you are CERTAIN of. If you are not sure exactly how something behaves at runtime, describe it generally or omit it — never invent a mechanism to sound thorough.
- Never reference code elements that are not present. Do not mention docstrings, comments, type hints, variables, or functions that do not literally appear in the code shown.
- Describe what an operation DOES (e.g. "raises TypeError"), not an imagined internal process. Do not speculate about how the interpreter works unless it is a well-established fact.
- If a claim would need verification to be safe to teach, leave it out. Completeness never outranks correctness.

Required JSON shape (all fields mandatory):
{{
  "summary":          "<one plain sentence: what this code does>",
  "what_it_does":     "<a teaching explanation, 4-8 sentences. Name the key concept(s) at work and explain WHY the code is written this way, so the reader learns the pattern. Explain any subtle language behavior. Aim to leave them understanding, not just informed.>",
  "potential_issues": ["<learning-oriented notes: the mistakes or misunderstandings a developer commonly has with this code or pattern, phrased to teach how to recognize and avoid them. Include any genuine bugs or risks too. Up to 5 items; empty array [] if none.>"],
  "complexity":       "<low|medium|high>"
}}

--- LANGUAGE: {language or "auto-detect"} ---

--- CODE ---
{code}

Respond with raw JSON only."""


def run_read(code: str, language: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured on the server.")

    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1536,
            messages=[{"role": "user", "content": build_read_prompt(code, language)}],
        )
    except anthropic.AuthenticationError:
        raise ValueError("Server API key is invalid.")
    except anthropic.RateLimitError:
        raise RuntimeError("Upstream rate limit hit. Try again shortly.")
    except anthropic.APIConnectionError:
        raise RuntimeError("Could not reach Claude API.")
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Claude API error {e.status_code}: {e.message}")

    raw = strip_code_fences(message.content[0].text)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned non-JSON: {raw[:200]}") from exc

    for key in ("summary", "what_it_does", "potential_issues", "complexity"):
        if key not in result:
            raise ValueError(f"Response missing field: {key}")

    return result


# ─── Routes ───────────────────────────────────────────────────────────────────

class UsageResponse(BaseModel):
    tier:         str
    fixes_used:   int
    fixes_limit:  int
    remaining:    int
    tokens_used:  int
    is_unlimited: bool


class CreateKeyRequest(BaseModel):
    email: Optional[str] = None
    label: Optional[str] = "default"

class CreateKeyResponse(BaseModel):
    api_key:    str
    email:      str
    tier:       str
    fixes_limit: int
    fixes_used: int
    message:    str


@app.post("/v1/keys", response_model=CreateKeyResponse, tags=["Keys"],
          summary="Get or create an API key for the authenticated user")
@limiter.limit("20/hour")
async def create_key(request: Request, body: CreateKeyRequest,
                     authorization: Optional[str] = Header(None)):
    import secrets
    from database import get_db, hash_key

    # Resolve user identity
    if authorization and authorization.startswith("Bearer "):
        user      = await verify_supabase_token(authorization)
        user_email = user["email"]
        user_id    = user["id"]
    elif body.email:
        user_email = body.email
        user_id    = None
    else:
        raise HTTPException(status_code=401, detail="Authentication required.")

    db = get_db()

    # Return existing key if present
    existing = db.table("api_keys").select("*").eq("user_email", user_email).execute()
    if existing.data:
        row = existing.data[0]
        return CreateKeyResponse(
            api_key     = row.get("raw_key") or "nbf_" + row["key_hash"][:32],
            email       = user_email,
            tier        = row["tier"],
            fixes_limit = row["fixes_limit"],
            fixes_used  = row.get("fixes_used", 0),
            message     = "Existing key retrieved.",
        )

    # Create new key
    raw_key = "nbf_" + secrets.token_urlsafe(32)
    db.table("api_keys").insert({
        "key_hash":          hash_key(raw_key),
        "raw_key":           raw_key,
        "user_email":        user_email,
        "supabase_user_id":  user_id,
        "tier":              "free",
        "fixes_limit":       100,
    }).execute()

    return CreateKeyResponse(
        api_key     = raw_key,
        email       = user_email,
        tier        = "free",
        fixes_limit = 100,
        fixes_used  = 0,
        message     = "API key created.",
    )


@app.get("/v1/usage", response_model=UsageResponse, tags=["Usage"],
         summary="Get current quota and usage for your API key")
async def get_usage(authorization: Optional[str] = Header(None),
                    x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    from database import get_db
    if authorization and authorization.startswith("Bearer "):
        user    = await verify_supabase_token(authorization)
        db      = get_db()
        res     = db.table("api_keys").select("*").eq("user_email", user["email"]).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="No API key found for this user.")
        key_row = res.data[0]
    elif x_api_key:
        key_row = verify_api_key(x_api_key)
    else:
        raise HTTPException(status_code=401, detail="Authentication required.")
    is_unlimited = key_row["tier"] == "team"
    fixes_limit  = key_row["fixes_limit"]
    fixes_used   = key_row["fixes_used"]
    return UsageResponse(
        tier         = key_row["tier"],
        fixes_used   = fixes_used,
        fixes_limit  = fixes_limit,
        remaining    = 999999 if is_unlimited else max(0, fixes_limit - fixes_used),
        tokens_used  = key_row["tokens_used"],
        is_unlimited = is_unlimited,
    )


@app.get("/", tags=["Meta"])
def root():
    return {
        "name": "Neo Bug Forge API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "public_fix":    "POST /v1/fix/public   (10 req/day, no auth)",
            "authenticated": "POST /v1/fix          (requires X-API-Key header)",
            "read":          "POST /v1/read/public  (15 req/day, explain code, no auth)",
            "retrieve":      "GET  /v1/fix/{fix_id}",
            "health":        "GET  /health",
        },
        "quick_start": "curl -X POST https://api.neobugforge.io/v1/fix/public -H 'Content-Type: application/json' -d '{\"broken_code\":\"def f(): return 1/0\",\"error_message\":\"ZeroDivisionError\",\"language\":\"python\"}'"
    }


@app.get("/health", response_model=HealthResponse, tags=["Meta"])
def health():
    return HealthResponse(
        status="ok",
        environment=ENVIRONMENT,
        timestamp=datetime.utcnow().isoformat() + "Z",
        anthropic_configured=bool(ANTHROPIC_API_KEY),
    )


@app.post("/v1/fix", response_model=FixResponse, tags=["Fix"],
          summary="Fix a bug (authenticated — quota-based)")
@limiter.limit("120/minute")
async def fix_authenticated(request: Request, body: FixRequest,
                             key_row: dict = Depends(verify_api_key)):
    real_ip = get_real_ip(request)
    try:
        device = hashlib.sha256(str(key_row.get("id", "unknown")).encode()).hexdigest()[:8]
    except Exception:
        device = "unknown"
    print(f"[REAL_USER] fix/auth device={device} ip={real_ip} tier={key_row.get('tier','?')} lang={body.language or 'auto'}")
    return await _process_fix(body, key_row=key_row)


@app.post("/v1/fix/public", response_model=FixResponse, tags=["Fix"],
          summary="Fix a bug (public — 10 req/day per IP)")
@limiter.limit("10/day")
async def fix_public(request: Request, body: FixRequest):
    real_ip    = get_real_ip(request)
    raw_id     = request.headers.get("x-install-id", "")
    device     = hashlib.sha256(raw_id.encode()).hexdigest()[:8] if raw_id else "unknown"
    print(f"[REAL_USER] fix/public device={device} ip={real_ip} lang={body.language or 'auto'}")
    return await _process_fix(body)


@app.post("/v1/read/public", response_model=ReadResponse, tags=["Read"],
          summary="Explain code (public — 15 req/day per IP, uses Haiku)")
@limiter.limit("15/day")
async def read_public(request: Request, body: ReadRequest):
    """
    Explain what a piece of code does without fixing it.
    Returns a summary, detailed explanation, potential issues, and complexity rating.
    No API key required — rate-limited to 15 requests/day per IP.
    """
    try:
        result = await asyncio.to_thread(run_read, body.code, body.language)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    lang    = body.language or result.get("language", "auto")
    real_ip = get_real_ip(request)
    raw_id  = request.headers.get("x-install-id", "")
    device  = hashlib.sha256(raw_id.encode()).hexdigest()[:8] if raw_id else "unknown"
    print(f"[REAL_USER] read/public device={device} ip={real_ip} lang={lang} complexity={result.get('complexity')}")

    return ReadResponse(
        summary          = result["summary"],
        what_it_does     = result["what_it_does"],
        potential_issues = result.get("potential_issues", []),
        complexity       = result.get("complexity", "medium"),
        language         = lang,
    )


@app.get("/v1/fix/{fix_id}", response_model=FixResponse, tags=["Fix"],
         summary="Retrieve a previous fix by ID")
async def get_fix(fix_id: str):
    fix = get_fix_by_id(fix_id)
    if not fix:
        raise HTTPException(status_code=404, detail=f"Fix '{fix_id}' not found.")
    return fix

# ─── Shared processing ────────────────────────────────────────────────────────

async def _process_fix(body: FixRequest, key_row: dict | None = None) -> FixResponse:
    fix_id = str(uuid.uuid4())[:8]
    start  = time.time()

    # Quota check for authenticated users
    if key_row:
        allowed, remaining = check_and_increment_quota(
            key_row["id"], key_row["tier"], key_row["fixes_limit"]
        )
        if not allowed:
            raise HTTPException(
                status_code=402,
                detail=f"Quota exhausted ({key_row['fixes_limit']} fixes). Upgrade your plan."
            )

    try:
        result = await asyncio.to_thread(
            run_fix, body.broken_code, body.error_message, body.language
        )
    except ValueError as e:
        # Rollback quota on AI failure
        if key_row:
            from database import get_db
            db = get_db()
            row = db.table("api_keys").select("fixes_used").eq("id", key_row["id"]).single().execute().data
            if row:
                db.table("api_keys").update({"fixes_used": max(0, row["fixes_used"] - 1)}).eq("id", key_row["id"]).execute()
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Estimate tokens (4 chars ≈ 1 token)
    tokens_used = (len(body.broken_code) + len(result.get("fixed_code", ""))) // 4

    response = FixResponse(
        fix_id      = fix_id,
        fixed_code  = result["fixed_code"],
        explanation = result["explanation"],
        root_cause  = result["root_cause"],
        confidence  = int(result["confidence"]),
        diff        = result["diff"],
        test_case   = result["test_case"],
        language    = body.language or "auto",
        created_at  = datetime.utcnow().isoformat() + "Z",
        share_url   = f"https://neobugforge.io/fix/{fix_id}",
    )

    # Persist to Supabase (non-blocking)
    asyncio.create_task(asyncio.to_thread(
        save_fix, fix_id, key_row["id"] if key_row else None,
        body.dict(), result, tokens_used
    ))

    elapsed = round(time.time() - start, 3)
    print(f"[fix/{fix_id}] lang={body.language or 'auto'} confidence={result['confidence']} tokens={tokens_used} elapsed={elapsed}s")

    return response

# ─── Stripe ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: Literal["pro", "team"]

@app.post("/v1/stripe/checkout", tags=["Billing"],
          summary="Create a Stripe Checkout Session")
@limiter.limit("10/hour")
async def create_checkout(request: Request, body: CheckoutRequest,
                          authorization: Optional[str] = Header(None)):
    user = await verify_supabase_token(authorization or "")
    stripe.api_key = STRIPE_SECRET_KEY
    price_id = STRIPE_PRICE_PRO if body.plan == "pro" else STRIPE_PRICE_TEAM
    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe price not configured.")
    app_url = "https://app.neobugforge.io"
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=user["email"],
        metadata={"supabase_user_id": user["id"], "user_email": user["email"], "plan": body.plan},
        success_url=f"{app_url}/dashboard?upgraded=1",
        cancel_url=f"{app_url}/dashboard?cancelled=1",
    )
    return {"url": session.url}


@app.post("/v1/stripe/webhook", tags=["Billing"],
          summary="Stripe webhook — upgrades user tier on successful payment")
async def stripe_webhook(request: Request):
    payload  = await request.body()
    sig      = request.headers.get("stripe-signature", "")
    stripe.api_key = STRIPE_SECRET_KEY
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    if event["type"] == "checkout.session.completed":
        obj = event.get("data", {}).get("object", {})
        if not obj.get("customer_email") and not obj.get("metadata"):
            full_event = stripe.Event.retrieve(event["id"])
            obj = full_event["data"]["object"]

        email = obj.get("customer_email") or obj.get("metadata", {}).get("user_email")
        plan  = obj.get("metadata", {}).get("plan", "pro")
        tier  = plan
        fixes_limit = 500 if tier == "pro" else 999999
        if email:
            from database import get_db
            db = get_db()
            db.table("api_keys").update({
                "tier": tier,
                "fixes_limit": fixes_limit,
            }).eq("user_email", email).execute()
            print(f"[webhook] Upgraded {email} to {tier}")

    return {"received": True}


@app.post("/v1/stripe/verify", tags=["Billing"],
          summary="Verify Stripe subscription and upgrade user tier")
@limiter.limit("20/hour")
async def verify_subscription(request: Request, authorization: Optional[str] = Header(None)):
    """Called from the dashboard after successful checkout to sync the subscription."""
    user = await verify_supabase_token(authorization or "")
    stripe.api_key = STRIPE_SECRET_KEY

    customers = stripe.Customer.list(email=user["email"], limit=1)
    if not customers.data:
        return {"upgraded": False, "tier": "free"}

    subscriptions = stripe.Subscription.list(
        customer=customers.data[0].id, status="active", limit=1
    )
    if not subscriptions.data:
        return {"upgraded": False, "tier": "free"}

    price_id = subscriptions.data[0]["items"]["data"][0]["price"]["id"]
    if price_id == STRIPE_PRICE_PRO:
        tier, fixes_limit = "pro", 500
    elif price_id == STRIPE_PRICE_TEAM:
        tier, fixes_limit = "team", 999999
    else:
        return {"upgraded": False, "tier": "free"}

    from database import get_db
    db = get_db()
    db.table("api_keys").update({
        "tier": tier,
        "fixes_limit": fixes_limit,
    }).eq("user_email", user["email"]).execute()
    print(f"[verify] Upgraded {user['email']} to {tier}")

    return {"upgraded": True, "tier": tier}


# ─── Admin endpoints ──────────────────────────────────────────────────────────

class AdminUpgradeRequest(BaseModel):
    email: str
    tier:  Literal["free", "pro", "team"]

@app.post("/v1/admin/upgrade", tags=["Admin"])
async def admin_upgrade(body: AdminUpgradeRequest,
                        authorization: Optional[str] = Header(None)):
    """Manually upgrade or downgrade any user's tier. Admin only."""
    caller = await verify_supabase_token(authorization or "")
    if caller["email"] != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin only.")

    tier_limits = {"free": 100, "pro": 500, "team": 999999}
    fixes_limit = tier_limits[body.tier]

    from database import get_db
    db  = get_db()
    res = db.table("api_keys").update({
        "tier": body.tier,
        "fixes_limit": fixes_limit,
    }).eq("user_email", body.email).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail=f"No user found with email {body.email}")

    print(f"[admin] {caller['email']} upgraded {body.email} → {body.tier}")
    return {"ok": True, "email": body.email, "tier": body.tier, "fixes_limit": fixes_limit}


@app.get("/v1/admin/users", tags=["Admin"])
async def admin_list_users(authorization: Optional[str] = Header(None)):
    """List all users with their tier and usage. Admin only."""
    caller = await verify_supabase_token(authorization or "")
    if caller["email"] != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin only.")

    from database import get_db
    db  = get_db()
    res = db.table("api_keys").select(
        "user_email, tier, fixes_used, fixes_limit, created_at"
    ).order("created_at", desc=True).execute()

    return {"users": res.data, "total": len(res.data)}


# ─── Global error handler ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if ENVIRONMENT == "development" else None
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
