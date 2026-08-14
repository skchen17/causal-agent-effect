# USENIX Security '27 Submission Readiness

Last updated: 2026-08-14.

## Current Decision

**Status: conditional no-go until the same-protocol five-method baseline artifact and final regeneration pass.**

The paper has a coherent systems-security contribution and a compilable USENIX-format manuscript. The fixed evidence supports the representation-collision result, finite counterfactual refinement, held-out source validation, a 232-query concrete-atom authorization mechanism, and a narrow deterministic provenance-origin mediation case study. The repeated DeepSeek benign experiment is complete: C1f is 1.0 percentage points below no guard on average, but its one-sided task-clustered 95% lower bound of -0.054 narrowly misses the pre-registered -0.05 non-inferiority gate. The frozen 320-case held-out run is complete, with 4/320 no-guard and 0/320 C1f attack successes but lower C1f task utility (235/320 versus 250/320). The provenance-normalized AgentLAB transfer, four-view, bounded-search, raw-field attribution, and concrete-authorizer runs have passed. Submission readiness now depends on the fresh five-method Qwen3-32B comparison and final manuscript regeneration.

The current narrative now separates effect facts, authorization-separating witnesses, representation sufficiency, and runtime mediation. It does not let the AgentDojo runtime result stand in for concrete-atom sufficiency, and it states that authority must be supplied independently of the planner.

## Passed Gates

- The active manuscript is `paper/current-usenix/main.tex`; no competing draft is used for claims.
- The technical body currently ends on labeled page 9, below the official 13-page limit before final-result insertion.
- The three theoretical statements have executable finite-domain checks and bounded claims.
- The registration audit discloses 67/67 retained descriptor fields and preserves invalid or unresolved interventions.
- Fixed evidence is indexed by a fail-fast claim-to-source reproduction ledger. The refreshed partial ledger contains 232 verified rows and records the missing fresh strong-baseline artifact explicitly.
- The current PDF has no undefined citations or references, missing files, fatal errors, or overfull boxes.
- All 34 cited references have entries and pass the repository metadata audit.
- All 12 interleaved DeepSeek benign runs pass with 388 task evaluations per method; the failed non-inferiority gate is retained as a negative result rather than relabeled.
- The AgentLAB transfer, four-view, bounded-search, raw-field attribution, and concrete-authorizer experiments pass their frozen-key, no-error, and relevant audit gates; their bounded scopes remain explicit.

## Blocking Gates

1. The fresh Qwen3-32B strong-baseline result must contain exactly 97 benign and 629 attack rows for each of no guard, Spotlighting, Prompt Sandwiching, PromptArmor-style local adapter, and C1f, with no errors or reused result rows.
2. Final prose, tables, claim map, case export, page-budget audit, and reproduction outputs must be regenerated after the job finishes, regardless of whether its results are favorable.

## Claim Boundary

The strongest supportable claim is that counterfactually validated, policy-relative effect atoms expose representation collisions and can drive auditable pre-commit mediation under explicit provenance and runtime assumptions. The current evidence does not establish a globally minimal atom schema, a complete authority system, production deployment safety, or unrestricted adaptive robustness.

## Author-Only Completion

Authors must verify all AI-assisted prose and numbers, provide author/ORCID/conflict metadata, perform the final anonymity review, and insert a stable anonymous artifact URL. These are the only remaining steps that cannot be completed from repository evidence.
