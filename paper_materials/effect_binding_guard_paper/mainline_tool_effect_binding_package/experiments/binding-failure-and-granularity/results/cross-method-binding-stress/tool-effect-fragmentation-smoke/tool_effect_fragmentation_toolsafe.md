# Tool-Effect Fragmentation: toolsafe

- Adapter status: `proxy_diagnostic`
- Paper-grade eligible: `False`
- Cases: `36`

## Metrics

| Method | FNR | Held-out-tool FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Abstain | Row/action mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|
| `arg_schema_classifier` | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| `effect_resource_abstraction` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 |
| `execution_evidence_upper_bound` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 |
| `plan_level_llm_judge` | 0.100 | 0.000 | 0.000 | 0.100 | 0.125 | 0.000 | 0.500 |
| `static_llm_self_audit` | 0.100 | 0.000 | 0.000 | 0.100 | 0.125 | 0.000 | 0.500 |
| `step_level_classifier` | 0.100 | 0.000 | 0.000 | 0.100 | 0.125 | 0.000 | 0.500 |
| `tool_name_classifier` | 0.600 | 1.000 | 1.000 | 0.600 | 0.000 | 0.000 | 0.500 |
| `trajectory_level_classifier` | 0.100 | 0.000 | 0.000 | 0.100 | 0.125 | 0.000 | 0.500 |

## Claim Boundary

- Proxy diagnostic only; not an original-author reproduction.
- Use for framework validation and hypothesis generation, not for method-performance claims.

## Reproduction Notes

- Proxy TS-Bench-style step tuples; not a TS-Guard author implementation.
