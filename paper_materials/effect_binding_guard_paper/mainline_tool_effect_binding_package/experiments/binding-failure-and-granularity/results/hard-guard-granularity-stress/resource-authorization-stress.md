# E50 Resource Authorization Stress

| Method | UPA | FDeny | Abstain | Coverage | Effect Acc | Resource Acc | Auth Acc | Prov Acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `control_provenance_minimal_check` | 0.408 | 0.000 | 0.062 | 0.938 | 0.892 | 0.983 | 0.542 | NA |
| `effect_binding_guard_full` | 0.383 | 0.000 | 0.079 | 0.921 | 0.896 | 0.904 | 0.529 | NA |
| `evidence_gated_selective_guard` | 0.383 | 0.000 | 0.079 | 0.921 | 0.896 | 0.904 | 0.529 | NA |
| `full_without_authorization_match` | 0.892 | 0.000 | 0.079 | 0.921 | 0.892 | 0.983 | 0.475 | NA |
| `full_without_provenance_overlay` | 0.383 | 0.000 | 0.079 | 0.921 | 0.896 | 0.904 | 0.529 | NA |
| `full_without_resource_match` | 0.617 | 0.000 | 0.062 | 0.938 | 0.892 | 0.983 | 0.433 | NA |
| `rule_tuple_guard` | 0.408 | 0.000 | 0.062 | 0.938 | 0.892 | 0.983 | 0.542 | NA |
