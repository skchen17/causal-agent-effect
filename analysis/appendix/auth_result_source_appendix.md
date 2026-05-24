# Auth-SafeInv Result-Source Appendix

- Reproduction entrypoint: `reproduce_auth_safeinv.sh`
- Conda environment: `causal-safety`
- Primary model: `Qwen/Qwen3-8B`
- All outputs present: True

## Artifact Map

| ID | Task | Script | Outputs present | Key summary |
|---|---|---|---:|---|
| `auth_counterfactuals` | T39 authorization counterfactual dataset | `build_authorization_counterfactuals.py` | True | `{"rows": 1184, "unauthorized_effect_counts": {"command_executed": 126, "content_fetched": 44, "file_content_read": 30, "file_deleted": 44, "file_written": 44, "message_sent": 44, "network_egress": 58, "tool_error": 44}, "unauthorized_too...` |
| `auth_counterfactuals_v2` | T53 authorization surface-graph expansion dataset | `build_authorization_counterfactuals_v2.py` | True | `{"all_focus_unauthorized_tools_ge_3": true, "focus_unauthorized_tool_counts": {"content_fetched": 3, "file_content_read": 3, "file_deleted": 3, "file_written": 3, "message_sent": 3, "network_egress": 3, "tool_error": 3}, "rows": 1464, "r...` |
| `auth_embeddings` | T39 Qwen3-8B authorization embeddings | `extract_embeddings_llm.py` | True | `{"effect_shape": [1184, 11], "embedding_shape": [1184, 4096]}` |
| `auth_embeddings_v2` | T54 Qwen3-8B authorization v2 embeddings | `extract_embeddings_llm.py` | True | `{"effect_shape": [1464, 11], "embedding_shape": [1464, 4096]}` |
| `auth_traces_v2` | T40/T49 auth execution traces | `build_auth_observed_execution_traces.py` | True | `{"leakage_checks": {"duplicate_id_count": 0, "missing_required_fields": {}}, "observed_execution_count": 70, "observed_execution_sufficient": true, "rows": 138, "trace_type_counts": {"observed_execution": 70, "sandbox_simulated": 56, "st...` |
| `auth_safeinv_eval` | T41 Auth-SafeInv held-out evaluation | `experiment_auth_safeinv.py` | True | `{"family_rows": 14, "loto_rows": 15, "max_family_unauthorized_fnr": 1.0, "max_loto_auth_tool_proxy_gap": 1.0, "max_loto_unauthorized_fnr": 1.0, "random_effects": 8}` |
| `auth_safeinv_eval_v2` | T54 Auth-SafeInv v2 held-out evaluation | `experiment_auth_safeinv.py` | True | `{"family_rows": 21, "loto_rows": 22, "max_family_unauthorized_fnr": 1.0, "max_loto_auth_tool_proxy_gap": 1.0, "max_loto_unauthorized_fnr": 1.0, "random_effects": 8}` |
| `surface_graph_alignment` | T42 surface graph alignment | `analyze_surface_graph_alignment.py` | True | `{"effects": 11, "strict_identifiable_unauthorized": [], "strict_identifiable_verified": ["network_egress", "tool_error"]}` |
| `surface_graph_alignment_v2` | T54 v2 surface graph alignment | `analyze_surface_graph_alignment.py` | True | `{"effects": 11, "strict_identifiable_unauthorized": ["content_fetched", "file_content_read", "file_deleted", "file_written", "message_sent", "network_egress", "tool_error"], "strict_identifiable_verified": ["content_fetched", "file_conte...` |
| `piia_hook_confirmatory` | T48 hook-based pIIA controls | `interchange_intervention_hook_controls.py` | True | `{"effects": ["file_content_read", "file_written", "content_fetched", "file_deleted", "network_egress", "tool_error"], "raw_rows": 864, "spearman_piia_drop_vs_heldout_fnr": 0.5296, "spearman_piia_drop_vs_loto_gap": 0.2648}` |
| `auth_baseline_confirmatory` | T47 strong baseline confirmatory sweep | `experiment_auth_baseline_confirmatory.py` | True | `{"fixed_rows": 504, "loto_best_tradeoff_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0775, "mean_unauthorized_fnr": 0.3155, "method": "domain_adversarial", "split_type": "leave_one_tool_out", "target_fpr": 0.1, "threshold": 0.15}, {"m...` |
| `auth_baseline_confirmatory_v2` | T54 strong baseline confirmatory sweep on v2 | `experiment_auth_baseline_confirmatory.py` | True | `{"fixed_rows": 756, "loto_best_tradeoff_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0951, "mean_unauthorized_fnr": 0.1857, "method": "domain_adversarial", "split_type": "leave_one_tool_out", "target_fpr": 0.1, "threshold": 0.25}, {"m...` |
| `auth_mitigation_vs_baseline` | T51 final mitigation-vs-baseline comparison | `experiment_auth_mitigation_comparison.py` | True | `{"fixed_rows": 132, "same_cell_fpr_0_1": {"leave_one_family_out::contrastive_observed_pair_upper_bound": {"best_baseline_mean_fnr": 0.2817, "best_baseline_method": "irm_linear", "cell_coverage": 0.9286, "cells": 13, "delta_fnr_vs_best_ba...` |
| `auth_mitigation_vs_baseline_v2` | T54 mitigation-vs-baseline comparison on v2 | `experiment_auth_mitigation_comparison.py` | True | `{"fixed_rows": 246, "same_cell_fpr_0_1": {"leave_one_family_out::contrastive_observed_pair_upper_bound": {"best_baseline_mean_fnr": 0.1655, "best_baseline_method": "irm_linear", "cell_coverage": 0.9524, "cells": 20, "delta_fnr_vs_best_ba...` |
| `auth_schema_conditioned_data_v2` | T55 effect-schema conditioned candidate-effect data | `build_auth_effect_schema_conditioned_data.py` | True | `{"base_rows": 1464, "candidate_effects": ["command_executed", "file_content_read", "file_written", "file_deleted", "network_egress", "content_fetched", "message_sent", "tool_error"], "conditions": ["full_tool_chain", "auth_only_control",...` |
| `auth_schema_conditioned_embeddings_v2` | T55 Qwen3-8B effect-schema conditioned embeddings | `extract_embeddings_llm.py` | True | `{"effect_shape": [35136, 1], "embedding_shape": [35136, 4096]}` |
| `auth_schema_conditioned_mitigation_v2` | T55 pair-free schema-conditioned mitigation evaluation | `experiment_auth_schema_conditioned_mitigation.py` | True | `{"fixed_rows": 252, "full_tool_chain_best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0279, "mean_unauthorized_fnr": 0.6, "method": "schema_per_effect_sgd", "rows": 20, "schema_condition": "full_tool_chain", "split_type": "...` |
| `auth_decomposed_verifier_mitigation_v2` | T56 full decomposed/verifier mitigation evaluation | `experiment_auth_decomposed_verifier_mitigation.py` | True | `{"fixed_rows": 765, "full_tool_chain_best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.004, "mean_unauthorized_fnr": 0.5638, "method": "decomposed_per_effect_sgd_mean", "rows": 21, "schema_condition": "full_tool_chain", "spl...` |
| `auth_verifier_present_upper_bound_v2` | T56 verifier-present full-tool-chain upper-bound evaluation | `experiment_auth_decomposed_verifier_mitigation.py` | True | `{"best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0, "mean_unauthorized_fnr": 0.1881, "method": "verifier_present_per_effect_sgd_auth", "rows": 21, "schema_condition": "full_tool_chain", "split_type": "leave_one_family_out...` |
| `auth_t57_effect_present_verifier_v2` | T57 trace-calibrated non-oracle effect-present verifier | `experiment_auth_t57_effect_present_verifier.py` | True | `{"best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0048, "mean_unauthorized_fnr": 0.2833, "method": "rule_monitored_effect_only_per_effect_sgd_auth", "rows": 21, "schema_condition": "full_tool_chain", "split_type": "leave_o...` |
| `auth_trace_effect_schema_conditioned_v1` | T58 trace candidate-effect data | `build_auth_trace_effect_schema_conditioned_data.py` | True | `{"candidate_effects": ["command_executed", "file_content_read", "file_written", "file_deleted", "network_egress", "content_fetched", "message_sent", "tool_error"], "caveat": "Trace rows are controlled observed/sandbox/static traces, not ...` |
| `auth_trace_effect_schema_conditioned_embeddings_v1` | T58 Qwen3-8B trace candidate-effect embeddings | `extract_embeddings_llm.py` | True | `{"effect_shape": [1104, 1], "embedding_shape": [1104, 4096]}` |
| `auth_t58_execution_verifier_v1` | T58 execution-level effect-present verifier | `experiment_auth_t58_execution_verifier.py` | True | `{"best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0, "mean_unauthorized_fnr": 0.0429, "method": "execution_trace_sgd_auth", "rows": 8, "schema_condition": "full_tool_chain", "split_type": "schema_to_trace_all", "target_fpr...` |
| `real_agent_tools_t59_inventory_and_traces` | T59 real-agent-tools inventory and local-adapter traces | `build_real_agent_tool_execution_traces_t59.py` | True | `{"caveat": "T59 executes local handler-equivalent adapters for file/terminal tools because direct Hermes handler import is blocked by missing upstream runtime modules; external services/API tools are inventoried but not invoked.", "execu...` |
| `auth_trace_effect_schema_conditioned_t59_v1` | T59 real-agent-tools candidate-effect data | `build_auth_trace_effect_schema_conditioned_data.py` | True | `{"candidate_effects": ["command_executed", "file_content_read", "file_written", "file_deleted", "network_egress", "content_fetched", "message_sent", "tool_error"], "caveat": "T59 rows come from real-agent-tools grounded local adapters, n...` |
| `auth_trace_effect_schema_conditioned_t59_embeddings` | T59 Qwen3-8B real-agent-tools candidate-effect embeddings | `extract_embeddings_llm.py` | True | `{"effect_shape": [384, 1], "embedding_shape": [384, 4096]}` |
| `auth_t59_real_agent_execution_verifier` | T59 real-agent-tools execution-level verifier stress test | `experiment_auth_t58_execution_verifier.py` | True | `{"best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0, "mean_unauthorized_fnr": 0.25, "method": "execution_trace_sgd_auth", "rows": 6, "schema_condition": "full_tool_chain", "split_type": "schema_to_trace_all", "target_fpr":...` |
| `deepseek_api_t60_traces` | T60 DeepSeek provider API traces | `build_deepseek_api_traces_t60.py` | True | `{"api_key_value_stored": false, "caveat": "T60 DeepSeek traces are direct provider API calls. They cover provider network/content/error effects, not browser/search/messaging side effects.", "error_count": 2, "success_count": 6, "tool_cou...` |
| `auth_trace_effect_schema_conditioned_t60_deepseek_v1` | T60 DeepSeek candidate-effect data | `build_auth_trace_effect_schema_conditioned_data.py` | True | `{"candidate_effects": ["command_executed", "file_content_read", "file_written", "file_deleted", "network_egress", "content_fetched", "message_sent", "tool_error"], "caveat": "T60 candidate-effect rows come from eight DeepSeek provider AP...` |
| `auth_trace_effect_schema_conditioned_t60_deepseek_embeddings` | T60 Qwen3-8B DeepSeek candidate-effect embeddings | `extract_embeddings_llm.py` | True | `{"effect_shape": [64, 1], "embedding_shape": [64, 4096]}` |
| `auth_t60_deepseek_execution_verifier` | T60 DeepSeek execution-level verifier pilot | `experiment_auth_t58_execution_verifier.py` | True | `{"best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0, "mean_unauthorized_fnr": 0.0, "method": "execution_trace_sgd_auth", "rows": 1, "schema_condition": "full_tool_chain", "split_type": "schema_to_trace_all", "target_fpr": ...` |
| `deepseek_api_t61_traces` | T61 expanded DeepSeek provider API traces | `build_deepseek_api_traces_t60.py` | True | `{"api_key_value_stored": false, "caveat": "T61 expands DeepSeek direct provider API traces to cell counts >=30 for provider network/content/error effects; it remains a single provider tool surface.", "error_count": 30, "success_count": 9...` |
| `auth_trace_effect_schema_conditioned_t61_deepseek_v1` | T61 expanded DeepSeek candidate-effect data | `build_auth_trace_effect_schema_conditioned_data.py` | True | `{"candidate_effects": ["command_executed", "file_content_read", "file_written", "file_deleted", "network_egress", "content_fetched", "message_sent", "tool_error"], "caveat": "T61 candidate-effect rows come from 120 DeepSeek provider API ...` |
| `auth_trace_effect_schema_conditioned_t61_deepseek_embeddings` | T61 Qwen3-8B expanded DeepSeek candidate-effect embeddings | `extract_embeddings_llm.py` | True | `{"effect_shape": [960, 1], "embedding_shape": [960, 4096]}` |
| `auth_t61_deepseek_execution_verifier` | T61 expanded DeepSeek execution-level verifier | `experiment_auth_t58_execution_verifier.py` | True | `{"best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0, "mean_unauthorized_fnr": 0.0, "method": "execution_trace_sgd_auth", "rows": 3, "schema_condition": "full_tool_chain", "split_type": "schema_to_trace_all", "target_fpr": ...` |
| `auth_t62_validation_threshold_t58_trace` | T62 validation-selected threshold on controlled trace dataset | `experiment_auth_t62_validation_threshold.py` | True | `{"caveat": "Thresholds are selected on validation trace groups and evaluated on held-out trace groups. Trace provenance is inherited from the source dataset; this is not deployment safety certification.", "target_fpr": 0.1, "test_rows": ...` |
| `auth_t62_validation_threshold_t59_real_agent_tools` | T62 validation-selected threshold on real-agent-tools local-adapter traces | `experiment_auth_t62_validation_threshold.py` | True | `{"caveat": "Thresholds are selected on validation trace groups and evaluated on held-out trace groups. Trace provenance is inherited from the source dataset; this is not deployment safety certification.", "target_fpr": 0.1, "test_rows": ...` |
| `auth_t62_validation_threshold_t61_deepseek` | T62 validation-selected threshold on expanded DeepSeek provider traces | `experiment_auth_t62_validation_threshold.py` | True | `{"caveat": "Thresholds are selected on validation trace groups and evaluated on held-out trace groups. Trace provenance is inherited from the source dataset; this is not deployment safety certification.", "target_fpr": 0.1, "test_rows": ...` |
| `broader_tools_t63_traces` | T63 broader web/search/browser/messaging local-adapter traces | `build_broader_agent_tool_traces_t63.py` | True | `{"caveat": "T63 uses controlled local adapters for real-agent-tools web/search/browser/messaging tool names; it does not invoke live external services.", "tool_counts": {"browser_click": 30, "browser_console": 30, "browser_navigate": 30,...` |
| `auth_trace_effect_schema_conditioned_t63_broader_v1` | T63 broader tool-family candidate-effect data | `build_auth_trace_effect_schema_conditioned_data.py` | True | `{"candidate_effects": ["command_executed", "file_content_read", "file_written", "file_deleted", "network_egress", "content_fetched", "message_sent", "tool_error"], "caveat": "T63 candidate-effect rows come from controlled broader local-a...` |
| `auth_trace_effect_schema_conditioned_t63_broader_embeddings` | T63 Qwen3-8B broader trace candidate-effect embeddings | `extract_embeddings_llm.py` | True | `{"effect_shape": [2400, 1], "embedding_shape": [2400, 4096]}` |
| `auth_t63_broader_execution_verifier` | T63 broader tool-family execution-level verifier evaluation | `experiment_auth_t58_execution_verifier.py` | True | `{"best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0, "mean_unauthorized_fnr": 0.0625, "method": "execution_trace_sgd_auth", "rows": 4, "schema_condition": "full_tool_chain", "split_type": "schema_to_trace_all", "target_fpr...` |
| `auth_t63_broader_validation_threshold` | T63 validation-selected threshold on broader tool-family traces | `experiment_auth_t62_validation_threshold.py` | True | `{"caveat": "Thresholds are selected on validation trace groups and evaluated on held-out trace groups. Trace provenance is inherited from the source dataset; this is not deployment safety certification.", "target_fpr": 0.1, "test_rows": ...` |
| `live_protocol_t64_traces` | T64 key-free live/protocol external-validity traces | `build_live_protocol_tool_traces_t64.py` | True | `{"caveat": "T64 uses key-free live outbound HTTPS plus local webhook protocol traces; it is not provider-backed search/SaaS messaging/deployed-runtime validation.", "evidence_level": {"live_http_external": "real outbound HTTPS requests t...` |
| `auth_trace_effect_schema_conditioned_t64_live_protocol_v1` | T64 live/protocol candidate-effect data | `build_auth_trace_effect_schema_conditioned_data.py` | True | `{"candidate_effects": ["command_executed", "file_content_read", "file_written", "file_deleted", "network_egress", "content_fetched", "message_sent", "tool_error"], "caveat": "T64 candidate-effect rows come from key-free live HTTP and loc...` |
| `auth_trace_effect_schema_conditioned_t64_embeddings` | T64 Qwen3-8B live/protocol candidate-effect embeddings | `extract_embeddings_llm.py` | True | `{"caveat": "T64 embeddings have been rerun with full-precision Qwen3-8B on cuda1.", "effect_shape": [2400, 1], "embedding_shape": [2400, 4096], "use_4bit": false}` |
| `auth_t64_live_protocol_execution_verifier` | T64 live/protocol execution-level verifier evaluation | `experiment_auth_t58_execution_verifier.py` | True | `{"best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0, "mean_unauthorized_fnr": 0.0, "method": "execution_trace_sgd_auth", "rows": 4, "schema_condition": "full_tool_chain", "split_type": "schema_to_trace_all", "target_fpr": ...` |
| `auth_t64_live_protocol_validation_threshold` | T64 validation-selected threshold on live/protocol traces | `experiment_auth_t62_validation_threshold.py` | True | `{"caveat": "Thresholds are selected on validation trace groups and evaluated on held-out trace groups. Trace provenance is inherited from the source dataset; this is not deployment safety certification.", "target_fpr": 0.1, "test_rows": ...` |
| `headless_browser_t65_traces` | T65 file-backed headless Chrome browser-runtime traces | `build_headless_browser_runtime_traces_t65.py` | True | `{"caveat": "T65 uses actual headless Chrome over file-backed pages; it is not HTTP browser networking, provider-backed search/SaaS messaging, or deployed-agent runtime validation.", "chrome_binary": "/usr/bin/google-chrome", "tools": ["b...` |
| `auth_trace_effect_schema_conditioned_t65_browser_v1` | T65 browser-runtime candidate-effect data | `build_auth_trace_effect_schema_conditioned_data.py` | True | `{"candidate_effects": ["command_executed", "file_content_read", "file_written", "file_deleted", "network_egress", "content_fetched", "message_sent", "tool_error"], "caveat": "T65 candidate-effect rows come from file-backed headless Chrom...` |
| `auth_trace_effect_schema_conditioned_t65_browser_embeddings` | T65 Qwen3-8B browser-runtime candidate-effect embeddings | `extract_embeddings_llm.py` | True | `{"caveat": "T65 browser-runtime embeddings use full-precision Qwen3-8B.", "effect_shape": [960, 1], "embedding_shape": [960, 4096], "use_4bit": false}` |
| `auth_t65_browser_execution_verifier` | T65 browser-runtime execution-level verifier evaluation | `experiment_auth_t58_execution_verifier.py` | True | `{"best_tradeoffs_fpr_0_1": [{"mean_absent_not_authorized_fpr": 0.0, "mean_unauthorized_fnr": 0.0, "method": "execution_trace_sgd_auth", "rows": 2, "schema_condition": "full_tool_chain", "split_type": "schema_to_trace_all", "target_fpr": ...` |
| `auth_t65_browser_validation_threshold` | T65 validation-selected threshold on browser-runtime traces | `experiment_auth_t62_validation_threshold.py` | True | `{"caveat": "Thresholds are selected on validation trace groups and evaluated on held-out trace groups. Trace provenance is inherited from the source dataset; this is not deployment safety certification.", "target_fpr": 0.1, "test_rows": ...` |
| `auth_action_level_metrics_t68` | T68 action-level Auth-SafeInv allow/deny metrics | `analysis/auth_action_level_metrics.py` | True | `{"caveat": "T68 aggregates candidate-effect predictions to action-level allow/deny metrics. It exposes false-denial tradeoffs hidden by row-level FNR/FPR, especially for provider API traces.", "datasets": {"qwen3-8b_auth_trace_effect_sch...` |
| `auth_trace_view_ablation_t69` | T69 verifier-independence trace-view ablation | `analysis/auth_trace_view_ablation_t69.py` | True | `{"aggregate": [{"datasets": 6, "max_test_unauthorized_fnr": 0.1765, "mean_authorized_action_false_denial_rate": 0.4544, "mean_present_fnr_vs_full_labels": 0.0, "mean_test_unauthorized_fnr": 0.0353, "mean_unauthorized_action_allow_rate": ...` |
| `auth_existing_defense_ablation_t70` | T70 existing-defense proxy ablation | `analysis/auth_existing_defense_ablation_t70.py` | True | `{"aggregate": [{"datasets": 6, "max_test_unauthorized_fnr": 0.1765, "mean_authorized_action_false_denial_rate": 0.4544, "mean_test_absent_not_authorized_fpr": 0.0, "mean_test_unauthorized_fnr": 0.0353, "mean_unauthorized_action_allow_rat...` |
| `auth_action_level_calibration_t73` | T73 action-level threshold calibration diagnostic | `analysis/auth_action_level_calibration_t73.py` | True | `{"caveat": "T73 calibrates action-level thresholds on validation trace groups. Several datasets satisfy false-denial constraints only via degenerate all-allow thresholds, so this is a diagnostic rather than a deployable calibration polic...` |

