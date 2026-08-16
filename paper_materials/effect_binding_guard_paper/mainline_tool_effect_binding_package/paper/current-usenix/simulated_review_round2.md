# Simulated USENIX Security Review, Round 2

**Recommendation: Borderline / Weak Reject.**

## Summary

The paper presents a policy-relative representation obligation for effectful tool calls, a source-executed counterfactual registration procedure, and a narrow deterministic provenance-origin mediator. All frozen validation artifacts and row-level reproduction gates are complete.

## Evidence Assessment

- The preregistered five-point benign-utility test does not pass its non-inferiority criterion.
- A closed-loop advantage of registered fields over at least one coarser monitor view is present on the selection-conditioned subset.
- A runtime difference between generic raw-field taint and validated-atom semantics is present; absent signal is treated as a negative attribution result.
- A favorable security or selectivity contribution from validated-atom semantics is present; unfavorable differences remain visible.
- The finite concrete-atom authorizer passes its exact 232-query mechanism check.
- Strong-baseline Pareto dominators of C1f on reported Qwen counts: `prompt_sandwiching`.
- Frozen generalization checks do not make C1f worse than no guard on attack success: `true`.
- The source-oracle collision and held-out ToolSandbox results remain the cleanest evidence for the atom representation; runtime ASR alone is not used to prove minimal atom discovery.

## Strengths

1. The paper separates representation, provenance, policy, mediation, and check-use assumptions.
2. Source execution and frozen interventions provide falsifiable evidence rather than evaluator-only semantic labels.
3. Negative results, invalid interventions, Spotlighting comparisons, utility outcomes, and selection boundaries remain visible.
4. The artifact exposes per-cell claim provenance and compact per-case final outcomes.

## Remaining Risks

1. The AgentDojo registry retains all 67 schema fields, so automatic sparse descriptor discovery is not demonstrated.
2. The confinement instance is limited to provenance-origin policy and literal task grounding; ACLs, delegation, quotas, and output-only goals remain outside scope.
3. ToolSandbox and the finite source domains are bounded; they do not certify unseen tools or asynchronous effects.
4. The collision theorem is elementary, so the contribution depends on the executable systems evidence and complete mediation path.

The recommendation does not imply production safety, complete authorization, or SOTA; those claims remain outside the evaluated boundary.

## Provisional Scores

| Criterion | Score (1--5) |
|---|---:|
| Originality | 3 |
| Technical quality | 4 |
| Correctness | 4 |
| Clarity | 4 |
| Systems-security fit | 4 |
