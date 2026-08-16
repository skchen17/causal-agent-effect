# Figures and Tables

## Main Figure

Figure 1 is now a rendered TikZ schematic in Section 3, not an appendix placeholder. Caption:

> Counterfactual tool-effect lattice used to separate surface invariance from safety-relevant sensitivity.

It covers:

- same-effect/different-surface;
- same-tool or same-surface/different-effect;
- authorization flip;
- resource mismatch;
- provenance shift.

## Main Tables

Table 1: main counterfactual lattice metrics.

- Header directions: consistency/correctness/sensitivity columns are `(up)`; resource mismatch error, unsafe pre-allow, and safe false denial are `(down)`.
- Values are formatted to three decimals.
- Artifact paths are moved to Appendix A.

Table 2: structured-defense and semantic-layer component findings.

- Values are formatted to three decimals.
- IPIGuard topology-only effect sensitivity is `N/I`, not zero, because no realized-effect decision interface is present.
- Scope labels distinguish component stress, diagnostic mapper rows, and upper-bound rows.

Appendix capability matrix:

- Source: `tables/main_capability_matrix.md`.
- Includes method scope, surface/effect/auth/resource fields, unsafe pre-allow, safe false denial, abstention or coverage, and evidence grounding.
- Uses `N/I` for absent decision interfaces rather than imputing values.

## Appendix-Only Figure Specs

The capability heatmap, IPIGuard semantic-layer diagram, and CaMeL control-dependency diagram remain appendix-only draft specs until rendered from source data.
