# All E47 Paper Experiments Manifest

| experiment_name | stage | case_count | row_count | group_count | method_scope_label | label_status | human_audited | paper_section |
|---|---|---|---|---|---|---|---|---|
| AgentDojo tool-surface and held-out-tool stress | Phase 2/3 | 1863 | 14904 | 24 | paper_grade_custom_stress | custom stress labels; Phase 4/6 audited labels support main counterfactual claims | False | Measurement setup and surface-fragmentation baseline |
| ToolSafe / TS-Guard official checkpoint custom stress | Phase 3/4 | 528 | 528 | 24 | official_method_custom_stress | audited custom-stress labels for Phase 4 core | True | Official checkpoint counterfactual results |
| Safiron official checkpoint custom stress | Phase 3/4 | 528 | 528 | 24 | official_method_custom_stress | audited custom-stress labels for Phase 4 core | True | Official checkpoint counterfactual results |
| Phase 4 counterfactual tool-effect lattice | Phase 4 | 528 | 528 | 24 | audited_custom_stress | human-audited after Phase 6 corrected-label update | True | Counterfactual stress design and main results |
| Phase 5 IPIGuard DAG component stress | Phase 5 | 168 | 168 | 24 | original_component_custom_stress | custom stress labels; semantic-layer claims separated | True | Structured defense analysis |
| Phase 5 CaMeL structural policy component stress | Phase 5/6 | 54 | 54 | 6 | original_component_custom_stress | corrected human-audited labels; no_side_effect_tool fixed | True | Structured defense analysis and failure taxonomy |
| Phase 5 IPIGuard / CaMeL original-pipeline local-model feasibility | Phase 5 | 4590 | 4590 |  | original_pipeline_local_model | pipeline feasibility/status, not main safety labels | False | Reproducibility and limitations |
| Phase 6 human audit | Phase 6 | 222 | 278 |  | audited_custom_stress | corrected labels pass upgrade gate | True | Human audit |
| Phase 6 IPIGuard semantic-layer comparison | Phase 6 | 240 | 1200 | 24 | diagnostic | audited custom-stress expected decisions; oracle row separated | True | Semantic-layer analysis |
| Phase 6 CaMeL unsafe miss decomposition | Phase 6 | 54 | 54 | 6 | audited_custom_stress | corrected human-audited labels | True | Structured defense failure taxonomy |
| Non-oracle evidence verifier and oracle / upper-bound comparisons | Phase 3/4/6 | 528 |  | 24 | diagnostic_or_upper_bound | audited custom-stress labels; oracle rows separated | True | Evidence grounding and upper-bound analysis |
