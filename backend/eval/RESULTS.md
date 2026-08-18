# Eval results log

Run `python -m app.eval` (needs `ANTHROPIC_API_KEY`) after any change to the
drafting prompt, the verify step, or the model. Record the summary here.

Decision rule: false confidence > 3% -> move `VERIFY_MODEL` to a stronger model.

| Date | Eval | draft / verify model | False confidence | Supported cov. | Contradicted caught | Ambiguous flagged | Cost / answer | Result |
|---|---|---|---|---|---|---|---|---|
| 2026-08-16 | v1 (50 Q, 8 passages) | haiku / haiku | 0.0% (0/50) | 20/20 | n/a | 10/10 | $0.00260 | PASS (weak eval) |
| 2026-08-16 | v2 (60 Q, near-miss) | haiku / haiku | 3.3% (2/60)* | 19/20 | 10/10 | 10/10 | $0.00335 | *both flags were correct denials (mislabels) |
| 2026-08-16 | v2.1 (labels fixed) | haiku / haiku | **0.0%** (0/60) | 20/20 | 10/10 | 10/10 | $0.00335 | PASS — haiku-only stands |
| 2026-08-18 | v2.1 rerun (post dev-brief-2) | haiku / haiku | **0.0%** (0/60) | 19/20 | 10/10 | 10/10 | $0.00341 | PASS — brief-2 changes didn't touch grounding |

## Notes

- **v1 was too easy** (feedback from marketing review): only 8 passages, and the
  unsupported topics were flatly absent, so abstaining was trivial. It also let a
  confident **"No" from silence** pass as safe — which is a real deal-losing bug
  (a customer may hold ISO 27001 and simply not have uploaded the certificate).

- **v2 (current) hardens three things:**
  1. **Bigger corpus with distractors** (13+ passages, adjacent + unrelated
     content) so near-miss evidence is present.
  2. **New `contradicted` category** (10 near-miss questions: monthly vs
     quarterly, AES-128 vs AES-256, 1h vs 24h, 99.99% vs 99.9%, etc.) — the
     "stale/near-miss evidence" case the whole product attacks.
  3. **Stricter false-confidence definition:** for *unsupported* questions, ANY
     confident answer (Yes OR No) counts as false confidence — absence is not
     evidence; only abstaining is correct. For *contradicted*, confirming the
     wrong specific (a confident "Yes") counts.

- **Product fix shipped with v2:** the drafting prompt now forbids answering "No"
  or assigning a status from silence (rule 1a), and forbids confirming a specific
  the documents state differently (rule 1b).

- **v2 live run = 3.3% "false confidence" (2/60), but on inspection both were the
  model being RIGHT, not wrong.** The corpus I added ("Acme operates no data
  centers of its own; production runs entirely in the public cloud") gives real
  evidence to *deny* the two flagged questions:
  - u11 "do your data centers use biometric controls?" -> correct **No** (we have
    no data centers). Grounded denial, not a hallucination.
  - u09 "do you offer on-prem deployment?" -> correct **No** (cloud-only).
  Both showed stance `answer` (a confident No), never `assert` (a false Yes). The
  labels were wrong: the corpus refutes the premise, so these were not "silent".
  **This is why you inspect flagged rows instead of trusting the aggregate.**
  We did NOT move verify to a stronger model over a mislabel.

- **v2.1 fix:** reworded u09/u11 to genuinely silent topics (SBOM, WAF) so
  "unsupported" means the documents truly don't address it.

- **v2.1 live run = 0% false confidence (0/60), the honest number on the hard
  eval.** 20/20 supported, 10/10 contradicted caught, 10/10 ambiguous flagged,
  $0.00335/answer. The reworked SBOM/WAF questions were correctly *abstained* on
  (the model did not invent a "No" on genuinely silent topics), which confirms
  the reword corrected a label, it didn't paper over a weakness. s19 (SSO)
  answered correctly this run — the earlier miss was run-to-run variance.
  **Claim we can stand behind: "0% false confidence across 60 questions including
  near-miss and contradicted evidence."**

- **2026-08-18 rerun after dev-brief-2** (source freshness, contradiction check,
  triage, no-bare-negatives). Those features all sit *around* the drafting path
  and don't touch the grounding rules the eval measures, so the frozen 60 was
  the regression check. Result held: **0% false confidence (0/60)**, 10/10
  contradicted caught, 10/10 ambiguous flagged, $0.00341/answer. Supported
  coverage was 19/20 this run (s09 "regular backups?" abstained instead of
  asserting) — a *conservative* miss, not false confidence, and run-to-run
  variance (s09 asserted in the v2.1 run). The claim stands unchanged.
