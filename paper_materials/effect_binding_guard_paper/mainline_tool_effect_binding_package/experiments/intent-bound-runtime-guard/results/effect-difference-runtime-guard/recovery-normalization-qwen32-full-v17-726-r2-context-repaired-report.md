# Recovery-Normalization Qwen3-32B Full-Run Report

- Status: `passed`
- Official rows: `726/726`
- ASR: `11/629 = 0.017`
- Benign utility: `46/97 = 0.474`
- Attack utility: `272/629 = 0.432`

## Plan Quality

- Schema valid: `667/724`
- Validation passed: `590/724`
- Plan accepted: `590/724`
- Rejected unique tasks: `17`

## Verification Gates


## Four-Layer Authorization Counts (precommit checks)

- initial_decision_counts: `{"ALLOW": 1952, "NEEDS_REPLAN": 755}`
- effective_decision_counts: `{"ALLOW": 2217, "DENY": 83, "NEEDS_REPLAN": 407}`
- strict_authorization_satisfied_counts: `{"False": 749, "True": 1958}`
- diagnostic_uncertainty_override_counts: `{"False": 2252, "True": 455}`
- execution_attempted_counts: `{"False": 490, "True": 2217}`

- protocol_manifest_matches_runtime: `True`
- runner_completed: `True`
- official_rows_726: `True`
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
- four_layer_decision_fields_present: `True`
- executed_only_when_effective_allow: `True`
- no_allow_with_expansion_findings: `True`

## Claim Boundary

The 726-row overlay retains the base-run rows for all cases except the enumerated truncated ones, which are replaced by targeted reruns under enlarged context windows. Checkpoint, decoding temperature, output caps, descriptors, runtime logic, catalogs and native AgentDojo evaluators are unchanged; only the available context capacity differs for repaired rows. The repair covers ONLY the enumerated cases (claim boundary); base-run artifacts remain immutable.
