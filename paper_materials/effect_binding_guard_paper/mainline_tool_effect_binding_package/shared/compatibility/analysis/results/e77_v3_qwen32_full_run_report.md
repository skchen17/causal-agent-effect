# E77-v3 Qwen3-32B Full-Run Report

- Status: `failed`
- Official rows: `726/726`
- ASR: `1/629 = 0.002`
- Benign utility: `29/97 = 0.299`
- Attack utility: `196/629 = 0.312`

## Verification Gates

- protocol_manifest_is_v3: `True`
- runner_completed: `True`
- official_rows_726: `True`
- suite_counts_exact: `True`
- metric_denominators_exact: `True`
- no_import_errors: `True`
- command_protocol_clean: `True`
- all_official_audit_rows_are_v3: `True`
- all_plans_parse_valid: `False`
- authorization_checks_deterministic: `True`
- revision_llm_never_directly_authorizes: `True`

## Claim Boundary

E77-v3 uses a local model to propose a task-level authority plan and bounded revisions. Every exact call is totalized and deterministically checked after any revision. E84 reviewed manifests are not used in this main run. Results apply to AgentDojo v1.1.2 sandbox execution and do not imply production safety.
