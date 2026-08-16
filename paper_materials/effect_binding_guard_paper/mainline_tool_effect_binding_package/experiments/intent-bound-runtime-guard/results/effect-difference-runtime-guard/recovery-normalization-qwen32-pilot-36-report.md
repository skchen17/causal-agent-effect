# Recovery-Normalization Qwen3-32B Fixed Pilot Report

- Status: `passed`
- Fixed pilot rows: `36/36`
- ASR: `0/24 = 0.000`
- Benign utility: `3/12 = 0.250`
- Attack utility: `9/24 = 0.375`

## Plan Quality

- Schema valid: `34/34`
- Validation passed: `33/34`
- Plan accepted: `33/34`
- Rejected unique tasks: `1`

## Verification Gates

- protocol_manifest_matches_runtime: `True`
- runner_completed: `True`
- fixed_pilot_rows_36: `True`
- suite_counts_exact: `True`
- metric_denominators_exact: `True`
- no_import_errors: `True`
- command_protocol_clean: `True`
- all_official_audit_rows_match_runtime: `True`
- plan_diagnostics_complete: `True`
- plan_diagnostics_consistent: `True`
- rejected_initial_plans_fail_closed: `True`
- authorization_checks_deterministic: `True`
- revision_llm_never_directly_authorizes: `True`

## Claim Boundary

This fixed 36-case pilot separates plan-schema parsing from semantic authority validation. A semantically rejected plan remains a measured model outcome and causes fail-closed handling for side-effectful calls; it is not treated as a harness failure. Exact authorization remains deterministic after bounded model-proposed revision. The fixed prefix selection is a development signal, not a replacement for the official 726-case run. Results apply to AgentDojo v1.1.2 sandbox execution and do not imply production safety.
