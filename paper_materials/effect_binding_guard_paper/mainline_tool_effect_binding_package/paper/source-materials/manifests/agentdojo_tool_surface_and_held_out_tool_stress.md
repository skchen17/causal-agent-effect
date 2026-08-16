# AgentDojo tool-surface and held-out-tool stress

- **experiment_name**: `AgentDojo tool-surface and held-out-tool stress`
- **stage**: `Phase 2/3`
- **source_scripts**: `["src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase2.py", "src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase3.py"]`
- **source_data**: `["data/tool_effect_fragmentation/phase3_stress_cases.jsonl", "data/tool_effect_fragmentation/phase3_predictions.jsonl"]`
- **output_artifacts**: `["analysis/results/tool_effect_fragmentation_agentdojo_phase3.json", "analysis/results/tool_effect_fragmentation_phase3_unified.json"]`
- **case_count**: `1863`
- **row_count**: `14904`
- **group_count**: `24`
- **method_scope_label**: `paper_grade_custom_stress`
- **evidence_type**: `saved AgentDojo/custom stress`
- **label_status**: `custom stress labels; Phase 4/6 audited labels support main counterfactual claims`
- **human_audited**: `False`
- **known_limitations**: `AgentDojo local stress anchor; not a universal benchmark of deployed systems.`
- **paper_section**: `Measurement setup and surface-fragmentation baseline`
- **claim_boundary**: `Supports tool-surface fragility diagnostics, not original-method failure claims.`
