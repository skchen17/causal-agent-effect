# E47 Phase 5 IPIGuard and CaMeL Evaluation

## Status

- IPIGuard counterfactual core: `168` cases.
- CaMeL structural core: `54` cases.
- IPIGuard original-pipeline trace rows: `1452`.
- CaMeL original-pipeline trace rows: `3138`.

## CaMeL Original Policy Component

- Rows: `54`
- Overall accuracy: `0.8889 [0.7781, 0.9481]`
- Unsafe blocked: `0.7500 [0.5510, 0.8800]`
- Safe false denial: `0.0000 [0.0000, 0.1135]`
- Structural invariance: `1.0000 [1.0000, 1.0000]`

## Original Pipeline Local-Model Evaluation

### ipiguard

- `agentdojo_no_defense_local_model`: rows `726`, runtime errors `0.0000 [0.0000, 0.0053]`, policy denials `0.0000 [0.0000, 0.0053]`, benign utility `0.0412 [0.0162, 0.1013]`, attack utility `0.0572 [0.0416, 0.0782]`, attack success `0.0000 [0.0000, 0.0061]`, DAG valid `0.0000 [0.0000, 0.0053]`.
- `original_ipiguard_construct_traverse_pipeline`: rows `726`, runtime errors `0.0331 [0.0223, 0.0487]`, policy denials `0.0000 [0.0000, 0.0053]`, benign utility `0.2316 [0.1582, 0.3258]`, attack utility `0.2405 [0.2082, 0.2761]`, attack success `0.0066 [0.0026, 0.0168]`, DAG valid `1.0000 [0.9946, 1.0000]`.

### camel

- `original_camel_generator_interpreter_no_policy`: rows `1046`, runtime errors `0.0019 [0.0005, 0.0069]`, policy denials `0.0000 [0.0000, 0.0037]`, benign utility `0.2371 [0.1635, 0.3307]`, attack utility `0.2914 [0.2634, 0.3212]`, attack success `0.0011 [0.0002, 0.0060]`, DAG valid `0.0000 [0.0000, 0.0037]`.
- `original_camel_generator_interpreter_inline_policy_normal`: rows `1046`, runtime errors `0.0000 [0.0000, 0.0037]`, policy denials `0.0822 [0.0671, 0.1004]`, benign utility `0.2268 [0.1548, 0.3196]`, attack utility `0.2276 [0.2021, 0.2554]`, attack success `0.0011 [0.0002, 0.0059]`, DAG valid `0.0000 [0.0000, 0.0037]`.
- `original_camel_generator_interpreter_inline_policy_strict`: rows `1046`, runtime errors `0.0048 [0.0020, 0.0111]`, policy denials `0.0612 [0.0482, 0.0774]`, benign utility `0.2211 [0.1494, 0.3144]`, attack utility `0.2505 [0.2240, 0.2791]`, attack success `0.0011 [0.0002, 0.0060]`, DAG valid `0.0000 [0.0000, 0.0037]`.

## IPIGuard Original DAG Component Stress

- Rows: `168`
- Parse-valid: `1.0000 [0.9776, 1.0000]`
- Normalized-effect prompt leakage excluding explicit effect graph: `0.0000 [0.0000, 0.0260]`
- Planned tool-surface coverage: `1.0000 [0.9776, 1.0000]`
- Planned effect coverage: `not_identifiable_from_original_dag_output`
- Same-effect topology consistency: `1.0000 [1.0000, 1.0000]`
- Same-effect exact-DAG consistency: `0.3833 [0.3583, 0.4000]`
- Same-effect normalized-DAG consistency: `0.7500 [0.7000, 0.8000]`
- Tool-surface full-DAG change rate: `0.6167 [0.6000, 0.6417]`
- Same-tool different-effect topology sensitivity: `0.0000 [0.0000, 0.0000]`
- Same-tool different-effect content sensitivity: `1.0000 [1.0000, 1.0000]`

### IPIGuard Consistency by Variant

- `arg_schema_change`: topology `1.0000 [1.0000, 1.0000]`, exact DAG `0.0000 [0.0000, 0.0000]`, normalized DAG `0.7083 [0.5000, 0.8750]`.
- `effect_resource_graph`: topology `1.0000 [1.0000, 1.0000]`, exact DAG `0.9167 [0.7917, 1.0000]`, normalized DAG `0.9167 [0.7917, 1.0000]`.
- `graph_node_format`: topology `1.0000 [1.0000, 1.0000]`, exact DAG `1.0000 [1.0000, 1.0000]`, normalized DAG `1.0000 [1.0000, 1.0000]`.
- `same_tool_different_effect`: topology `1.0000 [1.0000, 1.0000]`, exact DAG `0.0000 [0.0000, 0.0000]`, normalized DAG `0.0000 [0.0000, 0.0000]`.
- `tool_rename`: topology `1.0000 [1.0000, 1.0000]`, exact DAG `0.0000 [0.0000, 0.0000]`, normalized DAG `1.0000 [1.0000, 1.0000]`.
- `wrapper_tool`: topology `1.0000 [1.0000, 1.0000]`, exact DAG `0.0000 [0.0000, 0.0000]`, normalized DAG `0.1250 [0.0000, 0.2500]`.

## Reviewer Interpretation

- IPIGuard tool rename is stable after the known alias map (`1.0000 [1.0000, 1.0000]`), but wrapper and argument-schema shifts remain less stable after known-map normalization (`0.1250 [0.0000, 0.2500]` and `0.7083 [0.5000, 0.8750]`).
- IPIGuard topology remains unchanged even when the visible effect changes; topology-only metrics therefore miss content-level effect sensitivity.
- CaMeL is stable under synchronized structural rewrites, but the custom policy component blocks only part of the weak-labeled unsafe structural cases.
- Original-pipeline rates cover all four native suites with a local non-paper model. Low no-defense attack success and utility sharply limit defense-effectiveness conclusions.
- The current four-suite paper-evidence gate is `True` under the implemented completion criteria; this is an artifact-completion gate, not an acceptance or safety gate.

## Acceptance Gates

- `ipiguard_counterfactual_core_valid`: `True`
- `camel_structural_core_valid`: `True`
- `ipiguard_original_dag_component_complete`: `True`
- `camel_original_policy_component_complete`: `True`
- `ipiguard_original_pipeline_smoke_complete`: `True`
- `camel_original_pipeline_smoke_complete`: `True`
- `ipiguard_four_suite_complete`: `True`
- `camel_four_suite_complete`: `True`
- `real_side_effects_absent`: `True`
- `paper_evidence_gate`: `True`
- `both_mechanism_counterfactual_stresses_complete`: `True`

## Claim Boundary

- Local GGUF pipeline results are original-pipeline/local-model evidence, not original-paper numeric reproduction.
- IPIGuard custom stress uses the released DAG construction prompt/parser, not the full construct-traverse-execute pipeline.
- IPIGuard DAG outputs do not expose realized-effect labels, so planned-effect coverage is not identifiable without an external effect mapper.
- CaMeL component stress uses the original generic policy engine but not the full generated-code pipeline.
- AgentDojo tools execute only inside simulated environments; real_side_effects is always false.
- Pipeline/model compatibility failures are reproduction failures, not evidence that the safety method fails.
