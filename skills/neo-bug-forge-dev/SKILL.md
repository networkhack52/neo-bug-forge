---
name: neo-bug-forge-dev
description: >
  Full development context for Neo Bug Forge — an AI-powered VS Code bug-fixing SaaS.
  Use this skill whenever the user mentions Neo Bug Forge, nbf, neobugforge, wants to
  continue building the app, add Stripe payments, fix the dashboard, work on the API,
  update the extension, improve the landing page, or do anything related to this project.
  Trigger even if the user just says "let's continue" or "what's next" after a break,
  since this project is the primary ongoing work.
---

# Neo Bug Forge — Developer Context

## What this product is

Neo Bug Forge fixes code bugs using Claude AI. Users paste broken code → get fixed code, diff, and test case. Delivered via:
- **VS Code extension** (primary UX — select code, press Ctrl+Shift+F)
- **Web app** (dashboard to manage API key, usage, plan)
- **Landing page** (marketing + pricing)
- **REST API** (backend that calls Claude)

## Live URLs

| Service | URL |
|---|---|
| Landing page | https://neobugforge.io |
| Web app / dashboard | https://app.neobugforge.io |
| Backend API | https://api.neobugforge.io |
| VS Code extension | https://marketplace.visualstudio.com/items?itemName=neobugforge.neo-bug-forge |

## Repositories (3 separate GitHub repos — important!)

| Repo | What it deploys | Platform |
|---|---|---|
| `networkhack52/neo-bug-forge` | Main monorepo (landing, vscode-extension, scripts) | GitHub only |
| `networkhack52/neo-bug-forge-web` | React/Vite web app → `app.neobugforge.io` | Vercel (auto-deploy on push) |
| `networkhack52/neo-bug-forge-api` | FastAPI backend → `api.neobugforge.io` | Render (auto-deploy on push) |

**Critical**: Vercel watches `neo-bug-forge-web` and Render watches `neo-bug-forge-api`. Pushing to the main monorepo does NOT redeploy the web app or API. Must push to the correct repo.

### Pushing changes
```powershell
# Web app changes
cd C:\Users\lenovo\Downloads\nbf\web
git add .
git commit -m "your message"
git push origin HEAD:main   # pushes to neo-bug-forge-web

# API changes
cd C:\Users\lenovo\Downloads\nbf\api
git add .
git commit -m "your message"
git push origin HEAD:main   # pushes to neo-bug-forge-api

# Landing page / extension changes
cd C:\Users\lenovo\Downloads\nbf
git add .
git commit -m "your message"
git push                    # pushes to main monorepo
```

## Local folder structure

```
C:\Users\lenovo\Downloads\nbf\
├── landing\          ← Static HTML landing page (index.html, terms.html, privacy.html)
├── web\              ← React + Vite web app (has its own git repo inside)
│   ├── src\
│   │   ├── App.jsx           ← Main bug fixer UI
│   │   ├── main.jsx          ← React Router setup
│   │   ├── supabase.js       ← Supabase client
│   │   └── pages\
│   │       ├── Login.jsx
│   │       ├── Signup.jsx
│   │       └── Dashboard.jsx
│   ├── .env.development
│   ├── .env.production
│   └── vercel.json
├── api\              ← FastAPI backend (has its own git repo inside)
│   ├── api.py
│   ├── database.py
│   └── requirements.txt
└── vscode-extension\ ← VS Code extension (published as v1.0.2)
    ├── src\extension.ts
    └── package.json
```

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite, React Router v7, Space Grotesk + JetBrains Mono fonts |
| Auth | Supabase Auth (GitHub OAuth + email/password) |
| Database | Supabase (PostgreSQL) |
| Backend | Python FastAPI, slowapi rate limiting, httpx |
| AI | Anthropic Claude Haiku (`claude-haiku-4-5-20251001`) |
| Hosting | Vercel (web), Render (API), Cloudflare (DNS + domain) |
| Extension | VS Code extension (TypeScript), SecretStorage for API keys |

## Design system

- **Colours**: `--bg: #05050d`, `--accent: #7c6cfc`, `--accent2: #a78bfa`, `--cyan: #06b6d4`, `--green: #10b981`
- **Fonts**: Space Grotesk (UI), JetBrains Mono (code/keys)
- **Style**: Dark futuristic, neon glow effects, gradient text, CSS-in-JS (STYLES const in each component)

## Supabase project

