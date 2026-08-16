# Appendix

Appendix A is now titled "Reproducibility and Artifact Map." Artifact paths have been moved out of main-table captions and into this appendix.

Recommended appendix contents:

- Package validation command: `python scripts/build_tool_effect_paper_package.py --output . --validate-only`.
- Main capability matrix: `tables/main_capability_matrix.md`.
- Counterfactual lattice metrics: `tables/counterfactual_lattice_summary.md`.
- Official checkpoint metrics: `tables/official_checkpoint_summary.md`.
- Structured-defense metrics: `tables/structured_defense_summary.md`.
- Human audit: `audit/tool_effect_fragmentation_human_audit_phase6.md` and `tables/human_audit_summary.md`.
- Claim scope: `tables/claim_scope_table.md` and `writing/claim_boundary.md`.
- Failure examples and appendix tables.
- Appendix-only figure specifications clearly marked as draft specs.

The compact capability matrix is included in the appendix with scope labels and evidence/coverage fields. `N/I` means a realized-effect decision interface is not present for the corresponding metric.

Important stale-artifact note: `results/canonical/tool_effect_fragmentation_counterfactual_phase4.md` and older copied summaries may still say the human audit was pending. The finalized package README, `results/canonical/tool_effect_fragmentation_phase6_unified.md`, `audit/tool_effect_fragmentation_human_audit_phase6.md`, and `tables/human_audit_summary.md` mark the audit complete with upgrade gate true.
