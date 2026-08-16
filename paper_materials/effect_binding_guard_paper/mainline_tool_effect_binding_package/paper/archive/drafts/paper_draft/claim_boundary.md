# Claim Boundary

Allowed claims:

- Weak tool-surface baselines overestimate safety under held-out or counterfactual shifts.
- Official checkpoints are not merely tool-name classifiers under the E47 custom stress.
- Simple tool rename robustness does not imply tool-effect invariance.
- TS-Guard, Safiron, IPIGuard-style DAGs, and CaMeL-style structural policies cover different subsets of the joint safety decision problem.
- IPIGuard topology is stable, but topology-only outputs do not provide a realized-effect authorization decision interface.
- The tested CaMeL structural policy component is stable in synchronized rewrites and misses control-dependency violations in this custom stress.
- Human audit supports the corrected counterfactual labels under the package thresholds.
- Evidence-grounded and effect/resource-aware layers help diagnose missing capabilities, while current non-oracle versions remain incomplete.

Disallowed claims:

- Do not make system-wide failure claims about ToolSafe, Safiron, IPIGuard, or CaMeL.
- Do not claim original-paper numeric reproduction.
- Do not claim deployed-system safety certification.
- Do not treat local-model pipeline feasibility as defense-effectiveness evidence.
- Do not treat oracle or upper-bound rows as deployable methods.
- Do not imply graph, provenance, or structural defenses are intrinsically inadequate.
- Do not claim execution evidence is a complete deployed solution.
- Do not claim LLMs do not understand tools.
- Do not report topology-only IPIGuard effect sensitivity as a realized-effect safety metric; use `N/I`.

Main wording rule:

Use "under this controlled custom stress," "in the evaluated component," or "in this package" whenever interpreting system-specific rows.

Discussion split:

- Facts: package counts, metrics, audit completion, validation/build status.
- Measured results: per-axis rows in the lattice, structured component rows, and audit summary.
- Inferences: surface robustness is insufficient; topology stability can hide semantic gaps; control provenance is authorization-relevant.
- Design recommendations: report invariance/sensitivity separately, couple effect/resource/auth binding, add semantic decision layers, treat control provenance as policy input, and report utility/abstention with safety metrics.
