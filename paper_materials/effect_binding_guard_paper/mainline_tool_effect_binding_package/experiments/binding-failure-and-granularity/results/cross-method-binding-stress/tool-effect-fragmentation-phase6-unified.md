# E47 Phase 6 Evidence Consolidation

## Status

- Human audit: `complete`; upgrade gate `True`.
- IPIGuard semantic comparison complete: `True`.
- CaMeL miss decomposition complete: `True`.
- External pipeline: `pending_missing_deepseek_api_key`.

## Answers

- **1_are_defenses_merely_tool_name_classifiers**: No. Official checkpoints and structural methods resist some simple surface shifts, but they remain incomplete on the joint decision.
- **2_simple_surface_shift**: TS-Guard, IPIGuard alias-normalized DAGs, and CaMeL synchronized rewrites resist selected simple shifts.
- **3_effect_sensitive**: Some methods are effect-sensitive, but not jointly safe: local-Qwen semantic mapping reaches effect sensitivity 0.833, while topology-only IPIGuard exposes no effect decision.
- **4_authorization_sensitive**: Authorization sensitivity remains incomplete: local-Qwen reaches 0.375, Safiron is weak in Phase 4, and topology-only IPIGuard is not evaluable.
- **5_resource_binding**: Resource binding is a distinct bottleneck: local-Qwen resource sensitivity is 0.125, despite stronger effect sensitivity.
- **6_utility_preservation**: High refusal is separated from safety; local self-audit and some policies pay substantial utility or denial cost.
- **7_structural_defense**: Structural defenses improve format stability but do not by themselves establish joint effect-resource-authorization reasoning.
- **8_ipiguard_semantic_layer**: The deterministic mapper avoids unsafe pre-allow by abstaining on 0.579 of cases and has effect sensitivity 0.375; local-Qwen raises effect sensitivity to 0.833 and coverage, but unsafe pre-allow rises to 0.333. This supports a missing semantic-decision-layer diagnosis, not a solved guard.
- **9_camel_misses**: Current CaMeL custom-core unsafe misses are concentrated in control-dependency cases (6 misses).
- **10_evidence_scopes**: Results are explicitly separated into baseline, official-checkpoint custom stress, component stress, local/external pipeline evidence, diagnostic, oracle, and upper bound.
- **external_pipeline**: External DeepSeek pipeline status: pending_missing_deepseek_api_key.

## Acceptance Gates

- `human_audit_complete`: `True`
- `human_audit_upgrade_gate`: `True`
- `ipiguard_semantic_comparison_complete`: `True`
- `camel_miss_decomposition_complete`: `True`
- `local_pipeline_floor_effect_resolved_or_downgraded`: `True`
- `external_pipeline_gate_evaluated`: `False`
- `capability_matrix_complete`: `True`
- `real_side_effects_absent`: `True`

## Claim Boundary
- Simple surface robustness is not equivalent to joint effect-resource-authorization reasoning.
- Custom/component stress results are not original-paper benchmark reproductions.
- The sampled human audit is complete and passes its pre-registered gate; the unaudited remainder retains construction-gated status.
- Oracle and upper-bound rows are separated from non-oracle methods.
- No real side effects are executed.
