# USENIX Security '27 Submission Readiness

Last updated: 2026-08-16.

## Current Decision

**Status: paper evidence complete; author verification and artifact release remain.**

All eight frozen terminal experiments, the fixed evidence ledger, generated final tables, and compact per-case export have passed their fail-fast gates. Performance claims follow the observed outcomes, including any failed non-inferiority, baseline parity, or atom-attribution result.

## Evidence Outcome

- DeepSeek benign non-inferiority at the five-point margin: `false`.
- Security not worse than no guard on the frozen Qwen and held-out checks: `true`.
- Closed-loop registered-field granularity signal: `true`.
- Validated-atom versus generic raw-field runtime difference: `true`.
- Defined atom-semantic security/selectivity benefit: `true`.
- Finite concrete-atom authorizer exactness: `true`.
- Qwen Pareto dominators of C1f: `prompt_sandwiching`.
- Simulated second-round recommendation: **Borderline / Weak Reject**.

## Claim Boundary

The supportable claim is that counterfactually validated, policy-relative effect atoms expose representation collisions and can drive auditable pre-commit mediation under explicit provenance and runtime assumptions. The evidence does not establish a globally minimal schema, a complete authority system, production safety, unrestricted adaptive robustness, or SOTA.

## Author-Only Completion

Authors must verify all AI-assisted prose and numbers, provide author/ORCID/funding/conflict metadata, perform the final anonymity review, run the released package in a clean environment, and insert a stable anonymous artifact URL.
