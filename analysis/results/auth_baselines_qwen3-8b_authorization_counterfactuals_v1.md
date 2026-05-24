# Auth-SafeInv Strong Baselines

- Data: `qwen3-8b_authorization_counterfactuals_v1`
- Samples: 1184
- Methods: calibrated_abstention, direct_unauthorized_logistic, domain_adversarial, inverse_group_reweight, irm_linear, iterative_worst_group_reweight, open_set_abstain, pooled_logistic, supervised_contrastive, tool_conditioned_logistic
- Torch epochs: 25

## Aggregate

| Split | Method | Rows | Mean FNR | Median FNR | Max FNR | Mean absent FPR | Mean N unauth |
|---|---|---:|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `calibrated_abstention` | 14 | 0.6766 | 0.8834 | 1.0 | 0.0461 | 31.0 |
| `leave_one_family_out` | `direct_unauthorized_logistic` | 12 | 1.0 | 1.0 | 1.0 | 0.0 | 23.17 |
| `leave_one_family_out` | `domain_adversarial` | 14 | 0.5879 | 0.6151 | 1.0 | 0.0294 | 31.0 |
| `leave_one_family_out` | `inverse_group_reweight` | 14 | 0.8004 | 1.0 | 1.0 | 0.004 | 31.0 |
| `leave_one_family_out` | `irm_linear` | 14 | 0.2619 | 0.0 | 1.0 | 0.1124 | 31.0 |
| `leave_one_family_out` | `iterative_worst_group_reweight` | 14 | 0.8147 | 1.0 | 1.0 | 0.0016 | 31.0 |
| `leave_one_family_out` | `open_set_abstain` | 14 | 0.5342 | 0.504 | 1.0 | 0.1697 | 31.0 |
| `leave_one_family_out` | `pooled_logistic` | 14 | 0.829 | 1.0 | 1.0 | 0.0014 | 31.0 |
| `leave_one_family_out` | `supervised_contrastive` | 14 | 0.5524 | 0.5834 | 1.0 | 0.0181 | 31.0 |
| `leave_one_family_out` | `tool_conditioned_logistic` | 14 | 0.8129 | 1.0 | 1.0 | 0.0028 | 31.0 |
| `leave_one_tool_out` | `calibrated_abstention` | 14 | 0.4083 | 0.4828 | 1.0 | 0.1072 | 22.0 |
| `leave_one_tool_out` | `direct_unauthorized_logistic` | 14 | 0.9631 | 1.0 | 1.0 | 0.0027 | 22.0 |
| `leave_one_tool_out` | `domain_adversarial` | 14 | 0.4822 | 0.4828 | 1.0 | 0.0035 | 22.0 |
| `leave_one_tool_out` | `inverse_group_reweight` | 14 | 0.6524 | 1.0 | 1.0 | 0.0 | 22.0 |
| `leave_one_tool_out` | `irm_linear` | 14 | 0.1981 | 0.0 | 1.0 | 0.2878 | 22.0 |
| `leave_one_tool_out` | `iterative_worst_group_reweight` | 14 | 0.6524 | 1.0 | 1.0 | 0.0 | 22.0 |
| `leave_one_tool_out` | `open_set_abstain` | 14 | 0.0 | 0.0 | 0.0 | 1.0 | 22.0 |
| `leave_one_tool_out` | `pooled_logistic` | 14 | 0.6524 | 1.0 | 1.0 | 0.0 | 22.0 |
| `leave_one_tool_out` | `supervised_contrastive` | 14 | 0.4946 | 0.4624 | 1.0 | 0.0 | 22.0 |
| `leave_one_tool_out` | `tool_conditioned_logistic` | 14 | 0.6524 | 1.0 | 1.0 | 0.0 | 22.0 |
| `random_group` | `calibrated_abstention` | 40 | 0.0 | 0.0 | 0.0 | 0.0089 | 11.78 |
| `random_group` | `direct_unauthorized_logistic` | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 11.78 |
| `random_group` | `domain_adversarial` | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 11.78 |
| `random_group` | `inverse_group_reweight` | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 11.78 |
| `random_group` | `irm_linear` | 40 | 0.0 | 0.0 | 0.0 | 0.0052 | 11.78 |
| `random_group` | `iterative_worst_group_reweight` | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 11.78 |
| `random_group` | `open_set_abstain` | 40 | 0.0 | 0.0 | 0.0 | 0.046 | 11.78 |
| `random_group` | `pooled_logistic` | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 11.78 |
| `random_group` | `supervised_contrastive` | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 11.78 |
| `random_group` | `tool_conditioned_logistic` | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 11.78 |

## Caveats

- Most baselines train on realized effect labels and are evaluated on unauthorized-effect positives, matching Auth-SafeInv's effect-probe framing.
- `direct_unauthorized_logistic` trains directly on unauthorized labels and should be treated as an upper-bound safety-supervision control, not the same setting as effect detection.
- `iterative_worst_group_reweight` is a linear worst-group reweighting baseline, not a formal GroupDRO certificate.
- `open_set_abstain` can degenerate into rejecting all held-out-tool examples; interpret FNR=0/FPR=1 as an unusable safety/utility tradeoff, not a mitigation win.
- Torch baselines use compact full-batch pilots; for final paper claims, rerun with seed variance and hyperparameter sweeps.
- All metrics are fixed-threshold diagnostics except `calibrated_abstention`, which tunes a threshold on held-out training groups.
