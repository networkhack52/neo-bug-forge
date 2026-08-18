"""Runtime configuration, read from environment variables.

Every external dependency (Anthropic, Stripe) degrades gracefully when its
key is missing so the app runs end-to-end offline for local dev / grading.
"""
from __future__ import annotations

import os
from pathlib import Path

# Brand name is centralized so renaming the product (Attestly / ProofQ / …) is
# a one-line change everywhere it is shown to users.
BRAND_NAME = os.environ.get("ATTESTLY_BRAND", "Attestly")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("ATTESTLY_DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = os.environ.get("ATTESTLY_DB_PATH", str(DATA_DIR / "attestly.db"))

# When DATABASE_URL is set (e.g. a Supabase Postgres connection string), the app
# uses Postgres for durable storage; otherwise it uses the local SQLite file.
# Local dev and tests stay on SQLite with zero setup.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)

# Reject oversized uploads before parsing them — untrusted files (PDF/xlsx) are
# a DoS surface (parser blow-ups, embedding cost), so cap the bytes we accept.
MAX_UPLOAD_MB = int(os.environ.get("ATTESTLY_MAX_UPLOAD_MB", "20"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Per-IP rate limits (count, window_seconds) on abuse-prone endpoints. Disabled
# in tests via ATTESTLY_RATE_LIMIT=0.
RATE_LIMIT_ENABLED = os.environ.get("ATTESTLY_RATE_LIMIT", "1") not in ("0", "false", "False")

# Browser origins allowed to call the API (CORS). Locked to the app's own
# frontend; add a custom domain in prod via ATTESTLY_ALLOWED_ORIGINS (CSV).
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "ATTESTLY_ALLOWED_ORIGINS",
        "https://tryattestly.com,https://www.tryattestly.com,"
        "https://attestly-gamma.vercel.app,http://localhost:5173,http://localhost:3000",
    ).split(",") if o.strip()
]
RL_LOGIN = (10, 300)        # 10 attempts / 5 min — brute-force guard
RL_SIGNUP = (8, 3600)       # 8 new accounts / hour — mass-signup / cost guard
RL_ASSESSMENT = (20, 3600)  # 20 / hour — public endpoint, bounds compute cost
RL_UPLOAD = (30, 3600)      # 30 uploads / hour, enforced per IP AND per account

# Disposable / throwaway domains are ALWAYS blocked at signup (pure abuse vector).
_DISPOSABLE = (
    "mailinator.com,guerrillamail.com,10minutemail.com,tempmail.com,temp-mail.org,"
    "trashmail.com,dispostable.com,sharklasers.com,getnada.com,yopmail.com,"
    "throwawaymail.com,maildrop.cc,mintemail.com,fakeinbox.com"
)
DISPOSABLE_EMAIL_DOMAINS = {
    d.strip().lower() for d in os.environ.get("ATTESTLY_DISPOSABLE_DOMAINS", _DISPOSABLE).split(",") if d.strip()
}
# Free consumer domains are blocked only when REQUIRE_WORK_EMAIL is on. Default
# OFF: pre-launch we want founders and early evaluators (who often use Gmail) to
# sign up; the domain allowance + doc-gate + spend cap already bound abuse. Flip
# ATTESTLY_REQUIRE_WORK_EMAIL=1 to enforce work-email-only later.
_FREE_CONSUMER = (
    "gmail.com,googlemail.com,outlook.com,hotmail.com,live.com,msn.com,yahoo.com,"
    "ymail.com,rocketmail.com,aol.com,icloud.com,me.com,mac.com,proton.me,"
    "protonmail.com,pm.me,gmx.com,gmx.net,mail.com,zoho.com,yandex.com,yandex.ru,"
    "tutanota.com,hey.com,fastmail.com,qq.com,163.com,126.com"
)
FREE_CONSUMER_EMAIL_DOMAINS = {
    d.strip().lower() for d in os.environ.get("ATTESTLY_FREE_CONSUMER_DOMAINS", _FREE_CONSUMER).split(",") if d.strip()
}
REQUIRE_WORK_EMAIL = os.environ.get("ATTESTLY_REQUIRE_WORK_EMAIL", "0") not in ("0", "false", "False")

# Free-tier model-spend cap (USD) per calendar month. Paid accounts are never
# affected. Log warnings at 50% and 80%; pause free-tier DRAFTING at 100% (reuse
# still works). ~$0.0034/answer, so $50 covers ~100 companies' full 150 trials.
FREE_TIER_MONTHLY_SPEND_CAP_USD = float(os.environ.get("ATTESTLY_FREE_SPEND_CAP_USD", "50"))

# --- Anthropic (Claude) ---------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
# The verify/abstain pass runs on its own model so it can be upgraded to a
# stronger model in ONE config change if the false-confidence rate exceeds our
# threshold. Defaults to the same haiku model (haiku-only stands until measured).
VERIFY_MODEL = os.environ.get("ATTESTLY_VERIFY_MODEL", ANTHROPIC_MODEL)
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_VERSION = os.environ.get("ANTHROPIC_VERSION", "2023-06-01")
LLM_ENABLED = bool(ANTHROPIC_API_KEY)
# Trust features (only active when the LLM is enabled). Each is one extra
# request per drafted answer; disable to trade trust for lower COGS.
CITATIONS_ENABLED = os.environ.get("ATTESTLY_CITATIONS", "1") not in ("0", "false", "False")
VERIFY_ENABLED = os.environ.get("ATTESTLY_VERIFY", "1") not in ("0", "false", "False")
# Prompt caching (Anthropic ephemeral cache on the stable system prefix). OFF by
# default: it's a live-API change, so enable it and re-run `python -m app.eval`
# to confirm answers are unchanged and to see cached-token savings, THEN leave on.
PROMPT_CACHE_ENABLED = os.environ.get("ATTESTLY_PROMPT_CACHE", "0") not in ("0", "false", "False")

# Per-million-token prices (USD) for cost instrumentation, keyed by model id.
# Cached input is billed at ~10% of the input rate. Override via env as needed.
MODEL_PRICES = {
    "claude-haiku-4-5-20251001": {"input": 1.0, "cached_input": 0.10, "output": 5.0},
    "claude-sonnet-4-5": {"input": 3.0, "cached_input": 0.30, "output": 15.0},
}
DEFAULT_PRICE = {"input": 1.0, "cached_input": 0.10, "output": 5.0}


def price_for(model: str) -> dict:
    return MODEL_PRICES.get(model, DEFAULT_PRICE)

# --- Transactional email (Resend) -----------------------------------------
# Outbound email for password resets. Cloudflare Email Routing is INBOUND only,
# so a real sending provider is required. Gated on the key: with no key set, the
# reset flow still works end-to-end but the link is written to the server log
# instead of emailed (fine for local dev; in prod, set RESEND_API_KEY so the
# link reaches the user). Verify the sending domain in Resend (SPF/DKIM DNS on
# tryattestly.com) before turning this on in production.
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
RESEND_FROM = os.environ.get("ATTESTLY_EMAIL_FROM", f"{BRAND_NAME} <hello@tryattestly.com>")
RESEND_BASE_URL = os.environ.get("RESEND_BASE_URL", "https://api.resend.com")
EMAIL_ENABLED = bool(RESEND_API_KEY)
# Password-reset tokens are single-use and short-lived.
PASSWORD_RESET_TTL_SECONDS = int(os.environ.get("ATTESTLY_RESET_TTL", "3600"))  # 1 hour
RL_PASSWORD_FORGOT = (5, 900)  # 5 reset requests / 15 min per IP — anti-spam guard

# --- Embeddings (semantic retrieval) --------------------------------------
# Optional: when a Voyage AI key is present, answers/documents are embedded and
# retrieval blends semantic similarity with the lexical score. Without a key the
# system degrades cleanly to the pure lexical/fuzzy matcher (no new services).
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "").strip()
VOYAGE_MODEL = os.environ.get("VOYAGE_MODEL", "voyage-3.5-lite")
VOYAGE_BASE_URL = os.environ.get("VOYAGE_BASE_URL", "https://api.voyageai.com")
EMBEDDINGS_ENABLED = bool(VOYAGE_API_KEY)
# Semantic cosine (0-1) is scaled to 0-100 and blended with the lexical score.
# A match's final score is max(lexical, semantic * SEMANTIC_WEIGHT), so semantic
# can only *raise* recall — it never drops a strong lexical match.
SEMANTIC_WEIGHT = float(os.environ.get("ATTESTLY_SEMANTIC_WEIGHT", "100"))

