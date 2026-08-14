# Atom-vs-Field Semantic Attribution

This finite experiment holds source effects, policy predicates, retained schema fields, and decision semantics fixed. Only the monitor representation changes.

## Field-set control

Raw and validated registries contain the same 25 tools and 67 fields: `True`.

## Ordered-authorizer results

| Dataset | Representation | Queries | UPA | False deny | Accuracy |
|---|---|---:|---:|---:|---:|
| agentdojo_finite_56 | pre_validation_common_effects | 1184 | 236/1122 (0.210) | 0/62 (0.000) | 0.801 |
| agentdojo_finite_56 | raw_call_exact | 1184 | 0/1122 (0.000) | 6/62 (0.097) | 0.995 |
| agentdojo_finite_56 | raw_field_leaf_set | 1184 | 0/1122 (0.000) | 2/62 (0.032) | 0.998 |
| agentdojo_finite_56 | source_effect_oracle | 1184 | 0/1122 (0.000) | 0/62 (0.000) | 1.000 |
| agentdojo_finite_56 | tool_name | 1184 | 1122/1122 (1.000) | 0/62 (0.000) | 0.052 |
| agentdojo_finite_56 | validated_typed_atoms | 1184 | 0/1122 (0.000) | 0/62 (0.000) | 1.000 |
| toolsandbox_heldout_32 | pre_validation_common_effects | 232 | 85/150 (0.567) | 0/82 (0.000) | 0.634 |
| toolsandbox_heldout_32 | raw_call_exact | 232 | 14/150 (0.093) | 28/82 (0.341) | 0.819 |
| toolsandbox_heldout_32 | raw_field_leaf_set | 232 | 18/150 (0.120) | 28/82 (0.341) | 0.802 |
| toolsandbox_heldout_32 | source_effect_oracle | 232 | 0/150 (0.000) | 0/82 (0.000) | 1.000 |
| toolsandbox_heldout_32 | tool_name | 232 | 150/150 (1.000) | 0/82 (0.000) | 0.353 |
| toolsandbox_heldout_32 | validated_typed_atoms | 232 | 0/150 (0.000) | 0/82 (0.000) | 1.000 |

## Interpretation rule

Validated atoms provide independent value only where they improve authorization separation or the UPA/false-denial frontier relative to representations with the same retained fields. A stricter result with worse false denial is reported as a tradeoff, not dominance.

The pre-validation common-effect view is a deterministic coarse candidate, not a verbatim LLM output. The source oracle is used only for scoring.
