# Figure Specifications

| title | data | spec |
|---|---|---|
| Counterfactual Lattice Design | ["data/counterfactual_core_phase4.jsonl", "tables/counterfactual_lattice_summary.csv"] | Four panels: same effect/different surface, same tool/different effect, same effect/different authorization, same effect/different resource. Show expected decision stability or flip for each axis. |
| Capability Coverage Heatmap | ["tables/main_capability_matrix.csv"] | Rows are methods; columns are surface invariance, effect sensitivity, authorization sensitivity, resource awareness, unsafe pre-allow inverse, safe false deny inverse, abstain inverse, utility. Use scope annotations beside method names. |
| Failure-Mode Taxonomy | ["failure_examples/failure_examples.json", "tables/appendix_camel_miss_decomposition.csv"] | Tree from surface failure to effect-insensitivity, authorization failure, resource binding failure, evidence absence, and control-dependency failure. |
| IPIGuard Semantic-Layer Diagram | ["tables/structured_defense_summary.csv", "results/canonical/tool_effect_fragmentation_ipiguard_semantic_phase6.json"] | Pipeline diagram: DAG topology -> normalized content DAG -> effect/resource semantic mapper -> authorization decision. Mark topology-only as not decision-evaluable. |
| CaMeL Control-Dependency Failure | ["tables/appendix_camel_miss_decomposition.csv", "failure_examples/failure_examples.json"] | Show private tool output controlling a side-effectful action. The evaluated policy component allows it; required policy treats control provenance as authorization-relevant. |
