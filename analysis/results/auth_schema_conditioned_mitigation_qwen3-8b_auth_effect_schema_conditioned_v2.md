# Auth Effect-Schema Conditioned Mitigation

- Data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Samples: 35136
- Conditions: `['full_tool_chain', 'auth_only_control', 'tool_only_control']`
- Methods: `['schema_sgd_logistic', 'schema_per_effect_sgd']`
- Target FPR: 0.1

## Fixed Threshold Aggregate

| Split | Condition | Method | Rows | Cells | Mean FNR | Std FNR | Max FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `auth_only_control` | `schema_per_effect_sgd` | 20 | 20 | 0.5008 | 0.4163 | 1.0 | 0.0759 |
| `leave_one_family_out` | `auth_only_control` | `schema_sgd_logistic` | 21 | 21 | 0.6889 | 0.3915 | 1.0 | 0.0662 |
| `leave_one_family_out` | `full_tool_chain` | `schema_per_effect_sgd` | 20 | 20 | 0.6017 | 0.4634 | 1.0 | 0.0276 |
| `leave_one_family_out` | `full_tool_chain` | `schema_sgd_logistic` | 21 | 21 | 0.9048 | 0.1963 | 1.0 | 0.0102 |
| `leave_one_family_out` | `tool_only_control` | `schema_per_effect_sgd` | 20 | 20 | 0.7 | 0.4301 | 1.0 | 0.1061 |
| `leave_one_family_out` | `tool_only_control` | `schema_sgd_logistic` | 21 | 21 | 1.0 | 0.0 | 1.0 | 0.0 |
| `leave_one_tool_out` | `auth_only_control` | `schema_per_effect_sgd` | 21 | 21 | 0.4696 | 0.47 | 1.0 | 0.066 |
| `leave_one_tool_out` | `auth_only_control` | `schema_sgd_logistic` | 22 | 22 | 0.5909 | 0.4917 | 1.0 | 0.0444 |
| `leave_one_tool_out` | `full_tool_chain` | `schema_per_effect_sgd` | 21 | 21 | 0.4516 | 0.4856 | 1.0 | 0.0154 |
| `leave_one_tool_out` | `full_tool_chain` | `schema_sgd_logistic` | 22 | 22 | 0.7174 | 0.4406 | 1.0 | 0.0413 |
| `leave_one_tool_out` | `tool_only_control` | `schema_per_effect_sgd` | 21 | 21 | 0.5682 | 0.4447 | 1.0 | 0.0733 |
| `leave_one_tool_out` | `tool_only_control` | `schema_sgd_logistic` | 22 | 22 | 0.6409 | 0.431 | 1.0 | 0.05 |

## Best Ex-Post Tradeoffs

| Split | Condition | Method | Threshold | Cells | Mean FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|
| `leave_one_family_out` | `auth_only_control` | `schema_per_effect_sgd` | 0.5 | 20 | 0.5008 | 0.0759 |
| `leave_one_family_out` | `auth_only_control` | `schema_sgd_logistic` | 0.05 | 21 | 0.6889 | 0.0662 |
| `leave_one_family_out` | `full_tool_chain` | `schema_per_effect_sgd` | 0.05 | 20 | 0.6 | 0.0279 |
| `leave_one_family_out` | `full_tool_chain` | `schema_sgd_logistic` | 1.0 | 21 | 0.9048 | 0.0068 |
| `leave_one_family_out` | `tool_only_control` | `schema_per_effect_sgd` | 1.0 | 20 | 0.7 | 0.0969 |
| `leave_one_family_out` | `tool_only_control` | `schema_sgd_logistic` | 0.05 | 21 | 1.0 | 0.0 |
| `leave_one_tool_out` | `auth_only_control` | `schema_per_effect_sgd` | 0.05 | 21 | 0.4696 | 0.066 |
| `leave_one_tool_out` | `auth_only_control` | `schema_sgd_logistic` | 1.0 | 22 | 0.5909 | 0.0387 |
| `leave_one_tool_out` | `full_tool_chain` | `schema_per_effect_sgd` | 0.05 | 21 | 0.4516 | 0.0154 |
| `leave_one_tool_out` | `full_tool_chain` | `schema_sgd_logistic` | 0.05 | 22 | 0.7174 | 0.0413 |
| `leave_one_tool_out` | `tool_only_control` | `schema_per_effect_sgd` | 0.05 | 21 | 0.5682 | 0.0733 |
| `leave_one_tool_out` | `tool_only_control` | `schema_sgd_logistic` | 1.0 | 22 | 0.6409 | 0.0451 |

## Same-Cell Comparison vs T54 Baselines

- Baseline source: `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.json`
- Interpretation: Setting-shifted comparison: schema monitor trains on candidate unauthorized labels; baselines train on realized effects.

| Split | Condition | Method | Schema cells | Baseline cells | Schema FNR | Schema FPR | Best baseline | Base FNR | Base FPR | Delta FNR |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| `leave_one_family_out` | `auth_only_control` | `schema_per_effect_sgd` | 20 | 20 | 0.5008 | 0.0759 | `irm_linear` | 0.1655 | 0.0911 | -0.3353 |
| `leave_one_family_out` | `auth_only_control` | `schema_sgd_logistic` | 21 | 21 | 0.6889 | 0.0662 | `irm_linear` | 0.1771 | 0.0867 | -0.5118 |
| `leave_one_family_out` | `full_tool_chain` | `schema_per_effect_sgd` | 20 | 20 | 0.6 | 0.0279 | `irm_linear` | 0.1655 | 0.0911 | -0.4345 |
| `leave_one_family_out` | `full_tool_chain` | `schema_sgd_logistic` | 21 | 21 | 0.9048 | 0.0068 | `irm_linear` | 0.1771 | 0.0867 | -0.7277 |
| `leave_one_family_out` | `tool_only_control` | `schema_per_effect_sgd` | 20 | 20 | 0.7 | 0.0969 | `irm_linear` | 0.1655 | 0.0911 | -0.5345 |
| `leave_one_family_out` | `tool_only_control` | `schema_sgd_logistic` | 21 | 21 | 1.0 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | -0.8229 |
| `leave_one_tool_out` | `auth_only_control` | `schema_per_effect_sgd` | 21 | 21 | 0.4696 | 0.066 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.2861 |
| `leave_one_tool_out` | `auth_only_control` | `schema_sgd_logistic` | 22 | 21 | 0.5909 | 0.0387 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.4074 |
| `leave_one_tool_out` | `full_tool_chain` | `schema_per_effect_sgd` | 21 | 21 | 0.4516 | 0.0154 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.2681 |
| `leave_one_tool_out` | `full_tool_chain` | `schema_sgd_logistic` | 22 | 21 | 0.7174 | 0.0413 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.5339 |
| `leave_one_tool_out` | `tool_only_control` | `schema_per_effect_sgd` | 21 | 21 | 0.5682 | 0.0733 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.3847 |
| `leave_one_tool_out` | `tool_only_control` | `schema_sgd_logistic` | 22 | 21 | 0.6409 | 0.0451 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.4574 |

## Skips

- Skipped training rows: 6

## Caveats

- This is a pair-free schema-conditioned monitor; it does not train on cross-tool positive pairs.
- It trains directly on unauthorized-effect labels after candidate-effect query expansion, so comparisons to T54 realized-effect probes are setting-shifted.
- Threshold-curve tradeoffs are ex-post diagnostics, not deployment-calibrated thresholds.
- The auth_only_control and tool_only_control conditions test whether gains come from both authorization context and tool causal information.
