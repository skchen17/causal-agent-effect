# Direct Deployment-Style Policy Consumer

- Status: `passed`
- Contexts: `48`
- The consumer reads only the current representation and frozen policy manifest; ideal labels are used only after prediction for scoring.

| Representation | UPA | FD | Abstain | Coverage | Accuracy | Withheld authorized |
|---|---:|---:|---:|---:|---:|---:|
| `tool_name` | 0/24 (0.000) | 0/24 (0.000) | 48/48 (1.000) | 0/48 (0.000) | 0/48 (0.000) | 24/24 (1.000) |
| `canonical_raw_arguments` | 0/24 (0.000) | 0/24 (0.000) | 48/48 (1.000) | 0/48 (0.000) | 0/48 (0.000) | 24/24 (1.000) |
| `common_effect_fields` | 0/24 (0.000) | 0/24 (0.000) | 32/48 (0.667) | 16/48 (0.333) | 16/48 (0.333) | 21/24 (0.875) |
| `validated_typed_effects` | 0/24 (0.000) | 0/24 (0.000) | 0/48 (0.000) | 48/48 (1.000) | 48/48 (1.000) | 0/24 (0.000) |

Tool-name and raw-argument views remain opaque to an effect-policy consumer unless separate tool-specific semantics are added; the shared engine therefore abstains rather than importing the validated descriptor into those baselines. Common fields can resolve resource/target rules but abstain when a policy depends on removed qualifiers. Typed effects expose the complete tested policy interface.

This controlled result does not establish policy prevalence, independent policy authorship, or open-world descriptor soundness.
