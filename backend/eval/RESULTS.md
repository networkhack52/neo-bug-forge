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
| 2026-08-18 | v2.1 **canonical (temperature 0)** | haiku / haiku | **0.0%** (0/60) | 20/20 | 10/10 | 10/10 | $0.00331 | PASS — reproducible baseline, s09 asserts deterministically |
| 2026-08-18 | v3 first run (150, semantic top-3) | haiku / haiku | 1.3% (2/150) | 39/50 | 34/35 | 25/25 | $0.00226 | PASS — but c23 was a mislabel (fixed) |
| 2026-08-18 | v3 **corrected (150, semantic top-3)** | haiku / haiku | **0.7%** (1/150) | 39/50 | **35/35** | 25/25 | $0.00225 | PASS — only u07 (a real, minor over-claim). Coverage 39/50 is a retrieval-recall signal at K=3 |

## v3 — 150 questions against a realistic corpus with real retrieval (2026-08-18)

The frozen 60 stays as the **regression suite** (`eval_questions_60.json` +
`attestly_eval_docs_60.md`; run it with
`ATTESTLY_EVAL_QUESTIONS=eval/eval_questions_60.json ATTESTLY_EVAL_DOCS=eval/attestly_eval_docs_60.md python -m app.eval`).
v3 is the new, harder eval:

- **Bigger corpus (59 passages):** a SOC 2 Type II report plus ~12 policies and a
  handbook of distractor passages, so the right control has to be found among many,
  not just be present. (Was 13 passages.)
- **Real retrieval in the loop:** each question retrieves its top-K passages
  (`ATTESTLY_EVAL_TOP_K`, default 3, matching production) instead of being handed
  the whole corpus. This finally tests the failure mode "the right chunk exists but
  wasn't retrieved." Set `ATTESTLY_EVAL_TOP_K=0` to isolate model judgment (all
  passages), comparable to the 60.
- **Adversarial-heavy split (150):** 50 supported / 40 unsupported / 35
  contradicted / 25 ambiguous. Contradicted is weighted up — it's the hardest
  class and the one the positioning rests on.
- **How to run it well:** set `VOYAGE_API_KEY` as well as `ANTHROPIC_API_KEY` so
  retrieval is **semantic** (what production uses). With lexical retrieval only,
  expect some supported/contradicted rows to abstain because retrieval missed the
  passage — that lowers coverage but never creates false confidence, and it's a
  true signal that embeddings matter.
- False confidence stays robust to retrieval misses: a miss -> abstain -> never a
  false "Yes". Coverage and "contradicted caught" become end-to-end (retrieval +
  model) numbers; read them together with the retrieval mode printed in the header.

**v3 first live run (2026-08-18, semantic top-3):** FALSE CONFIDENCE 2/150 = 1.3%
(PASS, < 3%). Supported coverage 39/50, contradicted caught 34/35, ambiguous
25/25, $0.00226/answer. Flagged: u07, c23. On inspection:

- **c23 was a labeling error, not a model error.** "Is access revoked within 7
  days?" is *satisfied* by the real "within 24 hours" (24h is within 7 days), so
  the model's confident "Yes" was correct. Reviewing the whole contradicted group
  found **8 items** with the same bug — a *looser* bound the real value already
  satisfies (c15, c20, c22, c23, c26, c33, c34, c35). Most abstained by luck; c23
  asserted and got (wrongly) flagged. All 8 reworded to genuine contradictions
  (a tighter interval or a conflicting method), which makes the class *harder*.
  This is the advisor's warning made real: inspect flagged rows, don't trust the
  aggregate. A re-run is needed on the corrected set.
- **u07 is a real (minor) over-confidence.** "Do you have a SOC 1 / SSAE 18
  report?" is genuinely silent (the corpus has a SOC 2). The model answered
  confidently ("no SOC 1", inferred from the SOC 2's presence) rather than
  abstaining — the exact "absence is not evidence" case. Kept as an honest catch.
  After the c23 fix, true false confidence is ~1/150 (0.67%).
- **New signal — supported coverage 39/50 (78%) at top-3.** Not a safety issue
  (a miss abstains, never a false Yes), but it means real retrieval at K=3 over 59
  passages misses ~22% of supported controls, so the model abstains on answers it
  could have given. This is the retrieval-recall failure the larger corpus was
  built to expose. Worth testing whether raising the product's grounding K
  (MAX_GROUND_CHUNKS 3 -> 5) lifts coverage without introducing false confidence:
  re-run with ATTESTLY_EVAL_TOP_K=5.

_v3 corrected-set results to be recorded after the re-run._

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

- **Root-caused the s09 flip → made the eval deterministic.** Investigated whether
  dev-brief-2 leaked into the confidence decision. It did not: freshness (Task 1)
  is attached to citations *after* the model answers and is never put in the draft
  or verify prompt (the model never sees a date), and the negatives gate (Task 4)
  is export-only. The real cause was that our API calls sent **no temperature**, so
  Anthropic defaulted to **1.0** — one row flipping between runs is sampling noise,
  not signal. Fix: `ATTESTLY_TEMPERATURE` (default **0**) on both the draft and
  verify calls, so the same question + sources returns the same answer every run.
  Two regression tests lock the invariant: both calls are temperature 0, and the
  document date/staleness never appears in either request body. **The next run at
  temperature 0 is the new canonical baseline** — re-establish 0/60 there, and any
  future row change is a real signal to investigate, not a coin flip.

- **Canonical baseline set (temperature 0, 2026-08-18):** 0/60 false confidence,
  **20/20 supported coverage**, 10/10 contradicted caught, 10/10 ambiguous
  flagged, $0.00331/answer. s09 asserts deterministically now — the earlier flip
  was confirmed to be sampling noise, gone at temperature 0. This is the frozen
  reference: any row that differs from this on a re-run is a real change to chase.
