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
| existing_hard_effect_binding_guard | 0.043 | 0.000 | 0.200 | 0.800 | 0.060 |
| authz_aware_effect_binding_guard | 0.000 | 0.000 | 0.880 | 0.120 | 1.000 |

## Claim Boundary

E55 is a local mock pre-commit mediation evaluation. It does not execute real external side effects and does not prove production safety.
