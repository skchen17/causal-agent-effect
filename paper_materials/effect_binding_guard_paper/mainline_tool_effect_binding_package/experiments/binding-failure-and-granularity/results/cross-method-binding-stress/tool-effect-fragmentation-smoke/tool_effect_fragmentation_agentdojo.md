# Tool-Effect Fragmentation: agentdojo

- Adapter status: `paper_grade`
- Paper-grade eligible: `True`
- Cases: `216`

## Metrics

| Method | FNR | Held-out-tool FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Abstain | Row/action mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|
| `arg_schema_classifier` | 0.778 | 0.500 | 0.000 | 0.778 | NA | 0.000 | 0.500 |
| `effect_resource_abstraction` | 0.000 | 0.000 | 0.000 | 0.000 | NA | 0.000 | 0.000 |
| `execution_evidence_upper_bound` | 0.000 | 0.000 | 0.000 | 0.000 | NA | 0.000 | 0.000 |
| `plan_level_llm_judge` | 0.389 | 0.500 | 0.000 | 0.389 | NA | 0.000 | 0.500 |
| `static_llm_self_audit` | 0.389 | 0.500 | 0.000 | 0.389 | NA | 0.000 | 0.500 |
| `step_level_classifier` | 0.389 | 0.500 | 0.000 | 0.389 | NA | 0.000 | 0.500 |
| `tool_name_classifier` | 0.556 | 1.000 | 1.000 | 0.556 | NA | 0.000 | 1.000 |
| `trajectory_level_classifier` | 0.389 | 0.500 | 0.000 | 0.389 | NA | 0.000 | 0.500 |

## Claim Boundary

- Paper-grade only for the local artifacts named in source_path/source_version.
- Perturbed stress cases are synthetic transformations and should be reported as stress tests, not original benchmark metrics.

## Reproduction Notes

- Uses local T122 env-diff/effect verifier artifacts; no new side-effectful execution.
