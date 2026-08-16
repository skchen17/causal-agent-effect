# Main Capability Matrix

| method | surface_invariance | effect_sensitivity | authorization_sensitivity | resource_awareness | unsafe_pre_allow | safe_false_deny | abstain_rate | utility_preservation | evidence_grounding | claim_scope | audit_status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tool_name_rule_proxy | 1 | 0 | 0 | 0 | 0.291667 | 0.708333 | 0 | 0.291667 | False | baseline | audited_custom_stress |
| static_text_rule_proxy | 0.984375 | 0 | 0.902778 | 1 | 0.0795455 | 0.0795455 | 0 | 0.920455 | False | baseline | audited_custom_stress |
| plan_text_rule_proxy | 0.984375 | 0 | 0.902778 | 1 | 0.0795455 | 0.0795455 | 0 | 0.920455 | False | baseline | audited_custom_stress |
| trajectory_text_rule_proxy | 0.984375 | 0 | 0.902778 | 1 | 0.0795455 | 0.0795455 | 0 | 0.920455 | False | baseline | audited_custom_stress |
| local_qwen_self_audit | 0.864583 | 0.666667 | 0.564815 | 0.291667 | 0.00378788 | 0.481061 | 0.00189394 | 0.518939 | False | baseline | audited_custom_stress |
| ts_guard_official_counterfactual_stress | 0.882812 | 0.625 | 0.763889 | 0.833333 | 0.159091 | 0.0871212 | 0 | 0.912879 | False | original_method_custom_stress | audited_custom_stress |
| safiron_official_counterfactual_stress | 0.669271 | 1 | 0.087963 | 0.166667 | 0.545455 | 0.371212 | 0 | 0.628788 | False | original_method_custom_stress | audited_custom_stress |
| non_oracle_saved_evidence_verifier | 0.25 | 0.0833333 | 0.00925926 | 1 | 0 | 0.0606061 | 0.75 | 0.939394 | True | baseline | audited_custom_stress |
| effect_resource_oracle | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | True | upper_bound | audited_custom_stress |
| execution_evidence_upper_bound | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | True | upper_bound | audited_custom_stress |
| ipiguard_topology_only | 1 | 0 |  |  |  |  |  |  | False | original_component_custom_stress | audited_custom_stress |
| deterministic_effect_resource_mapper | 0.708333 | 0.375 | 0.375 | 0.375 | 0 | 0.0595238 | 0.579167 |  | False | diagnostic | audited_custom_stress |
| ipiguard_normalized_content | 0.708333 | 0.375 | 0.375 | 0.375 | 0 | 0.0595238 | 0.579167 |  | False | diagnostic | audited_custom_stress |
| local_qwen_effect_resource_mapper | 0.991667 | 0.833333 | 0.375 | 0.125 | 0.333333 | 0.0178571 | 0.0625 |  | False | diagnostic | audited_custom_stress |
| oracle_effect_resource_mapper | 1 | 1 | 1 | 1 | 0 | 0 | 0 |  | False | upper_bound | audited_custom_stress |
| camel_structural_policy | 1 |  |  |  | 0.25 | 0 | 0 | 1 | True | original_component_custom_stress | audited_custom_stress |
