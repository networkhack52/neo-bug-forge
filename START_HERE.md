# START HERE — everything, from the very beginning

This is the complete checklist to go from "code exists" to "first paying
customer." Do the steps in order. Deep detail lives in `DEPLOY.md` (going live)
and `SALES_PLAYBOOK.md` (getting customers); this file is the master sequence.

> **Product:** working name **Attestly** (rename anytime — see Step 5).
> **It has its own repo:** `networkhack52/attestly`, completely separate from
> `neo-bug-forge`. Different folder on your computer = zero chance of mixing up
> pushes.

---

## Step 1 — Install the tools (one time)
You need three things installed. Check each in a terminal:
```bash
git --version        # any recent version
python3 --version    # need 3.11 or newer
node --version       # need 18 or newer
```
If any is missing: Git → https://git-scm.com · Python → https://python.org/downloads
· Node → https://nodejs.org (LTS).

---

## Step 2 — Put the code in its own folder + push to the Attestly repo
The finished code currently sits on a branch of the *old* repo
(`attestly-only`). This moves it into your new, separate `attestly` repo. Run it
once, from wherever you keep projects (e.g. `Documents`):

```bash
git clone --branch attestly-only --single-branch \
  https://github.com/networkhack52/neo-bug-forge.git attestly
cd attestly
git branch -m main
git remote set-url origin https://github.com/networkhack52/attestly.git
git push -u origin main
```

✅ Now the `attestly/` folder is 100% independent. Everything below happens
**inside this folder.** From here on, `git push` only ever touches the Attestly
repo.

---

## Step 3 — Run it locally and confirm it works (no keys needed)
**Backend** (terminal 1):
```bash
cd backend
pip install -r requirements.txt
python run_demo.py          # watch it answer a sample questionnaire end-to-end
python -m pytest -q         # should say "17 passed"
python -m uvicorn app.main:app --port 8000   # leave this running
```

**Frontend** (terminal 2 — open a new terminal, go back to the attestly folder):
```bash
cd frontend
npm install
npm run dev                 # opens http://localhost:5173
```
Open http://localhost:5173, create a company, and upload
`backend/sample_data/sample_questionnaire.xlsx`. You should see it auto-answer.

---

## Step 4 — Generate your first sales asset (still no keys needed)
This is the report you send prospects (assessment-based selling):
```bash
cd backend
python -m app.make_assessment "Some Prospect Inc" --soc2 --volume 6 \
  --out prospect.html
```
Open `prospect.html` in a browser — that's the artifact. Full motion in
`SALES_PLAYBOOK.md`.

---

## Step 5 — (Optional) Lock the product name
Rename in **one place**: open `backend/app/config.py`, change
`BRAND_NAME = "Attestly"` to your chosen name. (Or set an env var
`ATTESTLY_BRAND=YourName` without editing code.) Commit + push:
```bash
git add -A && git commit -m "Rename brand" && git push
```

---

## Step 6 — Go live (only when you're ready to charge money)
Full click-by-click steps are in **`DEPLOY.md`**. The order:
1. **Anthropic key** — console.anthropic.com → create key (set a spend cap).
2. **Stripe** — create 3 products ($99/$249/$499), copy the price IDs, secret
   key, and add the webhook.
3. **Backend → Render** — root directory `backend`; paste the keys as env vars.
4. **Frontend → Vercel** — root directory `frontend`; set `VITE_API_URL` to the
   Render URL.
5. Verify `https://<backend>/health` shows `"llm_enabled": true,
   "stripe_enabled": true`.
6. **Before real customers:** attach a Render Disk or move to Supabase/Postgres
   so data survives deploys (DEPLOY.md §3).

---

## Step 7 — Get your first 20–30 customers (no ads)
Follow **`SALES_PLAYBOOK.md`**:
1. Build a list of ~100–150 companies that just got SOC 2 / hired a security
   person / raised a round.
2. Generate a readiness report for each (Step 4).
3. Send the "want your readiness report?" email.
4. Offer to auto-answer their real questionnaire free → they hit the wall →
   they upgrade.

---

## The map of the project
| Folder / file | What it is |
|---|---|
| `backend/` | The API + engine (push changes here → deploy to Render) |
| `frontend/` | The dashboard (push changes here → deploy to Vercel) |
| `financial_model/` | 12-month model (`python model.py`) |
| `VALIDATION_SCORECARD.md` | Why this product (signed off) |
| `GO_TO_MARKET.md` | 90-day launch + SEO plan |
| `SALES_PLAYBOOK.md` | Assessment-based selling — first customers |
| `DEPLOY.md` | Wiring keys + deploying |
| `START_HERE.md` | This file |

Stuck on any step? That step's detail is in the file named in the table above.
