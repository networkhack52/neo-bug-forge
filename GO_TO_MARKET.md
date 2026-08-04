# Attestly — Launch & SEO Plan (de-risking organic acquisition)

This plan attacks the single load-bearing assumption in the financial model:
that a solo, no-budget founder can acquire customers **organically**. It is
built around one honest constraint:

> **SEO does not produce revenue in 90 days.** New content takes 3–6 months to
> rank. So the first 20–30 customers come from **launch spikes + communities +
> a product-led free tool**, while SEO is *planted* now to become the dominant
> engine in months 4–12 — exactly when the model's growth ramp accelerates.

ICP for the beachhead (narrower than the paid ICP): **B2B SaaS companies,
~20–200 employees, that are SOC 2-certified or mid-audit and have just started
getting enterprise security questionnaires** — acute pain, no dedicated GRC
team, self-serve buyers. They overlap heavily with Vanta/Drata customers.

---

## 1. Free-tool lead magnet / beachhead strategy

Free *templates* are already commoditized (SecureSlate, Thinsky, VeriRFP).
Our wedge is a **free interactive tool that is literally the product's free
tier**, so using it *is* onboarding.

### Primary magnet — "Free Security Questionnaire Answer Generator"
- Paste up to **15 questions** (or upload a sheet) → get AI-drafted answers
  instantly, with confidence flags. This is the existing `/v1/fix`-style flow
  on the Free plan (25 answers/mo).
- **Gate the export, not the value:** answers show on screen free; downloading
  the filled `.xlsx` or saving to an Answer Library requires an email (account
  creation). This maximizes both SEO dwell-time *and* signups.
- Natural upgrade path: "You have 25 free answers. This questionnaire has 84.
  Upgrade to finish it." — the metering already enforces this.

### Secondary magnets (email-gated, SEO landing pages)
- **SIG Lite answer library** (starter bank as a downloadable, branded sheet).
- **CAIQ v4 starter answers** (17 CCM domains).
- **"Vendor security questionnaire response kit"** — template + 36 model
  answers + a 1-page "how to cut response time" guide.

### The programmatic magnet — model-answer pages (this is the big one)
Every entry in `starter_answer_bank.json` becomes an SEO landing page:
> **"How to answer: 'Do you encrypt data at rest?' (security questionnaire)"**
> → shows a model answer + why reviewers ask it + "generate answers to your
> whole questionnaire free" CTA.

- Ship the **36 starter answers as 36 pages on day 1**, then expand the bank to
  **150–200 questions → 150–200 pages** over 90 days.
- These are low-competition, high-intent, and they *demonstrate the product* on
  every page. This is the compounding SEO asset.

### Why this funnel converts
SEO/community traffic → free generator (see value in 30s) → email to export →
hits the 25-answer wall on a real questionnaire → upgrade. The tool solves
*one questionnaire*; the paid product solves *every* questionnaire with a
compounding bank.

---

## 2. SEO keyword targets + content plan

Four keyword tiers, prioritized by **commercial intent first, volume second**
(per the research: compliance-specific, lower-volume terms convert far better
than generic security phrases).

### Tier A — Bottom-funnel "money" keywords (highest priority)
| Keyword | Intent | Page |
|---|---|---|
| security questionnaire automation | buying | Homepage / product |
| security questionnaire software | buying | Product + comparison |
| how to answer security questionnaires faster | solution-aware | Pillar guide |
| automate SIG / CAIQ responses | buying | Product |
| AI security questionnaire tool | buying | Product |

### Tier B — Competitor capture (fast to rank, pre-qualified buyers)
One page each: **"[Competitor] alternative"** and **"[Competitor] pricing"** for
**Loopio, Responsive (RFPIO), Conveyor, Wolfia, AutoRFP.ai, Arphie, Vanta
Questionnaire Automation**. Angle: *self-serve, transparent pricing, no sales
call, starts free* — the exact gap the scorecard identified.

### Tier C — Framework / template (high volume, mid intent → email magnets)
`SIG questionnaire template`, `SIG Lite answer library`, `CAIQ template`,
`CAIQ v4 questions`, `VSAQ template`, `vendor security questionnaire template`,
`DDQ template`, `third-party risk questionnaire`. Each = a genuinely useful
page with an email-gated download.

### Tier D — Programmatic long-tail (the moat, low competition)
`how to answer "<question>" security questionnaire` × 150–200 questions +
`security questionnaire answer examples`, `<framework> example answers`.

### Educational TOFU (link magnets, build topical authority)
`what is a SIG questionnaire`, `CAIQ vs SIG vs VSAQ`, `how long does a security
questionnaire take`, `security questionnaire best practices`,
`SOC 2 vs security questionnaire`.

