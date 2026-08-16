# NDSS Candidate Restructured Draft

This directory contains a new NDSS-style restructured draft for the Tool-Effect Binding paper. It intentionally does not overwrite the older `paper_drafts/ndss_candidate/` or `paper_rewriting_output/` drafts.

## Positioning

The draft frames the paper as:

`measurement + diagnostic framework + local pre-commit authorization prototype`

It does not claim production-ready LLM-agent safety, a complete permission system, real SaaS deployment validation, or original benchmark reproduction for all compared methods.

## Contents

- `main.tex`: top-level LaTeX file.
- `sections/`: main paper sections.
- `tables/`: six main-paper tables.
- `figures/`: four TikZ figures.
- `appendix/`: additional tables, audit details, reproduction notes, and claim-source map.
- `references.bib`: verified core references used in the draft.
- `TODO.md`: follow-up tasks.
- `open_questions_for_user.md`: user-facing open questions and version-policy caveats.
- `writing_report.md`: summary of restructuring work and evidence policy.
- `claim_to_source_restructured.md`: Markdown claim-to-source map.

## Current Source Policy

- Main pre-commit result: E55-v2 strict.
- Audit/sensitivity: original E55 strict plus human-corrected sensitivity.
- Ablations: original E55 strict, explicitly labeled as such.
- E57-v2: deterministic perturbation and reference-authorizer validity.
- E57 human audit: separate human audit with corrections.

## Build

Run from this directory:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```
