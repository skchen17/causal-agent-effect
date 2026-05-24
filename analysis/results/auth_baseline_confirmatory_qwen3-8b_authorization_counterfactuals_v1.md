# Auth-SafeInv Baseline Confirmatory Sweep

- Data: `qwen3-8b_authorization_counterfactuals_v1`
- Samples: 1184
- Evaluations: ['loto', 'family']
- Torch seeds: [0, 1, 2]
- Hidden dims: [64, 128]
- Learning rates: [0.001]
- Torch epochs: 15

## Fixed Threshold Aggregate

| Split | Method | Rows | Mean FNR | Std FNR | Max FNR | Mean FPR | Std FPR |
|---|---|---:|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `calibrated_abstention` | 14 | 0.6766 | 0.3943 | 1.0 | 0.0461 | 0.0971 |
| `leave_one_family_out` | `domain_adversarial` | 84 | 0.5588 | 0.4194 | 1.0 | 0.039 | 0.0908 |
| `leave_one_family_out` | `irm_linear` | 42 | 0.254 | 0.3689 | 1.0 | 0.1392 | 0.2046 |
| `leave_one_family_out` | `open_set_abstain` | 14 | 0.5342 | 0.3918 | 1.0 | 0.1697 | 0.1701 |
| `leave_one_family_out` | `pooled_logistic` | 14 | 0.829 | 0.2912 | 1.0 | 0.0014 | 0.005 |
| `leave_one_family_out` | `supervised_contrastive` | 84 | 0.546 | 0.4426 | 1.0 | 0.019 | 0.0421 |
| `leave_one_tool_out` | `calibrated_abstention` | 14 | 0.4083 | 0.3818 | 1.0 | 0.1072 | 0.129 |
| `leave_one_tool_out` | `domain_adversarial` | 84 | 0.4299 | 0.4312 | 1.0 | 0.0043 | 0.0145 |
| `leave_one_tool_out` | `irm_linear` | 42 | 0.2244 | 0.341 | 1.0 | 0.256 | 0.3184 |
| `leave_one_tool_out` | `open_set_abstain` | 14 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 |
| `leave_one_tool_out` | `pooled_logistic` | 14 | 0.6524 | 0.439 | 1.0 | 0.0 | 0.0 |
| `leave_one_tool_out` | `supervised_contrastive` | 84 | 0.5214 | 0.4428 | 1.0 | 0.0015 | 0.0057 |

## Torch Seed Variance

| Split | Method | Seeds | Mean FNR | Std FNR | Min FNR | Max FNR | Mean FPR |
|---|---|---|---:|---:|---:|---:|---:|
| `leave_one_family_out` | `domain_adversarial` | `[0, 1, 2]` | 0.5588 | 0.0187 | 0.5327 | 0.5754 | 0.039 |
| `leave_one_family_out` | `irm_linear` | `[0, 1, 2]` | 0.254 | 0.0 | 0.254 | 0.254 | 0.1392 |
| `leave_one_family_out` | `supervised_contrastive` | `[0, 1, 2]` | 0.546 | 0.0017 | 0.5437 | 0.5473 | 0.019 |
| `leave_one_tool_out` | `domain_adversarial` | `[0, 1, 2]` | 0.4299 | 0.0297 | 0.3912 | 0.4635 | 0.0043 |
| `leave_one_tool_out` | `irm_linear` | `[0, 1, 2]` | 0.2244 | 0.0319 | 0.2006 | 0.2696 | 0.256 |
| `leave_one_tool_out` | `supervised_contrastive` | `[0, 1, 2]` | 0.5214 | 0.0047 | 0.5153 | 0.5268 | 0.0015 |

## Best Threshold Tradeoffs

| Split | Method | Target FPR | Threshold | Mean FNR | Mean FPR |
|---|---|---:|---:|---:|---:|
| `leave_one_family_out` | `domain_adversarial` | 0.05 | 0.35 | 0.5176 | 0.0478 |
| `leave_one_family_out` | `domain_adversarial` | 0.1 | 0.1 | 0.4315 | 0.0791 |
| `leave_one_family_out` | `domain_adversarial` | 0.2 | 0.05 | 0.3784 | 0.1101 |
| `leave_one_family_out` | `irm_linear` | 0.05 | 0.85 | 0.452 | 0.0475 |
| `leave_one_family_out` | `irm_linear` | 0.1 | 0.65 | 0.3013 | 0.0922 |
| `leave_one_family_out` | `irm_linear` | 0.2 | 0.4 | 0.253 | 0.1756 |
| `leave_one_family_out` | `pooled_logistic` | 0.05 | 0.05 | 0.6463 | 0.0323 |
| `leave_one_family_out` | `pooled_logistic` | 0.1 | 0.05 | 0.6463 | 0.0323 |
| `leave_one_family_out` | `pooled_logistic` | 0.2 | 0.05 | 0.6463 | 0.0323 |
| `leave_one_family_out` | `supervised_contrastive` | 0.05 | 0.1 | 0.5099 | 0.0387 |
| `leave_one_family_out` | `supervised_contrastive` | 0.1 | 0.05 | 0.5043 | 0.0509 |
| `leave_one_family_out` | `supervised_contrastive` | 0.2 | 0.05 | 0.5043 | 0.0509 |
| `leave_one_tool_out` | `domain_adversarial` | 0.05 | 0.25 | 0.3478 | 0.0428 |
| `leave_one_tool_out` | `domain_adversarial` | 0.1 | 0.15 | 0.3155 | 0.0775 |
| `leave_one_tool_out` | `domain_adversarial` | 0.2 | 0.05 | 0.2428 | 0.193 |
| `leave_one_tool_out` | `irm_linear` | 0.05 | 0.9 | 0.4012 | 0.0487 |
| `leave_one_tool_out` | `irm_linear` | 0.1 | 0.85 | 0.3905 | 0.0935 |
| `leave_one_tool_out` | `irm_linear` | 0.2 | 0.65 | 0.3442 | 0.1754 |
| `leave_one_tool_out` | `pooled_logistic` | 0.05 | 0.1 | 0.5687 | 0.0 |
| `leave_one_tool_out` | `pooled_logistic` | 0.1 | 0.05 | 0.5416 | 0.0575 |
| `leave_one_tool_out` | `pooled_logistic` | 0.2 | 0.05 | 0.5416 | 0.0575 |
| `leave_one_tool_out` | `supervised_contrastive` | 0.05 | 0.05 | 0.3443 | 0.0301 |
| `leave_one_tool_out` | `supervised_contrastive` | 0.1 | 0.05 | 0.3443 | 0.0301 |
| `leave_one_tool_out` | `supervised_contrastive` | 0.2 | 0.05 | 0.3443 | 0.0301 |

## Open-Set Degeneracy

- Reject-all degenerate rows: 14 / 28

## Caveats

- This is still a compact confirmatory sweep; it improves over the T44 pilot but is not a final hyperparameter search.
- Threshold curves are diagnostic FNR-FPR tradeoffs over unauthorized positives and absent-not-authorized negatives.
- Open-set abstention is isolated because it can reduce FNR by rejecting every held-out-tool example, yielding unusable FPR.
- All torch models train on realized effect labels; authorization is evaluated through unauthorized-effect positives.
