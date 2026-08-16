# E81 Frozen Common Protocol

- Status: `protocol_frozen_runner_pending`
- Benign cases per row: `26`
- Official attack pairs per row: `169`
- Total cases per row: `195`
- Trusted effect projections: `16`

| Row | Variant | Single change from A1 |
|---|---|---|
| A0 | no_guard | remove_all_runtime_mediation |
| A1 | full_reviewed_effect_contract_guard | full path |
| A2 | tool_call_level_only | remove_field_and_atom_granularity |
| A7 | no_provenance_control_binding | accept_untrusted_or_untyped_resolver_evidence |
| A9 | schema_description_only_registration | replace_counterfactually_validated_registry_with_round0_registry |
| A11 | no_task_authority_envelope | remove_reviewed_task_scoped_authority_bound |
| A12 | no_authorized_read_grounding | disable_typed_resolver_ledger |
| A13 | omitted_fields_permissive | do_not_fail_closed_on_unresolved_security_defaults |
| A15 | no_replan_recovery | replace_replan_feedback_with_terminal_denial |

## Execution Gate

This manifest is not an ablation result. Rows become evidence only after the hybrid reviewed-authority/effect-descriptor runner passes source-hash, row-count, and audit-log checks.

## Claim Boundary

E81 is scoped to the 26 AgentDojo tasks with runtime-ready reviewed authority manifests and all 169 official attack pairs for those tasks. It is not the full 726-case benchmark.
