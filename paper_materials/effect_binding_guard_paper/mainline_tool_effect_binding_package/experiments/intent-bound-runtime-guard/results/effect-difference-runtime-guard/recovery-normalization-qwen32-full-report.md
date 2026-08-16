# Recovery-Normalization Qwen3-32B Full-Run Report

- Status: `failed`
- Official rows: `726/726`
- ASR: `2/629 = 0.003`
- Benign utility: `32/97 = 0.330`
- Attack utility: `209/629 = 0.332`

## Plan Quality

- Schema valid: `663/719`
- Validation passed: `594/719`
- Plan accepted: `594/719`
- Rejected unique tasks: `17`

## Verification Gates

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

## Claim Boundary

This run separates plan-schema parsing from semantic authority validation. A semantically rejected plan remains a measured model outcome and causes fail-closed handling for side-effectful calls; it is not treated as a harness failure. Exact authorization remains deterministic after bounded model-proposed revision. Results apply to AgentDojo v1.1.2 sandbox execution and do not imply production safety.
