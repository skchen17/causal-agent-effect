# toolsafe Official Checkpoint E47 Custom Stress

- Method: `ts_guard_official_custom_stress`
- Cases: `216`
- Parse-valid: `216/216`
- FNR: `0.1750`
- Held-out-tool FNR: `0.0000`
- Held-out-wrapper FNR: `0.0000`
- ToolProxyGap: `0.0000`
- Unsafe pre-allow: `0.1750`
- Safe false deny: `0.1042`
- Same-effect consistency: `0.1667`

## By Perturbation

| Perturbation | N | FNR | FPR | Unsafe pre-allow | Safe false deny |
|---|---:|---:|---:|---:|---:|
| `hidden_trace_labels` | 24 | 0.0000 | 0.1667 | 0.0000 | 0.1667 |
| `original` | 24 | 0.1667 | 0.0000 | 0.1667 | 0.0000 |
| `same_effect_arg_schema_change` | 24 | 0.0000 | 0.2500 | 0.0000 | 0.2500 |
| `same_effect_tool_rename` | 24 | 0.0000 | 0.0833 | 0.0000 | 0.0833 |
| `same_effect_wrapper_tool` | 24 | 0.0000 | 0.0833 | 0.0000 | 0.0833 |
| `same_plan_different_planner_format` | 24 | 0.2500 | 0.1667 | 0.2500 | 0.1667 |
| `same_tool_different_effect` | 24 | 0.4167 | NA | 0.4167 | NA |
| `same_trajectory_different_trace_format` | 24 | 0.0833 | 0.0833 | 0.0833 | 0.0833 |
| `tool_name_graph_vs_effect_resource_graph` | 24 | 0.4167 | 0.0000 | 0.4167 | 0.0000 |

## Claim Boundary

- Uses the released official checkpoint and its published input/output format.
- The perturbations are E47 custom stress transformations, not original-paper benchmark cases.
- Expected decisions/effect labels remain proxy or published-derived labels and are not model inputs.
- Some intended perturbation views explicitly encode effect/resource semantics; report them separately from hidden-label settings.
- No tools or side effects are executed.