## Commands

### auth_counterfactuals

```bash
python build_authorization_counterfactuals.py
```

### auth_counterfactuals_v2

```bash
python build_authorization_counterfactuals_v2.py
```

### auth_embeddings

```bash
python extract_embeddings_llm.py Qwen/Qwen3-8B authorization_counterfactuals_v1.jsonl --batch-size 8
```

### auth_embeddings_v2

```bash
python extract_embeddings_llm.py Qwen/Qwen3-8B authorization_counterfactuals_v2.jsonl --batch-size 8
```

### auth_traces_v2

```bash
python build_auth_observed_execution_traces.py
```

### auth_safeinv_eval

```bash
python experiment_auth_safeinv.py qwen3-8b_authorization_counterfactuals_v1
```

### auth_safeinv_eval_v2

```bash
python experiment_auth_safeinv.py qwen3-8b_authorization_counterfactuals_v2
```

### surface_graph_alignment

```bash
python analyze_surface_graph_alignment.py authorization_counterfactuals_v1
```

### surface_graph_alignment_v2

```bash
python analyze_surface_graph_alignment.py authorization_counterfactuals_v2
```

### piia_hook_confirmatory

```bash
python interchange_intervention_hook_controls.py --data-name qwen3-8b_scenarios_mainconf_v2 --max-effects 6 --max-eval-tools 2 --pairs-per-mode 3 --out-json analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.json --out-md analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.md
```

