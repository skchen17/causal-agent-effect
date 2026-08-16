# E60-E64 Final Evidence Report

## Completed experiments

- E60 independently specified held-out contract: 480 cases; results in `evaluation/e60_heldout_contract/results_e60.json`; validator output in `evaluation/e60_heldout_contract/e60_artifact_level_review.json`; table `paper_tables/table_e60_heldout.tex`.
- E61 realistic trace replay: 300 traces; results in `evaluation/e61_realistic_trace_replay/results_e61.json`; table `paper_tables/table_e61_realistic_trace.tex`.
- E62 extraction-vs-authorization decomposition: E55-v2, E60, and E61; results in `evaluation/e62_extraction_decomposition/`; table `paper_tables/table_e62_decomposition.tex`.
- E63 interface burden and context degradation: results in `evaluation/e63_interface_burden/`; tables `paper_tables/table_e63_burden.tex` and `paper_tables/table_e63_degradation.tex`.
- E64 stronger baseline suite: B0-B7 implemented in `baselines/baseline_results.json`; B8 comparable adapter implemented under `baselines/b8_released_guardrail/`; tables under `paper_tables/table_baselines_*.tex` and `paper_tables/table_b8_released_adapter.tex`.

## Relationship to E55-v2

E55-v2 remains the controlled feasibility warm-up. E60 and E61 provide held-out-contract and realistic-trace validation; E62 decomposes extraction and authorization; E63 reports interface burden; E64 adds comparable baselines.

## Main performance changes

- E60 full atom mediation: UPA 0.000, FDeny 0.083, coverage 0.854.
- E61 full atom mediation: UPA 0.000, FDeny 0.053, coverage 0.847.
- E61 external subset: 156 saved AgentDojo-style/IPIGuard replay traces; UPA 0.000, FDeny 0.000, coverage 0.904.
- E64 summary is limited to non-atom baselines for the main comparison. B5 and B7 are diagnostic variants: B5 exposes false-denial cost when alias canonicalization is removed, and B7 can match full mediation when atom-equivalent capability context is supplied.

## Failure cases

Primary failure categories are extraction errors on noisy traces, alias ambiguity, missing/stale policy context, and provenance/control-source ambiguity. These are retained in result JSONs and should be reported as limitations.

## Open user-confirmation items

- E60 artifact-level review passes, but `e60_artifact_level_review.json` reports `blocked-by-external-human-review` for strict authorship; paper text should continue to use `independently specified`, not `independently authored`.
- The NDSS-template technical-body pass is under the 13-page target in the current artifact, but final submission polish still needs two-column formatting review for overfull boxes.
- B8 is implemented as a ToolSafe/TS-Guard-style comparable local adapter, not an original benchmark/checkpoint reproduction.

## NDSS resubmission evidence bar

The new evidence directly addresses too-synthetic, circular local-contract, missing realistic trace, weak baseline, and assumed-infrastructure concerns, but still does not establish a deployed-system guarantee.
