# Sales Playbook — Assessment-Based Selling (first 20–30 customers)

The goal: land the first paying customers **without ads**, by leading with a
free *assessment* instead of a pitch. The assessment is already built — see
`backend/app/assessment.py` and `make_assessment.py`.

## Why this works
- **Value first, pitch never.** You hand the prospect a finding about *their*
  company, not a claim about your product.
- **Diagnosis creates urgency.** A grade of "D — losing deals to slow
  responses" lands harder than any feature list.
- **It qualifies leads for you.** Only companies with the problem engage.
- **No ad budget** — just a target list + a repeatable assessment.

## The asset
Run this per prospect to produce a self-contained HTML report you email:
```bash
cd backend
python -m app.make_assessment "Prospect Inc" \
    --soc2 --trust-page --volume 6 --cta "https://app.<yourbrand>.io" \
    --out prospect_inc.html
```
Flags reflect what you can learn about them from public signals (SOC 2 badge,
trust page, etc.). Leave a flag off = that gap shows up in the report. The
report includes a **live auto-answer proof** (~60–80% of a standard
questionnaire) — the "wow" moment.

## Targeting — trigger events (who to email)
Aim at companies about to feel the pain, not everyone:
1. **Just earned SOC 2 / ISO 27001** — now selling to enterprise. Find via
   Vanta/Drata customer signals, LinkedIn "we're SOC 2 certified" posts, trust
   pages that just went live.
2. **Just hired their first security / GRC / compliance person.**
3. **Just raised Series A/B** and are moving upmarket.
Build a list of **100–150** and work it in batches of ~20.

## The outreach (email or LinkedIn — no phone required)
> **Subject:** quick security-questionnaire readiness check for {Company}
>
> Hi {name} — congrats on {trigger, e.g. "the SOC 2"}. That usually means
> enterprise buyers start sending you security questionnaires, and answering
> them well (and fast) is where deals stall.
>
> I ran a quick readiness check on {Company} and put it in a 1-page report —
> your score plus the specific gaps. I also had our tool auto-answer a standard
> questionnaire to show what's reusable. Want me to send it over?

Send the report on reply (or attach it up front for a stronger cold open).

## The conversion
The report *is* the meeting. On the follow-up:
1. Walk the gaps and the time-cost number.
2. Offer to auto-answer **their real pending questionnaire** free (Free tier).
3. They hit the free wall on a real questionnaire → upgrade to finish it.

## Metrics to watch (per batch of ~20)
- Reply rate to the assessment offer (target > 15% — it's value, not a pitch).
- Report → trial rate.
- Trial → paid rate.
Tag every prospect's source so you learn which trigger converts best, then
pour time into that one.

## How it graduates to self-serve
The same assessment becomes the **public "Readiness Score" lead-magnet tool**
and SEO page in `GO_TO_MARKET.md` — outbound now, inbound later, one asset.
