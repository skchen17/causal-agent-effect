# Deployment-Style Authorization Interface Experiment

- Status: `passed`
- Contexts: `8` across `4` domains
- Ideal labels: `{'ALLOW': 4, 'DENY': 4}`
- State-dependent contexts: `0`

## Primary fail-closed tri-state consumer

| Representation | UPA | FD | Abstain | Coverage | Accuracy | Withheld authorized |
|---|---:|---:|---:|---:|---:|---:|
| `tool_name` | 0/4 (0.000) | 0/4 (0.000) | 8/8 (1.000) | 0/8 (0.000) | 0/8 (0.000) | 4/4 (1.000) |
| `canonical_raw_arguments` | 0/4 (0.000) | 0/4 (0.000) | 0/8 (0.000) | 8/8 (1.000) | 8/8 (1.000) | 0/4 (0.000) |
| `common_effect_fields` | 0/4 (0.000) | 0/4 (0.000) | 0/8 (0.000) | 8/8 (1.000) | 8/8 (1.000) | 0/4 (0.000) |
| `validated_typed_effects` | 0/4 (0.000) | 0/4 (0.000) | 0/8 (0.000) | 8/8 (1.000) | 8/8 (1.000) | 0/4 (0.000) |

## Interpretation

The policies are explicit ACL, capability, and delegation-style rules over concrete committed effects. The copied sandbox and source-state diff determine the ideal decision. All four representations use the same compiled finite-domain consumer. A mixed representation cell returns ABSTAIN in the primary mode; uniform fail-open and fail-closed diagnostics expose the corresponding unsafe-allow/false-denial tradeoff.

This is a controlled four-domain deployment-style policy test. It establishes only bounded interface conformance on the frozen contexts and does not estimate policy prevalence or production safety.
