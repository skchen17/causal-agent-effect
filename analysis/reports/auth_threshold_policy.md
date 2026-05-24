# Auth-SafeInv Threshold Policy

Date: 2026-05-18

## Purpose

This document fixes the reporting policy for Auth-SafeInv FNR/FPR numbers so
paper tables do not mix deployment-style thresholds, LOTO stress-test
thresholds, and ex-post tradeoff summaries.

## Current Facts

- `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v1.json` reports both fixed-threshold rows and threshold curves for T47 baselines.
- `analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v1.json` reports the same for T51 contrastive projection.
- The `best_tradeoffs` fields in T47/T51 are ex-post summaries over reported threshold curves. They are useful for comparing FNR/FPR tradeoffs, but they are not deployment-calibrated thresholds.
- `calibrated_abstention` is the only current baseline that selects a threshold from held-out training groups. No current contrastive mitigation run has a validation-selected threshold.
- T62 adds validation-selected threshold diagnostics for trace-conditioned verifier-assisted monitors:
  - T58 controlled traces: execution verifier held-out test FNR=0.0/FPR=0.0 at threshold 0.05, with N+=44/N-=558.
  - T59 real-agent-tools local-adapter traces: execution verifier held-out test FNR=0.1765/FPR=0.0 at threshold 0.05, with N+=17/N-=178.
  - T61 DeepSeek provider API traces: execution verifier held-out test FNR=0.0/FPR=0.0 at threshold 0.05, with N+=78/N-=432; static verifiers have held-out test FNR=1.0/FPR=0.0.
  - T63 broader web/search/browser/messaging local-adapter traces: execution verifier held-out test FNR=0.0351/FPR=0.0 at threshold 0.05, with N+=114/N-=1133; static verifiers have held-out test FNR=0.614/FPR=0.0132.
  - These thresholds are selected on validation trace groups and tested on held-out trace groups. They are calibration diagnostics for controlled/API trace datasets, not deployment safety guarantees.

## Reporting Policy

1. Fixed-threshold diagnostics:
   - Use threshold 0.5 when reporting raw probe brittleness or historical comparability.
   - Label these as fixed-threshold diagnostics, not deployment calibration.

2. FPR-constrained method comparison:
   - Use FPR <= 0.10 as the main tradeoff target for comparing T47 baselines and T51 mitigation.
   - Label this as an ex-post FPR-constrained diagnostic curve summary.
   - Do not describe the selected threshold as a deployable policy unless it was selected without looking at the held-out test cell.

3. Deployment-style threshold claims:
   - Only validation-selected thresholds may be called calibrated for deployment-like use.
   - Current trace-monitor evidence with validation-selected thresholds is limited to T62/T63 over T58/T59/T61/T63 trace datasets.
   - A future mitigation threshold for new trace families must be selected on training/validation groups before testing to support deployment-like wording.
   - Do not describe T62/T63 as deployed calibration because their validation/test groups are controlled, local-adapter, or single-provider API traces rather than live deployed-agent traffic.

4. Theory/risk accounting:
   - Use deploy FNR only when the threshold is selected without test-cell information.
   - Use LOTO or family-holdout FNR only as coverage-missing stress-test quantities.
   - Do not substitute T47/T51 ex-post best tradeoff FNR into deploy-system safety bounds.

## Paper Wording

Allowed:

- "At FPR <= 0.10 on the reported diagnostic threshold curve, method X attains mean held-out unauthorized FNR Y."
- "This is a stress-test tradeoff summary rather than a deployment-calibrated threshold."
- "Observed-pair projection is an upper-bound repair setting because projection training has access to held-out-tool positive pairs."
- "Strict train-only projection is coverage-limited on Auth-SafeInv: LOTO covers 4/14 same-baseline cells and family holdout is worse than the best non-degenerate baseline at FPR <= 0.10."

Not allowed:

- "The mitigation reduces deploy FNR to 0."
- "FPR <= 0.10 threshold selection proves deployment safety."
- "Observed-pair upper-bound projection solves coverage-missing generalization."
- "Strict contrastive projection is the main solution for Auth-SafeInv" under the current T51 result.

## Table Policy

Main or appendix tables should include:

| Table | Threshold rule | Required columns |
|---|---|---|
| Raw Auth-SafeInv failure | fixed 0.5 | split, effect, heldout surface, N unauth, FNR, FPR, CI |
| Strong baseline comparison | FPR <= 0.10 ex-post curve summary | method, split, cells, threshold, mean FNR, mean FPR, max FNR |
| Mitigation comparison | FPR <= 0.10 ex-post curve summary plus coverage | method, split, cells, coverage, mean FNR, mean FPR, best baseline, delta FNR |
| Deployment-like calibration | validation-selected only | validation rule, target FPR, test FNR, test FPR |

## Consequence for Current Paper

T51 did not clear the mitigation gate for a strong main-conference method
claim. T54 then tested whether v2 surface-graph expansion fixes the failure.
It improves strict train-only coverage, but still does not beat the strongest
non-degenerate baseline at FPR <= 0.10. The paper can currently claim:

- Auth-SafeInv exposes severe coverage-missing failures.
- Strong baselines reduce mean FNR but leave residual high-FNR cells and FNR/FPR tradeoffs.
- Contrastive projection works as an observed-pair repair upper bound.
- v2 surface graph expansion makes strict split-train projection broadly evaluable, but it still does not beat strong baselines broadly enough for a main solution claim.
- verifier-assisted execution monitors now have validation-selected threshold evidence on T58/T59/T61/T63 trace datasets, with residual failure concentrated in local-adapter stress settings and broader external-validity coverage still missing.

The next main-conference step is either:

- develop a mitigation that does not require observed cross-tool positive pairs for the held-out effect; or
- strengthen the representation-learning method so strict train-only projection beats domain-adversarial / supervised-contrastive baselines under identical cells; or
- validate the verifier-assisted trace evidence on direct external-service or deployed-runtime browser/search/messaging traces, since T63 covers those families only through controlled local adapters.
