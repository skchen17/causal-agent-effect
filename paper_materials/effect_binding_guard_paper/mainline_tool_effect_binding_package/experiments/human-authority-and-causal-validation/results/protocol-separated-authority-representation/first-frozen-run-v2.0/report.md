# Protocol-Separated Authority Representation Benchmark

Status: **passed**

## Protocol

The experiment uses 1024 descriptor-blind contexts across four copied-sandbox domains. Policies are explicit ACL, capability, and delegation authority state. Evaluation contexts are generated without labels and mixed cells are discovered only after execution.

## Registration

Executable JSON descriptors matched the independent transition oracle on 288/384 registration contexts and passed 144/192 counterfactual relation checks.

## Direct authorization

| Representation | Coverage | UPA | False denial | Accuracy |
|---|---:|---:|---:|---:|
| tool_name | 0.0% | 0.0% | 0.0% | 0.0% |
| canonical_raw_arguments | 98.4% | 2.0% | 42.5% | 85.6% |
| common_effect_fields | 53.1% | 0.0% | 0.0% | 53.1% |
| validated_typed_effects | 71.4% | 0.0% | 0.0% | 71.4% |

## Representation collisions

| Representation | Mixed cells | Minimum unavoidable errors |
|---|---:|---:|
| tool_name | 4 | 263 |
| canonical_raw_arguments | 52 | 69 |
| common_effect_fields | 8 | 112 |
| validated_typed_effects | 1 | 77 |

## Claim boundary

This controlled, protocol-separated benchmark establishes representation sufficiency only for the frozen tool, intervention, and authority families. It is not independently authored, does not estimate production prevalence, and does not establish open-world descriptor soundness or production safety.
