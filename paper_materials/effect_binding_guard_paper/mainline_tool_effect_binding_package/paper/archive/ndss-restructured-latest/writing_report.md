# Writing Report

## Main Revision Goal

The active v2 paper centers the work on one thesis:

> Side-effectful tool calls are not atomic security actions. Safe pre-commit mediation requires expanding candidate tool calls into effect-resource-operation atoms and checking those atoms against explicit authorization and provenance context.

This pass keeps the main narrative unchanged while adding strict completion artifacts for E60 independent-authorship evidence, NDSS template/page-budget checking, E61 external replay evidence, and B8 comparable-adapter evidence.

## Completed Changes

- Removed filesystem path traces, internal count notes, stale directory-status notes, missing-bibliography placeholder language, and manuscript-status phrasing from PDF-included LaTeX.
- Added verified systems-security and provenance foundations to `references.bib` and Related Work.
- Added verified ARGUS and AgentVisor related-work citations as contemporary provenance/virtualization-style LLM-agent defenses.
- Kept ARGUS/AgentVisor outside the experimental evidence chain.
- Strengthened atom minimality, connected E50 resource/authorization failures to granularity failure, and clarified Table 1 axis metrics versus row-level UPA.
- Kept E55-v2 strict as the sole main pre-commit performance and ablation result.
- Repositioned E55-v2 as a controlled feasibility warm-up; E60/E61 are now the main transfer and trace-replay validation evidence.
- Added E60 independently specified held-out-contract evidence, E61 sandboxed realistic trace replay, E62 extraction-vs-authorization decomposition, E63 interface-burden/context-degradation results, and E64 B0--B7 comparable baselines.
- Added E60 artifact-level review packet with status `artifact-level-pass; blocked-by-external-human-review`.
- Added E61 external-trace subset pipeline and outputs for 156 saved AgentDojo-style/IPIGuard replay traces.
- Added E60 independent-review validator and status output under `evaluation/e60_heldout_contract/`.
- Added E61 external raw manifest and sidecar build entrypoint under `evaluation/e61_realistic_trace_replay/`.
- Added B8 ToolSafe/TS-Guard-style released-guardrail comparable local adapter under `baselines/b8_released_guardrail/`.
- Added root-level `scripts/reproduce_all_main_tables.py`, which regenerates `reproduction/all_main_tables.*` and `reproduction/claim_to_source_map.*`.
- Added `main_ndss_full.tex`, `main_ndss_technical.tex`, and `ndss_template/` for an official-template pass without replacing the article-template source.

## Evidence Policy

- E55-v2 strict is the controlled local pre-commit prototype result.
- E60 supports `independently specified held-out contract`; its artifact-level review does not certify strict `independently authored` wording.
- E61 is sandboxed/replayed trace evidence with a saved external replay subset, not live SaaS deployment evidence or independently human-labeled external gold data.
- E62 decomposes atom extraction, authorization checking, and context degradation.
- E63 reports interface burden and safe-degradation behavior.
- E64 baselines are comparable local adapters under deployable input restrictions, not original benchmark reproductions of external systems. B8 is a ToolSafe/TS-Guard-style comparable local adapter.
- The paper does not claim production safety, complete authorization infrastructure, real SaaS validation, or solved authorization.

## Number Checks

- E48 hard guard: coverage `0.917`, UPA `0.036`, FDeny `0.065`.
- E50 resource/auth stress: UPA `0.383` at coverage `0.921` after policy-label consistency repair.
- E55-v2 authz-aware guard: coverage `528/600 = 0.880`, UPA `0/276`, FDeny `0/252`.
- E55-v2 ablations: no multi-resource UPA `0.217`, no operation-mode UPA `0.217`, no provenance-overlay UPA `0.217`, no alias FDeny `0.238`.
- E57-v2 reference authorizer agreement is `1.000`; E57 human audit decision agreement is `54/60 = 0.900`; these are separate checks.
- E60 held-out contract: `480` cases, coverage `0.854`, UPA `0.000`, FDeny `0.083`, atom exact-set match `0.812`.
- E61 sandboxed realistic trace replay: `300` traces, coverage `0.847`, UPA `0.000`, FDeny `0.053`, atom exact-set match `0.733`.
- E61 external replay subset: `156` saved AgentDojo-style/IPIGuard replay traces, coverage `0.904`, UPA `0.000`, FDeny `0.000`, atom exact-set match `0.821`.
- E62 decomposition: E60 coverage moves `0.875 -> 0.854 -> 0.783`; E61 moves `1.000 -> 0.847 -> 0.707`.
- E64 summary: full atom-level mediation has UPA `0.000` at coverage `0.854` on E60 and UPA `0.000` at coverage `0.847` on E61; the strongest non-atom baselines have UPA `0.311`/coverage `0.625` and UPA `0.189`/coverage `0.700`.
- B8 comparable adapter: E55-v2 UPA `0.435`/coverage `0.900`; E60 UPA `0.533`/coverage `1.000`; E61 artifact-generated UPA `0.189`/coverage `1.000`; E61 external subset UPA `0.000`/coverage `1.000`.

## Reproduction Status

Command run from the v2 paper directory:

```bash
python reproduce_main_numbers.py
```

Status: passed. The script regenerates 55 rows across E48, E50, E55-v2, E55-v2 ablation, E56, E57-v2 validity, and E57 human-audit rows, including Table 6 pass/fail checks.

Command run from the artifact root:

```bash
python scripts/reproduce_all_main_tables.py
```

Status: passed. The script regenerates 445 rows across Table 1, Tables 2--6, E60, E60 claim-boundary checks, E61, E61 external, E61 combined accounting, E62, E63, E64, and B8 rows, including field-level PRF/F1 checks, required-artifact gates, and a reproduced claim-to-source map.

## Compile Status

Article-template command run from the v2 paper directory:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Status: passed. The regenerated article-template `main.pdf` is 19 pages. This is a sanity build, not an NDSS compliance signal.

NDSS-template full sanity command:

```bash
TEXINPUTS=./ndss_template//: latexmk -pdf -interaction=nonstopmode -halt-on-error main_ndss_full.tex
```

Status: passed. `main_ndss_full.pdf` is 13 pages total under the downloaded NDSS template files.

NDSS-template technical-body command:

```bash
TEXINPUTS=./ndss_template//: latexmk -pdf -interaction=nonstopmode -halt-on-error main_ndss_technical.tex
```

Status: passed for page counting. `main_ndss_technical.pdf` is 11 pages for Abstract through Conclusion, excluding Ethics, references, and appendices. The technical-body log intentionally has missing citation/reference warnings because references and appendices are excluded from that count.

## Page-Limit Status

- The NDSS 2027 CFP states a 13-page technical-paper limit excluding Ethics, references, and appendices, with the NDSS template required.
- The local NDSS-template technical-body pass is currently under that target at 11 pages.
- No evidence was removed for page fit.
- Final submission polish should still fix two-column overfull table/figure formatting warnings.
- If future content causes overflow, compress in this order: Related Work, Experimental Setup, Table 6 prose, then appendix verbosity. Do not remove E60--E64 main-text visibility for page fit.

## External Verification

- NDSS 2027 page-limit and anonymity requirements were checked against the official CFP.
- The NDSS template files were downloaded from the official NDSS templates page into `ndss_template/`.
- All cited arXiv entries were checked against their public arXiv pages where available; classic systems-security and provenance entries use public DOI-backed metadata.
