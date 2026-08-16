# NDSS Candidate Restructured v2

This directory contains the active v2 NDSS-style restructured paper for the Tool-Effect Binding work.

## Positioning

The v2 paper frames the work as:

`counterfactual measurement + effect-resource-operation atoms + E50 bottleneck + E55-v2 local feasibility + E60/E61 transfer/trace validation + E62-E64 mechanism, burden, and baselines`

It does not claim a deployed-system safety guarantee, a full enterprise authorization layer, real SaaS deployment validation, or original benchmark reproduction for all compared methods.

## Contents

- `main.tex`: top-level LaTeX file.
- `sections/`: main paper sections.
- `tables/`: original main tables plus E60--E64 generated result tables.
- `figures/`: four TikZ figures.
- `appendix/`: additional tables, audit details, reproduction notes, and claim-source map.
- `references.bib`: verified core references used in the paper.
- `open_questions_for_user.md`: user-facing open questions and version-policy caveats.
- `writing_report.md`: summary of restructuring work and evidence policy.
- `claim_to_source_restructured_v2.md`: Markdown claim-to-source map.
- `reproduce_main_numbers.py`: lightweight JSON-based reproduction shim.
- `reproduction/`: generated main-number and all-main-table reproduction outputs.

## Current Source Policy

- Main pre-commit result: E55-v2 strict.
- Main ablations: E55-v2 strict.
- Audit/sensitivity and version comparison: original E55 strict plus human-corrected sensitivity.
- E57-v2: deterministic perturbation and reference-authorizer validity.
- E57 human audit: separate human audit with corrections.
- E60: independently specified held-out contract.
- E61: sandboxed realistic trace replay.
- E62: extraction-vs-authorization decomposition.
- E63: interface burden and context degradation.
- E64: comparable local baselines under a common deployable input view.

## Build

Run from this directory:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

To regenerate the main-number reproduction outputs:

```bash
python reproduce_main_numbers.py
```

To regenerate the expanded all-main-table and claim-source outputs, run from the artifact root:

```bash
python scripts/reproduce_all_main_tables.py
```
