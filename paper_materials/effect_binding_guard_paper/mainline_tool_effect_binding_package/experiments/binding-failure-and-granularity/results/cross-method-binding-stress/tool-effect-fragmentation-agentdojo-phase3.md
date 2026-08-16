# AgentDojo Phase 3 Tool-Effect Fragmentation

## Protocol Counts

| Protocol | Balanced N | Unbalanced N |
|---|---:|---:|
| `random` | 144 | 144 |
| `held_out_tool` | 144 | 144 |
| `same_effect_different_tool` | 144 | 288 |

## Main Metrics

| Method | Protocol | N | FNR | Held-out-tool FNR | Unsafe pre-allow | Action error | ToolProxyGap |
|---|---|---:|---:|---:|---:|---:|---:|
| `tool_name_classifier` | `random` | 144 | 0.333 [0.262, 0.414] | NA | 0.333 [0.262, 0.414] | 0.333 [0.180, 0.533] | NA |
| `tool_name_classifier` | `held_out_tool` | 144 | 1.000 [0.974, 1.000] | 1.000 [0.974, 1.000] | 1.000 [0.974, 1.000] | 1.000 [0.862, 1.000] | NA |
| `tool_name_classifier` | `same_effect_different_tool` | 144 | 1.000 [0.974, 1.000] | 1.000 [0.949, 1.000] | 1.000 [0.974, 1.000] | 1.000 [0.862, 1.000] | NA |
| `arg_schema_classifier` | `random` | 144 | 0.500 [0.419, 0.581] | NA | 0.500 [0.419, 0.581] | 0.500 [0.314, 0.686] | NA |
| `arg_schema_classifier` | `held_out_tool` | 144 | 0.500 [0.419, 0.581] | 0.500 [0.419, 0.581] | 0.500 [0.419, 0.581] | 0.500 [0.314, 0.686] | NA |
| `arg_schema_classifier` | `same_effect_different_tool` | 144 | 0.757 [0.681, 0.820] | 0.514 [0.401, 0.626] | 0.757 [0.681, 0.820] | 0.500 [0.314, 0.686] | NA |
| `static_llm_self_audit` | `random` | 144 | 0.625 [0.544, 0.700] | NA | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `static_llm_self_audit` | `held_out_tool` | 144 | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `static_llm_self_audit` | `same_effect_different_tool` | 144 | 0.306 [0.236, 0.385] | 0.611 [0.496, 0.715] | 0.306 [0.236, 0.385] | 0.000 [0.000, 0.138] | NA |
| `plan_level_llm_judge` | `random` | 144 | 0.625 [0.544, 0.700] | NA | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `plan_level_llm_judge` | `held_out_tool` | 144 | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `plan_level_llm_judge` | `same_effect_different_tool` | 144 | 0.306 [0.236, 0.385] | 0.611 [0.496, 0.715] | 0.306 [0.236, 0.385] | 0.000 [0.000, 0.138] | NA |
| `step_level_classifier` | `random` | 144 | 0.625 [0.544, 0.700] | NA | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `step_level_classifier` | `held_out_tool` | 144 | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `step_level_classifier` | `same_effect_different_tool` | 144 | 0.306 [0.236, 0.385] | 0.611 [0.496, 0.715] | 0.306 [0.236, 0.385] | 0.000 [0.000, 0.138] | NA |
| `trajectory_level_classifier` | `random` | 144 | 0.625 [0.544, 0.700] | NA | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `trajectory_level_classifier` | `held_out_tool` | 144 | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `trajectory_level_classifier` | `same_effect_different_tool` | 144 | 0.306 [0.236, 0.385] | 0.611 [0.496, 0.715] | 0.306 [0.236, 0.385] | 0.000 [0.000, 0.138] | NA |
| `effect_resource_abstraction` | `random` | 144 | 0.000 [0.000, 0.026] | NA | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.138] | NA |
| `effect_resource_abstraction` | `held_out_tool` | 144 | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.138] | NA |
| `effect_resource_abstraction` | `same_effect_different_tool` | 144 | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.051] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.138] | NA |
| `execution_evidence_upper_bound` | `random` | 144 | 0.000 [0.000, 0.026] | NA | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.138] | NA |
| `execution_evidence_upper_bound` | `held_out_tool` | 144 | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.138] | NA |
| `execution_evidence_upper_bound` | `same_effect_different_tool` | 144 | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.051] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.138] | NA |

## Claim Boundary

- AgentDojo Phase 3 is paper-grade only for local T122-derived custom stress artifacts, not an official AgentDojo benchmark reproduction.
