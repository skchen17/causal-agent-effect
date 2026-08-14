# Representation Mechanism Attribution

## Scope

This finite-domain experiment holds source-observed effects and each authorization predicate fixed, and changes only the representation available to the monitor. It does not execute an agent or infer user authority.

## Policy construction

The deterministic generator produced 76 candidate policies; 76 had both ALLOW and DENY contexts and were retained. Policies exhaustively cover observed resource/target values, effect multiplicity, effect presence, and security-relevant qualifier values. Global effect-family policies are included as null controls.

## Aggregate results

| Dataset | Representation | Policies | Perfectly separable | Fail-closed coverage | Safe abstain | Permissive UPA | Minimum error |
|---|---|---:|---:|---:|---:|---:|---:|
| agentdojo_finite_56 | common_effect_tuple | 36 | 0.722 | 0.714 | 0.380 | 0.229 | 0.143 |
| agentdojo_finite_56 | effect_only | 36 | 0.167 | 0.401 | 0.781 | 0.489 | 0.294 |
| agentdojo_finite_56 | pact_role_provenance | 36 | 0.139 | 0.385 | 0.796 | 0.507 | 0.299 |
| agentdojo_finite_56 | pact_value_role_provenance | 36 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| agentdojo_finite_56 | source_full_effect | 36 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| agentdojo_finite_56 | tool_name | 36 | 0.139 | 0.385 | 0.796 | 0.507 | 0.299 |
| agentdojo_finite_56 | typed_effect_occurrence | 36 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| toolsandbox_heldout_32 | common_effect_tuple | 40 | 0.750 | 0.817 | 0.178 | 0.188 | 0.091 |
| toolsandbox_heldout_32 | effect_only | 40 | 0.500 | 0.699 | 0.293 | 0.309 | 0.151 |
| toolsandbox_heldout_32 | pact_role_provenance | 40 | 0.025 | 0.231 | 0.832 | 0.702 | 0.341 |
| toolsandbox_heldout_32 | pact_value_role_provenance | 40 | 0.475 | 0.591 | 0.414 | 0.403 | 0.110 |
| toolsandbox_heldout_32 | source_full_effect | 40 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| toolsandbox_heldout_32 | tool_name | 40 | 0.025 | 0.231 | 0.832 | 0.702 | 0.341 |
| toolsandbox_heldout_32 | typed_effect_occurrence | 40 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 |

## Interpretation

- A mixed cell is a constructive witness: one fixed policy requires different decisions for contexts that the monitor cannot distinguish.
- Fail-closed coverage reports the fraction of policy-context pairs that can be decided without guessing. Its unsafe-pre-allow count is zero by construction; safe cases in mixed cells become abstentions.
- Permissive UPA reports the opposite end of the tradeoff: mixed cells are allowed, preserving safe utility but admitting unsafe contexts.
- The minimum deterministic error is the best possible cell-wise binary classifier under the representation; it is not a learned-model accuracy estimate.

## Claim boundary

The result attributes finite-domain authorization ambiguity to representation granularity under the tested policy family. It does not establish production safety, authority soundness, complete mediation, or end-to-end AgentDojo utility.
