# Neo Bug Forge

> AI-powered code bug fixer. Paste broken code + error message → get fixed code, diff, explanation, and a test case in under 3 seconds.

Powered by Claude (Anthropic). Built to ship.

---

## Quick Start

```bash
# 1. Unzip and enter the project
cd neo-bug-forge

# 2. Run setup (installs everything, generates secrets, smoke tests)
chmod +x setup.sh && ./setup.sh

# 3. Run locally
cd api && source venv/bin/activate && uvicorn api:app --reload &
cd web && npm run dev
# → API:  http://localhost:8000
# → Web:  http://localhost:3000
```

---

## Project Structure

```
neo-bug-forge/
├── setup.sh                  ← Run this first
├── .env.example              ← Copy to .env, add your API key
├── .gitignore
│
├── api/                      ← FastAPI REST API
│   ├── api.py                ← Main application
│   ├── requirements.txt      ← Pinned Python deps
│   ├── Procfile              ← Railway / Heroku start command
│   ├── railway.toml          ← Railway deployment config
│   └── Dockerfile            ← Container build
│
├── web/                      ← React web app
│   ├── src/
│   │   ├── App.jsx           ← Main UI component
│   │   ├── api.js            ← API client (calls your backend)
│   │   └── main.jsx          ← React entry point
│   ├── index.html
│   ├── vite.config.js
│   ├── vercel.json           ← Vercel deployment config
│   └── Dockerfile            ← Container build
│
├── vscode-extension/         ← VS Code extension
│   ├── src/
│   │   ├── extension.ts      ← Commands + Claude API
│   │   └── panel.ts          ← Webview UI
│   ├── media/                ← icon.png goes here (128x128)
│   ├── package.json          ← Extension manifest
│   ├── tsconfig.json
│   ├── CHANGELOG.md
│   └── generate_icon.py      ← Generates placeholder icon
│
├── seo/                      ← SEO landing pages
│   ├── seo_generator.py      ← Generates all error pages
│   ├── seo-landing-page.html ← Hand-crafted flagship page
│   ├── sitemap.xml           ← Root sitemap index
│   └── sitemap-pages.xml     ← Core pages sitemap
│
├── scripts/
│   ├── verify-deployment.sh  ← Post-deploy checklist (5 checks)
│   └── estimate_costs.py     ← Monthly cost calculator
│
└── monitoring/
    ├── docker-compose.yml    ← Local dev with all services
    └── uptime.md             ← Better Uptime + alerting guide
```

---

## API Endpoints

| Method | Endpoint | Auth | Rate limit |
|---|---|---|---|
| POST | `/v1/fix/public` | None | 10/day per IP |
| POST | `/v1/fix` | X-API-Key header | 120/min |
| GET | `/v1/fix/{fix_id}` | None | — |
| GET | `/health` | None | — |
| GET | `/docs` | None | Swagger UI |

### Example request

```bash
curl -X POST https://api.neobugforge.io/v1/fix/public \
  -H "Content-Type: application/json" \
  -d '{
    "broken_code": "def avg(nums): return sum(nums)/len(nums)",
    "error_message": "ZeroDivisionError: division by zero",
    "language": "python"
  }'
```

### Example response

```json
{
  "fix_id":      "a3f9c2b1",
  "fixed_code":  "def avg(nums):\n    if not nums: return 0\n    return sum(nums) / len(nums)",
  "explanation": "Added guard clause for empty list — len([]) is 0, causing division by zero.",
  "root_cause":  "index_error",
  "confidence":  97,
  "diff":        "--- original\n+++ fixed\n...",
  "test_case":   "def test_avg_empty(): assert avg([]) == 0",
  "language":    "python",
  "created_at":  "2026-06-06T08:00:00Z",
  "share_url":   "https://neobugforge.io/fix/a3f9c2b1"
}
```

---

## Deployment

### API → Railway

```bash
cd api
railway login
railway new
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set API_SECRET_KEY=$(openssl rand -hex 32)
railway variables set ENVIRONMENT=production
railway up
```

### Web App → Vercel

```bash
cd web
# Set VITE_API_URL in Vercel dashboard to your Railway URL
vercel --prod
```

### VS Code Extension → Marketplace

```bash
cd vscode-extension

# Add 128x128 icon to media/icon.png
python generate_icon.py   # or use your own

# Compile and package
npm run compile
npm run package           # → neo-bug-forge-1.0.0.vsix

# Test locally
code --install-extension neo-bug-forge-1.0.0.vsix

# Publish
vsce login neo-bug-forge
vsce publish
```

### SEO Pages → Vercel

```bash
cd seo
python seo_generator.py       # generates dist/
vercel deploy dist/ --prod
# Submit sitemap to Google Search Console
```

---

## Verify Deployment

```bash
bash scripts/verify-deployment.sh https://your-api.up.railway.app
```

Runs 5 automated checks:
1. Health endpoint returns `status: ok`
2. Anthropic API key is loaded
3. Public fix endpoint returns a valid fix
4. Fix retrieval works by ID
5. Rate limiter blocks request 11 (returns 429)

---

## Cost Estimation

```bash
python scripts/estimate_costs.py --fixes 10000 --model sonnet
```

At 10,000 fixes/month on Sonnet 4: **~$19/month**
At 10,000 fixes/month on Haiku 4:  **~$5/month**

Recommendation: use Haiku for free-tier users, Sonnet for paying users.

---

## QA Test Results

All 4/4 hard test cases passing before launch:

| # | Language | Bug | Result |
|---|---|---|---|
| 2 | Python | KeyError — dict access | ✅ Pass |
| 4 | Python | List mutation in loop (silent) | ✅ Pass |
| 7 | JavaScript | var hoisting closure (silent) | ✅ 7/7 |
| 14 | Rust | Borrow after move | ✅ 8/8 |

---

## Tech Stack

- **AI**: Claude claude-sonnet-4-20250514 (Anthropic)
- **API**: FastAPI + uvicorn + slowapi
- **Web**: React 18 + Vite
- **Extension**: VS Code API + TypeScript
- **Deploy**: Railway (API) + Vercel (Web + SEO)
- **Monitor**: Better Uptime + Railway logs

---

## License

MIT © 2026 Neo Bug Forge
