# Auth-SafeInv Mitigation vs Baseline

- Data: `qwen3-8b_authorization_counterfactuals_v2`
- Samples: 1464
- Projection seeds: [0, 1, 2]
- Projection dim / epochs: 128 / 100
- Target FPR: 0.1

## Fixed Threshold Aggregate

| Split | Method | Rows | Cells | Mean FNR | Std FNR | Max FNR | Mean FPR |
|---|---|---:|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `contrastive_observed_pair_upper_bound` | 60 | 20 | 0.0167 | 0.128 | 1.0 | 0.0085 |
| `leave_one_family_out` | `contrastive_train_only` | 60 | 20 | 0.4183 | 0.4486 | 1.0 | 0.0199 |
| `leave_one_tool_out` | `contrastive_observed_pair_upper_bound` | 63 | 21 | 0.0137 | 0.1077 | 0.8621 | 0.0191 |
| `leave_one_tool_out` | `contrastive_train_only` | 63 | 21 | 0.3539 | 0.4268 | 1.0 | 0.0489 |

## Best Mitigation Tradeoffs

| Split | Method | Threshold | Rows | Cells | Mean FNR | Mean FPR |
|---|---|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `contrastive_observed_pair_upper_bound` | 0.35 | 60 | 20 | 0.0 | 0.0483 |
| `leave_one_family_out` | `contrastive_train_only` | 0.1 | 60 | 20 | 0.35 | 0.0948 |
| `leave_one_tool_out` | `contrastive_observed_pair_upper_bound` | 0.4 | 63 | 21 | 0.0 | 0.0524 |
| `leave_one_tool_out` | `contrastive_train_only` | 0.15 | 63 | 21 | 0.2804 | 0.0855 |

## Same-Cell Comparison vs T47 Baselines

- Baseline source: `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.json`
- `open_set_abstain` is excluded from best-baseline selection.

| Split | Mitigation | Cells | Coverage | Mit FNR | Mit FPR | Best baseline | Base FNR | Base FPR | Delta FNR |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| `leave_one_family_out` | `contrastive_observed_pair_upper_bound` | 20 | 0.9524 | 0.0 | 0.0483 | `irm_linear` | 0.1655 | 0.0911 | 0.1655 |
| `leave_one_family_out` | `contrastive_train_only` | 20 | 0.9524 | 0.35 | 0.0948 | `irm_linear` | 0.1655 | 0.0911 | -0.1845 |
| `leave_one_tool_out` | `contrastive_observed_pair_upper_bound` | 21 | 1.0 | 0.0 | 0.0524 | `supervised_contrastive` | 0.1835 | 0.0712 | 0.1835 |
| `leave_one_tool_out` | `contrastive_train_only` | 21 | 1.0 | 0.2804 | 0.0855 | `supervised_contrastive` | 0.1835 | 0.0712 | -0.0969 |

## Training-Signal Skips

- `fewer_than_two_positive_training_tools`: 12

## Caveats

- `contrastive_train_only` is the strict split-matched setting and can be non-evaluable when the held-out split leaves fewer than two positive training tools.
- `contrastive_observed_pair_upper_bound` uses observed held-out-tool positive pairs for projection training; it is an upper bound on repair with coverage, not a zero-shot mitigation result.
- All classifiers train on realized effect labels; authorization enters through unauthorized-effect positives and absent-not-authorized negatives at evaluation time.
- Same-cell baseline comparisons exclude `open_set_abstain` because the T47 audit showed reject-all degeneracy can produce FNR=0 with unusable FPR.
