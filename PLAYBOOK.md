# Attestly — Master Playbook

The single source of truth for what we're building, why, how it works, and where it lives.
Deep-dive docs are linked from each section. Keep this file updated as the project evolves.

---

## 1. What Attestly is (in one line)

> **Attestly — the self-serve security questionnaire tool that proves every answer.**

Upload a SIG, CAIQ, or any vendor questionnaire → Attestly drafts each answer from your own SOC 2
and security policies, **cites the exact source**, and reuses your approved answers so each
questionnaire gets faster.

**Positioning (say this, not "AI questionnaire tool"):**
*The self-serve questionnaire tool for small SaaS that proves every answer — no demo, no annual contract.*

Two differentiators the enterprise players can't claim:
1. **Proof** — every answer cites the exact document line; abstains instead of hallucinating.
2. **Self-serve + affordable** — sign up and go, free tier, $99+/mo. No sales call.

---

## 2. The customer

- **ICP:** B2B SaaS companies, ~20–200 people, that just earned SOC 2 and are getting hit with
  security questionnaires mid-deal.
- **Buyer/user:** Head of Security / GRC / CISO, or at smaller shops the founder/CTO or a sales engineer.
- **The goal:** ~20–50 paying customers → ~$100k profit in 12 months. Not "win the market" — a wedge.
- **Market reality:** crowded + validated. Enterprise incumbents (Vanta, Loopio, Drata, Conveyor,
  SafeBase, Responsive) + newer AI-native startups (Inventive, Tribble, AutoRFP, SecurityPal). "AI
  answers questionnaires" is table stakes — we win on **proof + self-serve + price for the mid-market.**

---

## 3. Architecture & stack

| Layer | Tech | Notes |
|---|---|---|
| Backend | FastAPI (Python) | `backend/app/` |
| Database | SQLite (dev) / Postgres (prod via `DATABASE_URL`) | dual backend; Supabase in prod |
| Frontend | React 18 + Vite | `frontend/`; Vite 8 |
| Drafting | Claude API (`claude-haiku-4-5`) | grounded, cited, verified — do NOT swap the model without reason |
| Semantic search | Voyage AI embeddings (optional) | stored as float32 BLOBs in SQL, no vector DB |
| Billing | Stripe (self-serve) | simulated when no key |
| Hosting | Render (backend) · Vercel (frontend) | |

**Total direct dependencies: 13** (9 backend, 4 frontend) — deliberately lean.

### Core value loop (`engine.py`)
1. Rank the org's Answer Library (lexical + semantic).
2. Confident match → **reuse verbatim** (free, instant, consistent).
3. Else → **draft with Claude**, grounded in approved answers + trust-document passages, with citations + a verification pass.
4. Approved answers flow back into the Library → accuracy + reuse-rate compound per customer (the moat).
Questions are answered **concurrently** (10-wide, `ATTESTLY_ANSWER_CONCURRENCY`, default 10) for speed.

---

## 4. Features shipped

