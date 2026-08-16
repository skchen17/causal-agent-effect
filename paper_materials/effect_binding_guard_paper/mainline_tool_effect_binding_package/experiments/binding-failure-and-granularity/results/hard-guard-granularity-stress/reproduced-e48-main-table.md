# E50 Reproduced E48 Main Table

| Method | UPA | FDeny | Abstain | Coverage | Effect Acc | Resource Acc | Auth Acc | Prov Acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `rule_tuple_guard` | 0.094 | 0.097 | 0.345 | 0.655 | 0.792 | 0.380 | 0.504 | 1.000 |
| `local_qwen_tuple_guard` | 0.106 | 0.067 | 0.038 | 0.962 | 0.809 | 0.877 | 0.930 | 0.815 |
| `multi_view_disagreement_guard` | 0.075 | 0.136 | 0.002 | 0.998 | 0.892 | 0.753 | 0.859 | 0.815 |
| `evidence_gated_selective_guard` | 0.064 | 0.065 | 0.075 | 0.925 | 0.836 | 0.726 | 0.848 | 0.722 |
| `control_provenance_minimal_check` | 0.094 | 0.097 | 0.345 | 0.655 | 0.792 | 0.380 | 0.504 | 1.000 |
| `effect_binding_guard_full` | 0.036 | 0.065 | 0.083 | 0.917 | 0.836 | 0.726 | 0.848 | 1.000 |
| `always_use_evidence` | 0.003 | 0.032 | 0.861 | 0.139 | 0.102 | 0.088 | 0.129 | 0.000 |
| `deny_all` | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| `allow_all` | 1.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
