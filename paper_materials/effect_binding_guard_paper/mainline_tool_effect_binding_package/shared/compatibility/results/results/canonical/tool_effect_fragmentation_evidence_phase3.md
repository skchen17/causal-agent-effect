# Tool-Effect Fragmentation Evidence Phase 3

- Cases: `1296`

| Method | FNR | Held-out-tool FNR | Unsafe pre-allow | Safe false deny | Action error | Claim |
|---|---:|---:|---:|---:|---:|---|
| `effect_resource_abstraction` | 0.000 [0.000, 0.003] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.003] | NA | 0.000 [0.000, 0.138] | upper_bound |
| `execution_evidence_upper_bound` | 0.000 [0.000, 0.003] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.003] | NA | 0.000 [0.000, 0.138] | upper_bound |
| `non_oracle_envdiff_verifier` | 0.000 [0.000, 0.006] | 0.000 [0.000, 0.034] | 0.000 [0.000, 0.003] | NA | 0.000 [0.000, 0.138] | baseline/non_oracle |
| `plan_level_llm_judge` | 0.486 [0.459, 0.513] | 0.625 [0.544, 0.700] | 0.486 [0.459, 0.513] | NA | 0.000 [0.000, 0.138] | baseline/non_oracle |
| `tool_name_classifier` | 0.704 [0.678, 0.728] | 1.000 [0.974, 1.000] | 0.704 [0.678, 0.728] | NA | 0.333 [0.180, 0.533] | baseline/non_oracle |
| `trajectory_level_classifier` | 0.486 [0.459, 0.513] | 0.625 [0.544, 0.700] | 0.486 [0.459, 0.513] | NA | 0.000 [0.000, 0.138] | baseline/non_oracle |

## Claim Boundary

- non_oracle_envdiff_verifier is a saved-evidence diagnostic over local AgentDojo env-diff previews, not a deployed execution verifier.
