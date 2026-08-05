# Attestly — Deployment & Key-Wiring Guide

The app runs fully offline with no keys. To go live you wire **three** things:
Anthropic (drafting), Stripe (billing), and the two hosts (backend + frontend).
You paste the actual secrets into the dashboards yourself — never commit them.

Architecture: **backend (FastAPI) → Render** · **frontend (React/Vite) →
Vercel** — mirroring the existing Neo Bug Forge setup.

---

## 1. Anthropic key (drafting)

1. Go to <https://console.anthropic.com> → **API Keys** → **Create Key**.
2. Copy the key (starts with `sk-ant-...`).
3. You'll paste it into the **backend host** as `ANTHROPIC_API_KEY` (step 4).
4. (Optional) set `ANTHROPIC_MODEL` — default `claude-haiku-4-5-20251001`
   (cheapest; keeps the 88% margin in the model). Use a larger model only if
   draft quality needs it.

**Cost control:** reuse from the Answer Library costs $0; only net-new drafts hit
the API. Set a monthly spend limit in the Anthropic console as a safety net.

---

## 1b. Voyage key (semantic search — optional, one-line toggle)

By default retrieval matches questions **lexically** (fuzzy word overlap). Add a
Voyage AI key and it *also* matches by **meaning**, so paraphrases like
*"Where is data stored?"* ↔ *"In which region does customer data reside?"* match,
and trust-document passages (SOC 2 / policies) are retrieved semantically.

1. Go to <https://dash.voyageai.com> → **API Keys** → create a key.
2. Paste it into the **backend host** as `VOYAGE_API_KEY` (step 4). That's the
   whole toggle — nothing else changes.

- **No key?** Everything still works; matching is lexical and document passages
  are found by wording. No errors, no missing features.
- **Cost:** `voyage-3.5-lite` is a few cents per million tokens — negligible.
  Embeddings are computed once when an answer/document is saved.
- **Backfill:** new answers/documents embed automatically. To embed everything
  created *before* you added the key, run the one-shot (locally, or in a Render
  Shell) — safe to re-run, only touches rows without a vector:
  ```
  python -m app.backfill_embeddings
  ```
- **Verify:** `/health` shows `"embeddings_enabled": true`.

---

## 2. Stripe (self-serve billing)

1. <https://dashboard.stripe.com> → create the account / use test mode first.
2. **Products → Add product** for each tier. Add **two prices** per product —
   a monthly and an annual ("2 months free") — and copy every **Price ID**
   (`price_...`):
   - *Attestly Starter* — **$99/mo** and **$990/yr**
   - *Attestly Growth* — **$249/mo** and **$2,490/yr**
   - *Attestly Scale* — **$499/mo** and **$4,990/yr**
   (You can skip the annual prices at first — if the `*_YEARLY` env vars are
   unset, the app creates the annual price inline at checkout.)
3. **Developers → API keys** → copy the **Secret key** (`sk_test_...` then
   `sk_live_...` when you flip to live).
4. **Developers → Webhooks → Add endpoint:**
   - URL: `https://api.neobugforge.io/v1/stripe/webhook` (your backend domain)
   - Events: `checkout.session.completed`, `customer.subscription.deleted`
   - Copy the **Signing secret** (`whsec_...`).

You'll paste `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and the three
`STRIPE_PRICE_*` IDs into the backend host.

> Until `STRIPE_SECRET_KEY` is set, checkout returns a **simulated** URL and the
> `/v1/billing/confirm` endpoint upgrades the org locally — good for demos.

---

## 3. Backend → Render

1. <https://dashboard.render.com> → **New → Web Service** → connect this repo.
2. Settings:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Environment → Add Environment Variable** (paste your real values):
   ```
   ANTHROPIC_API_KEY      = sk-ant-...
   ANTHROPIC_MODEL        = claude-haiku-4-5-20251001
   VOYAGE_API_KEY         = pa-...             (optional — turns on semantic search)
   DATABASE_URL           = postgresql://...   (Supabase — durable storage, see §3b)
   STRIPE_SECRET_KEY      = sk_live_...        (or sk_test_... first)
   STRIPE_WEBHOOK_SECRET  = whsec_...
   STRIPE_PRICE_STARTER   = price_...
   STRIPE_PRICE_GROWTH    = price_...
   STRIPE_PRICE_SCALE     = price_...
   ATTESTLY_APP_URL       = https://app.attestly.io   (your frontend URL)
   ```
4. Deploy. Verify: `curl https://<your-backend>/health` →
   `"llm_enabled": true, "stripe_enabled": true`.

---

## 3b. Durable storage → Supabase Postgres (recommended)

Without `DATABASE_URL` the app stores data in a local SQLite file, which on
Render's default (ephemeral) filesystem **resets on every deploy**. For real
customers, point it at Postgres — the app auto-detects `DATABASE_URL`, uses
Postgres, and **creates all its tables on first startup** (no manual SQL).

1. <https://supabase.com> → your project → **Connect** (top bar) → **Connection
   string** → **Transaction pooler** (port `6543`). It looks like:
   ```
   postgresql://postgres.<ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```
   Use the **pooler** (6543), not the direct connection — the app opens a
   connection per request, and the pooler is built for that.
2. Replace `<PASSWORD>` with your database password (URL-encode any special
   characters). If the connection is refused, append `?sslmode=require`.
3. Paste it into Render as `DATABASE_URL` and redeploy.
4. Verify: `/health` shows `"storage": "postgres"`. (SQLite shows
   `"storage": "sqlite"`.)

> Local dev and the test suite ignore `DATABASE_URL` unless you set it, so they
> stay on zero-setup SQLite. The full suite also passes against Postgres.

> **Alternative:** a Render Disk keeps SQLite instead (mount `/data`, set
> `ATTESTLY_DB_PATH=/data/attestly.db`) — simplest, but $7/mo and no managed
> backups. Supabase (Postgres) is free and the better long-term foundation.

---

## 4. Frontend → Vercel

1. <https://vercel.com> → **Add New → Project** → import this repo.
2. Settings:
   - **Root Directory:** `frontend`
   - Framework preset: **Vite** (build `npm run build`, output `dist`)
3. **Environment Variables:**
   ```
   VITE_API_URL = https://<your-backend>      (the Render URL / api.attestly.io)
   ```
4. Deploy. Open the URL, create a company, upload
   `backend/sample_data/sample_questionnaire.xlsx`.

---

## 5. Go-live checklist
- [ ] `/health` shows `llm_enabled: true` and `stripe_enabled: true`
      (and `embeddings_enabled: true` if you added the Voyage key)
- [ ] Real questionnaire upload → answers draft via Claude (not fallback)
- [ ] Stripe **test-mode** checkout completes → webhook flips tier to paid
- [ ] Flip Stripe to **live** keys; repeat one real $99 checkout
- [ ] DB persistence attached (Render Disk or Supabase) before onboarding users
- [ ] Custom domains + HTTPS on both hosts
- [ ] Analytics (Plausible) + funnel events wired (see GO_TO_MARKET.md)

## Local `.env` (optional, for local dev only)
Copy `.env.example` → `.env` in `attestly/` and fill in keys to test the live
path locally. **`.env` is gitignored — never commit real keys.**
