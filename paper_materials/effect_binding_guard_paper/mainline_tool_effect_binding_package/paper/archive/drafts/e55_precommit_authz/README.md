# E55 Pre-Commit Authorization Materials

This folder contains paper-ready E55 materials for the Effect-Binding Guard paper package.

- Outcome: `Outcome B`
- Interpretation: Authorization-aware guard preserves low UPA while greatly increasing coverage; ablations show the improvement depends on explicit authorization infrastructure.
- Scope: controlled local mock pre-commit mediation.
- Boundary: no real APIs, no real side effects, no production-safety proof, and no original-paper benchmark reproduction.
- Human-audit caveat: E57 found 6/60 decision corrections and 14/60 atom/resource/reason corrections in the spot-audit packet. Use `e55_human_corrected_sensitivity.md` and `e55_v2_corrected_rerun.md` for paper-facing wording.
- E55-v2 validity: E57-style checks on the corrected rerun passed with changed decisions `0`, UPA delta `0.0`, coverage delta `0.0`, reference decision agreement `1.0`, atom count agreement `1.0`, and resource-set agreement `1.0`.

Use this material as NDSS review-response support for the resource/authorization bottleneck identified in E50.
