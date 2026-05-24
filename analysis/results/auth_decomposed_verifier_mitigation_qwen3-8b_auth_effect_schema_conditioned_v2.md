# Auth Decomposed Verifier Mitigation

- Data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Samples: 35136
- Conditions: `['full_tool_chain', 'auth_only_control', 'tool_only_control']`
- Methods: `['decomposed_sgd_product', 'decomposed_sgd_mean', 'decomposed_per_effect_sgd_product', 'decomposed_per_effect_sgd_mean', 'verifier_present_sgd_auth', 'verifier_present_per_effect_sgd_auth']`
- Target FPR: 0.1

## Fixed Threshold Aggregate

| Split | Condition | Method | Rows | Cells | Mean FNR | Std FNR | Max FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `auth_only_control` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.0238 | 0.1065 | 0.5 | 0.9947 |
| `leave_one_family_out` | `auth_only_control` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.5389 | 0.4013 | 1.0 | 0.0444 |
| `leave_one_family_out` | `auth_only_control` | `decomposed_sgd_mean` | 21 | 21 | 0.0 | 0.0 | 0.0 | 1.0 |
| `leave_one_family_out` | `auth_only_control` | `decomposed_sgd_product` | 21 | 21 | 0.719 | 0.417 | 1.0 | 0.0493 |
| `leave_one_family_out` | `auth_only_control` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.1064 | 0.1954 | 0.5 | 0.0 |
| `leave_one_family_out` | `auth_only_control` | `verifier_present_sgd_auth` | 21 | 21 | 0.0 | 0.0 | 0.0 | 0.0 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.0308 | 0.1071 | 0.5 | 0.998 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.5709 | 0.3815 | 1.0 | 0.004 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_sgd_mean` | 21 | 21 | 0.071 | 0.1957 | 0.7857 | 0.9563 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_sgd_product` | 21 | 21 | 0.8294 | 0.3272 | 1.0 | 0.0005 |
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.1952 | 0.2935 | 1.0 | 0.0 |
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 21 | 21 | 0.0745 | 0.2238 | 1.0 | 0.0 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.0767 | 0.2329 | 1.0 | 0.9742 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.7857 | 0.3956 | 1.0 | 0.0159 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_sgd_mean` | 21 | 21 | 0.045 | 0.1389 | 0.5 | 0.998 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_sgd_product` | 21 | 21 | 0.881 | 0.3049 | 1.0 | 0.0 |
| `leave_one_family_out` | `tool_only_control` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.6349 | 0.4443 | 1.0 | 0.0 |
| `leave_one_family_out` | `tool_only_control` | `verifier_present_sgd_auth` | 21 | 21 | 0.2751 | 0.4373 | 1.0 | 0.0 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.0952 | 0.2935 | 1.0 | 1.0 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.4269 | 0.47 | 1.0 | 0.006 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_sgd_mean` | 22 | 22 | 0.0 | 0.0 | 0.0 | 1.0 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_sgd_product` | 22 | 22 | 0.7129 | 0.4331 | 1.0 | 0.0644 |
| `leave_one_tool_out` | `auth_only_control` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.1118 | 0.2975 | 1.0 | 0.0 |
| `leave_one_tool_out` | `auth_only_control` | `verifier_present_sgd_auth` | 22 | 22 | 0.0 | 0.0 | 0.0 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.0 | 0.0 | 0.0 | 0.9951 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.3547 | 0.4396 | 1.0 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_sgd_mean` | 22 | 22 | 0.0116 | 0.0533 | 0.2558 | 0.9996 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_sgd_product` | 22 | 22 | 0.6788 | 0.4639 | 1.0 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.0642 | 0.222 | 1.0 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 22 | 22 | 0.0042 | 0.0194 | 0.093 | 0.0 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.0476 | 0.213 | 1.0 | 0.8762 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.696 | 0.4207 | 1.0 | 0.0469 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_sgd_mean` | 22 | 22 | 0.0 | 0.0 | 0.0 | 1.0 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_sgd_product` | 22 | 22 | 0.7947 | 0.3896 | 1.0 | 0.0 |
| `leave_one_tool_out` | `tool_only_control` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.5222 | 0.4751 | 1.0 | 0.0 |
| `leave_one_tool_out` | `tool_only_control` | `verifier_present_sgd_auth` | 22 | 22 | 0.1041 | 0.2462 | 1.0 | 0.0 |

