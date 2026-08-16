# E50 Hard Effect-Binding Guard Robustness Summary

## Main Finding

E50 strengthens E48 as the current hard-method baseline while making the remaining bottlenecks explicit. The hard guard reproduces its E48 result and remains stable under source-balanced splits, but resource/authorization binding is still weak and LOSO is mixed.

## E48 Reproduction

- Full guard UPA: `0.036`.
- Full guard FDeny: `0.065`.
- Full guard coverage: `0.917`.

## Source-Balanced Splits

- Aggregate fixed-policy UPA: `0.051351351351351354` mean.
- Aggregate fixed-policy coverage: `0.923076923076923` mean.
- Aggregate fixed-policy FDeny: `0.05894736842105263` mean.

## Leave-One-Source-Out

- `strict_loso_camel`: UPA `0.000`, FDeny `0.000`, coverage `0.778`.
- `strict_loso_ipiguard`: UPA `0.125`, FDeny `0.083`, coverage `0.892`.
- `strict_loso_phase4`: UPA `0.015`, FDeny `0.061`, coverage `0.943`.

## Threshold Sensitivity

- Fixed E48 policy: UPA `0.03611111111111111`, FDeny `0.06493506493506493`, coverage `0.9172749391727494`.
- Safety-first operating point: policy `{'allow_threshold': 0.34, 'deny_threshold': 0.2, 'max_disagreement': 0.2}`, UPA `0.03333333333333333`, coverage `0.9172749391727494`.

## Targeted Stress Results

- Resource/auth stress: UPA `0.383`, FDeny `0.000`, coverage `0.921`.
- Expanded provenance stress: UPA `0.000`, FDeny `0.188`, coverage `0.545`.

## Recommended Paper Framing

- Main positive claim: explicit tuple binding plus selective evidence and provenance checks improves the custom-stress safety/coverage tradeoff over individual hard modules.
- Main limitation: resource and authorization binding remain the dominant non-oracle failure mode.
- Source-shift claim: source-balanced robustness is positive; LOSO must be described as mixed, especially for IPIGuard.

## Claim Boundary

- Custom-stress robustness evidence only.
- No production-readiness, complete permission-system, original-paper benchmark reproduction, or safety-certificate claim.
- Resource/authorization and source-shift failures must be reported rather than hidden.

## Required Reading

- See `e50_ablation_table.md` for module responsibility.
- See `e50_resource_authorization_stress.md` for scope-boundary failures.
- See `e50_control_provenance_stress.md` for expanded provenance behavior.
- See `e50_failure_examples.md` for representative failure cases.