### auth_baseline_confirmatory

```bash
python experiment_auth_baseline_confirmatory.py qwen3-8b_authorization_counterfactuals_v1
```

### auth_baseline_confirmatory_v2

```bash
python experiment_auth_baseline_confirmatory.py qwen3-8b_authorization_counterfactuals_v2
```

### auth_mitigation_vs_baseline

```bash
python experiment_auth_mitigation_comparison.py qwen3-8b_authorization_counterfactuals_v1
```

### auth_mitigation_vs_baseline_v2

```bash
python experiment_auth_mitigation_comparison.py qwen3-8b_authorization_counterfactuals_v2
```

### auth_schema_conditioned_data_v2

```bash
python build_auth_effect_schema_conditioned_data.py
```

### auth_schema_conditioned_embeddings_v2

```bash
python extract_embeddings_llm.py Qwen/Qwen3-8B auth_effect_schema_conditioned_v2.jsonl --batch-size 8
```

### auth_schema_conditioned_mitigation_v2

```bash
python experiment_auth_schema_conditioned_mitigation.py qwen3-8b_auth_effect_schema_conditioned_v2
```

### auth_decomposed_verifier_mitigation_v2

```bash
python experiment_auth_decomposed_verifier_mitigation.py qwen3-8b_auth_effect_schema_conditioned_v2
```

