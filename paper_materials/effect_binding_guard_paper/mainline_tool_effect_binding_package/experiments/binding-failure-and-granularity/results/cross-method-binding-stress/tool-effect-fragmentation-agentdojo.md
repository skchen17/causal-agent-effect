# Tool-Effect Fragmentation: agentdojo

- Adapter status: `paper_grade`
- Paper-grade eligible: `True`
- Cases: `1296`

## Metrics

| Method | FNR | Held-out-tool FNR | Held-out-wrapper FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Abstain | Intra-action inconsistency | Action-level error | Access guard |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `arg_schema_classifier` | 0.778 | 0.500 | 1.000 | 0.000 | 0.778 | NA | 0.000 | 0.500 | 0.500 | PASS |
| `effect_resource_abstraction` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | NA | 0.000 | 0.000 | 0.000 | PASS |
| `execution_evidence_upper_bound` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | NA | 0.000 | 0.000 | 0.000 | PASS |
| `plan_level_llm_judge` | 0.486 | 0.625 | 0.000 | 0.000 | 0.486 | NA | 0.000 | 0.625 | 0.000 | PASS |
| `static_llm_self_audit` | 0.486 | 0.625 | 0.000 | 0.000 | 0.486 | NA | 0.000 | 0.625 | 0.000 | PASS |
| `step_level_classifier` | 0.486 | 0.625 | 0.000 | 0.000 | 0.486 | NA | 0.000 | 0.625 | 0.000 | PASS |
| `tool_name_classifier` | 0.704 | 1.000 | 1.000 | 0.667 | 0.704 | NA | 0.000 | 0.667 | 0.333 | PASS |
| `trajectory_level_classifier` | 0.486 | 0.625 | 0.000 | 0.000 | 0.486 | NA | 0.000 | 0.625 | 0.000 | PASS |

## Claim Boundary

- Paper-grade only for the local artifacts named in source_path/source_version.
- Perturbed stress cases are synthetic transformations and should be reported as stress tests, not original benchmark metrics.

## Reproduction Notes

- Uses local T122 env-diff/effect verifier artifacts; no new side-effectful execution.
