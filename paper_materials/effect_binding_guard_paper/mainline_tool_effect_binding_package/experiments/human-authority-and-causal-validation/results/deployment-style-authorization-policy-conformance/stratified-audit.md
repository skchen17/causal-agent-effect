# Stratified audit of the frozen deployment-style authorization result

All 24 designed pairs are policy-separating (one ALLOW and one DENY).
The audit includes 7 pairs whose distinction depends on pre-state or state-resolved aliases/defaults.

## Pair collapse counts

- `canonical_raw_arguments`: 7/24 separating pairs
- `common_effect_fields`: 7/24 separating pairs
- `tool_name`: 24/24 separating pairs

## State-dependent subset

| Representation | Coverage | Accuracy | Abstain |
|---|---:|---:|---:|
| `canonical_raw_arguments` | 0/14 | 0/14 | 14/14 |
| `common_effect_fields` | 7/14 | 7/14 | 7/14 |
| `tool_name` | 0/14 | 0/14 | 14/14 |
| `validated_typed_effects` | 14/14 | 14/14 | 0/14 |

This is a read-only audit of the frozen result. It does not change the experiment's cases, policies, representations, or decisions.
