# Recovery-Normalization Qwen3-32B Full-Run Report

- Status: `failed`
- Official rows: `393/726`
- ASR: `7/629 = 0.021`
- Benign utility: `29/97 = 0.475`
- Attack utility: `157/629 = 0.473`

## Plan Quality

- Schema valid: `374/393`
- Validation passed: `340/393`
- Plan accepted: `340/393`
- Rejected unique tasks: `7`

## Verification Gates


## Four-Layer Authorization Counts (precommit checks)

- initial_decision_counts: `{"ALLOW": 736, "NEEDS_REPLAN": 436}`
- effective_decision_counts: `{"ALLOW": 941, "DENY": 44, "NEEDS_REPLAN": 187}`
- strict_authorization_satisfied_counts: `{"False": 430, "True": 742}`
- diagnostic_uncertainty_override_counts: `{"False": 858, "True": 314}`
- execution_attempted_counts: `{"False": 231, "True": 941}`

- protocol_manifest_matches_runtime: `True`
- runner_completed: `False`
- official_rows_726: `False`
- suite_counts_exact: `False`
- metric_denominators_exact: `False`
- no_import_errors: `False`
- command_protocol_clean: `False`
- all_official_audit_rows_match_runtime: `True`
- plan_diagnostics_complete: `True`
- plan_diagnostics_consistent: `True`
- rejected_initial_plans_fail_closed: `True`
- authorization_checks_deterministic: `True`
- revision_llm_never_directly_authorizes: `True`
- four_layer_decision_fields_present: `True`
- executed_only_when_effective_allow: `True`

## Claim Boundary

This run separates plan-schema parsing from semantic authority validation. A semantically rejected plan remains a measured model outcome and causes fail-closed handling for side-effectful calls; it is not treated as a harness failure. Exact authorization remains deterministic after bounded model-proposed revision. Results apply to AgentDojo v1.1.2 sandbox execution and do not imply production safety.
