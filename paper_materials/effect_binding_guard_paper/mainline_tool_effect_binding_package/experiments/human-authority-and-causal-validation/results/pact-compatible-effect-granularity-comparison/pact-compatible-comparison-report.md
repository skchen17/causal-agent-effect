# PACT-Compatible Argument Representation vs. Effect Occurrences

## Scope

This deterministic audit compares a public PACT-L2-inspired argument-role/provenance view with the paper's typed effect-occurrence view. It is not a reproduction of PACT's automatic role inference, cross-step provenance inference, policy, or AgentDojo evaluation.

The maximal argument view includes the tool name and every concrete argument name, value, reviewed semantic role, and trusted origin. This favors the argument representation. It still omits pre-state and the tool implementation's one-to-many effect expansion, because those objects are not call arguments.

## Results

| Dataset | Representation | Cells | Collision cells | Separating pairs | Overpartition pairs | Complete | Exact |
|---|---|---:|---:|---:|---:|:---:|:---:|
| agentdojo_finite_56 | tool_name | 5 | 5 | 564 | 0 | no | no |
| agentdojo_finite_56 | pact_role_provenance | 5 | 5 | 564 | 0 | no | no |
| agentdojo_finite_56 | pact_value_role_provenance | 56 | 0 | 0 | 0 | yes | yes |
| agentdojo_finite_56 | typed_effect_occurrence | 56 | 0 | 0 | 0 | yes | yes |
| agentdojo_finite_56 | source_full_effect | 56 | 0 | 0 | 0 | yes | yes |
| toolsandbox_heldout_32 | tool_name | 5 | 5 | 88 | 16 | no | no |
| toolsandbox_heldout_32 | pact_role_provenance | 6 | 6 | 72 | 16 | no | no |
| toolsandbox_heldout_32 | pact_value_role_provenance | 22 | 4 | 13 | 23 | no | no |
| toolsandbox_heldout_32 | typed_effect_occurrence | 25 | 0 | 0 | 0 | yes | yes |
| toolsandbox_heldout_32 | source_full_effect | 25 | 0 | 0 | 0 | yes | yes |

## Interpretation

On the fresh-state AgentDojo finite domain, the maximal argument view can preserve all observed distinctions. This domain alone does not separate argument values from effect occurrences.

On the pre-registered ToolSandbox domain, identical tool names and argument values can realize different effects under different pre-states, including no-op and compound setting changes. The maximal argument view therefore retains authorization collisions, while the typed effect-occurrence view matches the source-effect partition.

This is a finite representation comparison, not a claim that the full PACT system is unsafe or that effect occurrences dominate every argument-provenance policy.
