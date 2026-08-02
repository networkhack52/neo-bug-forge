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

**Cost control:** reuse from the Answer Bank costs $0; only net-new drafts hit
the API. Set a monthly spend limit in the Anthropic console as a safety net.

---

## 2. Stripe (self-serve billing)

1. <https://dashboard.stripe.com> → create the account / use test mode first.
2. **Products → Add product** three times:
   - *Attestly Starter* — recurring, **$99/mo**
   - *Attestly Growth* — recurring, **$249/mo**
   - *Attestly Scale* — recurring, **$499/mo**
   Copy each **Price ID** (`price_...`).
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
   - **Root Directory:** `attestly/backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Environment → Add Environment Variable** (paste your real values):
   ```
   ANTHROPIC_API_KEY      = sk-ant-...
   ANTHROPIC_MODEL        = claude-haiku-4-5-20251001
   STRIPE_SECRET_KEY      = sk_live_...        (or sk_test_... first)
   STRIPE_WEBHOOK_SECRET  = whsec_...
   STRIPE_PRICE_STARTER   = price_...
   STRIPE_PRICE_GROWTH    = price_...
   STRIPE_PRICE_SCALE     = price_...
   ATTESTLY_APP_URL       = https://app.attestly.io   (your frontend URL)
   ```
4. Deploy. Verify: `curl https://<your-backend>/health` →
   `"llm_enabled": true, "stripe_enabled": true`.

> **Persistence note:** SQLite is fine for launch/pilot. Attach a Render Disk
> (mount at `/data`, set `ATTESTLY_DB_PATH=/data/attestly.db`) so data survives
> deploys, **or** migrate to the existing Supabase/Postgres — the schema in
> `db.py` maps over directly. Do this before real customer data lands.

---

## 4. Frontend → Vercel

1. <https://vercel.com> → **Add New → Project** → import this repo.
2. Settings:
   - **Root Directory:** `attestly/frontend`
   - Framework preset: **Vite** (build `npm run build`, output `dist`)
3. **Environment Variables:**
   ```
   VITE_API_URL = https://<your-backend>      (the Render URL / api.attestly.io)
   ```
4. Deploy. Open the URL, create a company, upload
   `attestly/backend/sample_data/sample_questionnaire.xlsx`.

---

## 5. Go-live checklist
- [ ] `/health` shows `llm_enabled: true` and `stripe_enabled: true`
- [ ] Real questionnaire upload → answers draft via Claude (not fallback)
- [ ] Stripe **test-mode** checkout completes → webhook flips tier to paid
- [ ] Flip Stripe to **live** keys; repeat one real $99 checkout
- [ ] DB persistence attached (Render Disk or Supabase) before onboarding users
- [ ] Custom domains + HTTPS on both hosts
- [ ] Analytics (Plausible) + funnel events wired (see GO_TO_MARKET.md)

## Local `.env` (optional, for local dev only)
Copy `.env.example` → `.env` in `attestly/` and fill in keys to test the live
path locally. **`.env` is gitignored — never commit real keys.**