- **Project URL**: `https://gffkcuknsboezegjqnbu.supabase.co`
- **Anon key**: in `web/.env.production` and Vercel env vars
- **Service role key**: in Render env vars as `SUPABASE_SERVICE_ROLE_KEY`

### Database tables

**`api_keys`**
```
id (uuid, PK)
key_hash (text) — SHA-256 hash of the nbf_ key
raw_key (text) — stored for dashboard display
user_email (text)
supabase_user_id (uuid)
tier (text) — 'free' | 'pro' | 'team'
fixes_limit (int) — 100 free, 500 pro, 999999 team
fixes_used (int)
tokens_used (int)
is_active (bool)
last_used_at (timestamptz)
created_at (timestamptz)
```

**`fixes`**
```
fix_id (text, PK)
key_id (uuid, FK → api_keys)
language, confidence, tokens_used
broken_code, fixed_code, explanation, root_cause, diff, test_case
created_at
```

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/v1/fix` | X-API-Key header | Fix bug (quota-based) |
| POST | `/v1/fix/public` | None | Fix bug (10/day per IP) |
| GET | `/v1/fix/{fix_id}` | None | Get a previous fix |
| POST | `/v1/keys` | Bearer JWT or body.email | Get or create API key |
| GET | `/v1/usage` | Bearer JWT or X-API-Key | Get usage stats |
| GET | `/health` | None | Health check |

### Auth flow for dashboard
1. User logs in via Supabase → gets `session.access_token` (JWT)
2. Dashboard POSTs to `/v1/keys` with `Authorization: Bearer {jwt}`
3. Backend calls Supabase `/auth/v1/user` to verify JWT → gets user email
4. Creates or returns existing API key, stores `raw_key` in DB for display

## Pricing

| Plan | Price | Fixes/month | Notes |
|---|---|---|---|
| Free | $0 | 100 | No credit card |
| Pro | $12/user/mo | 500 | 1 seat only, no sharing |
| Team | $49/user/mo | Unlimited (fair use) | Up to 10 seats |

Beta offer: first 50 VS Code reviewers get lifetime Pro free.

## Environment variables

### Render (API)
- `ANTHROPIC_API_KEY`
- `SUPABASE_URL` = `https://gffkcuknsboezegjqnbu.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY`
- `API_SECRET_KEY`
- `ENVIRONMENT` = `production`

### Vercel (web app — neo-bug-forge-web project)
- `VITE_API_URL` = `https://api.neobugforge.io`
- `VITE_SUPABASE_URL` = `https://gffkcuknsboezegjqnbu.supabase.co`
- `VITE_SUPABASE_ANON_KEY`

## Known gotchas

1. **Three separate repos** — always push to the right one (see above)
2. **Windows CRLF warnings** from git are harmless — ignore them
3. **Never commit node_modules** — it breaks Vercel (permission denied on vite binary)
4. **Never commit `.env` files** with real secrets to any repo
5. **Render doesn't auto-deploy** reliably — sometimes needs Manual Deploy button
6. **Vercel root directory** for neo-bug-forge-web must be empty (files are at repo root, not in a subfolder)
7. **Supabase anon key is public** — safe to use in frontend; service role key is secret (backend only)

## What's been built ✅

- Landing page with animated terminal demo, pricing, beta offer
- Terms of Service and Privacy Policy (UK GDPR compliant)
- VS Code extension v1.0.2 published on marketplace
- FastAPI backend with rate limiting, quota management, fix history
- React web app: bug fixer (main page), Login, Signup, Dashboard
- Supabase auth: GitHub OAuth + email/password, email verification
- API key generation and display in dashboard
- Domain neobugforge.io on Cloudflare, all subdomains configured

## What's left to build 🔧

1. **Stripe payments** — Pro ($12/mo) and Team ($49/user/mo) subscription checkout
2. **Webhook to upgrade tier** — Stripe webhook updates `api_keys.tier` on payment
3. **Cloudflare email routing** — hello@neobugforge.io not receiving emails reliably
4. **Fix Monaco Editor** — App.jsx imports Monaco but it renders as textarea fallback
5. **Account sharing enforcement** — Pro tier rate-limited to 1 concurrent session
6. **Admin dashboard** — see all users, revenue, fix volume

## Next step

Start with Stripe: add `stripe` to `api/requirements.txt`, create `/v1/stripe/checkout` endpoint that creates a Stripe Checkout Session, and add upgrade buttons in the Dashboard that redirect to Stripe.
