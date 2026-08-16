# Writing Report

## Material Package Used

Source root:

`/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package`

Main evidence sources:

- `README.md`
- `PACKAGE_SUMMARY.md`
- `build_status.md`
- `MISSING_FILES.md`
- `method_materials/writing_package_e58/07_claim_to_source_map.md`
- `method_materials/writing_package_e58/tables/core_numbers.md`
- `paper_drafts/e55_precommit_authz/e55_e57_material_check.md`
- E48/E50/E55/E56/E57 JSON result files under `results/analysis/results/` and `audit/analysis/results/`

The AGENTS-requested files `FILE_MAP.md`, `analysis/final_summary.md`, `analysis/current_status_and_gaps.md`, and `analysis/roadmap.md` were not present in this package. I used the package summary, build status, claim maps, tables, and result JSONs as source-of-truth.

## Output Directory

Created:

`ndss_candidate_restructured/`

This directory contains:

- `main.tex`
- `sections/`
- `tables/`
- `figures/`
- `references.bib`
- `appendix/`
- `README.md`
- `TODO.md`
- `writing_report.md`
- `claim_to_source_restructured.md`
- `open_questions_for_user.md`

## Compile Status

Command run from `ndss_candidate_restructured/`:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Status: passed.

PDF:

`ndss_candidate_restructured/main.pdf`

Page count: 14 pages.

Log check:

```bash
rg -n "Overfull|undefined|Citation|Reference|Fatal|Error|does not exist" main.log
```

Result: no matches after the final compile. `pdfinfo` emitted a local Anaconda `libtiff` version warning, but it still reported the PDF metadata and page count.

## Structural Changes

- Expanded the draft from a compressed candidate into a full NDSS-style body structure.
- Added standalone sections for:
  - Threat Model and Security Goal
  - Tool-Effect Binding Problem
  - Effect-Resource-Operation Atoms
  - Counterfactual Stress-Test Framework
  - Reference Effect-Binding Guard
  - Authorization-Aware Pre-Commit Prototype
  - Experimental Setup
  - Results by findings
  - Failure Analysis
  - Discussion
  - Related Work
  - Limitations
  - Ethics and Artifact Scope
- Added six main-paper tables and four TikZ figure files.
- Added appendix files for version policy, audit details, reproduction notes, and claim-to-source map.

## Evidence Policy

- E55-v2 strict is the main pre-commit prototype result.
- Original E55 strict is used for ablation values because those are the current source for the requested ablation metrics.
- Original E55 human-corrected sensitivity is used as audit/sensitivity evidence.
- E57-v2 deterministic checks and E57 human audit are separated.
- All production-safety, complete-permission-system, and real-deployment claims are explicitly excluded.

## Number Conflicts and Resolution

- E55 authz-aware coverage:
  - E55-v2 strict: 528/600 = 0.880.
  - Original E55 strict/human-corrected sensitivity: 552/600 = 0.920.
  - Resolution in draft: E55-v2 is main; original E55 is sensitivity.

- Safe false denial:
  - E55-v2 strict: 0/252 = 0.000.
  - Original E55 human-corrected sensitivity: 4/230 = 0.017.
  - Resolution in draft: report both with labels.

- E57 agreement:
  - E57-v2 reference authorizer: 1.000 agreement.
  - E57 human audit: 54/60 decision agreement and corrections.
  - Resolution in draft: separate deterministic consistency from human audit.

- E55 ablations:
  - Original E55 strict: 0.333, 0.148, 0.148, 0.211.
  - E55-v2 strict: 0.217, 0.217, 0.217, 0.238.
  - Resolution in draft: Table 5 is labeled original E55 strict; open question asks whether to rerun/make E55-v2 ablations canonical.