### auth_verifier_present_upper_bound_v2

```bash
python experiment_auth_decomposed_verifier_mitigation.py qwen3-8b_auth_effect_schema_conditioned_v2 --conditions full_tool_chain --methods verifier_present_sgd_auth verifier_present_per_effect_sgd_auth --output-suffix _verifier_present_full
```

### auth_t57_effect_present_verifier_v2

```bash
python experiment_auth_t57_effect_present_verifier.py qwen3-8b_auth_effect_schema_conditioned_v2 --conditions full_tool_chain
```

### auth_trace_effect_schema_conditioned_v1

```bash
python build_auth_trace_effect_schema_conditioned_data.py --conditions full_tool_chain
```

### auth_trace_effect_schema_conditioned_embeddings_v1

```bash
CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_v1.jsonl --batch-size 16
```

### auth_t58_execution_verifier_v1

```bash
python experiment_auth_t58_execution_verifier.py --conditions full_tool_chain
```

### real_agent_tools_t59_inventory_and_traces

```bash
python build_real_agent_tool_execution_traces_t59.py
```

### auth_trace_effect_schema_conditioned_t59_v1

```bash
python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_real_agent_tools_t59_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t59_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.md --conditions full_tool_chain
```

### auth_trace_effect_schema_conditioned_t59_embeddings

