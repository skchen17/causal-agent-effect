# E55 Tables

## Main Method Table

| Method | UPA | FDeny | Coverage | Abstain | Decision Acc |
|---|---:|---:|---:|---:|---:|
| allow_all | 1.000 | 0.000 | 1.000 | 0.000 | 0.420 |
| deny_all | 0.000 | 1.000 | 1.000 | 0.000 | 0.460 |
| tool_name_proxy | 0.739 | 0.143 | 1.000 | 0.000 | 0.480 |
| text_rule_proxy | 0.522 | 0.000 | 0.880 | 0.120 | 0.760 |
| existing_hard_effect_binding_guard | 0.043 | 0.000 | 0.200 | 0.800 | 0.060 |
| authz_aware_effect_binding_guard | 0.000 | 0.000 | 0.880 | 0.120 | 1.000 |
| authz_aware_no_alias_resolution | 0.000 | 0.238 | 0.880 | 0.120 | 0.900 |
| authz_aware_no_multi_resource_expansion | 0.217 | 0.000 | 0.880 | 0.120 | 0.900 |
| authz_aware_no_operation_mode | 0.217 | 0.000 | 0.880 | 0.120 | 0.900 |
| authz_aware_no_provenance_overlay | 0.217 | 0.000 | 0.880 | 0.120 | 0.900 |
| authz_aware_no_evidence_fallback | 0.000 | 0.000 | 0.880 | 0.120 | 1.000 |

## Paired Deltas

- `authz_minus_existing_unsafe_pre_allow`: rate `-0.04000000000000001`, CI [`-0.2`, `0.0`], groups `60`
- `authz_minus_existing_safe_false_deny`: rate `0.0`, CI [`0.0`, `0.0`], groups `60`
- `authz_minus_existing_coverage`: rate `0.6799999999999999`, CI [`0.5`, `0.8`], groups `60`
