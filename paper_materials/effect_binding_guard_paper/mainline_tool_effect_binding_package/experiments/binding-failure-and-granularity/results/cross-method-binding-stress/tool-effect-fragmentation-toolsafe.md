# Tool-Effect Fragmentation: toolsafe

- Adapter status: `proxy_diagnostic`
- Paper-grade eligible: `False`
- Cases: `216`

## Metrics

| Method | FNR | Held-out-tool FNR | Held-out-wrapper FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Abstain | Intra-action inconsistency | Action-level error | Access guard |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `arg_schema_classifier` | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | PASS |
| `effect_resource_abstraction` | 0.067 | 0.083 | 0.083 | 0.000 | 0.067 | 0.417 | 0.000 | 0.333 | 0.000 | PASS |
| `execution_evidence_upper_bound` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 | 0.000 | PASS |
| `plan_level_llm_judge` | 0.075 | 0.083 | 0.000 | 0.000 | 0.075 | 0.865 | 0.000 | 0.417 | 0.000 | PASS |
| `static_llm_self_audit` | 0.075 | 0.083 | 0.000 | 0.000 | 0.075 | 0.865 | 0.000 | 0.417 | 0.000 | PASS |
| `step_level_classifier` | 0.075 | 0.083 | 0.000 | 0.000 | 0.075 | 0.865 | 0.000 | 0.417 | 0.000 | PASS |
| `tool_name_classifier` | 0.733 | 1.000 | 1.000 | 0.667 | 0.733 | 0.000 | 0.000 | 0.333 | 0.667 | PASS |
| `trajectory_level_classifier` | 0.075 | 0.083 | 0.000 | 0.000 | 0.075 | 0.865 | 0.000 | 0.417 | 0.000 | PASS |

## Claim Boundary

- Proxy diagnostic only; not an original-author reproduction.
- Use for framework validation and hypothesis generation, not for method-performance claims.

## Reproduction Notes

- Proxy over published TS-Bench step/trajectory tuples when present; not a TS-Guard author checkpoint reproduction.
- Exact TS-Guard requires HF checkpoint/inference wiring and is kept outside paper-grade claims.