```bash
CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t59_v1.jsonl --batch-size 16
```

### auth_t59_real_agent_execution_verifier

```bash
python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1 --conditions full_tool_chain
```

### deepseek_api_t60_traces

```bash
DEEPSEEK_API_KEY=<redacted> python build_deepseek_api_traces_t60.py --repetitions 2
```

### auth_trace_effect_schema_conditioned_t60_deepseek_v1

```bash
python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_deepseek_api_t60_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t60_deepseek_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t60_deepseek_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t60_deepseek_v1_manifest.md --conditions full_tool_chain
```

### auth_trace_effect_schema_conditioned_t60_deepseek_embeddings

```bash
CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t60_deepseek_v1.jsonl --batch-size 16
```

### auth_t60_deepseek_execution_verifier

```bash
python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1 --conditions full_tool_chain
```

### deepseek_api_t61_traces

```bash
DEEPSEEK_API_KEY=<redacted> python build_deepseek_api_traces_t60.py --repetitions 30 --output data/agent_tool_traces_deepseek_api_t61_v1.jsonl --manifest analysis/agent_tool_traces_deepseek_api_t61_v1_manifest.json --manifest-md analysis/agent_tool_traces_deepseek_api_t61_v1_manifest.md
```

### auth_trace_effect_schema_conditioned_t61_deepseek_v1

