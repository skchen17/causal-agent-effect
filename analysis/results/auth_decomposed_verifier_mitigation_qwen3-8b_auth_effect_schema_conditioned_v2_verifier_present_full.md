# Auth Decomposed Verifier Mitigation

- Data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Samples: 35136
- Conditions: `['full_tool_chain']`
- Methods: `['verifier_present_sgd_auth', 'verifier_present_per_effect_sgd_auth']`
- Target FPR: 0.1

## Fixed Threshold Aggregate

| Split | Condition | Method | Rows | Cells | Mean FNR | Std FNR | Max FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.1952 | 0.2935 | 1.0 | 0.0 |
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 21 | 21 | 0.0745 | 0.2238 | 1.0 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.0642 | 0.222 | 1.0 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 22 | 22 | 0.0042 | 0.0194 | 0.093 | 0.0 |

## Best Ex-Post Tradeoffs

| Split | Condition | Method | Threshold | Cells | Mean FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 0.05 | 21 | 0.1881 | 0.0 |
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 0.05 | 21 | 0.0745 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 0.05 | 21 | 0.0642 | 0.0 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 0.05 | 22 | 0.0042 | 0.0 |

## Same-Cell Comparison vs T54 Baselines

- Baseline source: `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.json`
- Interpretation: Setting-shifted comparison: decomposed verifier uses candidate present/authorized supervision over schema-conditioned inputs; T54 baselines train realized-effect probes.

| Split | Condition | Method | Cells | Baseline cells | Dec FNR | Dec FPR | Best baseline | Base FNR | Base FPR | Delta FNR |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.1881 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | -0.011 |
| `leave_one_family_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 21 | 21 | 0.0745 | 0.0 | `irm_linear` | 0.1771 | 0.0867 | 0.1026 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_per_effect_sgd_auth` | 21 | 21 | 0.0642 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.1193 |
| `leave_one_tool_out` | `full_tool_chain` | `verifier_present_sgd_auth` | 22 | 21 | 0.0042 | 0.0 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.1793 |

## Skips

- Skipped rows: 1

## Caveats

- This is a pair-free decomposed verifier over frozen schema-conditioned embeddings.
- The method trains on candidate-effect presence and authorization labels, then composes the unauthorized score as realized times not-authorized.
- `verifier_present_*` methods use the candidate-effect-present label at evaluation as a verifier-assisted upper-bound setting; they are not pure LLM representation probes.
- Comparisons to T54 baselines are setting-shifted because the verifier receives candidate-effect schema text and auxiliary supervision.
- Threshold tradeoffs are ex-post diagnostics, not deployment-calibrated thresholds.
