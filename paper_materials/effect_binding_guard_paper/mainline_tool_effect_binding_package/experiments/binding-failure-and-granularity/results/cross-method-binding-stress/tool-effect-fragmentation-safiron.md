# Tool-Effect Fragmentation: safiron

- Adapter status: `proxy_diagnostic`
- Paper-grade eligible: `False`
- Cases: `216`

## Metrics

| Method | FNR | Held-out-tool FNR | Held-out-wrapper FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Abstain | Intra-action inconsistency | Action-level error | Access guard |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `arg_schema_classifier` | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | PASS |
| `effect_resource_abstraction` | 0.222 | 0.267 | 0.267 | 0.000 | 0.222 | 0.333 | 0.000 | 0.417 | 0.000 | PASS |
| `execution_evidence_upper_bound` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.375 | 0.000 | PASS |
| `plan_level_llm_judge` | 0.562 | 0.667 | 0.000 | 0.000 | 0.562 | 0.250 | 0.000 | 0.792 | 0.000 | PASS |
| `static_llm_self_audit` | 0.562 | 0.667 | 0.000 | 0.000 | 0.562 | 0.250 | 0.000 | 0.792 | 0.000 | PASS |
| `step_level_classifier` | 0.562 | 0.667 | 0.000 | 0.000 | 0.562 | 0.250 | 0.000 | 0.792 | 0.000 | PASS |
| `tool_name_classifier` | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | PASS |
| `trajectory_level_classifier` | 0.562 | 0.667 | 0.000 | 0.000 | 0.562 | 0.250 | 0.000 | 0.792 | 0.000 | PASS |

## Claim Boundary

- Proxy diagnostic only; not an original-author reproduction.
- Use for framework validation and hypothesis generation, not for method-performance claims.

## Reproduction Notes

- Proxy over Agentic-Guardian Pre-Ex-Bench plan-level examples; not a Safiron author model reproduction.
- Exact Safiron requires the released guardian model/inference stack.
