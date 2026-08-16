# E49 Same-Core Comparisons

## phase4

| Method | UPA | FDeny | Coverage |
|---|---:|---:|---:|
| `learned_calibrator` | 0.073 | 0.055 | 1.000 |
| `effect_binding_guard_full` | 0.018 | 0.018 | 0.900 |
| `local_qwen_tuple_guard` | 0.000 | 0.109 | 0.982 |
| `rule_tuple_guard` | 0.164 | 0.091 | 0.727 |

## ipiguard

| Method | UPA | FDeny | Coverage |
|---|---:|---:|---:|
| `learned_calibrator` | 0.400 | 0.000 | 1.000 |
| `effect_binding_guard_full` | 0.133 | 0.057 | 0.920 |
| `local_qwen_tuple_guard` | 0.133 | 0.057 | 1.000 |
| `rule_tuple_guard` | 0.333 | 0.000 | 0.520 |

## camel

| Method | UPA | FDeny | Coverage |
|---|---:|---:|---:|
| `learned_calibrator` | 0.000 | 0.000 | 0.778 |
| `effect_binding_guard_full` | 0.000 | 0.000 | 0.778 |
| `local_qwen_tuple_guard` | 0.750 | 0.200 | 0.889 |
| `rule_tuple_guard` | 0.000 | 0.000 | 0.778 |

Same-core comparisons use E48 rows only; E47 official-checkpoint results remain referenced by prior E47 artifacts and are not averaged with E49 learned rows.
