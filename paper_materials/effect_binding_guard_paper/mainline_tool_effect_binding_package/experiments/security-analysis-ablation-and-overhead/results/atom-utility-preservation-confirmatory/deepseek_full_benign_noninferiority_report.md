# DeepSeek atom-description benign utility pilot

- Status: `passed_with_model_failures`
- Rows: `582/582`
- Runtime guard: `disabled`

| Condition | Utility | Total | Rate | Repeat rates |
|---|---:|---:|---:|---|
| pristine | 168 | 194 | 0.866 | 0.866, 0.866 |
| compact_neutral | 177 | 194 | 0.912 | 0.897, 0.928 |
| compact_atoms | 173 | 194 | 0.892 | 0.866, 0.918 |

## Paired against pristine

```json
{
  "compact_atoms": {
    "both_fail": 15,
    "both_pass": 162,
    "treatment_gain": 11,
    "treatment_loss": 6
  },
  "compact_neutral": {
    "both_fail": 14,
    "both_pass": 165,
    "treatment_gain": 12,
    "treatment_loss": 3
  }
}
```

## Paired uncertainty

```json
{
  "compact_atoms_vs_compact_neutral": {
    "baseline": "compact_neutral",
    "bootstrap_samples": 10000,
    "bootstrap_seed": 7007,
    "clustered_bootstrap_95pct_interval": [
      -0.061855670103092786,
      0.020618556701030927
    ],
    "clustered_bootstrap_one_sided_95pct_lower": -0.05670103092783505,
    "n_paired_observations": 194,
    "n_task_clusters": 97,
    "noninferiority_margin": 0.05,
    "noninferiority_passed": false,
    "treatment": "compact_atoms",
    "utility_rate_difference": -0.020618556701030927
  },
  "compact_atoms_vs_pristine": {
    "baseline": "pristine",
    "bootstrap_samples": 10000,
    "bootstrap_seed": 7007,
    "clustered_bootstrap_95pct_interval": [
      -0.010309278350515464,
      0.06701030927835051
    ],
    "clustered_bootstrap_one_sided_95pct_lower": -0.005154639175257732,
    "n_paired_observations": 194,
    "n_task_clusters": 97,
    "noninferiority_margin": 0.05,
    "noninferiority_passed": true,
    "treatment": "compact_atoms",
    "utility_rate_difference": 0.02577319587628866
  }
}
```

Full 97-task AgentDojo v1.1.2 benign-utility non-inferiority test of compact atom descriptions with the runtime guard disabled. It tests representation-induced utility loss, not attack resistance, authorization correctness, deployed safety, or zero loss in every individual run.
