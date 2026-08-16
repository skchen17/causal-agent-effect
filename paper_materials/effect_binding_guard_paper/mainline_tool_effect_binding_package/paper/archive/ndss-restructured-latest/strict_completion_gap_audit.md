# Strict Completion Gap Audit

## Summary

This audit checks the strict completion plan against the current `ndss_candidate_restructured_v2/` artifact. The main narrative remains unchanged:

Tool-effect binding -> effect-resource-operation atoms -> counterfactual stress tests -> E50 resource/auth bottleneck -> E55-v2 local prototype -> E56/E57 audit -> E60--E64 stronger evidence.

Status labels:

- `done`: requirement is implemented and has a traceable artifact.
- `done-with-caveat`: implemented, but the evidence has a boundary that must remain visible.
- `blocked-by-user-input`: cannot be completed without external user/human material.
- `optional-not-blocking`: explicitly optional in the plan or not required for core acceptance.

## Strict Requirement Checklist

| Requirement | Status | Evidence | Notes |
|---|---:|---|---|
| E60 held-out contract with at least 3 domains and 240 cases | done | `evaluation/e60_heldout_contract/dataset_manifest.json`; `results_e60.json` | Current artifact has 480 cases across five domains. |
| E60 schema/tool/alias/policy differences from E55 | done | `dataset_manifest.json`; `reports/e60_heldout_report.md` | Manifest records different tool names, fields, alias style, resource IDs, and policy format. |
| E60 gold atoms/labels separated from deployable input | done | `deployable_inputs.jsonl`; `gold_atoms.jsonl`; `gold_labels.jsonl`; `leakage_report.json` | Leakage report records zero violations. |
| E60 artifact-level review | done | `independent_author_review_packet.{json,md}`; `e60_artifact_level_review.json`; `reports/e60_independent_review_status.md` | Validator reports `artifact-level-pass` and confirms artifact existence, leakage, deployable-input hiding, no deletion, and schema/data-separation checks. |
| E60 strict independently authored proof | blocked-by-user-input | `e60_artifact_level_review.json`; `independent_author_review_packet.template.json` | Validator reports `blocked-by-external-human-review`. Paper must say `independently specified`, not `independently authored`, until a real non-E55 human review packet passes. |
| E60 enters main paper | done-with-caveat | `sections/results.tex`; `tables/table_e60_heldout.tex` | Main text includes E60 as Finding 4, with strict wording caveat. |
| E61 realistic trace replay with at least 200 traces and 3 domains | done | `evaluation/e61_realistic_trace_replay/trace_manifest.json`; `results_e61.json` | Current artifact has 300 sandboxed/replayed traces across five domains. |
| E61 trace sources A/B/C | done | `trace_manifest.json`; `reports/e61_realistic_trace_report.md` | Clean sandbox, noisy realistic, and adversarial/provenance-shift sources are represented. |
| E61 no real side effects and label-hidden replay | done | `deployable_inputs.jsonl`; `gold_atoms.jsonl`; `gold_labels.jsonl`; `leakage_report.json` | Evaluation is sandboxed/replayed and leakage-free. |
| E61 enters main paper | done | `sections/results.tex`; `tables/table_e61_realistic_trace.tex`; `paper_figures/figure_e61_trace_pipeline.tex` | Main text reports trace-source mix and failure modes. |
| E61 external trace subset | done-with-caveat | `evaluation/e61_realistic_trace_replay/external_trace_subset/`; `raw_manifest.json`; `reports/e61_external_trace_report.md`; `tables/table_e61_external_trace_subset.tex`; `tables/table_e61_combined.tex` | Added 156 saved AgentDojo-style/IPIGuard replay traces. Labels are metadata-derived and atoms are rule-derived sidecar annotations, not independent human annotation. |
| E62 Mode A/B/C decomposition on E55-v2, E60, and E61 | done | `evaluation/e62_extraction_decomposition/results_e55.json`; `results_e60.json`; `results_e61.json` | Results separate checker ceiling, extraction error, and degraded context. |
| E62 main table/figure | done | `tables/table_e62_decomposition.tex`; `paper_figures/figure_e62_error_attribution.tex` | Included in Results Finding 6. |
| E63 interface burden manifest | done | `evaluation/e63_interface_burden/burden_manifest.json`; `tables/table_e63_burden.tex` | Reports tools, schemas, atom rules, auth fields, aliases, policy rules, and authoring-time estimates. |
| E63 context degradation tests | done | `evaluation/e63_interface_burden/context_degradation_results.json`; `tables/table_e63_degradation.tex` | Reports abstention/FDeny/UPA tradeoffs under missing or contradictory context. |
| E64 B0--B7 comparable baselines | done | `baselines/baseline_results.json`; `baselines/baseline_input_contract.json`; `paper_tables/table_baselines_*.tex` | Main comparison uses non-atom baselines under a common deployable input view. |
| E64 B8 released guardrail adapter | done-with-caveat | `baselines/b8_released_guardrail/`; `reports/b8_released_guardrail_adapter_report.md`; `tables/table_b8_released_adapter.tex` | Implemented a ToolSafe/TS-Guard-style comparable local adapter. It is not an original benchmark/checkpoint reproduction. |
| External trace corpus extension | done-with-caveat | `evaluation/e61_realistic_trace_replay/external_trace_subset/`; `reports/e61_external_corpus_discovery.md` | Added saved external replay subset. A human-labeled external corpus remains a future extension. |
| Reproduce all main tables script | done | `scripts/reproduce_all_main_tables.py`; `reproduction/all_main_tables.*`; `reproduction/reproduction_status.json` | Generates 445 rows and fails fast on missing keys/artifacts; status includes E60/E61/B8 claim boundaries. |
| v2 lightweight reproduction shim | done | `ndss_candidate_restructured_v2/reproduce_main_numbers.py`; `reproduction/main_numbers_reproduced.*` | Generates 55 rows for Tables 2--6 and audit checks. |
| Results rewrite for new evidence | done-with-caveat | `sections/results.tex` | E55-v2 is a controlled warm-up; E60/E61/E62/E63/E64 are visible in the main Results. Strict E60 authorship remains unavailable. |
| Avoid production-safety and solved-authorization claims | done-with-caveat | `sections/limitations.tex`; `sections/discussion.tex`; final scans | Current text is artifact-bounded; final scan must remain clean before submission. |
| NDSS official-template technical-body page check | done-with-caveat | `main_ndss_full.tex`; `main_ndss_technical.tex`; `ndss_template_page_report.md` | Technical body builds at 11 pages under the downloaded NDSS template files. Two-column overfull formatting polish remains. |
| Final paper build | done-with-caveat | `main.pdf`; `main_ndss_full.pdf`; `main_ndss_technical.pdf` | Article sanity build and NDSS-template builds compile. Template polish remains before submission. |

## Remaining Strict Blockers

1. E60 now has an artifact-level review packet and validator output, but strict independent-authorship remains not certified.
   - The packet supplies reviewer metadata, review date, reviewed artifact list, independence checks, data-separation checks, leakage confirmation, result review, and review findings.
   - The validator status is `artifact-level-pass` for artifact checks and `blocked-by-external-human-review` for strict authorship.
   - The paper correctly uses `independently specified`; do not upgrade to `independently authored`.

2. Final submission-format polish is still required.
   - Current NDSS-template technical-body page count is under target.
   - Remaining issue is two-column formatting polish, not evidence deletion.

## Non-Blocking Optional Items

- Full original-system ToolSafe/TS-Guard reproduction remains outside this pass; B8 is only a comparable local adapter.
- Human-labeled external trace-corpus integration remains a future validation extension.

## Evidence-Bar Assessment

The current artifact now addresses the main reviewer objections about excessive synthetic evidence, circular local contracts, missing realistic traces, weak baselines, and assumed authorization infrastructure. E60 has artifact-level review support for independently specified transfer, but it does not satisfy the stronger independently authored standard. E61 external and B8 add useful evidence, but they do not establish deployed-system safety or original-system benchmark reproduction.
