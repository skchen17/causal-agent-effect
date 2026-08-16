# Deployment-Style Authorization Interface Experiment

- Status: `passed`
- Contexts: `48` across `4` domains
- Ideal labels: `{'ALLOW': 24, 'DENY': 24}`
- State-dependent contexts: `14`

## Primary fail-closed tri-state consumer

| Representation | UPA | FD | Abstain | Coverage | Accuracy | Withheld authorized |
|---|---:|---:|---:|---:|---:|---:|
| `tool_name` | 0/24 (0.000) | 0/24 (0.000) | 48/48 (1.000) | 0/48 (0.000) | 0/48 (0.000) | 24/24 (1.000) |
| `canonical_raw_arguments` | 0/24 (0.000) | 0/24 (0.000) | 19/48 (0.396) | 29/48 (0.604) | 29/48 (0.604) | 11/24 (0.458) |
| `common_effect_fields` | 0/24 (0.000) | 0/24 (0.000) | 41/48 (0.854) | 7/48 (0.146) | 7/48 (0.146) | 21/24 (0.875) |
| `validated_typed_effects` | 0/24 (0.000) | 0/24 (0.000) | 0/48 (0.000) | 48/48 (1.000) | 48/48 (1.000) | 0/24 (0.000) |

## Interpretation

The policies are explicit ACL, capability, and delegation-style rules over concrete committed effects. The copied sandbox and source-state diff determine the ideal decision. All four representations use the same compiled finite-domain consumer. A mixed representation cell returns ABSTAIN in the primary mode; uniform fail-open and fail-closed diagnostics expose the corresponding unsafe-allow/false-denial tradeoff.

This is a controlled four-domain deployment-style policy test. It establishes only bounded interface conformance on the frozen contexts and does not estimate policy prevalence or production safety.
