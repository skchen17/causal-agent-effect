# E85 Causal-Mediation Contract Validation

- Status: `passed_bounded_finite_model`
- Controlled intervention cases: `9`
- Contract variants: `6`

| Contract | Mediation recall | Mediation precision | Gap rate | Over-sensitivity | Flip agreement |
|---|---:|---:|---:|---:|---:|
| none | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |
| omit_target | 0.000 | 0.000 | 1.000 | 0.000 | 0.333 |
| collapse_multi_resource | 0.857 | 1.000 | 0.111 | 0.000 | 0.889 |
| omit_default_effect | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 |
| omit_compound_effect | 0.857 | 0.857 | 0.111 | 0.000 | 1.000 |
| include_placebo | 1.000 | 0.875 | 0.000 | 0.500 | 1.000 |

## Claim Boundary

E85 validates the causal-mediation metric implementation on a finite controlled tool model. It shows that the checks accept a complete contract and expose target, multi-resource, default, compound-effect, and placebo failures. It does not establish soundness for AgentDojo or external tools.
