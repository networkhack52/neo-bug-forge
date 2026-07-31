# Deploy Checklist — Neo Bug Forge

Launch-day (Hacker News) edition. Work top to bottom; the 🚀 section is what
must be true **before you post**.

## 🚀 Launch-critical (do before the HN post)

1. **Redeploy the API to Render from `main`.** This ships several backend
   changes that are merged but NOT yet live in production:
   - `CF-Connecting-IP` handling in `get_real_ip` (PR #12)
   - env-configurable models + 5/day public limit (PR #12)
   - the direct-to-origin block middleware (PR #16)
   Until you redeploy, none of these are active.

2. **Cloudflare origin protection — pick ONE (don't need both):**
   - **A.** Restrict the Render service to Cloudflare's IP ranges (allowlist), **or**
   - **B.** Set `ORIGIN_SECRET=<openssl rand -hex 32>` in Render env **and** add a
     Cloudflare Transform Rule that injects `X-Origin-Secret: <same value>` on all
     requests to the API hostname.
   ⚠️ Without this, someone can hit the Render origin directly with a forged
   `CF-Connecting-IP` header and bypass per-IP rate limits. If you use A, leave
   `ORIGIN_SECRET` empty (the middleware stays dormant).
   ⚠️ Before setting `ORIGIN_SECRET`: confirm `api.neobugforge.io` is proxied
   through Cloudflare (**orange cloud**, not "DNS only") — otherwise the edge
   never injects the header and every real browser/extension request gets 403'd.

   **Verify (one-glance) — `origin_secret_configured`:**
   ```bash
   # Through Cloudflare — must be 200 (the edge injects X-Origin-Secret):
   curl -s -o /dev/null -w "cloudflare: %{http_code}\n" https://api.neobugforge.io/
   # Straight to the Render origin — must be 403 (no header → rejected):
   curl -s -o /dev/null -w "direct:     %{http_code}\n" https://<your-service>.onrender.com/
   ```
   Want: `cloudflare: 200` + `direct: 403`. If `direct: 200`, the origin is
   unprotected (secret unset / origin reachable). If `cloudflare: 403`, the
   Cloudflare header rule isn't firing — real users are being blocked, back it
   out. (Option A instead? `direct` should be a connection refused/timeout, and
   `ORIGIN_SECRET` stays empty.)

3. **RLS — ✅ DONE.** `api_keys` and `fixes` have RLS enabled with no anon
   policies (anon key gets zero rows).

   **Verify (one-glance) — RLS enabled** (Supabase SQL editor):
   ```sql
   select relname, relrowsecurity as rls_enabled
   from pg_class where relname in ('api_keys','fixes');   -- both must be true
   ```
   And confirm no anon policies snuck in (want **zero rows**):
   ```sql
   select tablename, policyname, roles from pg_policies
   where tablename in ('api_keys','fixes');
   ```

4. **Data-privacy migrations.** Run **after** the corresponding code is deployed
   (code stops writing/reading these columns first, then drop them). Skip any
   that are already done.

   **a. API-key `raw_key`** (stop storing plaintext keys):
   ```sql
   UPDATE api_keys SET raw_key = NULL;      -- scrub existing plaintext first
   ALTER TABLE api_keys DROP COLUMN raw_key;
   ```

   **b. `fixes` content columns** (stop storing user code — makes "we store
   nothing of your code" true, including for historical rows):
   ```sql
   ALTER TABLE fixes
     DROP COLUMN IF EXISTS broken_code,
     DROP COLUMN IF EXISTS fixed_code,
     DROP COLUMN IF EXISTS explanation,
     DROP COLUMN IF EXISTS diff,
     DROP COLUMN IF EXISTS test_case;
   ```

   **Verify (one-glance) — no sensitive columns remain:**
   ```sql
   select table_name, column_name
   from information_schema.columns
   where (table_name = 'api_keys'  and column_name = 'raw_key')
      or (table_name = 'fixes'     and column_name in
          ('broken_code','fixed_code','explanation','diff','test_case'));
   -- want ZERO rows
   ```

5. **Anthropic budget + cost lever.** Make sure the account has enough credit for
   a spike. `FIX_MODEL` defaults to `claude-sonnet-5` (pricey). If credit burns
   too fast mid-launch, flip it **without a redeploy** by setting the Render env
   var `FIX_MODEL=claude-haiku-4-5-20251001` (it's read from env).

6. **Confirm production env vars on Render:** `ANTHROPIC_API_KEY`,
   `API_SECRET_KEY` (must NOT be `dev-secret-change-in-prod`), `SUPABASE_URL`,
   `SUPABASE_SERVICE_ROLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
   `STRIPE_PRICE_PRO`, `STRIPE_PRICE_TEAM`, `ADMIN_EMAIL`, and `ORIGIN_SECRET`
   (only if using option 2B).

7. **Render health check path = `/health`.** The origin-secret middleware exempts
   `/health`, and Render's liveness probe hits the origin directly — make sure the
   configured health check path is `/health`, not `/`.

## ✅ Smoke test right after deploy

- `GET https://api.neobugforge.io/health` → `{"status":"ok", ...}`
- Submit a bug from the site → get a fix end-to-end.
- Render logs: `[REAL_USER] ... ip=` shows **varied real client IPs**, not a few
  repeating Cloudflare IPs (confirms the CF-IP handling works).
- Dashboard: sign in → generate a key → rotate it (confirm step appears, key shown
  once).
- Marketplace listing shows **1.5.22** with the demo GIF.

## 🎚 Launch-day levers (keep this handy)

- **Credits draining:** Render env `FIX_MODEL=claude-haiku-4-5-20251001` (no deploy).
- **Getting hammered:** public limit is `5/day` per IP on `/v1/fix/public`
  (`@limiter.limit` in `api.py`; changing it needs a deploy). Decide before launch
  whether 5/day is the right free-taste number.
- Watch: Render logs + the Anthropic usage dashboard.

## 🧹 Housekeeping (non-blocking)

- Delete stale merged branches (all verified merged / from closed PRs):
  `bump-1521`, `remove-review-banner`, `vercel/install-and-configure-vercel-w-vews2t`,
  `vercel/install-vercel-web-analytics-y6mt5y`, `deploy-api-improvements`,
  `fix-thinking-block`, `v1.5.18-improvements`, `v1.5.18-bump`, `v1.5.18-release`,
  `v1.5.20-bump`.
