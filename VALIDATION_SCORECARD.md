# Attestly — Validation Scorecard (signed off)

**Product:** Self-serve AI that answers security questionnaires (SIG, CAIQ,
VSAQ, custom vendor sheets) from a compounding Answer Library.
**ICP:** B2B SaaS companies, $1M–$100M revenue, that sell to larger companies
and get hit with security questionnaires.
**Price:** $99 / $249 / $499 per month, self-serve.
**Status:** ✅ Approved by both parties (narrowed to security questionnaires).

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Problem severity | 🟢 5/5 | 54% lose deals to slow questionnaires; 88% take 2+ weeks manually; 78% of buyers pick the first responder; win rate 47%→20% past 50 days. |
| 2 | Market size | 🟢 4/5 | RFP/proposal software TAM $3.2–3.7B (2026), ~10–12% CAGR; mid-market firms answer ~162 RFPs/yr. Base case needs ~200 customers → negligible share. |
| 3 | Willingness to pay | 🟢 5/5 | Incumbents $6.5k–28k/yr (Responsive), ~$20k/yr (Loopio). Self-serve comps work: Bidara $299–599/mo, Nusii $29–129/mo. |
| 4 | Unit economics | 🟢 4/5 | Claude Haiku COGS < $0.01/drafted answer; reuse is free. Gross margin ~88%. |
| 5 | Technical feasibility | 🟢 4/5 | Parse → fuzzy-match bank → Claude draft → export. Built and tested on the existing stack. |
| 6 | Competitive moat | 🔴 2/5 | Crowded (Loopio, Responsive, Wolfia, AutoRFP.ai, Arphie, Inventive.ai, DeepRFP). No tech moat — value is the customer's compounding Answer Library + self-serve price + niche. |
| 7 | Distribution (no budget) | 🔴 2/5 | Pure self-serve, $0 ad budget. Viable only via narrow-niche long-tail SEO + G2/Capterra + a platform marketplace. **The load-bearing risk.** |

**Verdict:** Problem, market, WTP, and economics are A-grade. Moat and
distribution are the real risks and are validated openly (see the Pessimistic
scenario in the financial model, which lands at ~$47k). The mitigation is the
**narrow niche** (security questionnaires for B2B SaaS) plus the **compounding
Answer Library** as the retention moat.

**First thing to validate post-launch:** the organic acquisition funnel
(sessions → free signups → paid conversion). If it compounds, the base case
($129,860 net profit) holds; if not, the pessimistic case applies.
