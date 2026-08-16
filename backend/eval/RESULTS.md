# Eval results log

Run `python -m app.eval` (needs `ANTHROPIC_API_KEY`) after any change to the
drafting prompt, the verify step, or the model. Record the summary here.

Decision rule: false confidence > 3% -> move `VERIFY_MODEL` to a stronger model.

| Date | draft / verify model | False confidence | Supported coverage | Ambiguous flagged | Cost / answer | Result |
|---|---|---|---|---|---|---|
| 2026-08-16 | claude-haiku-4-5 / claude-haiku-4-5 | **0.0%** (0/50) | 20/20 | 10/10 | $0.00260 | PASS — haiku-only stands |

## Notes

- 2026-08-16 baseline: zero false confidence, full coverage on supported
  controls, full hedging on ambiguous ones. The 3 unsupported items that show
  stance `answer` (ISO 27001, FedRAMP, PCI DSS) were correct confident "No"s,
  not false assertions. Total run cost ~$0.13 for 50 questions.
