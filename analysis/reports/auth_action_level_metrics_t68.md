# T68 Action-Level Auth-SafeInv Metrics

- Train data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Condition: `full_tool_chain`
- Validation split seed: `20260520`

Action-level ground truth marks an action unauthorized if any candidate effect row for that action is an unauthorized realized effect. A monitor denies an action if any candidate effect crosses the T62 validation-selected threshold.

## Summary

| Trace data | Method | Actions | Unauthorized actions | Unauthorized Action Allow Rate | Authorized Action False Denial Rate | Row macro unauth FNR | Row macro absent FPR |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen3-8b_auth_trace_effect_schema_conditioned_v1 | execution_trace | 83 | 39 | 0.0 | 0.1591 | 0.0 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_v1 | static_trace_semantic | 83 | 39 | 0.0 | 0.4091 | 0.0 | 0.0511 |
| qwen3-8b_auth_trace_effect_schema_conditioned_v1 | static_monitored_effect_only | 83 | 39 | 0.0 | 0.2955 | 0.125 | 0.0241 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1 | execution_trace | 29 | 15 | 0.2 | 0.3571 | 0.2083 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1 | static_trace_semantic | 29 | 15 | 0.2 | 0.3571 | 0.2083 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1 | static_monitored_effect_only | 29 | 15 | 0.3333 | 0.3571 | 0.375 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1 | execution_trace | 72 | 57 | 0.0 | 1.0 | 0.0 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1 | static_trace_semantic | 72 | 57 | 1.0 | 0.0 | 1.0 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1 | static_monitored_effect_only | 72 | 57 | 1.0 | 0.0 | 1.0 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1 | execution_trace | 180 | 80 | 0.05 | 0.21 | 0.0345 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1 | static_trace_semantic | 180 | 80 | 0.4875 | 0.21 | 0.6136 | 0.0255 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1 | static_monitored_effect_only | 180 | 80 | 0.4875 | 0.21 | 0.6136 | 0.0255 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1 | execution_trace | 72 | 41 | 0.0 | 1.0 | 0.0 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1 | static_trace_semantic | 72 | 41 | 1.0 | 0.0 | 1.0 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1 | static_monitored_effect_only | 72 | 41 | 1.0 | 0.0 | 1.0 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1 | execution_trace | 180 | 162 | 0.0 | 0.0 | 0.0 | 0.0 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1 | static_trace_semantic | 180 | 162 | 0.321 | 0.0 | 0.4823 | 0.1363 |
| qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1 | static_monitored_effect_only | 180 | 162 | 0.321 | 0.0 | 0.4823 | 0.1363 |

## Caveats

- These are action-level aggregates over candidate-effect rows, not deployment traffic.
- The thresholds are inherited from T62 validation-selected trace-group evaluation.
- False denial counts are action-level and can be higher than candidate-row FPR when one false-positive row denies an otherwise authorized action.
- T64 has been rerun with full-precision Qwen3-8B trace embeddings; T65 is file-backed headless Chrome browser-runtime evidence, not provider-backed browser networking.
