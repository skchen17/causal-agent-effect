# Paper Checklist

## Source Validation

- Package validation command: `python scripts/build_tool_effect_paper_package.py --output . --validate-only`
- Result: passed; validated `/data/CSK/causal-agent-safety-research/paper_package_tool_effect_invariance`.

## Build Validation

- TeX command: `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`
- Result: passed and produced `paper_draft/main.pdf`.
- TeX engine status: available; `tikz.sty`, `tabularx.sty`, `latexmk`, and `pdftotext` were present.
- Auxiliary cleanup: required after final build; retain `paper_draft/main.pdf`.

## Revision Acceptance Checks

- Preferred title is used in `main.tex`: "Surface Robustness Is Not Enough: Counterfactual Tool-Effect Invariance for LLM Agent Safety Defenses."
- Abstract is a single conference-style paragraph covering side effects, decision variables, evaluated scopes, main conclusion, audit counts, and claim boundary.
- Introduction includes the `send_email` running example and connects it to `d = f(e, r, a, v, p)`.
- Section 3 includes a rendered TikZ Figure 1 with the required caption.
- Table 1 uses three-decimal formatting, direction markers, and moves artifact paths to Appendix A.
- Table 2 uses three-decimal formatting, direction markers, and `N/I` for IPIGuard topology-only realized-effect decision metrics.
- Appendix includes a compact capability matrix with scope labels and evidence/coverage fields.
- RQ results end with explicit takeaway sentences.
- RQ4 is split into topology semantic incompleteness and CaMeL control-dependency misses.
- Discussion is organized as five numbered design implications.
- Related Work uses only verified citations and source-level TODO comments for broader bibliography.
- Limitations are bullet-form and include all claim-boundary constraints.

## Numeric Claim Anchors

- Phase 4 lattice size, official checkpoint metrics, and baseline metrics: `tables/counterfactual_lattice_summary.md`, `tables/official_checkpoint_summary.md`, `results/canonical/phase4_summary.md`.
- IPIGuard and CaMeL component metrics: `tables/structured_defense_summary.md`, `tables/main_capability_matrix.md`, `results/canonical/phase6_summary.md`.
- Human audit metrics: `audit/tool_effect_fragmentation_human_audit_phase6.md`, `tables/human_audit_summary.md`.
- Claim-scope constraints: `tables/claim_scope_table.md`, `writing/claim_boundary.md`, `reproducibility/scope_label_guide.md`.
- Spot-check result: headline numbers in `main.tex` were found in `tables/`, `results/canonical/`, or `audit/`.

## Text Checks

- Source/PDF scan found no corrupted soft-hyphen or unknown-character artifacts.
- Source/PDF scan found no unresolved citation-marker placeholders.
- Overclaim scan matched only negated or boundary language, not affirmative forbidden claims.
- TODO strings are source-level related-work reminders, not visible placeholders for results.

## Claim Split

- Facts: counts, metrics, audit completion, package validation, and TeX build status.
- Measured results: per-axis lattice rows, structured component rows, semantic/evidence diagnostics, and audit summary.
- Inferences: surface robustness is insufficient; topology stability can hide semantic gaps; resource and authorization binding are distinct bottlenecks; control provenance is authorization-relevant.
- Recommendations: evaluate paired counterfactual groups; report invariance and sensitivity separately; report unsafe pre-allow, safe false denial, abstention, coverage, and utility together; separate component stress, diagnostics, feasibility, oracle rows, and deployable methods.

## Claim Boundaries

- No new experiments were run.
- No original-paper numeric reproduction is claimed.
- No deployed-system safety certification is claimed.
- Oracle and upper-bound rows are not described as deployable defenses.
- Local-pipeline feasibility is not used as defense-effectiveness evidence.
- The draft does not claim ToolSafe, Safiron, IPIGuard, or CaMeL generally fail.
