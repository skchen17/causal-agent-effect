# Source Discovery Log

This log records which E47-E57 artifacts were found by the E58 builder. Missing files are treated as material-recovery issues, not as license to invent replacement paths.

| Name | Path | Status | Size bytes |
| --- | --- | --- | --- |
| e48 | analysis/results/e48_tuple_guard_results.json | present | 380893 |
| e50 | analysis/results/e50_hard_guard_robustness_results.json | present | 9604056 |
| e55_strict | analysis/results/e55_precommit_authz_results_strict.json | present | 859580 |
| e55_audit | analysis/results/e55_decision_path_audit.json | present | 12424 |
| e55_leakage | analysis/results/e55_precommit_authz_leakage_audit.json | present | 276 |
| e55_ablation_md | analysis/results/e55_precommit_authz_ablation_table.md | present | 2087 |
| e55_slice_md | analysis/results/e55_precommit_authz_slice_table.md | present | 15482 |
| e55_sanity | analysis/results/e55_sanity_checks.md | present | 586 |
| e56 | analysis/results/e56_final_report.json | present | 7843 |
| e57 | analysis/results/e57_validity_checks_report.json | present | 1848 |
| e57_perturb | analysis/results/e57_resource_perturbation_results.json | present | 27875 |
| e57_reference | analysis/results/e57_reference_authorizer_agreement.json | present | 2086 |
| e57_spot | analysis/results/e57_spot_audit_summary.md | present | 399 |
| e57_packet | analysis/results/e57_spot_audit_packet.jsonl | present | 154053 |
| artifact_inventory | paper_materials/effect_binding_guard_paper/artifact_inventory.json | present | 106139 |
| ndss_main | paper_materials/effect_binding_guard_paper/ndss_candidate/main.tex | present | 494 |
| ndss_pdf | paper_materials/effect_binding_guard_paper/ndss_candidate/main.pdf | present | 121731 |
| ndss_refs | paper_materials/effect_binding_guard_paper/ndss_candidate/references.bib | present | 0 |

## Missing Or Uncertain Artifacts

- No required source artifact in this E58 source list is missing.

## Current NDSS Material Recovery Facts

- `paper_materials/effect_binding_guard_paper/ndss_candidate/main.pdf` exists but is a 2-page compact candidate, not a complete submission draft.
- `paper_materials/effect_binding_guard_paper/ndss_candidate_pre_e56_backup/` is missing and must be treated as a recovery blocker.
