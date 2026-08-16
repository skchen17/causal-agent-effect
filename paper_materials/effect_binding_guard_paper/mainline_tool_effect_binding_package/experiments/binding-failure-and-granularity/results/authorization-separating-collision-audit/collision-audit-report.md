# Authorization-Separating Representation Collision Audit

- Status: `passed`
- Witness cells: `288`
- Equality is canonical-JSON equality over the declared representation.
- Cells are keyed by both representation and an identical semantic authority object; changing the authority does not create a collision.

| Dataset | Representation | Rows | Cells | Mixed cells | Rows in mixed cells | Lower bound | Sufficient on observed rows |
|---|---|---:|---:|---:|---:|---:|---|
| E48-explicit-authority-subset | `tool_name` | 528 | 150 | 45 | 362 | 96 | false |
| E48-explicit-authority-subset | `ideal_effect` | 528 | 144 | 35 | 408 | 48 | false |
| E48-explicit-authority-subset | `ideal_effect_resource` | 528 | 190 | 0 | 0 | 0 | true |
| E48-explicit-authority-subset | `rule_extracted_effect` | 528 | 172 | 38 | 365 | 67 | false |
| E48-explicit-authority-subset | `rule_extracted_effect_resource` | 528 | 246 | 30 | 242 | 43 | false |
| E48-explicit-authority-subset | `rule_decision_representation` | 528 | 276 | 35 | 197 | 43 | false |
| E48-explicit-authority-subset | `full_guard_decision_representation` | 528 | 368 | 14 | 72 | 18 | false |
| E50-repaired-resource-authorization | `tool_name` | 240 | 94 | 23 | 165 | 72 | false |
| E50-repaired-resource-authorization | `ideal_effect` | 240 | 133 | 22 | 93 | 45 | false |
| E50-repaired-resource-authorization | `ideal_effect_resource` | 240 | 201 | 0 | 0 | 0 | true |
| E50-repaired-resource-authorization | `rule_extracted_effect` | 240 | 126 | 22 | 102 | 45 | false |
| E50-repaired-resource-authorization | `rule_extracted_effect_resource` | 240 | 190 | 8 | 26 | 10 | false |
| E50-repaired-resource-authorization | `rule_decision_representation` | 240 | 190 | 8 | 26 | 10 | false |
| E50-repaired-resource-authorization | `full_guard_decision_representation` | 240 | 187 | 8 | 29 | 11 | false |

## Interpretation

- E48 includes only rows whose authority can be parsed into an explicit semantic bound; excluded rows remain in the original benchmark metrics.
- E50 uses the repaired frozen policy oracle for all 240 rows.
- An observed-row sufficiency result is not collision completeness over the open tool domain.
- Neural-checkpoint internal representations are not inferred from equal output decisions.
