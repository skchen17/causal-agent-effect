# B8 Released Guardrail Adapter Report

Adapter: `B8_ToolSafe_TSGuard_style_comparable_local_adapter`.

Claim scope: comparable local adapter under this artifact's deployable-input restriction; not an original benchmark reproduction.

| Dataset | Rows | UPA | FDeny | Coverage | Abstain | Unsupported | Adapter failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| E55-v2 | 600 | 0.435 | 0.095 | 0.900 | 0.100 | 60 | 0 |
| E60 | 480 | 0.533 | 0.200 | 1.000 | 0.000 | 0 | 0 |
| E61 artifact-generated | 300 | 0.189 | 0.222 | 1.000 | 0.000 | 0 | 0 |
| E61 external subset | 156 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 |

The adapter uses no gold labels, gold atoms, expected decisions, violation reasons, or result-derived fields. Its high-level behavior is step-level guardrail mediation: deny visible untrusted-control or visible policy violations, abstain on unsupported/missing trusted context, and allow otherwise.
