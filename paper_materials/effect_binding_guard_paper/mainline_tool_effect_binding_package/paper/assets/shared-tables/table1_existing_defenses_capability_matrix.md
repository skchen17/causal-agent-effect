# Existing Defenses Capability Matrix

Source: `paper_package_tool_effect_invariance/tables/main_capability_matrix.csv`

| method | surface_invariance | effect_sensitivity | authorization_sensitivity | resource_awareness | unsafe_pre_allow |
| --- | --- | --- | --- | --- | --- |
| tool_name_rule_proxy | 1 | 0 | 0 | 0 | 0.291667 |
| static_text_rule_proxy | 0.984375 | 0 | 0.902778 | 1 | 0.0795455 |
| plan_text_rule_proxy | 0.984375 | 0 | 0.902778 | 1 | 0.0795455 |
| trajectory_text_rule_proxy | 0.984375 | 0 | 0.902778 | 1 | 0.0795455 |
| local_qwen_self_audit | 0.864583 | 0.666667 | 0.564815 | 0.291667 | 0.00378788 |
| ts_guard_official_counterfactual_stress | 0.882812 | 0.625 | 0.763889 | 0.833333 | 0.159091 |
| safiron_official_counterfactual_stress | 0.669271 | 1 | 0.087963 | 0.166667 | 0.545455 |
| non_oracle_saved_evidence_verifier | 0.25 | 0.0833333 | 0.00925926 | 1 | 0 |
| effect_resource_oracle | 1 | 1 | 1 | 1 | 0 |
| execution_evidence_upper_bound | 1 | 1 | 1 | 1 | 0 |
| ipiguard_topology_only | 1 | 0 |  |  |  |
| deterministic_effect_resource_mapper | 0.708333 | 0.375 | 0.375 | 0.375 | 0 |
| ipiguard_normalized_content | 0.708333 | 0.375 | 0.375 | 0.375 | 0 |
| local_qwen_effect_resource_mapper | 0.991667 | 0.833333 | 0.375 | 0.125 | 0.333333 |
| oracle_effect_resource_mapper | 1 | 1 | 1 | 1 | 0 |
| camel_structural_policy | 1 |  |  |  | 0.25 |
