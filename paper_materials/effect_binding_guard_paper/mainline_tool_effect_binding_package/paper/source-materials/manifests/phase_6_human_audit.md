# Phase 6 human audit

- **experiment_name**: `Phase 6 human audit`
- **stage**: `Phase 6`
- **source_scripts**: `["src/experiments/tool_effect_fragmentation/phase6_core.py"]`
- **source_data**: `["data/tool_effect_fragmentation/human_audit_packet_phase6.jsonl", "data/tool_effect_fragmentation/human_audit_secondary_phase6.jsonl"]`
- **output_artifacts**: `["analysis/results/tool_effect_fragmentation_human_audit_phase6.json"]`
- **case_count**: `222`
- **row_count**: `278`
- **group_count**: ``
- **method_scope_label**: `audited_custom_stress`
- **evidence_type**: `primary and secondary human audit`
- **label_status**: `corrected labels pass upgrade gate`
- **human_audited**: `True`
- **known_limitations**: `Audit validates custom-stress labels, not external deployment validity.`
- **paper_section**: `Human audit`
- **claim_boundary**: `Model-generated labels alone do not satisfy this gate.`
