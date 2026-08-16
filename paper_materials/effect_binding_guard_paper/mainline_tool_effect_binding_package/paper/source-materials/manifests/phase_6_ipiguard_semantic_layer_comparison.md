# Phase 6 IPIGuard semantic-layer comparison

- **experiment_name**: `Phase 6 IPIGuard semantic-layer comparison`
- **stage**: `Phase 6`
- **source_scripts**: `["src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase6.py", "src/experiments/tool_effect_fragmentation/phase6_semantic_worker.py"]`
- **source_data**: `["data/tool_effect_fragmentation/ipiguard_semantic_core_phase6.jsonl"]`
- **output_artifacts**: `["analysis/results/tool_effect_fragmentation_ipiguard_semantic_phase6.json"]`
- **case_count**: `240`
- **row_count**: `1200`
- **group_count**: `24`
- **method_scope_label**: `diagnostic`
- **evidence_type**: `semantic-layer diagnostic over IPIGuard DAG inputs`
- **label_status**: `audited custom-stress expected decisions; oracle row separated`
- **human_audited**: `True`
- **known_limitations**: `Added mapper is not original IPIGuard and not a deployable guard.`
- **paper_section**: `Semantic-layer analysis`
- **claim_boundary**: `Supports missing semantic layer diagnosis, not solved safety.`
