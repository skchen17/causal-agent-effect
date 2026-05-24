# T58 Execution-Level Effect-Present Verifier

- Train data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Trace data: `qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1`
- Train condition: `full_tool_chain`
- Train rows used: 11712
- Trace rows: 960
- Conditions: `['full_tool_chain']`
- Present verifiers: `['execution_trace', 'static_trace_semantic', 'static_monitored_effect_only']`
- Target FPR: 0.1

## Present Verifier Aggregate

| Split | Condition | Verifier | Rows | Cells | Mean present FNR | Mean present FPR | Max present FNR |
|---|---|---|---:|---:|---:|---:|---:|
| `schema_to_trace_all` | `full_tool_chain` | `execution_trace` | 3 | 3 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_monitored_effect_only` | 3 | 3 | 1.0 | 0.0 | 1.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_trace_semantic` | 3 | 3 | 1.0 | 0.0 | 1.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `execution_trace` | 5 | 5 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_monitored_effect_only` | 5 | 5 | 1.0 | 0.0 | 1.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_trace_semantic` | 5 | 5 | 1.0 | 0.0 | 1.0 |
| `schema_to_trace_type` | `full_tool_chain` | `execution_trace` | 3 | 3 | 0.0 | 0.0 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_monitored_effect_only` | 3 | 3 | 1.0 | 0.0 | 1.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_trace_semantic` | 3 | 3 | 1.0 | 0.0 | 1.0 |

## Best Ex-Post Unauthorized Tradeoffs

| Split | Condition | Method | Threshold | Cells | Mean FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|
| `schema_to_trace_all` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 2 | 0.0 | 0.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | 0.05 | 2 | 1.0 | 0.0 |
| `schema_to_trace_all` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | 0.05 | 2 | 1.0 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 2 | 0.0 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | 0.05 | 2 | 1.0 | 0.0 |
| `schema_to_trace_tool` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | 0.05 | 2 | 1.0 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `execution_trace_sgd_auth` | 0.05 | 2 | 0.0 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_monitored_effect_only_sgd_auth` | 0.05 | 2 | 1.0 | 0.0 |
| `schema_to_trace_type` | `full_tool_chain` | `static_trace_semantic_sgd_auth` | 0.05 | 2 | 1.0 | 0.0 |

## Static-vs-Execution Mismatch

### `full_tool_chain`

Verifier: `static_trace_semantic`

| Group | FP | FN |
|---|---:|---:|
| `false_negative::file_content_read::browser_navigate::headless_chrome_file_browser_runtime` | 0 | 90 |
| `false_negative::content_fetched::browser_navigate::headless_chrome_file_browser_runtime` | 0 | 90 |
| `false_negative::tool_error::browser_navigate::headless_chrome_file_browser_runtime` | 0 | 30 |
| `false_negative::file_content_read::browser_snapshot::headless_chrome_file_browser_runtime` | 0 | 30 |
| `false_negative::content_fetched::browser_snapshot::headless_chrome_file_browser_runtime` | 0 | 30 |

Verifier: `static_monitored_effect_only`

| Group | FP | FN |
|---|---:|---:|
| `false_negative::file_content_read::browser_navigate::headless_chrome_file_browser_runtime` | 0 | 90 |
| `false_negative::content_fetched::browser_navigate::headless_chrome_file_browser_runtime` | 0 | 90 |
| `false_negative::tool_error::browser_navigate::headless_chrome_file_browser_runtime` | 0 | 30 |
| `false_negative::file_content_read::browser_snapshot::headless_chrome_file_browser_runtime` | 0 | 30 |
| `false_negative::content_fetched::browser_snapshot::headless_chrome_file_browser_runtime` | 0 | 30 |

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
