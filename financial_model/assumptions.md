# Attestly — 12-Month Financial Model: Assumptions & Evidence

Run `python model.py` to reproduce every number below. Three scenarios are
computed; the **Base case reaches $129,860 cumulative net profit**, clearing
the $100k goal. The Pessimistic case lands at ~$47k — included deliberately,
because the validation scorecard rated **distribution a 2/5 risk** and an
honest model must show the downside.

| Scenario | Ending customers | Ending MRR | 12-mo revenue | 12-mo net profit | Hits $100k? |
|---|---|---|---|---|---|
| Pessimistic | 95 | $14.2k | $62.8k | **$47.4k** | ❌ |
| **Base** | **202** | **$36.4k** | **$157.6k** | **$129.9k** | ✅ |
| Optimistic | 331 | $66.1k | $287.5k | **$246.0k** | ✅ |

---

## Key assumptions and why they are defensible

### 1. Pricing — Starter $99 / Growth $249 / Scale $499 per month
- Incumbents are **expensive and sales-led**: Loopio ≈ **$20k/yr**, Responsive (RFPIO) ≈ **$6.5k–$28k/yr** (third-party estimates). This leaves the entire self-serve bottom of the market unserved.
- Self-serve at this layer is **proven to convert**: Bidara publishes **$299–$599/mo** self-serve, Nusii **$29–$129/mo**. Our ladder sits deliberately below the sales-led incumbents and in line with working self-serve comps.
- **Blended ARPU = $180/mo**, from a tier mix of 55% Starter / 35% Growth / 10% Scale ($191.5) discounted for annual prepay and launch promos.

### 2. Problem is severe enough to drive self-serve purchase
- **54%** of companies report **losing deals** because they couldn't complete security questionnaires in time.
- **88%** of organizations take **2+ weeks** to complete vendor assessments manually.
- **78%** of buyers pick the vendor that **responds first**; win rates fall from **47% → 20%** once a deal drags past 50 days.
- One recovered deal pays for a year of Attestly many times over — the ROI story that makes self-serve conversion realistic without a sales team.

### 3. Market is large enough that a tiny share suffices
- Proposal/RFP software TAM **$3.2–3.7B in 2026**, growing **~10–12% CAGR**.
- Mid-market firms answer **~162 RFPs/year** each (plus security questionnaires on top).
- The Base case needs **~200 paying customers**. Against a multi-billion-dollar, fast-growing market this is a rounding error of share — the constraint is **distribution, not demand**.

### 4. Gross margin = 88%
- COGS is almost entirely Claude tokens, and **only net-new (drafted) questions cost anything — reuse from the Answer Library is free**. In the demo, 26% of questions were reused on the *first* questionnaire with a cold bank; that rate climbs as the bank compounds.
- A drafted answer is ≈3k input + 0.7k output tokens. At **Claude Haiku 4.5 pricing (~$1 / $5 per million tokens)** that is **< $0.01 per answer**. Even a heavy customer drafting thousands of answers/month costs a few dollars; infra (Render + Supabase + Vercel) is ~$100/mo total. 88% is conservative.

### 5. Churn = 5%/month (Base)
- Typical self-serve SMB/mid-market logo churn. **Mitigant baked into the product:** the Answer Library is the customer's own compounding asset — leaving means abandoning a growing, curated answer library, which raises switching cost over time (the retention moat from the scorecard).

### 6. Costs
- **Fixed:** $300/mo (hosting, domain, transactional email, misc tools). **No founder salary** — net profit is measured pre-owner-compensation, consistent with the goal of the business *generating* $100k.
- **One-time:** $500 (incorporation, logo, marketplace/listing setup).
- **Payment fees:** 3% (Stripe).

### 7. The distribution ramp — the load-bearing assumption
The Base case adds **2 → 44 net-new paying customers/month** over the year, entirely organic (no ad budget), from:
- **Long-tail SEO / free tools** on high-intent queries ("how to answer a SIG/CAIQ questionnaire", "security questionnaire template", "SOC 2 questionnaire response examples").
- **Marketplace/discovery presence** (G2, Capterra — now consolidated under G2 — plus a Slack/HubSpot listing).
- **Content compounding** from a full-time founder.

This is the **riskiest number in the model** and directly reflects the scorecard's 2/5 distribution score. If organic growth underperforms (Pessimistic ramp), the year ends at ~$47k net — still a real business, but short of the goal. This is the assumption to validate first and hardest after launch (track: organic sessions → free signups → paid conversion).

---

## What would break the model
1. **Organic acquisition doesn't compound** (biggest risk) → Pessimistic path.
2. **A funded competitor** (Wolfia, AutoRFP.ai, Arphie, Inventive.ai) launches an aggressive self-serve free tier and out-SEOs a solo founder.
3. **Answer quality/trust** issues cause churn before the bank compounds — mitigated by the human-review gate and confidence flags in the product.

## Sources
- Loopio / Responsive pricing, self-serve comps (Bidara, Nusii): vendor pricing pages & 2026 comparison articles.
- Security-questionnaire deal-loss / time-cost stats: KillChain, Iris AI, AutoRFP 2026 analyses.
- TAM / CAGR / RFP volume: Fortune Business Insights, Research and Markets, Business Research Insights, Bidara/AutoRFP RFP statistics (2026).
- Claude Haiku token pricing: Anthropic model pricing.
