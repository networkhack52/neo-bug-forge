# Neo Bug Forge 🛠️

**The fastest AI-powered bug fixer for VS Code & Cursor**

Select broken code → press `Ctrl+Shift+F` → get fixed code, a diff, and a test case. That's it.

![Demo](https://github.com/networkhack52/neo-bug-forge/raw/main/media/demo.gif)

[Install from VS Marketplace](https://marketplace.visualstudio.com/items?itemName=neobugforge.neo-bug-forge) · [neobugforge.io](https://neobugforge.io)

---

## ✨ Latest Features (v1.4.2)

- **Lightbulb Quick Fix** — hover over any red squiggle → click ⚡ → fixed in seconds
- **Smart Iterative Fixing** — "Try Again" passes the previous attempt to Claude so it tries a different approach
- **Save Test File** — one-click save of the generated test case to your project
- Deep workspace context awareness — automatically pulls in related files
- Clean diff preview + one-click apply + Git stage
- Works great inside **Cursor**

---

## Quick Start

1. Open VS Code or Cursor
2. Go to Extensions (`Ctrl+Shift+X`) and search **"Neo Bug Forge"**
3. Install and add your API key via `Ctrl+Shift+P` → **Neo Bug Forge: Set API Key**
4. Select broken code → press `Ctrl+Shift+F` (or click the lightbulb on any squiggle)

---

## What you get back

| | |
|---|---|
| ✅ Fixed code | Complete corrected version — ready to apply |
| 🔍 Diff preview | Side-by-side diff before you commit to anything |
| 🧠 Explanation | Plain-English: what was wrong and what changed |
| 📊 Confidence | How certain the AI is (0–100%) |
| 🏷 Root cause | null_reference · type_mismatch · off_by_one · logic_error · and more |
| 🧪 Test case | Minimal unit test that would have caught this bug |

---

## Project Structure

```
neo-bug-forge/
├── vscode-extension/   ← VS Code extension (TypeScript)
├── web/                ← React + Vite web app → app.neobugforge.io
├── api/                ← FastAPI backend → api.neobugforge.io
├── landing/            ← Static landing page → neobugforge.io
└── scripts/            ← Cost estimator, deploy helpers
```

---

## API

```bash
curl -X POST https://api.neobugforge.io/v1/fix/public \
  -H "Content-Type: application/json" \
  -d '{
    "broken_code": "def avg(nums): return sum(nums)/len(nums)",
    "error_message": "ZeroDivisionError: division by zero",
    "language": "python"
  }'
```

| Method | Endpoint | Auth |
|---|---|---|
| POST | `/v1/fix/public` | None (10/day per IP) |
| POST | `/v1/fix` | X-API-Key header |
| GET | `/v1/fix/{fix_id}` | None |
| GET | `/health` | None |

---

## Tech Stack

- **AI**: Claude (Anthropic)
- **API**: FastAPI + slowapi
- **Web**: React 18 + Vite + Supabase Auth
- **Extension**: VS Code API + TypeScript
- **Deploy**: Render (API) · Vercel (Web) · Cloudflare (DNS)

---

## Roadmap

- Multi-model support (GPT, Gemini, Grok)
- Stripe payments (Pro/Team plans)
- More language-specific fixes

---

## Support

- ⭐ Star this repo if you find it useful
- 💬 [Leave a review on the Marketplace](https://marketplace.visualstudio.com/items?itemName=neobugforge.neo-bug-forge&ssr=false#review-details)
- 🐛 [Open an issue](https://github.com/networkhack52/neo-bug-forge/issues)
- 📧 [hello@neobugforge.io](mailto:hello@neobugforge.io)

---

**Made with ❤️ by a solo dev for solo devs & indie hackers.**

MIT © 2026 Neo Bug Forge
