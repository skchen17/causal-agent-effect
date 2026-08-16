# E55 Tables

## Main Method Table

| Method | UPA | FDeny | Coverage | Abstain | Decision Acc |
|---|---:|---:|---:|---:|---:|
| allow_all | 1.000 | 0.000 | 1.000 | 0.000 | 0.380 |
| deny_all | 0.000 | 1.000 | 1.000 | 0.000 | 0.540 |
| tool_name_proxy | 0.667 | 0.000 | 1.000 | 0.000 | 0.560 |
| text_rule_proxy | 0.593 | 0.000 | 0.880 | 0.120 | 0.640 |
| existing_hard_effect_binding_guard | 0.037 | 0.000 | 0.200 | 0.800 | 0.100 |
| authz_aware_effect_binding_guard | 0.000 | 0.000 | 0.920 | 0.080 | 1.000 |
| authz_aware_no_alias_resolution | 0.000 | 0.211 | 0.920 | 0.080 | 0.920 |
| authz_aware_no_multi_resource_expansion | 0.333 | 0.000 | 0.920 | 0.080 | 0.820 |
| authz_aware_no_operation_mode | 0.148 | 0.000 | 0.920 | 0.080 | 0.920 |
| authz_aware_no_provenance_overlay | 0.148 | 0.000 | 0.940 | 0.060 | 0.900 |
| authz_aware_no_evidence_fallback | 0.000 | 0.000 | 0.880 | 0.120 | 0.960 |

## Paired Deltas

- `authz_minus_existing_unsafe_pre_allow`: rate `-0.04000000000000001`, CI [`-0.2`, `0.0`], groups `60`
- `authz_minus_existing_safe_false_deny`: rate `0.0`, CI [`0.0`, `0.0`], groups `60`
- `authz_minus_existing_coverage`: rate `0.7200000000000001`, CI [`0.6000000000000001`, `0.8`], groups `60`
