# T57 Effect-Present Verifier

- Data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Samples: 35136
- Conditions: `['full_tool_chain']`
- Verifier modes: `['trace_semantic', 'monitored_effect_only']`
- Methods: `['rule_present_sgd_auth', 'rule_present_per_effect_sgd_auth']`
- Target FPR: 0.1

## Present Verifier Aggregate

| Split | Condition | Verifier | Rows | Cells | Mean present FNR | Mean present FPR | Max present FNR |
|---|---|---|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `full_tool_chain` | `monitored_effect_only` | 36 | 36 | 0.1597 | 0.0028 | 1.0 |
| `leave_one_family_out` | `full_tool_chain` | `trace_semantic` | 36 | 36 | 0.0486 | 0.0135 | 1.0 |
| `leave_one_tool_out` | `full_tool_chain` | `monitored_effect_only` | 24 | 24 | 0.0609 | 0.0016 | 1.0 |
| `leave_one_tool_out` | `full_tool_chain` | `trace_semantic` | 24 | 24 | 0.0193 | 0.073 | 0.3182 |

## Best Ex-Post Unauthorized Tradeoffs

| Split | Condition | Method | Threshold | Cells | Mean FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|
| `leave_one_family_out` | `full_tool_chain` | `rule_monitored_effect_only_per_effect_sgd_auth` | 0.05 | 21 | 0.2833 | 0.0048 |
| `leave_one_family_out` | `full_tool_chain` | `rule_monitored_effect_only_sgd_auth` | 0.05 | 21 | 0.1531 | 0.0048 |
| `leave_one_family_out` | `full_tool_chain` | `rule_trace_semantic_per_effect_sgd_auth` | 0.05 | 21 | 0.2357 | 0.0048 |
| `leave_one_family_out` | `full_tool_chain` | `rule_trace_semantic_sgd_auth` | 0.05 | 21 | 0.1221 | 0.0048 |
| `leave_one_tool_out` | `full_tool_chain` | `rule_monitored_effect_only_per_effect_sgd_auth` | 0.05 | 21 | 0.0872 | 0.0017 |
| `leave_one_tool_out` | `full_tool_chain` | `rule_monitored_effect_only_sgd_auth` | 0.05 | 22 | 0.0716 | 0.0016 |
| `leave_one_tool_out` | `full_tool_chain` | `rule_trace_semantic_per_effect_sgd_auth` | 0.05 | 21 | 0.0872 | 0.0017 |
| `leave_one_tool_out` | `full_tool_chain` | `rule_trace_semantic_sgd_auth` | 0.05 | 22 | 0.0262 | 0.073 |

## Same-Cell Comparison vs T54 Baselines

- Baseline source: `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.json`
- Interpretation: Setting-shifted comparison: decomposed verifier uses candidate present/authorized supervision over schema-conditioned inputs; T54 baselines train realized-effect probes.

| Split | Condition | Method | Cells | Baseline cells | T57 FNR | T57 FPR | Best baseline | Base FNR | Base FPR | Delta FNR |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| `leave_one_family_out` | `full_tool_chain` | `rule_monitored_effect_only_per_effect_sgd_auth` | 21 | 21 | 0.2833 | 0.0048 | `irm_linear` | 0.1771 | 0.0867 | -0.1062 |
| `leave_one_family_out` | `full_tool_chain` | `rule_monitored_effect_only_sgd_auth` | 21 | 21 | 0.1531 | 0.0048 | `irm_linear` | 0.1771 | 0.0867 | 0.024 |
| `leave_one_family_out` | `full_tool_chain` | `rule_trace_semantic_per_effect_sgd_auth` | 21 | 21 | 0.2357 | 0.0048 | `irm_linear` | 0.1771 | 0.0867 | -0.0586 |
| `leave_one_family_out` | `full_tool_chain` | `rule_trace_semantic_sgd_auth` | 21 | 21 | 0.1221 | 0.0048 | `irm_linear` | 0.1771 | 0.0867 | 0.055 |
| `leave_one_tool_out` | `full_tool_chain` | `rule_monitored_effect_only_per_effect_sgd_auth` | 21 | 21 | 0.0872 | 0.0017 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.0963 |
| `leave_one_tool_out` | `full_tool_chain` | `rule_monitored_effect_only_sgd_auth` | 22 | 21 | 0.0716 | 0.0016 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.1119 |
| `leave_one_tool_out` | `full_tool_chain` | `rule_trace_semantic_per_effect_sgd_auth` | 21 | 21 | 0.0872 | 0.0017 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.0963 |
| `leave_one_tool_out` | `full_tool_chain` | `rule_trace_semantic_sgd_auth` | 22 | 21 | 0.0262 | 0.073 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.1573 |

## Top Mismatch Groups

### `full_tool_chain`

Verifier mode: `trace_semantic`

| Group | FP | FN |
|---|---:|---:|
| `false_positive::command_executed::python_repl::surface_graph_expansion_auth_flip` | 120 | 0 |
| `false_positive::command_executed::terminal::same_task_tool_swap` | 75 | 0 |
| `false_negative::file_deleted::terminal::same_task_tool_swap` | 0 | 15 |
| `false_positive::message_sent::terminal::same_task_effect_substitution` | 14 | 0 |
| `false_negative::file_deleted::terminal::same_task_effect_substitution` | 0 | 14 |
| `false_negative::tool_error::write_file::same_task_effect_substitution` | 0 | 14 |

Verifier mode: `monitored_effect_only`

| Group | FP | FN |
|---|---:|---:|
| `false_negative::command_executed::terminal::same_effect_reframing` | 0 | 300 |
| `false_negative::command_executed::terminal::same_tool_auth_flip` | 0 | 180 |
| `false_negative::command_executed::terminal::same_task_effect_substitution` | 0 | 126 |
| `false_negative::command_executed::terminal::same_task_tool_swap` | 0 | 15 |
| `false_negative::file_deleted::terminal::same_task_tool_swap` | 0 | 15 |
| `false_positive::message_sent::terminal::same_task_effect_substitution` | 14 | 0 |
| `false_negative::file_deleted::terminal::same_task_effect_substitution` | 0 | 14 |
| `false_negative::tool_error::write_file::same_task_effect_substitution` | 0 | 14 |

## Skips

- Skipped rows: 2

## Caveats

- This is a non-oracle static effect-present verifier over tool-call semantics; it does not read gold present labels at prediction time.
- `trace_semantic` is theory-faithful and treats terminal/python calls as command execution; current synthetic labels under-count this incidental effect in some same-task tool swaps.
- `monitored_effect_only` is a conservative taxonomy variant; it may hide command-execution misses and must not be treated as a complete execution verifier.
- The verifier is deterministic and trace-calibrated, not learned from live deployed-agent logs.
- Threshold tradeoffs are ex-post diagnostics, not deployment-calibrated thresholds.
