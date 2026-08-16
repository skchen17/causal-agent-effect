# E55 Main Table

| Method | UPA | FDeny | Coverage | Abstain | Decision Acc | Atom Exact |
|---|---:|---:|---:|---:|---:|---:|
| existing_hard_effect_binding_guard | 0.037 | 0.000 | 0.200 | 0.800 | 0.100 | 0.000 |
| authz_aware_effect_binding_guard | 0.000 | 0.000 | 0.920 | 0.080 | 1.000 | 1.000 |
| authz_aware_no_alias_resolution | 0.000 | 0.211 | 0.920 | 0.080 | 0.920 | 1.000 |
| authz_aware_no_multi_resource_expansion | 0.333 | 0.000 | 0.920 | 0.080 | 0.820 | 0.300 |
| authz_aware_no_operation_mode | 0.148 | 0.000 | 0.920 | 0.080 | 0.920 | 1.000 |
| authz_aware_no_provenance_overlay | 0.148 | 0.000 | 0.940 | 0.060 | 0.900 | 1.000 |
| authz_aware_no_evidence_fallback | 0.000 | 0.000 | 0.880 | 0.120 | 0.960 | 0.960 |

Note: this is the original E55 label table. E57 human audit found a corrected-label subset. Under the 600-row minimal human correction, the full authorization-aware guard remains UPA `0/320 = 0.000` and coverage `552/600 = 0.920`, while FDeny becomes `4/230 = 0.017`. See `e55_human_corrected_sensitivity.md` for the paper-facing sensitivity table.
