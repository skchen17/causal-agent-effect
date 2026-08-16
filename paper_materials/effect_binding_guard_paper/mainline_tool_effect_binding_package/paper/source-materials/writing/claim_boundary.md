Allowed claims:

- Weak tool-surface baselines overestimate safety under held-out or counterfactual shifts.
- Official checkpoints are not merely tool-name classifiers.
- Simple tool rename robustness does not imply tool-effect invariance.
- TS-Guard, Safiron, IPIGuard, and CaMeL cover different subsets of the joint safety decision problem.
- IPIGuard DAG topology is stable but needs an effect/resource semantic layer for effect-level decision sensitivity.
- CaMeL structural policy is stable in the tested component but misses control-dependency violations in the custom stress.
- Human audit supports the corrected counterfactual labels under the pre-registered thresholds.
- Evidence-grounded or effect/resource-aware layers can help diagnose missing capabilities, but current non-oracle versions are not complete deployable guards.

Disallowed claims:

- Do not claim full original-paper benchmark reproduction.
- Do not claim ToolSafe, Safiron, IPIGuard, or CaMeL generally fail.
- Do not claim graph, provenance, or structural defenses generally fail.
- Do not claim execution evidence is a complete deployable solution.
- Do not claim LLMs do not understand tools at all.
- Do not treat local-model pipeline feasibility as defense-effectiveness evidence.
- Do not treat oracle or upper-bound rows as deployable methods.
- Do not treat artifact-completion gates as safety-acceptance gates.
