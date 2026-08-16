# Experiments

The empirical story is organized by research question rather than chronology.

RQ1 asks whether weak surface baselines overestimate safety. The relevant artifacts are `tables/counterfactual_lattice_summary.md`, `tables/main_capability_matrix.md`, and `results/canonical/tool_effect_fragmentation_agentdojo_phase3.md`.

RQ2 and RQ3 ask whether official checkpoint guardrails are merely tool-name classifiers and whether they satisfy tool-effect invariance. The relevant artifacts are `tables/official_checkpoint_summary.md`, `results/canonical/tool_effect_fragmentation_counterfactual_phase4_toolsafe.md`, and `results/canonical/tool_effect_fragmentation_counterfactual_phase4_safiron.md`.

RQ4 asks whether structural defenses solve fragmentation, split into graph topology semantic incompleteness and CaMeL control-dependency misses. The relevant artifacts are `tables/structured_defense_summary.md`, `tables/appendix_ipiguard_consistency_by_variant.md`, `results/canonical/tool_effect_fragmentation_ipiguard_semantic_phase6.md`, and `results/canonical/tool_effect_fragmentation_camel_miss_decomposition_phase6.md`.

RQ5 asks whether semantic or evidence grounding helps. The relevant artifacts are `results/canonical/tool_effect_fragmentation_ipiguard_semantic_phase6.md` and `manifests/non_oracle_evidence_verifier_and_oracle_upper_bound_comparisons.md`.

RQ6 asks whether labels are reliable. The relevant artifacts are `audit/tool_effect_fragmentation_human_audit_phase6.md` and `tables/human_audit_summary.md`.

No new experiments are run for this draft.