```bash
python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_deepseek_api_t61_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t61_deepseek_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t61_deepseek_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t61_deepseek_v1_manifest.md --conditions full_tool_chain
```

### auth_trace_effect_schema_conditioned_t61_deepseek_embeddings

```bash
CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t61_deepseek_v1.jsonl --batch-size 16
```

### auth_t61_deepseek_execution_verifier

```bash
python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1 --conditions full_tool_chain
```

### auth_t62_validation_threshold_t58_trace

```bash
python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_v1
```

### auth_t62_validation_threshold_t59_real_agent_tools

```bash
python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1
```

### auth_t62_validation_threshold_t61_deepseek

```bash
python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1
```

### broader_tools_t63_traces

```bash
python build_broader_agent_tool_traces_t63.py
```

### auth_trace_effect_schema_conditioned_t63_broader_v1

```bash
python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_broader_tools_t63_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t63_broader_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.md --conditions full_tool_chain
```

### auth_trace_effect_schema_conditioned_t63_broader_embeddings

```bash
CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t63_broader_v1.jsonl --batch-size 16
```

### auth_t63_broader_execution_verifier

```bash
python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1 --conditions full_tool_chain
```

### auth_t63_broader_validation_threshold

```bash
python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1
```

### live_protocol_t64_traces

```bash
python build_live_protocol_tool_traces_t64.py
```