## Best Ex-Post Tradeoffs

| Split | Condition | Method | Threshold | Cells | Mean FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|
| `leave_one_family_out` | `auth_only_control` | `decomposed_per_effect_sgd_mean` | 0.65 | 21 | 0.5389 | 0.0444 |
| `leave_one_family_out` | `auth_only_control` | `decomposed_per_effect_sgd_product` | 0.05 | 21 | 0.5373 | 0.0446 |
| `leave_one_family_out` | `auth_only_control` | `decomposed_sgd_mean` | 0.9 | 21 | 0.719 | 0.0489 |
| `leave_one_family_out` | `auth_only_control` | `decomposed_sgd_product` | 0.95 | 21 | 0.719 | 0.0487 |
| `leave_one_family_out` | `auth_only_control` | `verifier_present_per_effect_sgd_auth` | 0.05 | 21 | 0.1032 | 0.0 |
| `leave_one_family_out` | `auth_only_control` | `verifier_present_sgd_auth` | 0.05 | 21 | 0.0 | 0.0 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_per_effect_sgd_mean` | 0.55 | 21 | 0.5638 | 0.004 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_per_effect_sgd_product` | 0.05 | 21 | 0.5638 | 0.004 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_sgd_mean` | 0.55 | 21 | 0.8278 | 0.0007 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_sgd_product` | 0.05 | 21 | 0.8262 | 0.0007 |
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 0.05 | 21 | 0.1881 | 0.0 |
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 0.05 | 21 | 0.0745 | 0.0 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_per_effect_sgd_mean` | 1.0 | 21 | 0.7857 | 0.0079 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_per_effect_sgd_product` | 1.0 | 21 | 0.7857 | 0.0079 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_sgd_mean` | 0.55 | 21 | 0.881 | 0.0 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_sgd_product` | 0.05 | 21 | 0.881 | 0.0 |
| `leave_one_family_out` | `tool_only_control` | `verifier_present_per_effect_sgd_auth` | 0.05 | 21 | 0.6349 | 0.0 |
| `leave_one_family_out` | `tool_only_control` | `verifier_present_sgd_auth` | 0.05 | 21 | 0.2751 | 0.0 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_per_effect_sgd_mean` | 0.55 | 21 | 0.4269 | 0.006 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_per_effect_sgd_product` | 0.05 | 21 | 0.4269 | 0.006 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_sgd_mean` | 0.55 | 22 | 0.7098 | 0.0652 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_sgd_product` | 0.05 | 22 | 0.7098 | 0.0652 |
| `leave_one_tool_out` | `auth_only_control` | `verifier_present_per_effect_sgd_auth` | 0.05 | 21 | 0.1118 | 0.0 |
| `leave_one_tool_out` | `auth_only_control` | `verifier_present_sgd_auth` | 0.05 | 22 | 0.0 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_per_effect_sgd_mean` | 0.55 | 21 | 0.3547 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_per_effect_sgd_product` | 0.05 | 21 | 0.3547 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_sgd_mean` | 0.55 | 22 | 0.6788 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_sgd_product` | 0.05 | 22 | 0.6788 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 0.05 | 21 | 0.0642 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 0.05 | 22 | 0.0042 | 0.0 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_per_effect_sgd_mean` | 0.55 | 21 | 0.696 | 0.0469 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_per_effect_sgd_product` | 0.05 | 21 | 0.696 | 0.0469 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_sgd_mean` | 0.55 | 22 | 0.7947 | 0.0 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_sgd_product` | 0.05 | 22 | 0.7947 | 0.0 |
| `leave_one_tool_out` | `tool_only_control` | `verifier_present_per_effect_sgd_auth` | 0.05 | 21 | 0.5222 | 0.0 |
| `leave_one_tool_out` | `tool_only_control` | `verifier_present_sgd_auth` | 0.05 | 22 | 0.1041 | 0.0 |

## Same-Cell Comparison vs T54 Baselines

- Baseline source: `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.json`
- Interpretation: Setting-shifted comparison: decomposed verifier uses candidate present/authorized supervision over schema-conditioned inputs; T54 baselines train realized-effect probes.

