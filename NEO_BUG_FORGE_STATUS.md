# Neo Bug Forge — Status & Reference
*Last updated: June 28, 2026*

---

## Current Version
**v1.5.2** — live on VS Code Marketplace

---

## Infrastructure
| Service | URL | Platform |
|---|---|---|
| Landing page | neobugforge.io | Vercel (neo-bug-forge-landing) |
| Web app | app.neobugforge.io | Vercel (neo-bug-forge-web) |
| API | api.neobugforge.io | Render (neo-bug-forge-api) |
| Admin panel | app.neobugforge.io/admin | — |

---

## GitHub Repos
| Repo | Purpose |
|---|---|
| networkhack52/neo-bug-forge | Monorepo (extension + web + landing) |
| networkhack52/neo-bug-forge-api | API only — what Render deploys from |
| networkhack52/neo-bug-forge-web | Web app only — what Vercel deploys from |

---

## How to Publish a New Extension Version
1. Make code changes in `vscode-extension/`
2. Bump version in `vscode-extension/package.json`
3. Commit everything together
4. Tag and push:
```
git add .
git commit -m "feat: your change"
git tag v1.x.x
git push origin main v1.x.x
```
GitHub Actions auto-publishes to the marketplace. ✅

---

## How to Deploy API Changes
Push to the **neo-bug-forge-api** repo (NOT the monorepo):
```
cd C:\Users\lenovo\Downloads\nbf\api
git add .
git commit -m "your change"
git push origin master:main
```
Render auto-deploys. ✅

---

## How to Deploy Web App Changes
Push to the **neo-bug-forge-web** repo OR push to the monorepo (Vercel watches both):
```
cd C:\Users\lenovo\Downloads\nbf
git add web/
git commit -m "your change"
git push
```
Vercel auto-deploys. ✅

---

## Features Shipped (v1.4.x)
- ⚡ Lightbulb quick fix — click any red squiggle
- 🔄 Smart retry — Claude sees previous attempt and tries differently
- 💾 Save test file — one click
- 🎁 Free trial — 10 fixes/day, no signup needed
- 💡 Welcome prompt on first install
- 🔔 Signup prompt at fix #1, #3, #5
- 🤖 Auto-publish via GitHub Actions

---

## Admin Panel
- URL: app.neobugforge.io/admin
- Only accessible by: ya7308312@gmail.com
- Shows all users, tiers, usage
- Can upgrade any user's tier manually

---

## Decisions Made (don't rebuild these)
- **Phase 4 (Security Scan, Multi-file Agent, Custom Rules)** → Wait. No paying users yet.
- **Phase 3 (Multi-model, Game Dev Mode, Analytics)** → Wait. Only do multi-model on backend later.
- **Gmail BCC / email automation** → Wait until 10+ real signups.
- **Custom rules / teach mode** → Park for v2.0.

---

## This Week's Focus
1. 🎬 Record Facebook demo video (squiggle → lightbulb → fixed in 3 seconds)
2. 📢 Post in Facebook dev groups (see below)
3. 👀 Watch free trial conversion (Render logs: `/v1/fix/public` hits)
4. ⏳ Wait for signup signal before building more features

---

## Facebook Groups to Post In
1. **Python Developers** — search on Facebook, 100k+ members
2. **JavaScript Developers** — 200k+ members
3. **VS Code Users / Visual Studio Code** — your exact audience
4. **Indie Hackers / Solo Developers** — builders who relate to your story
5. **Freelance Developers** — they fix bugs daily, perfect fit
6. **Cursor AI Users** — hot audience right now, mention Cursor support

**Post angle that worked:** "Tired of copy-pasting errors into ChatGPT? There's a faster way inside VS Code" + demo video

---

## Secrets & Keys (DO NOT COMMIT)
- Anthropic API key: in Render env vars
- Supabase service role key: in Render env vars
- Stripe keys: in Render env vars
- VSCE_PAT: in GitHub Secrets (Actions)
- Supabase anon key: safe to commit (public by design)

---

## Pricing
| Plan | Fixes/month | Price |
|---|---|---|
| Free | 100 | $0 |
| Pro | 500 | $12.99/mo |
| Team | Unlimited | $49.99/mo |

---

## Support
- hello@neobugforge.io
- github.com/networkhack52/neo-bug-forge/issues
