# Method Definition

## Counterfactual Stress-Test Framework

The evaluation constructs paired cases that hold one semantic axis fixed while changing tool surface, resource authorization, operation mode, provenance/control source, or evidence availability. Metrics report whether decisions stay invariant when they should and change when safety-relevant axes change.

## Reference Hard Effect-Binding Guard

The hard guard infers effect/resource/authorization/provenance tuples from non-oracle views, checks multi-view disagreement, uses selective evidence fallback when available, overlays hard provenance rules, and outputs `ALLOW`, `DENY`, or `ABSTAIN`.

## Authorization-Aware Local Pre-Commit Prototype

The E55 prototype expands tool calls into effect-resource-operation atoms, canonicalizes resources and aliases, checks each atom against a typed authorization context, applies provenance overlay, and abstains when evidence/canonicalization is insufficient. This is local mock contract evidence, not a production permission system.
