# Full-Scale Deployment-Style Authorization Experiment

Status: **passed**

## Scope

The frozen evaluation contains 24 contexts, 12 policy-separating pairs, 1 tools, and 1 domains. Every tool call executes only in a copied in-memory sandbox.

The candidate descriptors were validated before evaluation on 18 registration contexts and 9 counterfactual pairs. Registration and held-out evaluation use disjoint case IDs and concrete values.

## Registration

- Descriptor/source exact-set match: 18/18.
- Counterfactual relation accuracy: 9/9.
- Sensitive pairs: 8; surface-invariant pairs: 1.

## Direct Policy Decisions

All representations are passed to the same tri-state policy engine. Opaque or incomplete effect inventories produce ABSTAIN; known unauthorized facts produce DENY.

| Representation | UPA | False denial | Abstain | Coverage | Accuracy |
|---|---:|---:|---:|---:|---:|
| tool_name | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% |
| canonical_raw_arguments | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% |
| common_effect_fields | 0.0% | 0.0% | 58.3% | 41.7% | 41.7% |
| validated_typed_effects | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |

## Representation-Capacity Diagnostics

Mixed cells contain calls that look identical under one representation but require different ideal authorization decisions. The lower bound is the minority count in each mixed cell.

| Representation | Cells | Mixed cells | Rows in mixed cells | Error lower bound | Fail-open UPA | Fail-closed false denial |
|---|---:|---:|---:|---:|---:|---:|
| tool_name | 1 | 1 | 24 | 12 | 100.0% | 100.0% |
| canonical_raw_arguments | 16 | 3 | 10 | 3 | 25.0% | 58.3% |
| common_effect_fields | 10 | 1 | 13 | 3 | 25.0% | 83.3% |
| validated_typed_effects | 15 | 0 | 0 | 0 | 0.0% | 0.0% |

## State-Dependent Authorization

The held-out set contains 3 same-argument, different-pre-state pairs. Raw arguments collide on 3/3 pairs; typed effects collide on 0/3.

## Interpretation

1. Coarse views contain constructive policy-separating collisions under the frozen deployment-style policies. Any deterministic completion of a mixed cell must either allow an unauthorized effect or withhold authorized work.
2. The counterfactually validated typed representation exposes the concrete resource, operation, target, qualifier, commit mode, and state-dependent effects needed by the same policy engine on this bounded domain.
3. These results establish bounded representation sufficiency, not open-world descriptor soundness or production safety.

## Claim Boundary

Controlled eight-tool copied-sandbox authorization experiment over frozen ACL, capability, and delegation policies. It measures representation sufficiency on the enumerated intervention and policy families; it does not establish open-world descriptor soundness, policy correctness, deployment prevalence, or production safety.