# --- Stripe ---------------------------------------------------------------
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY)
APP_BASE_URL = os.environ.get("ATTESTLY_APP_URL", "http://localhost:5173")

# --- Retrieval tuning -----------------------------------------------------
# If the best Answer-Bank match scores at/above this, reuse it verbatim.
FUZZY_REUSE_THRESHOLD = float(os.environ.get("ATTESTLY_FUZZY_THRESHOLD", "88"))
# Matches at/above this are passed to Claude as grounding context.
FUZZY_CONTEXT_THRESHOLD = float(os.environ.get("ATTESTLY_CONTEXT_THRESHOLD", "45"))
# A drafted answer is compared against the closest approved library answer only
# when that match is at/above this score — high enough that it's genuinely the
# same question, so a material difference is a real contradiction (T2), not two
# different questions that happen to share words.
CONTRADICTION_MATCH_THRESHOLD = float(os.environ.get("ATTESTLY_CONTRADICTION_THRESHOLD", "72"))
# How many context Q&A pairs to hand the model.
CONTEXT_TOP_K = int(os.environ.get("ATTESTLY_CONTEXT_TOP_K", "5"))
# Questions answered concurrently per questionnaire (each drafted one makes
# several sequential API calls, so parallelism is the main latency win).
ANSWER_CONCURRENCY = int(os.environ.get("ATTESTLY_ANSWER_CONCURRENCY", "10"))

