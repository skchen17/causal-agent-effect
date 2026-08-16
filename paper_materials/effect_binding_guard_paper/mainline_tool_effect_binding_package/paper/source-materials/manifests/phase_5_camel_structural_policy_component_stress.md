# Phase 5 CaMeL structural policy component stress

- **experiment_name**: `Phase 5 CaMeL structural policy component stress`
- **stage**: `Phase 5/6`
- **source_scripts**: `["src/experiments/tool_effect_fragmentation/phase5_camel.py", "src/experiments/tool_effect_fragmentation/phase5_camel_component_worker.py"]`
- **source_data**: `["data/tool_effect_fragmentation/camel_structural_counterfactual_phase5.jsonl"]`
- **output_artifacts**: `["analysis/results/tool_effect_fragmentation_camel_phase5.json", "analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json"]`
- **case_count**: `54`
- **row_count**: `54`
- **group_count**: `6`
- **method_scope_label**: `original_component_custom_stress`
- **evidence_type**: `generic SecurityPolicyEngine component`
- **label_status**: `corrected human-audited labels; no_side_effect_tool fixed`
- **human_audited**: `True`
- **known_limitations**: `Component stress, not full CaMeL generated-code benchmark.`
- **paper_section**: `Structured defense analysis and failure taxonomy`
- **claim_boundary**: `Misses are custom structural stress findings, not general CaMeL failure claims.`
