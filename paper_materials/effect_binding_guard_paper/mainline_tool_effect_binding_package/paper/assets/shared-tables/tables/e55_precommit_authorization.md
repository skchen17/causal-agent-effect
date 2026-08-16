# E55 Precommit Authorization

| method | unsafe_pre_allow | safe_false_deny | coverage | abstain | decision_accuracy | atom_expansion_exact_match | claim_scope |
| --- | --- | --- | --- | --- | --- | --- | --- |
| existing_hard_effect_binding_guard | 0.037037 | 0 | 0.2 | 0.8 | 0.1 | 0 | controlled local mock pre-commit mediation |
| authz_aware_effect_binding_guard | 0 | 0 | 0.92 | 0.08 | 1 | 1 | controlled local mock pre-commit mediation |
| authz_aware_no_alias_resolution | 0 | 0.210526 | 0.92 | 0.08 | 0.92 | 1 | controlled local mock pre-commit mediation |
| authz_aware_no_multi_resource_expansion | 0.333333 | 0 | 0.92 | 0.08 | 0.82 | 0.3 | controlled local mock pre-commit mediation |
| authz_aware_no_operation_mode | 0.148148 | 0 | 0.92 | 0.08 | 0.92 | 1 | controlled local mock pre-commit mediation |
| authz_aware_no_provenance_overlay | 0.148148 | 0 | 0.94 | 0.06 | 0.9 | 1 | controlled local mock pre-commit mediation |
| authz_aware_no_evidence_fallback | 0 | 0 | 0.88 | 0.12 | 0.96 | 0.96 | controlled local mock pre-commit mediation |
