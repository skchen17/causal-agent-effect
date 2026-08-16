# Phase 5 IPIGuard DAG component stress

- **experiment_name**: `Phase 5 IPIGuard DAG component stress`
- **stage**: `Phase 5`
- **source_scripts**: `["src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase5.py", "src/experiments/tool_effect_fragmentation/phase5_ipiguard_component_worker.py"]`
- **source_data**: `["data/tool_effect_fragmentation/ipiguard_counterfactual_phase5.jsonl"]`
- **output_artifacts**: `["analysis/results/tool_effect_fragmentation_ipiguard_phase5.json", "analysis/results/tool_effect_fragmentation_ipiguard_component_phase5.jsonl"]`
- **case_count**: `168`
- **row_count**: `168`
- **group_count**: `24`
- **method_scope_label**: `original_component_custom_stress`
- **evidence_type**: `released DAG prompt/parser component`
- **label_status**: `custom stress labels; semantic-layer claims separated`
- **human_audited**: `True`
- **known_limitations**: `DAG topology has no realized-effect decision interface.`
- **paper_section**: `Structured defense analysis`
- **claim_boundary**: `Topology stability is not equivalent to effect-level safety.`
