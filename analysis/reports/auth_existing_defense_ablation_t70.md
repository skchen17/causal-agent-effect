# T70 Existing-Defense Proxy Ablation

- Train data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Trace condition: `full_tool_chain`
- Target FPR: 0.1

## Method Boundary

- `pre_action_rule_only_sgd_auth`: static tool-call semantics before execution plus schema-trained authorization score.
- `provenance_only_boundary`: coarse tool/source provenance rules checked directly against the authorization envelope.
- `raw_status_boundary`: minimal raw result/status/state attribution checked directly against the authorization envelope.
- `effectverif_label_hidden_sgd_auth`: label-hidden raw effect verification plus schema-trained authorization score.
- `effectverif_full_labels_sgd_auth`: full-label execution verifier upper bound.

## Aggregate

| Method | Mean FNR | Max FNR | Mean FPR | Mean U-Allow | Mean FDeny |
|---|---:|---:|---:|---:|---:|
| `effectverif_full_labels_sgd_auth` | 0.0353 | 0.1765 | 0.0 | 0.0417 | 0.4544 |
| `effectverif_label_hidden_sgd_auth` | 0.1162 | 0.3387 | 0.048 | 0.0459 | 0.7428 |
| `pre_action_rule_only_sgd_auth` | 0.57 | 1.0 | 0.0186 | 0.5014 | 0.1627 |
| `provenance_only_boundary` | 0.2873 | 0.4474 | 0.0733 | 0.0486 | 0.3762 |
| `raw_status_boundary` | 0.1113 | 0.3387 | 0.0101 | 0.0171 | 0.0265 |

## Per Dataset

| Trace data | Method | Threshold | Policy | Test FNR | Test FPR | U-Allow | FDeny |
|---|---|---:|---|---:|---:|---:|---:|
| `qwen3-8b_auth_trace_effect_schema_conditioned_v1` | `effectverif_full_labels_sgd_auth` | 0.05 | `t62_validation_selected` | 0.0 | 0.0 | 0.0 | 0.1591 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_v1` | `effectverif_label_hidden_sgd_auth` | 0.05 | `t62_validation_selected` | 0.0455 | 0.129 | 0.0256 | 0.8182 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_v1` | `pre_action_rule_only_sgd_auth` | 0.05 | `t62_validation_selected` | 0.0 | 0.052 | 0.0 | 0.4091 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_v1` | `provenance_only_boundary` | 0.5 | `fixed_direct_boundary` | 0.2045 | 0.0878 | 0.0 | 0.4318 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_v1` | `raw_status_boundary` | 0.5 | `fixed_direct_boundary` | 0.2273 | 0.0287 | 0.1026 | 0.1591 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1` | `effectverif_full_labels_sgd_auth` | 0.05 | `t62_validation_selected` | 0.1765 | 0.0 | 0.2 | 0.3571 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1` | `effectverif_label_hidden_sgd_auth` | 0.05 | `t62_validation_selected` | 0.1765 | 0.0506 | 0.2 | 0.4286 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1` | `pre_action_rule_only_sgd_auth` | 0.05 | `t62_validation_selected` | 0.1765 | 0.0 | 0.2 | 0.3571 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1` | `provenance_only_boundary` | 0.5 | `fixed_direct_boundary` | 0.2941 | 0.0169 | 0.0667 | 0.0714 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1` | `raw_status_boundary` | 0.5 | `fixed_direct_boundary` | 0.0 | 0.0 | 0.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1` | `effectverif_full_labels_sgd_auth` | 0.05 | `t62_validation_selected` | 0.0 | 0.0 | 0.0 | 1.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1` | `effectverif_label_hidden_sgd_auth` | 0.05 | `t62_validation_selected` | 0.0 | 0.0 | 0.0 | 1.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1` | `pre_action_rule_only_sgd_auth` | 0.05 | `t62_validation_selected` | 1.0 | 0.0 | 1.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1` | `provenance_only_boundary` | 0.5 | `fixed_direct_boundary` | 0.2564 | 0.0463 | 0.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1` | `raw_status_boundary` | 0.5 | `fixed_direct_boundary` | 0.0 | 0.0 | 0.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1` | `effectverif_full_labels_sgd_auth` | 0.05 | `t62_validation_selected` | 0.0351 | 0.0 | 0.05 | 0.21 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1` | `effectverif_label_hidden_sgd_auth` | 0.05 | `t62_validation_selected` | 0.0351 | 0.0 | 0.05 | 0.21 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1` | `pre_action_rule_only_sgd_auth` | 0.05 | `t62_validation_selected` | 0.614 | 0.0132 | 0.4875 | 0.21 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1` | `provenance_only_boundary` | 0.5 | `fixed_direct_boundary` | 0.4474 | 0.045 | 0.225 | 0.27 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1` | `raw_status_boundary` | 0.5 | `fixed_direct_boundary` | 0.0 | 0.0 | 0.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1` | `effectverif_full_labels_sgd_auth` | 0.05 | `t62_validation_selected` | 0.0 | 0.0 | 0.0 | 1.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1` | `effectverif_label_hidden_sgd_auth` | 0.05 | `t62_validation_selected` | 0.3387 | 0.0 | 0.0 | 1.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1` | `pre_action_rule_only_sgd_auth` | 0.05 | `t62_validation_selected` | 1.0 | 0.0 | 1.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1` | `provenance_only_boundary` | 0.5 | `fixed_direct_boundary` | 0.3387 | 0.1363 | 0.0 | 0.4839 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1` | `raw_status_boundary` | 0.5 | `fixed_direct_boundary` | 0.3387 | 0.0 | 0.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1` | `effectverif_full_labels_sgd_auth` | 0.05 | `t62_validation_selected` | 0.0 | 0.0 | 0.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1` | `effectverif_label_hidden_sgd_auth` | 0.05 | `t62_validation_selected` | 0.1015 | 0.1085 | 0.0 | 1.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1` | `pre_action_rule_only_sgd_auth` | 0.05 | `t62_validation_selected` | 0.6294 | 0.0462 | 0.321 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1` | `provenance_only_boundary` | 0.5 | `fixed_direct_boundary` | 0.1827 | 0.1077 | 0.0 | 1.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1` | `raw_status_boundary` | 0.5 | `fixed_direct_boundary` | 0.1015 | 0.0316 | 0.0 | 0.0 |

## Caveats

- These are proxy baselines for reviewer-facing boundary analysis, not faithful reimplementations of any particular external defense system.
- Boundary methods use the explicit authorized-effect envelope available in this benchmark; deployed systems would need a policy extraction layer.
- EffectVerif full-label is an upper-bound verifier; label-hidden EffectVerif is the more realistic non-label-copying comparison.
- All learned thresholds use validation trace groups and held-out trace groups, following T62.