- Upload questionnaire (SIG/CAIQ/VSAQ/custom xlsx/csv), auto-detect question column
- Reuse-first answering + Claude drafting (grounded, first-person, concise)
- **Answer Library** (compounding) + one-click "Load starter answers" (45 baseline, incl. Gulf/UAE frameworks: PDPL, ISO 27001, DIFC/ADGM, VARA, IA/NESA)
- **Trust Documents** — upload SOC 2 / policies (PDF/text), chunked + embedded
- **Citations "show proof"** drawer — exact source span per answer (the killer demo)
- **Verification pass** — flags unsupported claims; **abstains** instead of hallucinating
- **First-run nudge** — empty Upload screen guides new users to load starter answers + upload a SOC 2 first, so the first questionnaire returns cited answers, not abstentions
- **Choice field** (Yes/No/Partially/Not Applicable)
- Export: **clean .xlsx** and **filled original** (write back into the customer's own template)
- Real accounts: email + password login, one account per email
- **Forgot-password flow** — single-use, 1-hour reset link emailed via Resend (`app/email.py`); non-enumerating `/v1/password/forgot`, and `/v1/password/reset` also rotates the API token. Gated on `RESEND_API_KEY`: with no key the link is logged, not emailed (needs Resend + verified sending domain to reach inboxes)
- Self-serve billing (monthly + annual "2 months free"), simulated without Stripe
- Assessment report generator (lead magnet)

---

## 5. Security posture — 9/10

| # | Control | Status |
|---|---|---|
| 1 | Stripe webhook signature enforced (no forged upgrades) | ✅ |
| 2 | Rate limiting (login/signup/assessment) | ✅ |
| 3 | API tokens hashed at rest | ✅ |
| 4 | Token rotation / revocation | ✅ |
| 5 | CSP + security headers (`frontend/vercel.json`) | ✅ |
| 6 | CORS locked to known origins | ✅ |
| 7 | Least-privilege DB role | ⬜ (hygiene) |
| 8 | TLS to DB (`sslmode=require`, enforced in code) | ✅ |
| 9 | Dependency scanning — pip-audit + npm audit clean, Dependabot on | ✅ |
| 10 | Backups — weekly pg_dump via GitHub Action | ✅ |

Passwords + tokens hashed, parameterized SQL, per-tenant scoping, prompt-injection defense,
upload size cap. Full review lives in the security scorecard section of the git history.

**GitHub:** `main` is branch-protected (force-push + deletion blocked). Deploy workflow is a direct
push to `main`, so PR-required protection is intentionally *off*. Only remaining gap on the scorecard
is #7 (least-privilege DB role — accepted hygiene item).

---

## 6. Live infrastructure

| Thing | URL / location |
|---|---|
| App (frontend) | https://tryattestly.com (custom domain) · https://attestly-gamma.vercel.app (Vercel) |
| Backend API | https://attestly-f8p0.onrender.com |
| Health check | `…/health` → `{status, storage:"postgres", llm_enabled, embeddings_enabled}` |
| Repo (pull from here) | github.com/networkhack52/Attestly (branch `main`) |
| Database | Supabase Postgres (Transaction pooler, port 6543) |
| Landing page | `marketing/` (see §8) |

⚠ **Render free tier spins the backend down after ~15 min idle → the next request cold-starts for ~50s.**
Fine while building solo. **Before driving any prospect to the app link, upgrade to Render Starter ($7/mo, no
spin-down)** so their first load isn't a 50-second spinner — the frontend (Vercel) is fast/static, but nothing
renders until the backend wakes. Downgrade back to free anytime.

**Env vars** (set in Render, never in the repo): `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY` (optional),
`DATABASE_URL`, `STRIPE_*` (when billing goes live), `ATTESTLY_APP_URL`. Full setup: **`DEPLOY.md`**.

---

## 7. Local dev

```bash
# backend
cd backend && python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q            # full suite
python -m uvicorn app.main:app --port 8000

# frontend
cd frontend && npm install && npm run dev

# enable the copy-lint pre-commit hook (once per clone)
git config core.hooksPath .githooks
```
Pull latest before working: `git pull origin main` (the deployed app builds from the remote —
your local can drift behind and that's fine, but pull to stay in sync).

---

## 8. The marketing site (`marketing/`)

- `index.html` — the landing page ("Answer security questionnaires with receipts")
- `terms.html` — Terms of Service **(template — lawyer review + fill [brackets])**
- `privacy.html` — Privacy Policy **(template — discloses AI subprocessors + data-location §3a; keep it accurate)**
- `dpa.html` — Data Processing Agreement **(template — GDPR + UAE PDPL/DIFC/ADGM aware; lawyer review + fill [brackets])**

**To deploy** (any static host): point a new Vercel project at the `marketing/` directory, or
drag-drop the folder into Netlify. Then set the app link / custom domain. The CTA buttons point to
the live app; footer links point to `/terms.html`, `/privacy.html`, and `/dpa.html`.

⚠ **Before publishing legal pages:** replace every `[bracketed]` field (legal entity, jurisdiction,
contact email, dates) and have a lawyer review. Confirm the Privacy subprocessor table matches your
live setup.

---

## 9. Go-to-market

- **Now (0→first customers):** direct outreach + **design partners** > SEO. Offer to run a
  prospect's *real* questionnaire for free and hand it back filled in. Templates + target search
  recipes in **`SALES_PLAYBOOK.md`**; 90-day plan in **`GO_TO_MARKET.md`**.
- **Find buyers without burning LinkedIn limits:** Google X-ray
  (`site:linkedin.com/in ("Head of Security" OR CISO) SaaS -consultant`), post commenters, and
  Reddit r/SaaS "new" (venters).
- **GEO/AEO (background, compounding):** get listed on G2/Capterra/Product Hunt + "best of" listicles,
  be active on Reddit, keep question-shaped content (the landing FAQ) — AI answer engines quote it.
- **The one demo that closes:** upload the prospect's questionnaire → click "show proof" → show the
  exact SOC 2 line. That's the "it's not making things up" moment.
- **Gulf / UAE wedge (in progress):** SOC 2-fresh SaaS selling into Dubai + maturing PDPL = a real niche.
  Groundwork shipped (regional starter answers, data-location disclosure, PDPL-aware DPA). Full plan,
  priorities, and risks in **`GULF_EXPANSION.md`**. Next: Arabic landing page, then the Frankfurt move.

---

## 10. Voice & copy rules

How Attestly sounds — in the product, the landing page, legal pages, and LinkedIn posts.
Audience is security / GRC / CISO: skeptical, technical, allergic to hype and to anything that
smells AI-generated. Write like a competent peer, not a marketer.

**Punctuation**
- **No em/en dashes (— –) anywhere in customer-facing copy** — the marketing site *and* product UI
  strings. To this audience the em dash reads as AI-written. Use a period, a comma, a colon, or the
  brand's **`·`** separator instead. (Internal docs like this playbook are exempt.)
- Use **`·`** as the brand separator (e.g. "Start free · 25 answers, no card").
- Curly quotes (" " ' ') are fine in prose; the linter only warns on them (they can break in meta tags).

**Enforcement — `copy-lint.mjs` (repo root)**
- Runs automatically as a **pre-commit hook** (`.githooks/pre-commit`). Enable once per clone:
  `git config core.hooksPath .githooks`. Bypass a single commit with `git commit --no-verify`.
- Run by hand anytime: `node copy-lint.mjs` (defaults to the brand-voice scope below). Needs Node 22+.
- **Scope = brand-voice surfaces only:** `marketing/index.html` + `frontend/src`. The legal templates
  (`terms/privacy/dpa.html`) are **excluded on purpose** — formal, lawyer-owned register. Lint them
  explicitly if ever needed: `node copy-lint.mjs "marketing/*.html"`.
- **Backend + generated text:** Python prose doesn't lint cleanly with the JS tool, so the backend's
  user-facing strings (abstain text, block prompts, export labels) are guarded by
  `tests/test_copy_voice.py` instead. Generated answers are governed by the drafting prompt (grounded,
  no promotional language) and legitimately contain figures like "99.9%" or "AES-256", so percentages
  are NOT banned at runtime — only the marketing tells ("trusted by", accuracy-% claims) are.
- **Errors fail** (exit 1): em/en dash, hype words, unbacked claims, throat-clearing openers.
  **Warnings are advisory:** curly quotes, filler words ("just"/"really"), spelled-out numbers.
- **Delete the `unbacked-claim` rule the day we have data to back it** — pre-launch it stops us
  putting "95% accurate" / "trusted by thousands" on the site, which a CISO would ask us to prove.

**Words & tone**
- Say **"prove every answer"**, not "AI questionnaire tool". Lead with proof + self-serve + price.
- **Never over-claim.** No certifications, controls, or commitments we can't back. Honesty beats polish —
  especially under PDPL / to a CISO. If unsure, abstain or hedge, don't assert.
- **Concise and direct.** Product answers: first-person plural ("We …"), 1–3 sentences, answer the
  specific question, no tangential restating (mirrors the drafting system prompt).
- Plain, concrete, lowercase-y confidence. Avoid buzzwords ("revolutionary", "cutting-edge", "seamless"),
  exclamation marks, and emoji in product/marketing copy.
- **LinkedIn:** hook in line 1, one idea per post, end with a question ~half the time, product ~1 in 3
  posts. Details in `CONTENT_LOG.md`.

---

## 11. Decision log (why things are the way they are)

- **Model = `claude-haiku-4-5`** — deliberate cost choice; keeps margins. Don't swap without reason.
- **No vector DB** — embeddings as SQLite/Postgres BLOBs; keeps infra at zero services.
- **Structured JSON citations, not native Claude Citations** — native + forced JSON corrupted the
  output; we ask the model for a clean answer + a separate citations array.
- **Postgres via Supabase (not the $7 Render disk)** — free, durable, better long-term.
- **Fast token hash (SHA-256), slow password hash (PBKDF2)** — tokens are high-entropy, passwords aren't.
- **Login rotates the token** — only the hash is stored, so we can't hand back the old token.
- **Answer concurrency = 10** — drafts finish in fewer waves; `ATTESTLY_ANSWER_CONCURRENCY` overrides.
- **First-run nudge over a blank screen** — a new user with an empty library gets abstentions; the nudge
  makes the first questionnaire come back cited (the trust moment) instead.
- **Gulf: don't translate the *answers* to Arabic** — Gulf questionnaires (SIG/CAIQ/ISO) are in English;
  Arabic answers would break the deliverable. Arabic belongs on marketing + app chrome only.
- **Gulf: "EU-hosted (Frankfurt)", never claim in-UAE residency we don't have** — honesty under PDPL / to a
  CISO matters more than the marketing line; the US AI processing is disclosed plainly.
- **`main` branch protection = force-push/deletion blocked, but PR not required** — the deploy is a direct
  push to `main`, so requiring PRs would lock us out of our own release path.
- **Free tier = one-time 150 onboarding pool (per email DOMAIN) + recurring 25/30-day.** Real
  questionnaires run 124-855 questions; a 25-answer free tier that *declined* over-quota uploads meant
  every new user's first action was a rejection. The 150 pool lets a new team run a real questionnaire;
  it's domain-scoped so one company can't farm it across many signups.
- **Over-quota = partial, never decline.** Answer up to the remaining quota, mark the rest `Locked`,
  always produce the export. A rejected upload is a dead first impression.
- **Export carries proof: `Section | Question | Vendor Response | Source | Status`.** The product is
  "prove every answer"; the file the customer sends must show the source line and a per-row status
  (Answered / Needs review / No evidence / Locked).
- **Abstentions are one line** ("No supporting evidence found in the uploaded documents. Needs owner
  review."), applied deterministically when an answer has no citations. Detail lives in the Status column,
  not in prose the customer forwards.
- **Free-allowance abuse controls (all in config, env-overridable):** drafting is gated behind a
  trust document; disposable email domains always blocked at signup, and strict work-email-only
  (`REQUIRE_WORK_EMAIL`, default OFF so Gmail founders/evaluators can sign up) available to flip on
  later; upload/generate rate-limited per IP AND per account (`RL_UPLOAD`); a monthly free-tier
  model-spend cap (`FREE_TIER_MONTHLY_SPEND_CAP_USD`, default $50 ≈ 100 full trials at $0.0034/answer)
  that logs at 50/80% and pauses free-tier *drafting* at 100% (reuse + paid unaffected).
- **Haiku-only until measured; verify is one config change away from a stronger model.** `VERIFY_MODEL`
  (`ATTESTLY_VERIFY_MODEL`) is its own config value, and the verify pass is scoped to the *cited passages
  only* (~500 tokens) so a stronger verify model stays cheap. Gate: run `python -m app.eval` (50 labelled
  questions vs `backend/eval/`); if **false confidence > 3%** (asserting a control the docs don't support),
  upgrade `VERIFY_MODEL`. Cost is logged per answer (`usage_events`, `GET /v1/usage/cost`) and read
  alongside the eval.

---

## 12. Backlog / next

- [ ] Land first 3–5 design partners (the actual priority)
- [ ] **Upgrade Render to Starter ($7/mo) before prospect outreach** — kills the free-tier 50s cold-start (§6)
- [ ] Deploy the marketing site + fill in legal templates — now terms, privacy, **and dpa** (lawyer review)
- [ ] **Gulf/UAE (see `GULF_EXPANSION.md`):** Arabic landing page → then move Render + Supabase to Frankfurt
  (co-located) for latency + an EU-residency story. Regional answers + data-location + DPA already shipped.
- [ ] Turn on Stripe (webhook fix already makes this safe) when ready to charge
- [x] **Password reset — SHIPPED.** Resend-backed reset flow (`app/email.py`, `/v1/password/forgot` +
  `/v1/password/reset`, frontend "Forgot password?" + reset view). Non-enumerating, single-use 1-hour token,
  rotates the API token on reset. To go live: create a Resend account, set `RESEND_API_KEY` on Render, and
  verify tryattestly.com as a sending domain (add its SPF/DKIM DNS records in Cloudflare). Until then the reset
  link is written to the server log instead of emailed.
- [ ] **Email verification at signup** (the other half of the Resend work). Signup still creates accounts
  instantly with no verify step. Build once Resend is wired for password reset — same provider. Stopgap:
  one-account-per-email dedup + signup rate-limiting.
- [ ] Security hygiene: least-privilege DB role (#7) — the one remaining scorecard gap (backups #10 done)
- [ ] Housekeeping: delete stale one-off branches on the repo (e.g. `deps-audit-fix`) — no open PRs
- [ ] Optional: Cloudflare in front (stronger rate limiting) once a custom domain is set
- [ ] Two-sided "trust exchange" vision — see `ROADMAP.md`

---

*Keep this file current. When in doubt, this is what we're building and why.*
