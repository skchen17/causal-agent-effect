# DeepSeek atom-description benign utility pilot

- Status: `passed`
- Rows: `96/96`
- Runtime guard: `disabled`

| Condition | Utility | Total | Rate | Repeat rates |
|---|---:|---:|---:|---|
| pristine | 24 | 24 | 1.000 | 1.000, 1.000 |
| compact_neutral | 22 | 24 | 0.917 | 0.917, 0.917 |
| compact_atoms | 24 | 24 | 1.000 | 1.000, 1.000 |
| compact_atoms_guided | 24 | 24 | 1.000 | 1.000, 1.000 |

## Paired against pristine

```json
{
  "compact_atoms": {
    "both_pass": 24
  },
  "compact_atoms_guided": {
    "both_pass": 24
  },
  "compact_neutral": {
    "both_pass": 22,
    "treatment_loss": 2
  }
}
```

## Paired uncertainty

```json
{
  "compact_atoms_guided_vs_compact_neutral": {
    "baseline": "compact_neutral",
    "bootstrap_samples": 10000,
    "bootstrap_seed": 7007,
    "clustered_bootstrap_95pct_interval": [
      0.0,
      0.25
    ],
    "clustered_bootstrap_one_sided_95pct_lower": 0.0,
    "n_paired_observations": 24,
    "n_task_clusters": 12,
    "noninferiority_margin": null,
    "noninferiority_passed": null,
    "treatment": "compact_atoms_guided",
    "utility_rate_difference": 0.08333333333333333
  },
  "compact_atoms_vs_compact_neutral": {
    "baseline": "compact_neutral",
    "bootstrap_samples": 10000,
    "bootstrap_seed": 7007,
    "clustered_bootstrap_95pct_interval": [
      0.0,
      0.25
    ],
    "clustered_bootstrap_one_sided_95pct_lower": 0.0,
    "n_paired_observations": 24,
    "n_task_clusters": 12,
    "noninferiority_margin": null,
    "noninferiority_passed": null,
    "treatment": "compact_atoms",
    "utility_rate_difference": 0.08333333333333333
  },
  "compact_atoms_vs_pristine": {
    "baseline": "pristine",
    "bootstrap_samples": 10000,
    "bootstrap_seed": 7007,
    "clustered_bootstrap_95pct_interval": [
      0.0,
      0.0
    ],
    "clustered_bootstrap_one_sided_95pct_lower": 0.0,
    "n_paired_observations": 24,
    "n_task_clusters": 12,
    "noninferiority_margin": null,
    "noninferiority_passed": null,
    "treatment": "compact_atoms",
    "utility_rate_difference": 0.0
  }
}
```

Paired 12-task compact-interface development pilot. It is not a full-benchmark, non-inferiority, or security result.