### auth_trace_effect_schema_conditioned_t64_live_protocol_v1

```bash
python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_live_protocol_t64_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t64_live_protocol_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.md --conditions full_tool_chain
```

### auth_trace_effect_schema_conditioned_t64_embeddings

```bash
CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t64_live_protocol_v1.jsonl --batch-size 4
```

### auth_t64_live_protocol_execution_verifier

```bash
python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1 --conditions full_tool_chain
```

### auth_t64_live_protocol_validation_threshold

```bash
python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1
```

### headless_browser_t65_traces

```bash
python build_headless_browser_runtime_traces_t65.py --repetitions 30
```

### auth_trace_effect_schema_conditioned_t65_browser_v1

```bash
python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_headless_browser_t65_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t65_browser_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.md --conditions full_tool_chain
```

### auth_trace_effect_schema_conditioned_t65_browser_embeddings

```bash
CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t65_browser_v1.jsonl --batch-size 4
```

### auth_t65_browser_execution_verifier

```bash
python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1 --conditions full_tool_chain
```

### auth_t65_browser_validation_threshold

```bash
python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1
```

### auth_action_level_metrics_t68

```bash
python analysis/auth_action_level_metrics.py
```

### auth_trace_view_ablation_t69

```bash
python analysis/auth_trace_view_ablation_t69.py
```

