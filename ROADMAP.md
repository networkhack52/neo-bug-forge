# Attestly — Roadmap

The through-line: **start as a tool for one side, become a network across both.**
Keep the beachhead discipline — nail the seller side first — but make every
decision keep the door open to the two-sided endgame.

## Now — Seller side (the beachhead) ✅ shipping
Help B2B SaaS **vendors** answer security questionnaires in minutes.
- Upload questionnaire → reuse from Answer Bank → draft the rest with Claude →
  review → export.
- Trust-hardened engine: grounded-only answers, verifiable **citations**, a
  **verification pass**, human-review gate, injection defense.
- Self-serve billing (monthly + annual "2 months free"), metering, tiers.
- **Why first:** clear payer, acute pain, self-serve. One ICP, one motion.

## Next — Trust Profile export (small, high-leverage)
An org's Answer Bank *is* its **Trust Profile**. Let a seller export/share it:
- A clean, branded "security response" export (already have xlsx export).
- A shareable, read-only Trust Profile link a seller can send to any buyer.
- **Why:** every answered questionnaire now carries an Attestly footprint to the
  buyer — the seed of the loop below. Minimal new code (schema is already
  org + answers = a profile).

## Then — Buyer side (auto-review)
Serve the **buyer** (the enterprise security/procurement team) drowning in
incoming vendor answers.
- Given a vendor's returned answers + the buyer's risk rubric: **score each
  answer, flag vague/missing/risky ones, and draft follow-ups.**
- **Why it's cheap to build:** it's the *same* retrieve → ground → verify engine
  pointed at *evaluation* instead of *generation*. Not a rewrite — a second mode.

## The network loop (the endgame)
Once both sides exist, the flywheel:
1. A seller answers a buyer's questionnaire with Attestly and shares the export.
2. The buyer receives an Attestly-answered response → signs up to **review**
   faster (free).
3. The buyer sends *their other vendors* to Attestly to standardize responses.
4. Each new participant makes the network more valuable (Whistic / SafeBase /
   Conveyor "trust exchange" pattern).

**This directly attacks the weakest row on the validation scorecard —
distribution (2/5).** The loop is organic, no-budget, and compounding: exactly
what a solo founder needs.

## Guardrails (don't lose the plot)
- **Do not build both sides at once.** Two-sided cold-start kills solo founders.
  Sequence it: seller traction → profile export → buyer auto-review → loop.
- Keep the data model **profile-centric** (org's bank = its trust profile) so the
  buyer side and sharing can consume it with no schema surgery. (Already true.)
- Every roadmap step must still serve a paying seller today. If a "network"
  feature doesn't help a current seller, it waits.

## Pricing note
Monthly: $99 / $249 / $499. Annual: $990 / $2,490 / $4,990 ("pay for 10, get
12"). Annual is the default toggle — it pulls cash forward and cuts churn, which
is what gets the business to $100k net in year one. See
`financial_model/assumptions.md`.
