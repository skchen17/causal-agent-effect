# E49 Ablation Results

| Split | Method | Feature mode | Overlay | UPA | FDeny | Coverage |
|---|---|---|---:|---:|---:|---:|
| `source_balanced_seed0` | `logistic_calibrator` | `full` | `True` | 0.135 | 0.032 | 0.988 |
| `source_balanced_seed0` | `calibrated_linear_fusion` | `full` | `True` | 0.095 | 0.074 | 0.988 |
| `source_balanced_seed0` | `small_gbdt_fusion` | `full` | `True` | 0.068 | 0.053 | 0.988 |
| `source_balanced_seed0` | `text_only_classifier_baseline` | `full` | `True` | 0.027 | 0.400 | 0.988 |
| `source_balanced_seed0` | `logistic_calibrator__no_provenance__no_provenance_overlay` | `no_provenance` | `False` | 0.203 | 0.084 | 1.000 |
| `source_balanced_seed0` | `logistic_calibrator__no_evidence` | `no_evidence` | `True` | 0.108 | 0.147 | 0.988 |
| `source_balanced_seed0` | `logistic_calibrator__no_disagreement` | `no_disagreement` | `True` | 0.108 | 0.032 | 0.988 |
| `source_balanced_seed0` | `logistic_calibrator__no_local_qwen` | `no_local_qwen` | `True` | 0.230 | 0.021 | 0.988 |
| `source_balanced_seed0` | `logistic_calibrator__decision_votes_only` | `decision_votes_only` | `True` | 0.122 | 0.011 | 0.988 |
| `source_balanced_seed0` | `logistic_calibrator__tuple_fields_only` | `tuple_fields_only` | `True` | 0.095 | 0.032 | 0.988 |
| `source_balanced_seed0` | `logistic_calibrator__no_provenance_overlay` | `full` | `False` | 0.081 | 0.074 | 1.000 |
| `source_balanced_seed0` | `logistic_calibrator__source_aware_diagnostic` | `full_plus_source_scope` | `True` | 0.149 | 0.021 | 0.988 |
| `source_balanced_seed1` | `logistic_calibrator` | `full` | `True` | 0.095 | 0.000 | 0.988 |
| `source_balanced_seed2` | `logistic_calibrator` | `full` | `True` | 0.041 | 0.147 | 0.988 |
| `source_balanced_seed3` | `logistic_calibrator` | `full` | `True` | 0.108 | 0.000 | 0.988 |
| `source_balanced_seed4` | `logistic_calibrator` | `full` | `True` | 0.081 | 0.000 | 0.988 |
| `e48_hashed_split` | `logistic_calibrator` | `full` | `True` | 0.071 | 0.056 | 1.000 |
| `strict_loso_camel` | `logistic_calibrator` | `full` | `True` | 0.083 | 0.000 | 0.778 |
| `strict_loso_phase4` | `logistic_calibrator` | `full` | `True` | 0.033 | 0.926 | 1.000 |
| `strict_loso_ipiguard` | `logistic_calibrator` | `full` | `True` | 0.036 | 0.898 | 1.000 |
