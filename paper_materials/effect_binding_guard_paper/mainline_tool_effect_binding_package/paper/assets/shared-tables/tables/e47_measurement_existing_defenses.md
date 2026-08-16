# E47 Measurement Existing Defenses

| method | claim_scope | surface_invariance | effect_sensitivity | authorization_sensitivity | resource_awareness | unsafe_pre_allow | safe_false_deny | coverage | evidence_grounding |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tool_name_rule_proxy | baseline | 1 | 0 | 0 | 0 | 0.291667 | 0.708333 |  | False |
| static_text_rule_proxy | baseline | 0.984375 | 0 | 0.902778 | 1 | 0.0795455 | 0.0795455 |  | False |
| plan_text_rule_proxy | baseline | 0.984375 | 0 | 0.902778 | 1 | 0.0795455 | 0.0795455 |  | False |
| trajectory_text_rule_proxy | baseline | 0.984375 | 0 | 0.902778 | 1 | 0.0795455 | 0.0795455 |  | False |
| local_qwen_self_audit | baseline | 0.864583 | 0.666667 | 0.564815 | 0.291667 | 0.00378788 | 0.481061 |  | False |
| ts_guard_official_counterfactual_stress | original_method_custom_stress | 0.882812 | 0.625 | 0.763889 | 0.833333 | 0.159091 | 0.0871212 |  | False |
| safiron_official_counterfactual_stress | original_method_custom_stress | 0.669271 | 1 | 0.087963 | 0.166667 | 0.545455 | 0.371212 |  | False |
| non_oracle_saved_evidence_verifier | baseline | 0.25 | 0.0833333 | 0.00925926 | 1 | 0 | 0.0606061 |  | True |
| effect_resource_oracle | upper_bound | 1 | 1 | 1 | 1 | 0 | 0 |  | True |
| execution_evidence_upper_bound | upper_bound | 1 | 1 | 1 | 1 | 0 | 0 |  | True |
| ipiguard_topology_only | original_component_custom_stress | 1 | 0 |  |  |  |  |  | False |
| deterministic_effect_resource_mapper | diagnostic | 0.708333 | 0.375 | 0.375 | 0.375 | 0 | 0.0595238 |  | False |
| ipiguard_normalized_content | diagnostic | 0.708333 | 0.375 | 0.375 | 0.375 | 0 | 0.0595238 |  | False |
| local_qwen_effect_resource_mapper | diagnostic | 0.991667 | 0.833333 | 0.375 | 0.125 | 0.333333 | 0.0178571 |  | False |
| oracle_effect_resource_mapper | upper_bound | 1 | 1 | 1 | 1 | 0 | 0 |  | False |
| camel_structural_policy | original_component_custom_stress | 1 |  |  |  | 0.25 | 0 |  | True |
