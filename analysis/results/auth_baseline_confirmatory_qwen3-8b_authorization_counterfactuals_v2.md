# Auth-SafeInv Baseline Confirmatory Sweep

- Data: `qwen3-8b_authorization_counterfactuals_v2`
- Samples: 1464
- Evaluations: ['loto', 'family']
- Torch seeds: [0, 1, 2]
- Hidden dims: [64, 128]
- Learning rates: [0.001]
- Torch epochs: 15

## Fixed Threshold Aggregate

| Split | Method | Rows | Mean FNR | Std FNR | Max FNR | Mean FPR | Std FPR |
|---|---|---:|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `calibrated_abstention` | 21 | 0.367 | 0.4181 | 1.0 | 0.0668 | 0.0867 |
| `leave_one_family_out` | `domain_adversarial` | 126 | 0.4057 | 0.4549 | 1.0 | 0.0164 | 0.0398 |
| `leave_one_family_out` | `irm_linear` | 63 | 0.1682 | 0.3535 | 1.0 | 0.1081 | 0.1669 |
| `leave_one_family_out` | `open_set_abstain` | 21 | 0.2593 | 0.3642 | 1.0 | 0.4915 | 0.2977 |
| `leave_one_family_out` | `pooled_logistic` | 21 | 0.5098 | 0.4386 | 1.0 | 0.0 | 0.0 |
| `leave_one_family_out` | `supervised_contrastive` | 126 | 0.4129 | 0.4557 | 1.0 | 0.0042 | 0.0169 |
| `leave_one_tool_out` | `calibrated_abstention` | 21 | 0.2182 | 0.335 | 1.0 | 0.1637 | 0.2452 |
| `leave_one_tool_out` | `domain_adversarial` | 126 | 0.2961 | 0.3866 | 1.0 | 0.0382 | 0.09 |
| `leave_one_tool_out` | `irm_linear` | 63 | 0.105 | 0.2234 | 1.0 | 0.2418 | 0.2915 |
| `leave_one_tool_out` | `open_set_abstain` | 21 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 |
| `leave_one_tool_out` | `pooled_logistic` | 21 | 0.4047 | 0.4278 | 1.0 | 0.0154 | 0.0533 |
| `leave_one_tool_out` | `supervised_contrastive` | 126 | 0.3299 | 0.413 | 1.0 | 0.0205 | 0.0757 |

## Torch Seed Variance

| Split | Method | Seeds | Mean FNR | Std FNR | Min FNR | Max FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `domain_adversarial` | `[0, 1, 2]` | 0.4057 | 0.005 | 0.4021 | 0.4127 | 0.0164 |
| `leave_one_family_out` | `irm_linear` | `[0, 1, 2]` | 0.1682 | 0.0317 | 0.1349 | 0.2109 | 0.1081 |
| `leave_one_family_out` | `supervised_contrastive` | `[0, 1, 2]` | 0.4129 | 0.0018 | 0.4104 | 0.4148 | 0.0042 |
| `leave_one_tool_out` | `domain_adversarial` | `[0, 1, 2]` | 0.2961 | 0.0125 | 0.2809 | 0.3115 | 0.0382 |
| `leave_one_tool_out` | `irm_linear` | `[0, 1, 2]` | 0.105 | 0.0037 | 0.1016 | 0.1102 | 0.2418 |
| `leave_one_tool_out` | `supervised_contrastive` | `[0, 1, 2]` | 0.3299 | 0.0058 | 0.3258 | 0.3381 | 0.0205 |

## Best Threshold Tradeoffs

| Split | Method | Target FPR | Threshold | Mean FNR | Mean FPR |
|---|---|---:|---:|---:|---:|
| `leave_one_family_out` | `domain_adversarial` | 0.05 | 0.15 | 0.3556 | 0.0427 |
| `leave_one_family_out` | `domain_adversarial` | 0.1 | 0.05 | 0.2545 | 0.0813 |
| `leave_one_family_out` | `domain_adversarial` | 0.2 | 0.05 | 0.2545 | 0.0813 |
| `leave_one_family_out` | `irm_linear` | 0.05 | 0.7 | 0.2341 | 0.047 |
| `leave_one_family_out` | `irm_linear` | 0.1 | 0.55 | 0.1771 | 0.0867 |
| `leave_one_family_out` | `irm_linear` | 0.2 | 0.35 | 0.1275 | 0.1892 |
| `leave_one_family_out` | `pooled_logistic` | 0.05 | 0.05 | 0.3832 | 0.0245 |
| `leave_one_family_out` | `pooled_logistic` | 0.1 | 0.05 | 0.3832 | 0.0245 |
| `leave_one_family_out` | `pooled_logistic` | 0.2 | 0.05 | 0.3832 | 0.0245 |
| `leave_one_family_out` | `supervised_contrastive` | 0.05 | 0.05 | 0.3836 | 0.0317 |
| `leave_one_family_out` | `supervised_contrastive` | 0.1 | 0.05 | 0.3836 | 0.0317 |
| `leave_one_family_out` | `supervised_contrastive` | 0.2 | 0.05 | 0.3836 | 0.0317 |
| `leave_one_tool_out` | `domain_adversarial` | 0.05 | 0.45 | 0.2677 | 0.0433 |
| `leave_one_tool_out` | `domain_adversarial` | 0.1 | 0.25 | 0.1857 | 0.0951 |
| `leave_one_tool_out` | `domain_adversarial` | 0.2 | 0.1 | 0.1492 | 0.1775 |
| `leave_one_tool_out` | `irm_linear` | 0.05 | 0.95 | 0.2816 | 0.0424 |
| `leave_one_tool_out` | `irm_linear` | 0.1 | 0.8 | 0.189 | 0.0937 |
| `leave_one_tool_out` | `irm_linear` | 0.2 | 0.6 | 0.1317 | 0.18 |
| `leave_one_tool_out` | `pooled_logistic` | 0.05 | 0.45 | 0.3857 | 0.0254 |
| `leave_one_tool_out` | `pooled_logistic` | 0.1 | 0.1 | 0.2754 | 0.0826 |
| `leave_one_tool_out` | `pooled_logistic` | 0.2 | 0.05 | 0.2246 | 0.1109 |
| `leave_one_tool_out` | `supervised_contrastive` | 0.05 | 0.15 | 0.2232 | 0.0474 |
| `leave_one_tool_out` | `supervised_contrastive` | 0.1 | 0.05 | 0.1835 | 0.0712 |
| `leave_one_tool_out` | `supervised_contrastive` | 0.2 | 0.05 | 0.1835 | 0.0712 |

## Open-Set Degeneracy

- Reject-all degenerate rows: 21 / 42

## Caveats

- This is still a compact confirmatory sweep; it improves over the T44 pilot but is not a final hyperparameter search.
- Threshold curves are diagnostic FNR-FPR tradeoffs over unauthorized positives and absent-not-authorized negatives.
- Open-set abstention is isolated because it can reduce FNR by rejecting every held-out-tool example, yielding unusable FPR.
- All torch models train on realized effect labels; authorization is evaluated through unauthorized-effect positives.
