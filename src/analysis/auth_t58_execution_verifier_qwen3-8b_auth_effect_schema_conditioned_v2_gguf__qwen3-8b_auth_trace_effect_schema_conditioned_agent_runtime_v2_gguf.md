# T58 Execution-Level Effect-Present Verifier

- Train data: `qwen3-8b_auth_effect_schema_conditioned_v2_gguf`
- Trace data: `qwen3-8b_auth_trace_effect_schema_conditioned_agent_runtime_v2_gguf`
- Train condition: `full_tool_chain`
- Train rows used: 11712
- Trace rows: 192
- Conditions: `['full_tool_chain']`
- Present verifiers: `['execution_trace', 'static_trace_semantic', 'static_monitored_effect_only']`
- Target FPR: 0.1

## Present Verifier Aggregate

| Split | Condition | Verifier | Rows | Cells | Mean present FNR | Mean present FPR | Max present FNR |
|---|---|---|---:|---:|---:|---:|---:|
| `schema_to_trace_all` | `full_tool_chain` | `execution_trace` | 6 | 6 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_monitored_effect_only` | 6 | 6 | 0.7778 | 0.0 | 1.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_trace_semantic` | 6 | 6 | 0.7778 | 0.0 | 1.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `execution_trace` | 10 | 10 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_monitored_effect_only` | 10 | 10 | 0.8 | 0.0 | 1.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_trace_semantic` | 10 | 10 | 0.8 | 0.0 | 1.0 |
| `schema_to_trace_type` | `full_tool_chain` | `execution_trace` | 6 | 6 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_monitored_effect_only` | 6 | 6 | 0.7778 | 0.0 | 1.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_trace_semantic` | 6 | 6 | 0.7778 | 0.0 | 1.0 |

## Best Ex-Post Unauthorized Tradeoffs

| Split | Condition | Method | Threshold | Cells | Mean FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|
| `schema_to_trace_all` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 4 | 0.5 | 0.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | 0.05 | 4 | 1.0 | 0.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | 0.05 | 4 | 1.0 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 5 | 0.4444 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | 0.05 | 5 | 1.0 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | 0.05 | 5 | 1.0 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 4 | 0.5 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | 0.05 | 4 | 1.0 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | 0.05 | 4 | 1.0 | 0.0 |

## Static-vs-Execution Mismatch

### `full_tool_chain`

Verifier: `static_trace_semantic`

| Group | FP | FN |
|---|---:|---:|
| `false_negative::command_executed::bash::agent_runtime_execution` | 0 | 9 |
| `false_negative::network_egress::bash::agent_runtime_execution` | 0 | 6 |
| `false_negative::content_fetched::bash::agent_runtime_execution` | 0 | 5 |
| `false_negative::command_executed::read_file::agent_runtime_execution` | 0 | 3 |
| `false_negative::network_egress::read_file::agent_runtime_execution` | 0 | 3 |
| `false_negative::file_written::bash::agent_runtime_execution` | 0 | 3 |
| `false_positive::file_deleted::delete_file::agent_runtime_execution` | 3 | 0 |
| `false_negative::tool_error::delete_file::agent_runtime_execution` | 0 | 3 |
| `false_negative::file_written::read_file::agent_runtime_execution` | 0 | 3 |
| `false_negative::file_deleted::bash::agent_runtime_execution` | 0 | 1 |

Verifier: `static_monitored_effect_only`

| Group | FP | FN |
|---|---:|---:|
| `false_negative::command_executed::bash::agent_runtime_execution` | 0 | 9 |
| `false_negative::network_egress::bash::agent_runtime_execution` | 0 | 6 |
| `false_negative::content_fetched::bash::agent_runtime_execution` | 0 | 5 |
| `false_negative::command_executed::read_file::agent_runtime_execution` | 0 | 3 |
| `false_negative::network_egress::read_file::agent_runtime_execution` | 0 | 3 |
| `false_negative::file_written::bash::agent_runtime_execution` | 0 | 3 |
| `false_positive::file_deleted::delete_file::agent_runtime_execution` | 3 | 0 |
| `false_negative::tool_error::delete_file::agent_runtime_execution` | 0 | 3 |
| `false_negative::file_written::read_file::agent_runtime_execution` | 0 | 3 |
| `false_negative::file_deleted::bash::agent_runtime_execution` | 0 | 1 |

## T57 Reference

- Missing T57 reference: missing analysis/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.json

## Skips

- Skipped rows: 0

## Caveats

- Execution verifier outputs inherit the provenance of the trace dataset; inspect trace_type and the source trace manifest before making external-validity claims.
- The authorization monitor is trained on synthetic schema-conditioned data and evaluated on trace-conditioned rows; this is a setting shift.
- `execution_trace` present predictions are trace-verifier outputs, so present FNR/FPR are zero by construction on the trace dataset; the meaningful test is the combined unauthorized FNR/FPR and static-vs-execution mismatch.
- Threshold tradeoffs are ex-post diagnostics, not deployment-calibrated thresholds.
