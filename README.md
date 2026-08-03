# Attestly

**Answer security questionnaires in minutes, not weeks.**

Attestly is a self-serve tool for B2B SaaS companies that lose time (and deals)
to vendor security questionnaires — SIG, CAIQ, VSAQ, and custom spreadsheets.
Upload a questionnaire; Attestly reuses your **approved answers** for anything
it has seen before and drafts the rest with Claude, then hands you a filled
`.xlsx` to review and send.

> The moat is the customer's own **Answer Bank**: every answer they approve is
> saved and reused, so accuracy climbs and API cost falls with every
> questionnaire — and switching away means abandoning a curated asset.

---

## Why this exists (validated before a line of code)

- **54%** of companies report *losing deals* to slow security questionnaires.
- **88%** take **2+ weeks** to complete a vendor assessment manually.
- **78%** of buyers pick whoever **responds first**.
- Incumbents (Loopio ≈ $20k/yr, Responsive ≈ $6.5k–28k/yr) are **sales-led and
  expensive**, leaving the entire self-serve bottom of the market open.

See [`VALIDATION_SCORECARD.md`](VALIDATION_SCORECARD.md) for the full
scorecard and [`financial_model/`](financial_model/) for the 12-month model
(base case: **$129,860 net profit**).

---

## Architecture

```
attestly/
├── backend/            FastAPI + SQLite (Claude drafting, Stripe billing)
│   ├── app/
│   │   ├── main.py         HTTP API
│   │   ├── parsing.py      xlsx/csv question extraction
│   │   ├── retrieval.py    fuzzy Answer-Bank matching (rapidfuzz)
│   │   ├── drafting.py     Claude client + offline fallback
│   │   ├── engine.py       reuse-or-draft orchestration
│   │   ├── billing.py      Stripe Checkout + webhook
│   │   └── db.py           sqlite persistence
│   ├── tests/          pytest suite (12 tests)
│   ├── run_demo.py     full pipeline, no server needed
│   └── sample_data/    36-answer starter bank + sample questionnaire
├── frontend/           React + Vite dashboard
└── financial_model/    runnable 12-month P&L + assumptions
```

Stack reused from the existing product: **Claude** (Haiku 4.5) · **FastAPI** ·
**Supabase/Postgres-ready schema** · **Stripe** · **Vercel/Render** deploy.

---

## Quick start

### 1. Backend
```bash
cd backend
pip install -r requirements.txt

# See the whole thing work end-to-end (no server, no keys needed):
python run_demo.py

# Run the test suite:
python -m pytest -q

# Seed a demo org and run the API:
python -m app.seed          # prints an API token + loads the starter bank
python -m uvicorn app.main:app --reload --port 8000
```

Health check: `curl localhost:8000/health`

### 2. Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /v1 to :8000)
```

Open the app, create a company, add a few answers (or none), then upload
`backend/sample_data/sample_questionnaire.xlsx`.

---

## Configuration

Copy `.env.example` to `.env` (backend reads plain env vars). Everything
degrades gracefully when a key is missing:

| Variable | Effect if unset |
|---|---|
| `ANTHROPIC_API_KEY` | Drafting uses a flagged offline fallback instead of Claude |
| `STRIPE_SECRET_KEY` | Billing returns a *simulated* checkout you can confirm locally |
| `ATTESTLY_DB_PATH` | Defaults to `backend/data/attestly.db` |

With `ANTHROPIC_API_KEY` set, unmatched questions are drafted by
`claude-haiku-4-5-20251001` (override with `ANTHROPIC_MODEL`).

---

## How answering works

For each question:
1. **Rank** the Answer Bank with fuzzy/lexical matching.
2. If the top match ≥ 88% → **reuse it verbatim** (instant, $0 API, consistent).
3. Otherwise → **draft with Claude**, grounded in the closest prior answers,
   returning a confidence score and a `needs_review` flag.
4. Approved answers **flow back into the Bank**, so reuse compounds.

## Readiness Assessment (sales asset)

Generate a shareable, self-contained readiness report to send prospects
(assessment-based selling — see [`SALES_PLAYBOOK.md`](SALES_PLAYBOOK.md)):

```bash
cd backend
python -m app.make_assessment "Prospect Inc" --soc2 --trust-page --volume 6 \
  --cta "https://app.yourbrand.io" --out prospect.html
```

Or via the public API: `POST /v1/assessment` (JSON) and
`POST /v1/assessment/report` (HTML). Example output:
`backend/sample_data/sample_assessment_report.html`.

## Pricing

| Plan | Price | Answers/mo | Bank |
|---|---|---|---|
| Free | $0 | 25 | 50 |
| Starter | $99 | 750 | 500 |
| Growth | $249 | 3,000 | ∞ |
| Scale | $499 | ∞ | ∞ |

## License

Proprietary — all rights reserved (product code).
