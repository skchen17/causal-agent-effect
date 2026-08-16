# Tool-Effect Fragmentation: ipiguard

- Adapter status: `proxy_diagnostic`
- Paper-grade eligible: `False`
- Cases: `135`

## Metrics

| Method | FNR | Held-out-tool FNR | Held-out-wrapper FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Abstain | Intra-action inconsistency | Action-level error | Access guard |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `arg_schema_classifier` | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | PASS |
| `effect_resource_abstraction` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | PASS |
| `execution_evidence_upper_bound` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.200 | 0.000 | PASS |
| `plan_level_llm_judge` | 0.405 | 0.500 | 0.000 | 0.000 | 0.405 | 0.250 | 0.000 | 0.600 | 0.000 | PASS |
| `static_llm_self_audit` | 0.405 | 0.500 | 0.000 | 0.000 | 0.405 | 0.250 | 0.000 | 0.600 | 0.000 | PASS |
| `step_level_classifier` | 0.405 | 0.500 | 0.000 | 0.000 | 0.405 | 0.250 | 0.000 | 0.600 | 0.000 | PASS |
| `tool_name_classifier` | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | PASS |
| `trajectory_level_classifier` | 0.405 | 0.500 | 0.000 | 0.000 | 0.405 | 0.250 | 0.000 | 0.600 | 0.000 | PASS |

## Claim Boundary

- Proxy diagnostic only; not an original-author reproduction.
- Use for framework validation and hypothesis generation, not for method-performance claims.

## Reproduction Notes

- Proxy TDG-style cases; not an IPIGuard author implementation.
