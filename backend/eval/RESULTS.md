# Eval results log

Run `python -m app.eval` (needs `ANTHROPIC_API_KEY`) after any change to the
drafting prompt, the verify step, or the model. Record the summary here.

Decision rule: false confidence > 3% -> move `VERIFY_MODEL` to a stronger model.

| Date | Eval | draft / verify model | False confidence | Supported cov. | Contradicted caught | Ambiguous flagged | Cost / answer | Result |
|---|---|---|---|---|---|---|---|---|
| 2026-08-16 | v1 (50 Q, 8 passages) | haiku / haiku | 0.0% (0/50) | 20/20 | n/a | 10/10 | $0.00260 | PASS (weak eval) |
| 2026-08-16 | v2 (60 Q, near-miss) | haiku / haiku | _pending re-run_ | | | | | |

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
  the documents state differently (rule 1b). Re-run `python -m app.eval` to get
  the v2 number under the new prompt.
