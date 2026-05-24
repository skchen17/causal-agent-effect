# T58 Execution-Level Effect-Present Verifier

- Train data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Trace data: `qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1`
- Train condition: `full_tool_chain`
- Train rows used: 11712
- Trace rows: 2400
- Conditions: `['full_tool_chain']`
- Present verifiers: `['execution_trace', 'static_trace_semantic', 'static_monitored_effect_only']`
- Target FPR: 0.1

## Present Verifier Aggregate

| Split | Condition | Verifier | Rows | Cells | Mean present FNR | Mean present FPR | Max present FNR |
|---|---|---|---:|---:|---:|---:|---:|
| `schema_to_trace_all` | `full_tool_chain` | `execution_trace` | 4 | 4 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_monitored_effect_only` | 4 | 4 | 0.425 | 0.1357 | 1.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_trace_semantic` | 4 | 4 | 0.425 | 0.1357 | 1.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `execution_trace` | 10 | 10 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_monitored_effect_only` | 10 | 10 | 0.5 | 0.4 | 1.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_trace_semantic` | 10 | 10 | 0.5 | 0.4 | 1.0 |
| `schema_to_trace_type` | `full_tool_chain` | `execution_trace` | 6 | 6 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_monitored_effect_only` | 6 | 6 | 0.5333 | 0.1 | 1.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_trace_semantic` | 6 | 6 | 0.5333 | 0.1 | 1.0 |

## Best Ex-Post Unauthorized Tradeoffs

| Split | Condition | Method | Threshold | Cells | Mean FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|
| `schema_to_trace_all` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 4 | 0.0 | 0.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | None | 0 | None | None |
| `schema_to_trace_all` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | None | 0 | None | None |
| `schema_to_trace_tool` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 9 | 0.0 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | None | 0 | None | None |
| `schema_to_trace_tool` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | None | 0 | None | None |
| `schema_to_trace_type` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 6 | 0.0 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | 0.05 | 6 | 0.5833 | 0.1 |
| `schema_to_trace_type` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | 0.05 | 6 | 0.5833 | 0.1 |

## Static-vs-Execution Mismatch

### `full_tool_chain`

Verifier: `static_trace_semantic`

| Group | FP | FN |
|---|---:|---:|
| `false_negative::content_fetched::http_get::live_http_external` | 0 | 60 |
| `false_negative::content_fetched::web_extract::live_http_external` | 0 | 30 |
| `false_negative::network_egress::browser_navigate::live_http_external` | 0 | 30 |
| `false_negative::content_fetched::browser_navigate::live_http_external` | 0 | 30 |
| `false_positive::network_egress::http_post::local_protocol_messaging` | 30 | 0 |
| `false_positive::message_sent::send_message::local_protocol_messaging` | 30 | 0 |
| `false_negative::tool_error::send_message::local_protocol_messaging` | 0 | 30 |
| `false_positive::network_egress::http_get::local_protocol_messaging` | 30 | 0 |
| `false_negative::content_fetched::http_get::local_protocol_messaging` | 0 | 30 |

Verifier: `static_monitored_effect_only`

| Group | FP | FN |
|---|---:|---:|
| `false_negative::content_fetched::http_get::live_http_external` | 0 | 60 |
| `false_negative::content_fetched::web_extract::live_http_external` | 0 | 30 |
| `false_negative::network_egress::browser_navigate::live_http_external` | 0 | 30 |
| `false_negative::content_fetched::browser_navigate::live_http_external` | 0 | 30 |
| `false_positive::network_egress::http_post::local_protocol_messaging` | 30 | 0 |
| `false_positive::message_sent::send_message::local_protocol_messaging` | 30 | 0 |
| `false_negative::tool_error::send_message::local_protocol_messaging` | 0 | 30 |
| `false_positive::network_egress::http_get::local_protocol_messaging` | 30 | 0 |
| `false_negative::content_fetched::http_get::local_protocol_messaging` | 0 | 30 |

## T57 Reference

- Source: `analysis/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.json`
- This is a reference only; T57 schema LOTO cells and T58 trace rows are not the same evaluation population.

## Skips

- Skipped rows: 0

## Caveats

- Execution verifier outputs inherit the provenance of the trace dataset; inspect trace_type and the source trace manifest before making external-validity claims.
- The authorization monitor is trained on synthetic schema-conditioned data and evaluated on trace-conditioned rows; this is a setting shift.
- `execution_trace` present predictions are trace-verifier outputs, so present FNR/FPR are zero by construction on the trace dataset; the meaningful test is the combined unauthorized FNR/FPR and static-vs-execution mismatch.
- Threshold tradeoffs are ex-post diagnostics, not deployment-calibrated thresholds.