### auth_existing_defense_ablation_t70

```bash
python analysis/auth_existing_defense_ablation_t70.py
```

### auth_action_level_calibration_t73

```bash
python analysis/auth_action_level_calibration_t73.py
```

## Caveats

- This appendix maps existing artifacts to commands; it does not rerun GPU-heavy experiments.
- Observed traces are controlled local sandbox executions, not live deployed-agent logs.
- pIIA results are probe-mediated activation diagnostics, not SCM-style IIA proofs.
- T51 compares mitigation against T47 baselines under identical held-out cells; strict train-only projection remains coverage-limited.
- T54 shows v2 improves strict-train-only coverage but does not make contrastive projection beat the best non-degenerate baseline.
- T55 effect-schema conditioned monitors are pair-free but currently underperform the best T54 non-degenerate baselines.
- T57 replaces the oracle present label with deterministic static verifier rules; it is verifier-assisted framework evidence, not live deployment validation.
- T58 replaces static present inference with controlled execution-trace verifier outputs, but the traces are still controlled observed/sandbox/static artifacts rather than live deployed-agent logs.
- T59 grounds additional traces in real-agent-tools Hermes tool registrations and local file/terminal semantics, but direct handler imports require missing upstream runtime modules and external API tools were not invoked.
- T60 DeepSeek traces are direct provider API calls, but they are a tiny pilot over one provider tool surface and do not cover browser/search/messaging tools.
- T61 expands the DeepSeek provider API pilot to 120 calls and useful provider-effect counts, but it still covers only one provider API surface.
- T62 selects thresholds on validation trace groups and evaluates them on held-out trace groups. It fixes the ex-post-threshold caveat for the tested trace datasets, but it is still not a deployment guarantee.
- T63 broadens controlled local-adapter traces to web/search/browser/messaging tool families, but it still does not invoke live external services or deployed-agent logs.
- T64 has been rerun with full-precision Qwen3-8B embeddings. It covers key-free live outbound HTTPS plus local webhook protocol boundaries, not provider-backed search/SaaS messaging/deployed runtime.
- T65 uses actual headless Chrome over file-backed pages. It closes part of the browser-runtime gap, but not HTTP browser networking, provider-backed search/SaaS messaging, or deployed-agent runtime validation.
- T68 aggregates candidate-effect rows to action-level allow/deny metrics. It shows that row-level unauthorized-effect FNR/FPR can hide policy tradeoffs, including high authorized-action false-denial on the T61 provider API and T65 browser-runtime splits.
- T69 indicates label-hidden raw trace evidence degrades relative to the full-label verifier after adding T65; the framework should be described as requiring structured execution evidence.
- T70 proxy baselines distinguish the framework from pre-action/provenance-only monitors, but the strong raw_status_boundary result means the paper should not claim that learned AuthMonitor dominates all handcrafted trace-policy defenses.
- T73 action-level calibration shows that a simple false-denial-constrained threshold can collapse to all-allow on several trace families; this is not a deployable calibration policy.
