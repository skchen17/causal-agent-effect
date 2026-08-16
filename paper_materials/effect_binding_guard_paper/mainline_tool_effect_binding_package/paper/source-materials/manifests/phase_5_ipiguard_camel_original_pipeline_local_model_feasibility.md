# Phase 5 IPIGuard / CaMeL original-pipeline local-model feasibility

- **experiment_name**: `Phase 5 IPIGuard / CaMeL original-pipeline local-model feasibility`
- **stage**: `Phase 5`
- **source_scripts**: `["src/experiments/tool_effect_fragmentation/phase5_pipeline_worker.py", "src/experiments/tool_effect_fragmentation/phase5_original_runner.py"]`
- **source_data**: `["data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl", "data/tool_effect_fragmentation/camel_phase5_traces.jsonl"]`
- **output_artifacts**: `["analysis/results/tool_effect_fragmentation_phase5_unified.json"]`
- **case_count**: `4590`
- **row_count**: `4590`
- **group_count**: ``
- **method_scope_label**: `original_pipeline_local_model`
- **evidence_type**: `full local-model pipeline feasibility`
- **label_status**: `pipeline feasibility/status, not main safety labels`
- **human_audited**: `False`
- **known_limitations**: `Local GGUF model has low no-defense attack success and low utility.`
- **paper_section**: `Reproducibility and limitations`
- **claim_boundary**: `Do not use as defense-effectiveness evidence.`