# --- Plans / metering -----------------------------------------------------
# question_limit = billable "answers generated" per 30-day period.
# bank_limit     = max approved entries in the Answer Bank.
# yearly_price = "pay for 10 months, get 12" (2 months free, ~16.7% off).
TIERS: dict[str, dict] = {
    "free": {"name": "Free", "price": 0, "yearly_price": 0, "question_limit": 25, "bank_limit": 50, "seats": 1},
    "starter": {"name": "Starter", "price": 99, "yearly_price": 990, "question_limit": 750, "bank_limit": 500, "seats": 1},
    "growth": {"name": "Growth", "price": 249, "yearly_price": 2490, "question_limit": 3000, "bank_limit": 100000, "seats": 5},
    "scale": {"name": "Scale", "price": 499, "yearly_price": 4990, "question_limit": 100000, "bank_limit": 100000, "seats": 25},
}
DEFAULT_TIER = "free"

# Source freshness: an answer's cited document is flagged "stale" when its
# source date is older than this many months. Reviewers treat stale evidence as
# a red flag, so we surface it — the answer is still correct, it just carries a
# warning. Configurable; 0 disables the flag.
SOURCE_STALE_MONTHS = int(os.environ.get("ATTESTLY_SOURCE_STALE_MONTHS", "12"))

# One-time onboarding allowance: a pool of free answers granted per email DOMAIN
# (shared across everyone at the same company), so a new team can run a real
# 124-855 question questionnaire before falling back to the recurring free limit.
# Scoped to the domain so one company can't farm it across many signups.
ONBOARDING_ALLOWANCE = int(os.environ.get("ATTESTLY_ONBOARDING_ALLOWANCE", "150"))
