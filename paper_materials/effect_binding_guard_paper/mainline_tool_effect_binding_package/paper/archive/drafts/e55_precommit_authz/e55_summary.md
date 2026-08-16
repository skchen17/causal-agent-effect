# E55 Realistic Pre-Commit Authorization Binding

- Rows: 600
- Domain counts: `{'email': 120, 'calendar': 120, 'file': 120, 'slack': 120, 'transaction': 120}`
- Slice counts: `{'multi_resource': 516, 'draft_commit': 204, 'alias': 120, 'public_visibility': 156, 'provenance_shift': 108, 'evidence_fallback': 24}`
- Leakage-free: `True`
- Outcome: **Outcome B**
- Interpretation: Authorization-aware guard preserves low UPA while greatly increasing coverage; ablations show the improvement depends on explicit authorization infrastructure.
- Paper framing: Use E55 as mixed evidence: diagnostic binding monitor plus partial authorization-aware prototype.

## Main Comparison

| Method | UPA | FDeny | Coverage | Abstain | Decision Acc |
|---|---:|---:|---:|---:|---:|
| existing_hard_effect_binding_guard | 0.037 | 0.000 | 0.200 | 0.800 | 0.100 |
| authz_aware_effect_binding_guard | 0.000 | 0.000 | 0.920 | 0.080 | 1.000 |

## Human-Corrected Sensitivity

E57 human audit identified 6/60 decision corrections and 14/60 atom/resource/reason corrections in the spot-audit packet. Applying the 6 decision corrections to the 600-row label map preserves zero unsafe pre-allow for the full authorization-aware guard (`0/320`) and coverage `552/600 = 0.920`, but changes FDeny from `0/228` to `4/230 = 0.017`. E55-v2 corrects the transaction `amount` atom and unknown-resource fallback behavior; its strict rerun gives full-guard UPA `0/276 = 0.000`, FDeny `0/252 = 0.000`, and coverage `528/600 = 0.880`.

## E55-v2 Validity Checks

E57-style checks were rerun on the corrected E55-v2 construction. Deterministic resource-name perturbation changed `0` decisions and left authz-aware UPA/coverage deltas at `0.0`; the independent v2 reference authorizer matched the corrected dataset with decision agreement `1.0`, atom count agreement `1.0`, and atom resource-set agreement `1.0`.

## Claim Boundary

E55 is a local mock pre-commit mediation evaluation. It does not execute real external side effects and does not prove production safety.
