# E47-E50 Code, Logic, and Evidence Re-Audit

Date: 2026-07-14

## Verdict

After the repairs in this pass, E47-E50 support the following bounded claim:

> On controlled counterfactual stress, released checkpoints and local guards
> exhibit partial effect sensitivity but fail to jointly bind effect, resource,
> authorization, and provenance. Resource and authorization distinctions remain
> the clearest failure surface for the reference hard guard.

They do not by themselves establish that this failure rate is representative of
deployed agents, that the evaluated checkpoints fail their original benchmarks,
or that tool-effect binding is the only explanation for real-world attacks.

## E47: Existing-Method Capability Stress

Status: `correct for controlled-custom-stress claims, with scope caveats`.

- Phase 4 constructs 528 rows from 24 independent anchor groups and evaluates
  same-effect invariance, effect-change sensitivity, authorization sensitivity,
  resource mismatch, unsafe pre-allow, false denial, and coverage.
- TS-Guard and Safiron use released local checkpoints through the official
  checkpoint inference adapters. The inputs and labels are E47's adapted custom
  stress, so these rows are not original-paper benchmark reproductions.
- The tool-name proxy has perfect surface consistency but zero effect,
  authorization, and resource sensitivity. TS-Guard and Safiron show nonzero
  capability on several axes, so the correct finding is incomplete joint
  binding, not "all methods are tool-name classifiers."
- Human review is sampled. The capability matrix now records
  `sampled_human_audit_construction_gated_remainder`; the sampled gate no longer
  upgrades the full custom suite to fully audited status.

Representative group-level results:

| Method | Surface invariance | Effect sensitivity | Authorization sensitivity | Resource awareness | UPA |
|---|---:|---:|---:|---:|---:|
| Tool-name proxy | 1.000 | 0.000 | 0.000 | 0.000 | 0.292 |
| TS-Guard released checkpoint | 0.883 | 0.625 | 0.764 | 0.833 | 0.159 |
| Safiron released checkpoint | 0.669 | 1.000 | 0.088 | 0.167 | 0.545 |
| Local Qwen self-audit | 0.865 | 0.667 | 0.565 | 0.292 | 0.004 |

These results establish heterogeneous partial binding on this custom stress.
They do not rank the original systems under their authors' protocols.

## E48: Reference Hard Guard

Status: `correct after statistical-unit repair`.

- The unified dataset has 822 rows from Phase 4, IPIGuard-style, and CaMeL-style
  controlled components, with 6,840 counterfactual relations.
- Gold labels and construction metadata are separated from deployable input;
  split groups are shared across related Phase 4/IPIGuard anchors to prevent
  cross-split leakage.
- Row metrics are unchanged: the full guard has UPA 13/360 = 0.036, FDeny
  30/462 = 0.065, and coverage 754/822 = 0.917.
- Pairwise intervals previously treated correlated pairs as independent. They
  now average within `split_group_id` and bootstrap groups. Pair-relation
  accuracy is 0.852 with group-bootstrap 95% interval [0.825, 0.877] across 30
  groups; the artifact also retains raw successes 5,931/6,840.

Residual caveat: some Phase 4 `evidence_summary` rows contain simulated
counterfactual evidence. This is not label leakage because construction fields
are stripped, but it is synthetic evidence. Results remain stratified by
evidence origin and must not be described as execution evidence from all rows.

## E49: Learned Calibrator

Status: `correct diagnostic; not positive proof of the proposed mechanism`.

- Training excludes gold tuple fields, construction axes, audit/source metadata,
  and calibrated E48 decisions.
- Resource/auth and provenance stress are evaluation-only.
- The repaired resource/auth stress yields UPA 0.500, FDeny 0.042, and coverage
  1.000 for the learned calibrator, versus UPA 0.383, FDeny 0.000, and coverage
  0.913 for its hard-guard comparator.

The learned calibrator does not solve the bottleneck and should remain a
diagnostic/negative result. It is not needed to establish the core problem.

## E50: Robustness and Bottleneck Stress

Status: `correct after semantic construction repair and full rerun`.

The previous resource/auth result was invalid for paper use. Two DENY variants
visibly authorized the candidate effect they labeled unsafe, and the alias
variant did not actually change the candidate resource. The pre-fix artifacts
are retained only under
`results/analysis/results/archive/e47_e50_pre_semantic_fix_20260714/`.

The repaired generator now:

- authorizes the original effect when testing an alternate effect;
- states explicitly that committed effects are unauthorized in commit-mode
  counterfactuals;
- materializes a distinct alias plus an alias-to-canonical map;
- independently recomputes each expected label from a policy oracle; and
- fails generation if the visible policy and label disagree.

Corrected full-guard result:

| Stress | Rows | UPA | FDeny | Coverage |
|---|---:|---:|---:|---:|
| Resource/authorization | 240 | 46/120 = 0.383 | 0/120 = 0.000 | 221/240 = 0.921 |
| Control provenance | 336 | 0/144 = 0.000 | 36/192 = 0.188 | 183/336 = 0.545 |

The 46 resource/auth unsafe allows are concentrated in three axes:

- near-alias resource: 20/24;
- out-of-scope resource: 20/24;
- same-resource alternate effect: 6/24.

The full guard has zero unsafe allows on explicit missing authorization and
explicit commit denial after the repair. Ablation remains mechanistically
informative: removing resource matching raises UPA to 0.617, while removing
authorization matching raises UPA to 0.892. This supports the bottleneck claim
more cleanly than the invalid pre-fix headline did.

## What the Experiments Prove

Supported:

1. Tool-name stability is not effect binding.
2. Released checkpoints can encode nontrivial effect/authorization sensitivity
   while still failing joint binding on controlled counterfactuals.
3. A hard effect-binding guard improves aggregate E48 tradeoffs but still makes
   unsafe, high-coverage decisions on resource/authorization shifts.
4. Resource matching and authorization matching are causal contributors to the
   E50 result under the implemented ablations.

Not supported by E47-E50 alone:

1. prevalence of the problem in deployed agents;
2. production safety or complete mediation;
3. original TS-Guard/Safiron benchmark reproduction;
4. reliable automatic atom extraction from arbitrary real traces; or
5. a claim that all existing defenses reduce to tool-name classification.

For a USENIX submission, E47-E50 are sufficient as controlled motivation and
mechanism diagnosis. The broader security claim must rely on the later
registered-contract implementation, official AgentDojo comparison, complete
call audit, benign utility, and explicit theorem assumptions.

## Verification

- Original source tests: `43 passed` for E47 Phase 4/6 and E48-E50 targeted tests.
- Consolidated-package tests: `21 passed` for E48/E50.
- E48, E49, and E50 result-generation commands completed successfully.
- E50 acceptance gates all pass after regeneration.
- Lightweight paper reproduction: `55` rows regenerated.
- Unified reproduction: status `passed`, `573` claim-to-source rows.

The exact repair rationale is recorded in
`results/analysis/results/e47_e50_semantic_fix_note.md`.
