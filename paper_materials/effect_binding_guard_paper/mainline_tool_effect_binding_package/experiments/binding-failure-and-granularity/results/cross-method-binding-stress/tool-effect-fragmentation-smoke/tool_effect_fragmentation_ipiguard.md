# Tool-Effect Fragmentation: ipiguard

- Adapter status: `proxy_diagnostic`
- Paper-grade eligible: `False`
- Cases: `36`

## Metrics

| Method | FNR | Held-out-tool FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Abstain | Row/action mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|
| `arg_schema_classifier` | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| `effect_resource_abstraction` | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 |
| `execution_evidence_upper_bound` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.250 |
| `plan_level_llm_judge` | 0.536 | 0.667 | 0.000 | 0.536 | 0.250 | 0.000 | 0.750 |
| `static_llm_self_audit` | 0.536 | 0.667 | 0.000 | 0.536 | 0.250 | 0.000 | 0.750 |
| `step_level_classifier` | 0.536 | 0.667 | 0.000 | 0.536 | 0.250 | 0.000 | 0.750 |
| `tool_name_classifier` | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| `trajectory_level_classifier` | 0.536 | 0.667 | 0.000 | 0.536 | 0.250 | 0.000 | 0.750 |

## Claim Boundary

- Proxy diagnostic only; not an original-author reproduction.
- Use for framework validation and hypothesis generation, not for method-performance claims.

## Reproduction Notes

- Proxy TDG-style cases; not an IPIGuard author implementation.
