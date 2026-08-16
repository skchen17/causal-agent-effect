# E50 Robustness

| method | unsafe_pre_allow | safe_false_deny | coverage | abstain | effect_accuracy | resource_accuracy | authorization_accuracy | provenance_accuracy | scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| e48_reproduction_full_guard | 0.0361111 | 0.0649351 | 0.917275 | 0.0827251 | 0.835766 | 0.726277 | 0.847656 | 1 | main_reproduction |
| source_balanced_fixed_policy_mean | 0.0513514 | 0.0589474 | 0.923077 | 0.0769231 |  |  |  |  |  |
| strict_loso_camel | 0 | 0 | 0.777778 | 0.222222 | 0.648148 | 0.888889 |  | 1 | LOSO |
| strict_loso_ipiguard | 0.125 | 0.0833333 | 0.891667 | 0.108333 | 0.879167 | 0.675 | 0.795833 |  | LOSO |
| strict_loso_phase4 | 0.0151515 | 0.0606061 | 0.943182 | 0.0568182 | 0.835227 | 0.732955 | 0.871212 |  | LOSO |
| resource_authorization_stress | 0.616667 | 0 | 0.920833 | 0.0791667 | 0.895833 | 0.908333 | 0.4125 |  | evaluation_only_controlled_stress |
| expanded_control_provenance_stress | 0 | 0.1875 | 0.544643 | 0.455357 | 0.4375 | 0.6875 | 0.4375 | 1 | evaluation_only_controlled_stress |
