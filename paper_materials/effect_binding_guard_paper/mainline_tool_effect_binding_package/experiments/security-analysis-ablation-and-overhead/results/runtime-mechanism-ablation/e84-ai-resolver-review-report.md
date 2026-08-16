# E84 Label-Hidden AI Resolver Artifact Review

- Reviewer type: `ai_artifact_reviewer`
- Rows: `60`
- APPROVE: `2`
- REJECT: `58`
- Runtime result values used: `false`
- Benchmark outcome labels used: `false`

## Decision Categories

- `approved_direct_typed_binding`: `2`
- `broad_history_without_row_selector`: `7`
- `delegated_unstructured_instruction`: `20`
- `derived_value_without_reviewed_computation`: `10`
- `generation_interpretation_or_canonical_binding_required`: `7`
- `message_selection_or_interpretation_required`: `3`
- `nested_value_not_supported_by_scalar_projection`: `3`
- `query_not_executable_in_clean_task_state`: `5`
- `unstructured_text_without_reviewed_parser`: `3`

## Claim Boundary

This is a label-hidden AI artifact review, not an independent human review. Approval means only that the resolver has a direct typed binding justified by the original task and public schema; sandbox execution and projection validity are checked separately by the validator.
