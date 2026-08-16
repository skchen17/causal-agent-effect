# Protocol-Separated Authority Representation Benchmark

Status: **passed**

## Protocol

The experiment uses 1024 descriptor-blind contexts across four copied-sandbox domains. Policies are explicit ACL, capability, and delegation authority state. Evaluation contexts are generated without labels and mixed cells are discovered only after execution.

## Registration

Executable JSON descriptors matched the independent transition oracle on 384/384 registration contexts and passed 192/192 counterfactual relation checks.

## Direct authorization

| Representation | Coverage | UPA | False denial | Accuracy |
|---|---:|---:|---:|---:|
| tool_name | 0.0% | 0.0% | 0.0% | 0.0% |
| canonical_raw_arguments | 99.6% | 1.1% | 49.2% | 87.2% |
| common_effect_fields | 81.0% | 0.0% | 0.0% | 81.0% |
| validated_typed_effects | 100.0% | 0.0% | 0.0% | 100.0% |

## Representation collisions

| Representation | Mixed cells | Minimum unavoidable errors |
|---|---:|---:|
| tool_name | 4 | 240 |
| canonical_raw_arguments | 51 | 64 |
| common_effect_fields | 9 | 24 |
| validated_typed_effects | 0 | 0 |

## Claim boundary

This controlled, protocol-separated benchmark establishes representation sufficiency only for the frozen tool, intervention, and authority families. It is not independently authored, does not estimate production prevalence, and does not establish open-world descriptor soundness or production safety.
