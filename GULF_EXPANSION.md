# Attestly — Gulf / UAE Expansion Plan

Making Attestly faster and more trusted for users in the Gulf (esp. Dubai / UAE).
Lean changes only — no rewrite. Referenced from `PLAYBOOK.md`.

---

## Key insight (saves wasted effort)

**The frontend is already fast in Dubai, and Vercel `dxb1` won't change that.** The app is a
*static* Vite SPA — Vercel already serves it from its global edge CDN (incl. the Dubai PoP).
`dxb1` / region config only affects serverless/edge functions, which we don't have. The latency
Gulf users actually feel is **API round-trips to Render (US)** and the **Claude drafting call**.
That's where to aim.

---

## 1. Current state

| Area | Today | Gulf implication |
|---|---|---|
| Frontend | Vercel static SPA, global edge CDN. No regions in `vercel.json`. | Already fast in Dubai — leave it. |
| Backend API | Render, single region (US by default — confirm). | ~230–280ms RTT/call from Dubai; several sequential calls feel sluggish. |
| Database | Supabase Postgres (region fixed at creation; confirm). | Cross-region app↔DB latency if not co-located. |
| LLM / embeddings | Anthropic Claude + Voyage AI — **US, fixed, cannot relocate**. | Dominates answer latency; geography barely helps. |
| Data location | All subprocessors default US. Now disclosed in `privacy.html §3a`. | Was: no clean residency story. Now: stated honestly. |
| Language | 100% hardcoded English (`App.jsx`). No RTL/locale. | No Arabic yet. |
| Frameworks | Now covers SOC 2, ISO 27001, GDPR **+ PDPL, DIFC/ADGM, VARA, IA/NESA** (starter bank). | First run by a Gulf customer recognises regional asks. |

## 2. Prioritized changes

**HIGH / LOW effort**
1. ✅ Data-location statement + PDPL-aware DPA (done — `privacy.html §3a`, `dpa.html`).
2. ✅ Regional starter answers (done — 8 added: PDPL, ISO 27001, DIFC/ADGM, VARA, IA/NESA, residency, transfers).
3. ⬜ Arabic **landing page** (`index.ar.html`, `dir="rtl"`) — highest localization ROI.

**MEDIUM / MEDIUM effort**
4. ⬜ Move Render + Supabase **together** to Frankfurt (`eu-central`). Halves user RTT **and** backs the
   "EU-hosted" residency story. Region is fixed at creation → recreate service + migrate DB (use the
   `pg_dump` backup). Move BOTH, co-located.
5. ⬜ Perceived-speed UX: optimistic approve, skeleton loaders, parallelize `/v1/me` + `/v1/answers`,
   keep backend warm (paid Render plan).

**LOWER / defer**
6. ⬜ Arabic **app UI** chrome — tiny hand-rolled i18n (`STRINGS[lang]` + `dir`), no new deps. After the
   landing page proves demand.
7. ⬜ True in-UAE residency (AWS me-central / local cloud) — big lift, only on a specific enterprise deal.

## 3. Done in this pass (zero-infra)

- `backend/sample_data/starter_answer_bank.json` — +8 Gulf/UAE framework answers (37 → 45).
- `marketing/privacy.html` — new **§3a "Where your data is processed"** + PDPL in international transfers.
- `marketing/dpa.html` — new GDPR + UAE PDPL / DIFC / ADGM-aware DPA template (lawyer review pending).
- `marketing/index.html` — footer links to the DPA.
- `frontend/src/App.jsx` — first-run nudge copy notes the regional frameworks (no hardcoded count).

## 4. Risks / things to avoid

- **Never translate the security *answers* into Arabic** — Gulf questionnaires (SIG/CAIQ/ISO) are in
  English; Arabic answers break the deliverable. Arabic = marketing + app chrome only.
- **Never claim UAE/in-country residency we don't have.** Frankfurt = "EU-hosted", not "UAE-hosted".
  Misrepresenting under PDPL / to a CISO backfires. Disclose the US AI processing honestly.
- **Region is fixed at creation** on Render + Supabase → migrate-and-cutover, not a toggle. Plan a
  window, keep old project until the new one is verified.
- **Move app + DB together**; splitting regions adds latency.
- **RTL CSS can break layouts** — scope to the landing page first.
- **Keep one codebase** — language as a flag/dictionary, not a fork (protects the lean-deps story).

---

*The 80/20: the data-residency + PDPL story (pure content, big sales impact) and the Frankfurt
co-located move (halves latency + backs the residency claim). Arabic landing page is a strong third.*