### Content cadence (solo, sustainable)
- **Weeks 1–2:** 5 cornerstone pages — homepage, product, pillar guide ("Answer
  security questionnaires in minutes"), 1 template page, 1 competitor page +
  the 36 programmatic pages (generated from the bank).
- **Weeks 3–12:** **3 pieces/week** — rotate: 1 competitor/comparison, 1
  template/framework, 1 TOFU educational; **plus** batch-publish programmatic
  answer pages as the bank grows (target +150 pages by day 90).
- Internal linking: every programmatic page links up to the pillar and the free
  tool; templates link to competitor pages; competitor pages link to product.
- Technical: one Next.js/Vite marketing site, SSR/static for crawlability, fast
  Core Web Vitals, schema.org `HowTo`/`FAQ` markup on answer pages.

---

## 3. G2 / Capterra / marketplace listing plan

### G2 + Capterra (now both under G2) — do in week 1
- List in categories: **Security Questionnaire**, **Vendor Security & Privacy
  Assessment**, **RFP Software**, **GRC**.
- Complete profiles fully (screenshots, the demo GIF, transparent pricing —
  transparency is itself a differentiator vs. sales-led incumbents).
- **Reviews:** enroll in G2's review program; ask every activated free user and
  early customer for an honest review (a small gift card via G2's official
  incentive program is allowed). Target **10 reviews in 60 days** to appear in
  category grids and "alternatives" pages — which also feeds Tier-B SEO.

### Integration directories (highest-leverage discovery)
- **Vanta & Drata integration/partner directories** — their customers *are* our
  ICP and are actively handling security reviews. Build a lightweight
  integration (pull existing policies/evidence into the Answer Library) and list in
  both marketplaces. This is the best-fit channel we have.
- **Conveyor / Trust Center adjacency** — content + comparison, not integration.

### Product surfaces
- **Chrome extension** — answer questionnaires inside web portals (OneTrust,
  ServiceNow, SecurityScorecard, Whistic). Distributed free via the Chrome Web
  Store (a marketplace with native discovery) → drives installs → signups.
- **Slack app** — "questionnaire answered / needs review" notifications; listed
  in the Slack App Directory.

### Launch spikes
- **Product Hunt** launch (week 7–8) — coordinate for a top-5-of-day spike;
  offer a PH-exclusive annual discount.
- **Communities:** r/SecurityCareers, r/cybersecurity (where allowed),
  r/SaaS, Indie Hackers, RevGenius, Vanta/Drata user Slacks, "SOC 2" LinkedIn
  groups, and founder communities. Lead with the **free tool**, not a pitch.

---

## 4. 90-day timeline → first 20–30 paying customers

**Funnel math (target = 25 paying):** at ~4% free→paid, need ~**600 free
signups**; at ~3% visitor→signup on the generator, need ~**20k visitors** over
the quarter, front-loaded by launch spikes since SEO lags. Every milestone
below feeds one of those three numbers.

### Phase 1 — Foundation & first signal (Weeks 1–3)
- [ ] Deploy backend (Render) + frontend (Vercel); wire **live Anthropic +
      Stripe** keys; add analytics (Plausible) + funnel events.
- [ ] Ship the **free generator** + email-gated export.
- [ ] Publish 5 cornerstone pages + **36 programmatic answer pages**.
- [ ] G2 + Capterra listings live.
- [ ] Soft launch to warm network + 5 communities (free tool angle).
- **Milestone:** 300 visitors, 40 free signups, **2–3 paying**, 3 G2 reviews.

### Phase 2 — Content engine + community (Weeks 4–7)
- [ ] 3 posts/week (competitor + template + TOFU); grow bank/pages toward 100.
- [ ] Ship **Vanta or Drata integration** + directory listing (pick one first).
- [ ] Founder-led onboarding: personally DM every free signup, learn why they
      churned or converted, fix the top objection.
- [ ] Collect reviews → hit 10 on G2.
- **Milestone (cum):** 4k visitors, 180 signups, **8–10 paying**.

### Phase 3 — Distribution spikes (Weeks 8–11)
- [ ] **Product Hunt launch** (annual-discount offer).
- [ ] Ship **Chrome extension** → Web Store listing.
- [ ] 1–2 guest posts / podcast appearances in compliance/SaaS communities.
- [ ] Double down on the 5 keywords/pages showing early impressions in Search
      Console; expand programmatic pages to ~150.
- **Milestone (cum):** 12k visitors, 400 signups, **16–20 paying**.

### Phase 4 — Convert & compound (Weeks 12–13)
- [ ] Onboarding polish: guided bank seeding (import existing policies), sample
      questionnaire on signup, "invite a teammate."
- [ ] Pricing experiments: annual prepay, "finish this questionnaire" upgrade
      prompt at the metering wall.
- [ ] 2 short **case studies** from happy early customers → sales proof + SEO.
- **Milestone (cum, day 90):** 20k visitors, **600 signups, 22–28 paying** →
      on-track for the model's base case.

### What to watch (kill/scale signals)
- **Visitor→signup < 2%** → the free tool isn't compelling; fix the first-run
  experience before spending on content.
- **Free→paid < 3%** → value/price mismatch or the wall is in the wrong place.
- **Which channel produced each paying customer** (tag every signup source) →
  cut what doesn't convert, pour time into what does.
- **Answer reuse-rate climbing per customer** → the moat is working; feature it
  in onboarding and case studies.

---

## Sequencing note
SEO (Tiers C/D) is planted in Phase 1–2 but pays off in **months 4–12**, which
is precisely where the financial model's ramp steepens (14→44 net-new
customers/month). The 90-day plan buys the first ~25 customers with spikes and
community so the compounding SEO engine has time to take over. If Phase 1–2
milestones miss by >40%, revert to the model's **Pessimistic** ramp and
re-underwrite before scaling spend.
