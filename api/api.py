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
MODEL             = "claude-haiku-4-5-20251001"
MAX_TOKENS        = 2048

from database import lookup_api_key, check_and_increment_quota, save_fix, get_fix_by_id

# ─── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

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

# ─── Prompt ───────────────────────────────────────────────────────────────────

def build_prompt(code: str, error: str, language: str) -> str:
    return f"""You are an expert software engineer and debugger specializing in {language or "multiple languages"}.

A developer has submitted broken code and its error message.

Tasks:
1. Identify the exact root cause.
2. Fix the code without changing original intent or logic.
3. Generate a minimal unit test that would have caught this bug.
4. Return ONLY a raw JSON object — no markdown, no extra text.

Required JSON shape (all fields mandatory):
{{
  "fixed_code":  "<complete corrected code>",
  "explanation": "<plain English: what was wrong and what changed>",
  "root_cause":  "<one of: null_reference|type_mismatch|off_by_one|async_race|scope_error|logic_error|syntax_error|import_error|index_error|other>",
  "confidence":  <integer 0-100>,
  "diff":        "<unified diff, --- original, +++ fixed>",
  "test_case":   "<minimal unit test in the same language>"
}}

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

    raw = message.content[0].text.strip()
    raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned non-JSON: {raw[:200]}") from exc

    for key in ("fixed_code", "explanation", "root_cause", "confidence", "diff", "test_case"):
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
    email: str = Field(..., min_length=5, max_length=200)

class CreateKeyResponse(BaseModel):
    api_key:     str
    email:       str
    tier:        str
    fixes_limit: int
    message:     str


@app.post("/v1/keys", response_model=CreateKeyResponse, tags=["Keys"],
          summary="Generate a new API key")
@limiter.limit("5/hour")
async def create_key(request: Request, body: CreateKeyRequest):
    import secrets
    from database import get_db, hash_key

    raw_key = "nbf_" + secrets.token_urlsafe(32)
    db = get_db()

    # Check if email already has a key
    existing = db.table("api_keys").select("id").eq("user_email", body.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="An API key already exists for this email.")

    db.table("api_keys").insert({
        "key_hash":    hash_key(raw_key),
        "user_email":  body.email,
        "tier":        "free",
        "fixes_limit": 100,
    }).execute()

    return CreateKeyResponse(
        api_key     = raw_key,
        email       = body.email,
        tier        = "free",
        fixes_limit = 100,
        message     = "Save this key — it won't be shown again.",
    )


@app.get("/v1/usage", response_model=UsageResponse, tags=["Usage"],
         summary="Get current quota and usage for your API key")
async def get_usage(key_row: dict = Depends(verify_api_key)):
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
            "public":        "POST /v1/fix/public  (10 req/day, no auth)",
            "authenticated": "POST /v1/fix         (requires X-API-Key header)",
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
    return await _process_fix(body, key_row=key_row)


@app.post("/v1/fix/public", response_model=FixResponse, tags=["Fix"],
          summary="Fix a bug (public — 10 req/day per IP)")
@limiter.limit("10/day")
async def fix_public(request: Request, body: FixRequest):
    return await _process_fix(body)


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
