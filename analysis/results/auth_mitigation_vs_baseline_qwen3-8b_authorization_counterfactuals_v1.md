# Auth-SafeInv Mitigation vs Baseline

- Data: `qwen3-8b_authorization_counterfactuals_v1`
- Samples: 1184
- Projection seeds: [0, 1, 2]
- Projection dim / epochs: 128 / 100
- Target FPR: 0.1

## Fixed Threshold Aggregate

| Split | Method | Rows | Cells | Mean FNR | Std FNR | Max FNR | Mean FPR |
|---|---|---:|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `contrastive_observed_pair_upper_bound` | 39 | 13 | 0.0 | 0.0 | 0.0 | 0.0138 |
| `leave_one_family_out` | `contrastive_train_only` | 39 | 13 | 0.7051 | 0.4194 | 1.0 | 0.0113 |
| `leave_one_tool_out` | `contrastive_observed_pair_upper_bound` | 42 | 14 | 0.0 | 0.0 | 0.0 | 0.0379 |
| `leave_one_tool_out` | `contrastive_train_only` | 12 | 4 | 0.6628 | 0.4083 | 1.0 | 0.0 |

## Best Mitigation Tradeoffs

| Split | Method | Threshold | Rows | Cells | Mean FNR | Mean FPR |
|---|---|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `contrastive_observed_pair_upper_bound` | 0.65 | 39 | 13 | 0.0 | 0.0051 |
| `leave_one_family_out` | `contrastive_train_only` | 0.1 | 39 | 13 | 0.467 | 0.0699 |
| `leave_one_tool_out` | `contrastive_observed_pair_upper_bound` | 0.6 | 42 | 14 | 0.0 | 0.0281 |
| `leave_one_tool_out` | `contrastive_train_only` | 0.1 | 12 | 4 | 0.4128 | 0.0 |

## Same-Cell Comparison vs T47 Baselines

- Baseline source: `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v1.json`
- `open_set_abstain` is excluded from best-baseline selection.

| Split | Mitigation | Cells | Coverage | Mit FNR | Mit FPR | Best baseline | Base FNR | Base FPR | Delta FNR |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| `leave_one_family_out` | `contrastive_observed_pair_upper_bound` | 13 | 0.9286 | 0.0 | 0.0051 | `irm_linear` | 0.2817 | 0.0992 | 0.2817 |
| `leave_one_family_out` | `contrastive_train_only` | 13 | 0.9286 | 0.467 | 0.0699 | `irm_linear` | 0.2817 | 0.0992 | -0.1853 |
| `leave_one_tool_out` | `contrastive_observed_pair_upper_bound` | 14 | 1.0 | 0.0 | 0.0281 | `domain_adversarial` | 0.3155 | 0.0775 | 0.3155 |
| `leave_one_tool_out` | `contrastive_train_only` | 4 | 0.2857 | 0.4128 | 0.0 | `domain_adversarial` | 0.4981 | 0.0268 | 0.0853 |

## Training-Signal Skips

- `fewer_than_two_positive_training_tools`: 42

## Caveats

- `contrastive_train_only` is the strict split-matched setting and can be non-evaluable when the held-out split leaves fewer than two positive training tools.
- `contrastive_observed_pair_upper_bound` uses observed held-out-tool positive pairs for projection training; it is an upper bound on repair with coverage, not a zero-shot mitigation result.
- All classifiers train on realized effect labels; authorization enters through unauthorized-effect positives and absent-not-authorized negatives at evaluation time.
- Same-cell baseline comparisons exclude `open_set_abstain` because the T47 audit showed reject-all degeneracy can produce FNR=0 with unusable FPR.
