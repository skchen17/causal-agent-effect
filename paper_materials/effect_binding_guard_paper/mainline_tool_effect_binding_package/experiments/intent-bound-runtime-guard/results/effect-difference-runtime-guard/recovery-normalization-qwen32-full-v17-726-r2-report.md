# Recovery-Normalization Qwen3-32B Full-Run Report

- Status: `failed`
- Official rows: `726/726`
- ASR: `11/629 = 0.017`
- Benign utility: `46/97 = 0.474`
- Attack utility: `275/629 = 0.437`

## Plan Quality

- Schema valid: `654/711`
- Validation passed: `577/711`
- Plan accepted: `577/711`
- Rejected unique tasks: `17`

## Verification Gates


## Four-Layer Authorization Counts (precommit checks)

- initial_decision_counts: `{"ALLOW": 1907, "NEEDS_REPLAN": 754}`
- effective_decision_counts: `{"ALLOW": 2172, "DENY": 83, "NEEDS_REPLAN": 406}`
- strict_authorization_satisfied_counts: `{"False": 748, "True": 1913}`
- diagnostic_uncertainty_override_counts: `{"False": 2234, "True": 427}`
- execution_attempted_counts: `{"False": 489, "True": 2172}`

- protocol_manifest_matches_runtime: `True`
- runner_completed: `True`
- official_rows_726: `True`
- suite_counts_exact: `True`
- metric_denominators_exact: `True`
- no_import_errors: `True`
- command_protocol_clean: `False`
- all_official_audit_rows_match_runtime: `True`
- plan_diagnostics_complete: `True`
- plan_diagnostics_consistent: `True`
- rejected_initial_plans_fail_closed: `True`
- authorization_checks_deterministic: `True`
- revision_llm_never_directly_authorizes: `True`
- four_layer_decision_fields_present: `True`
- executed_only_when_effective_allow: `True`
- no_allow_with_expansion_findings: `True`

## Claim Boundary

This run separates plan-schema parsing from semantic authority validation. A semantically rejected plan remains a measured model outcome and causes fail-closed handling for side-effectful calls; it is not treated as a harness failure. Exact authorization remains deterministic after bounded model-proposed revision. Results apply to AgentDojo v1.1.2 sandbox execution and do not imply production safety.
