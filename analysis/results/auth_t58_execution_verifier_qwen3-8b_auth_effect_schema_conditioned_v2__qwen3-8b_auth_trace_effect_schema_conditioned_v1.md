# T58 Execution-Level Effect-Present Verifier

- Train data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Trace data: `qwen3-8b_auth_trace_effect_schema_conditioned_v1`
- Train condition: `full_tool_chain`
- Train rows used: 11712
- Trace rows: 1104
- Conditions: `['full_tool_chain']`
- Present verifiers: `['execution_trace', 'static_trace_semantic', 'static_monitored_effect_only']`
- Target FPR: 0.1

## Present Verifier Aggregate

| Split | Condition | Verifier | Rows | Cells | Mean present FNR | Mean present FPR | Max present FNR |
|---|---|---|---:|---:|---:|---:|---:|
| `schema_to_trace_all` | `full_tool_chain` | `execution_trace` | 8 | 8 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_monitored_effect_only` | 8 | 8 | 0.1313 | 0.0157 | 1.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_trace_semantic` | 8 | 8 | 0.0063 | 0.0399 | 0.05 |
| `schema_to_trace_tool` | `full_tool_chain` | `execution_trace` | 16 | 16 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_monitored_effect_only` | 16 | 16 | 0.075 | 0.0902 | 1.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_trace_semantic` | 16 | 16 | 0.0125 | 0.1672 | 0.2 |
| `schema_to_trace_type` | `full_tool_chain` | `execution_trace` | 18 | 18 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_monitored_effect_only` | 18 | 18 | 0.1111 | 0.0157 | 1.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_trace_semantic` | 18 | 18 | 0.0 | 0.0157 | 0.0 |

## Best Ex-Post Unauthorized Tradeoffs

| Split | Condition | Method | Threshold | Cells | Mean FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|
| `schema_to_trace_all` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 8 | 0.0429 | 0.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | 0.05 | 8 | 0.15 | 0.0157 |
| `schema_to_trace_all` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | 0.05 | 8 | 0.0429 | 0.0399 |
| `schema_to_trace_tool` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 10 | 0.0393 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | None | 0 | None | None |
| `schema_to_trace_tool` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | None | 0 | None | None |
| `schema_to_trace_type` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 14 | 0.0286 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | 0.05 | 14 | 0.1 | 0.0202 |
| `schema_to_trace_type` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | 0.05 | 14 | 0.0286 | 0.0202 |

## Static-vs-Execution Mismatch

### `full_tool_chain`

Verifier: `static_trace_semantic`

| Group | FP | FN |
|---|---:|---:|
| `false_positive::command_executed::terminal::sandbox_simulated` | 24 | 0 |
| `false_positive::network_egress::terminal::sandbox_simulated` | 4 | 0 |
| `false_positive::network_egress::web_search::sandbox_simulated` | 4 | 0 |
| `false_positive::file_written::write_file::sandbox_simulated` | 4 | 0 |
| `false_negative::file_deleted::terminal::static_replay` | 0 | 1 |
| `false_positive::file_written::write_file::static_replay` | 1 | 0 |
| `false_positive::message_sent::terminal::static_replay` | 1 | 0 |

Verifier: `static_monitored_effect_only`

| Group | FP | FN |
|---|---:|---:|
| `false_negative::command_executed::terminal::observed_execution` | 0 | 10 |
| `false_positive::network_egress::terminal::sandbox_simulated` | 4 | 0 |
| `false_positive::network_egress::web_search::sandbox_simulated` | 4 | 0 |
| `false_positive::file_written::write_file::sandbox_simulated` | 4 | 0 |
| `false_negative::command_executed::terminal::static_replay` | 0 | 4 |
| `false_negative::file_deleted::terminal::static_replay` | 0 | 1 |
| `false_positive::file_written::write_file::static_replay` | 1 | 0 |
| `false_positive::message_sent::terminal::static_replay` | 1 | 0 |

## T57 Reference

- Source: `analysis/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.json`
- This is a reference only; T57 schema LOTO cells and T58 trace rows are not the same evaluation population.

## Skips

- Skipped rows: 0

## Caveats

- Execution verifier outputs come from controlled observed execution, sandbox simulation, and static replay traces, not live deployed-agent traffic.
- The authorization monitor is trained on synthetic schema-conditioned data and evaluated on trace-conditioned rows; this is a setting shift.
- `execution_trace` present predictions are trace-verifier outputs, so present FNR/FPR are zero by construction on the trace dataset; the meaningful test is the combined unauthorized FNR/FPR and static-vs-execution mismatch.
- Threshold tradeoffs are ex-post diagnostics, not deployment-calibrated thresholds.
