# Final Assessment: Deployment-Style Authorization Interface Experiment

## Status

The frozen full experiment and its direct-policy-consumer extension both pass. No tool performs an external side effect: every call executes against a copied in-memory sandbox state.

The final protocol contains 48 contexts over four tools and four domains: calendar, workspace sharing, messaging, and banking. The contexts form 24 policy-separating pairs, each containing one authorized and one unauthorized execution under a frozen ACL, capability, or delegation-style policy. Seven pairs, comprising 14 contexts, require pre-state, defaults, or state-resolved aliases to determine the committed effect.

The independently implemented pre-commit descriptor and the before/after source-state oracle agree on all 48 contexts. This is bounded descriptor conformance, not open-world soundness.

## Representation Capacity on the Frozen Policy Relation

The same finite-domain consumer is applied to every representation. It returns the unanimous policy decision for a representation cell and `ABSTAIN` for a mixed cell.

| Representation | Mixed cells | Unit-cost error lower bound | Coverage | Accuracy | Withheld authorized work |
|---|---:|---:|---:|---:|---:|
| Tool name | 4 | 24 | 0/48 | 0/48 | 24/24 |
| Canonical raw arguments | 7 | 7 | 29/48 | 29/48 | 11/24 |
| Common effect fields | 5 | 7 | 27/48 | 27/48 | 14/24 |
| Validated typed effects | 0 | 0 | 48/48 | 48/48 | 0/24 |

Resolving every mixed cell uniformly as `ALLOW` produces unsafe-pre-allow rates of 24/24, 8/24, 7/24, and 0/24 respectively. Resolving every mixed cell as `DENY` produces false-denial rates of 24/24, 11/24, 14/24, and 0/24. These are common decision rules applied uniformly to all four views; they expose the safety/permissiveness tradeoff caused by mixed representation cells.

Across the 24 designed policy-separating pairs, tool name collapses 24, raw arguments collapse 7, common fields collapse 7, and typed effects collapse none.

## Direct Policy Consumer Without Test-Label Compilation

A second frozen extension removes the possibility that the primary cell consumer benefits from seeing the finite test relation. Its prediction function reads only the current representation and the frozen policy manifest. Ideal labels are attached only after prediction for scoring.

| Representation | UPA | False denial | Abstain | Coverage | Accuracy |
|---|---:|---:|---:|---:|---:|
| Tool name | 0/24 | 0/24 | 48/48 | 0/48 | 0/48 |
| Canonical raw arguments | 0/24 | 0/24 | 48/48 | 0/48 | 0/48 |
| Common effect fields | 0/24 | 0/24 | 32/48 | 16/48 | 16/48 |
| Validated typed effects | 0/24 | 0/24 | 0/48 | 48/48 | 48/48 |

Tool-name and raw-argument views are opaque to the shared effect-policy engine. Importing typed descriptor semantics into those baselines would change the representation being tested, so the engine fails closed. Common fields can decide visible resource and target violations but abstain when a policy depends on a removed qualifier. Typed effects expose every field required by the four frozen policies.

## State-Dependent Authorization

On the 14 state-dependent contexts, raw arguments have 0/14 coverage because identical explicit arguments cross policy decisions when defaults, existence, fees, or aliases change in pre-state. Common fields decide 7/14. Typed effects decide all 14 correctly with no abstention.

## Answers to the Core Questions

1. **Do coarse representations lose policy-relevant distinctions under deployment-style policies?** Yes, on this frozen controlled domain. Each coarse view contains executable policy-separating collisions. Therefore no deterministic consumer over that view can avoid both unsafe allowance and withheld authorized work on every member of the mixed cells.
2. **Do validated typed effects improve end-to-end authorization correctness?** Yes, on the same frozen calls, states, policies, and consumers. The typed view has no mixed cell, reproduces all 48 ideal decisions in both the relation-capacity and direct-policy tests, and distinguishes all state-dependent pairs.

## Claim Boundary

This experiment materially strengthens the manuscript beyond source-effect multiset containment: the ideal decisions come from explicit ACL, capability, and delegation-style rules over concrete effects. It remains a controlled mechanism experiment. The policies and descriptor were authored within the same project, so the result does not establish independent policy authorship, prevalence of these policies in deployment, or open-world descriptor soundness. The perfect typed result should be stated as bounded conformance to the frozen four-domain policy relation, not universal authorization correctness.

The earlier pilot under `results/deployment-style-authorization-interface/` is excluded because its common-field projection removed resource and target information in addition to qualifiers. The final protocol changes no cases or policies and restores the common-field definition used by the manuscript.

## Reproduction

```bash
python -m pytest \
  shared/compatibility/tests/tests/test_deployment_style_authorization_interface.py \
  shared/compatibility/tests/tests/test_deployment_style_direct_policy_consumer.py -q
python shared/compatibility/scripts/run_deployment_style_authorization_interface.py --mode full
python shared/compatibility/scripts/summarize_deployment_style_authorization_interface.py
python shared/compatibility/scripts/run_deployment_style_direct_policy_consumer.py
```
