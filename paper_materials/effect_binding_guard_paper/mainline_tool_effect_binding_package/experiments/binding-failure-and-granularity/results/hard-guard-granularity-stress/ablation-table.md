# E50 Ablation Table

| Method | UPA | FDeny | Abstain | Coverage | Effect Acc | Resource Acc | Auth Acc | Prov Acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `allow_all` | 1.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| `always_use_evidence` | 0.003 | 0.032 | 0.861 | 0.139 | 0.102 | 0.088 | 0.129 | 0.000 |
| `control_provenance_minimal_check` | 0.094 | 0.097 | 0.345 | 0.655 | 0.792 | 0.380 | 0.504 | 1.000 |
| `deny_all` | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| `effect_binding_guard_full` | 0.036 | 0.065 | 0.083 | 0.917 | 0.836 | 0.726 | 0.848 | 1.000 |
| `evidence_gated_selective_guard` | 0.064 | 0.065 | 0.075 | 0.925 | 0.836 | 0.726 | 0.848 | 0.722 |
| `full_without_evidence_fallback` | 0.042 | 0.136 | 0.017 | 0.983 | 0.892 | 0.753 | 0.859 | 1.000 |
| `full_without_local_qwen_view` | 0.058 | 0.110 | 0.308 | 0.692 | 0.629 | 0.400 | 0.540 | 1.000 |
| `full_without_multi_view_disagreement` | 0.094 | 0.097 | 0.345 | 0.655 | 0.792 | 0.380 | 0.504 | 1.000 |
| `full_without_provenance_overlay` | 0.064 | 0.065 | 0.075 | 0.925 | 0.836 | 0.726 | 0.848 | 0.722 |
| `local_qwen_tuple_guard` | 0.106 | 0.067 | 0.038 | 0.962 | 0.809 | 0.877 | 0.930 | 0.815 |
| `multi_view_disagreement_guard` | 0.075 | 0.136 | 0.002 | 0.998 | 0.892 | 0.753 | 0.859 | 0.815 |
| `never_use_evidence` | 0.075 | 0.136 | 0.002 | 0.998 | 0.892 | 0.753 | 0.859 | 0.815 |
| `rule_tuple_guard` | 0.094 | 0.097 | 0.345 | 0.655 | 0.792 | 0.380 | 0.504 | 1.000 |
| `rule_tuple_guard_no_provenance` | 0.128 | 0.097 | 0.331 | 0.669 | 0.792 | 0.380 | 0.504 | 0.000 |