| Split | Condition | Method | Cells | Baseline cells | Dec FNR | Dec FPR | Best baseline | Base FNR | Base FPR | Delta FNR |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| `leave_one_family_out` | `auth_only_control` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.5389 | 0.0444 | `irm_linear` | 0.1771 | 0.0867 | -0.3618 |
| `leave_one_family_out` | `auth_only_control` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.5373 | 0.0446 | `irm_linear` | 0.1771 | 0.0867 | -0.3602 |
| `leave_one_family_out` | `auth_only_control` | `decomposed_sgd_mean` | 21 | 21 | 0.719 | 0.0489 | `irm_linear` | 0.1771 | 0.0867 | -0.5419 |
| `leave_one_family_out` | `auth_only_control` | `decomposed_sgd_product` | 21 | 21 | 0.719 | 0.0487 | `irm_linear` | 0.1771 | 0.0867 | -0.5419 |
| `leave_one_family_out` | `auth_only_control` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.1032 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | 0.0739 |
| `leave_one_family_out` | `auth_only_control` | `verifier_present_sgd_auth` | 21 | 21 | 0.0 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | 0.1771 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.5638 | 0.004 | `irm_linear` | 0.1771 | 0.0867 | -0.3867 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.5638 | 0.004 | `irm_linear` | 0.1771 | 0.0867 | -0.3867 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_sgd_mean` | 21 | 21 | 0.8278 | 0.0007 | `irm_linear` | 0.1771 | 0.0867 | -0.6507 |
| `leave_one_family_out` | `full_tool_chain` | `decomposed_sgd_product` | 21 | 21 | 0.8262 | 0.0007 | `irm_linear` | 0.1771 | 0.0867 | -0.6491 |
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.1881 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | -0.011 |
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 21 | 21 | 0.0745 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | 0.1026 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.7857 | 0.0079 | `irm_linear` | 0.1771 | 0.0867 | -0.6086 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.7857 | 0.0079 | `irm_linear` | 0.1771 | 0.0867 | -0.6086 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_sgd_mean` | 21 | 21 | 0.881 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | -0.7039 |
| `leave_one_family_out` | `tool_only_control` | `decomposed_sgd_product` | 21 | 21 | 0.881 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | -0.7039 |
| `leave_one_family_out` | `tool_only_control` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.6349 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | -0.4578 |
| `leave_one_family_out` | `tool_only_control` | `verifier_present_sgd_auth` | 21 | 21 | 0.2751 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | -0.098 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.4269 | 0.006 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.2434 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.4269 | 0.006 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.2434 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_sgd_mean` | 22 | 21 | 0.7098 | 0.0652 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.5263 |
| `leave_one_tool_out` | `auth_only_control` | `decomposed_sgd_product` | 22 | 21 | 0.7098 | 0.0652 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.5263 |
| `leave_one_tool_out` | `auth_only_control` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.1118 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.0717 |
| `leave_one_tool_out` | `auth_only_control` | `verifier_present_sgd_auth` | 22 | 21 | 0.0 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.1835 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.3547 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.1712 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.3547 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.1712 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_sgd_mean` | 22 | 21 | 0.6788 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.4953 |
| `leave_one_tool_out` | `full_tool_chain` | `decomposed_sgd_product` | 22 | 21 | 0.6788 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.4953 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.0642 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.1193 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 22 | 21 | 0.0042 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.1793 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_per_effect_sgd_mean` | 21 | 21 | 0.696 | 0.0469 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.5125 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_per_effect_sgd_product` | 21 | 21 | 0.696 | 0.0469 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.5125 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_sgd_mean` | 22 | 21 | 0.7947 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.6112 |
| `leave_one_tool_out` | `tool_only_control` | `decomposed_sgd_product` | 22 | 21 | 0.7947 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.6112 |
| `leave_one_tool_out` | `tool_only_control` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.5222 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.3387 |
| `leave_one_tool_out` | `tool_only_control` | `verifier_present_sgd_auth` | 22 | 21 | 0.1041 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.0794 |

## Skips

- Skipped rows: 9

## Caveats

- This is a pair-free decomposed verifier over frozen schema-conditioned embeddings.
- The method trains on candidate-effect presence and authorization labels, then composes the unauthorized score as realized times not-authorized.
- `verifier_present_*` methods use the candidate-effect-present label at evaluation as a verifier-assisted upper-bound setting; they are not pure LLM representation probes.
- Comparisons to T54 baselines are setting-shifted because the verifier receives candidate-effect schema text and auxiliary supervision.
- Threshold tradeoffs are ex-post diagnostics, not deployment-calibrated thresholds.
