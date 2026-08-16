# Final E61/B8/Title Completion Report

## Completed Work

- E61 external corpus discovery: `reports/e61_external_corpus_discovery.md`.
- E61 external subset pipeline: `evaluation/e61_realistic_trace_replay/{ingest_external_traces.py,normalize_external_traces.py,build_external_sidecars.py,validate_external_trace_leakage.py,evaluate_external_trace_subset.py}`.
- E61 external outputs: `evaluation/e61_realistic_trace_replay/external_trace_subset/`.
- B8 adapter: `baselines/b8_released_guardrail/`.
- Tables: `paper_tables/table_e61_external_trace_subset.tex`, `paper_tables/table_e61_combined.tex`, `paper_tables/table_b8_released_adapter.tex`.
- Reproduction: `reproduction/all_main_tables.*`, status `passed`, `445` rows.
- Paper text: Setup, Results, Limitations, Reproduction Notes, and claim-source map updated.
- Title note: `reports/title_positioning_note.md`.

## Required Answers

1. E61 is no longer only artifact-generated realistic replay. It now has the original 300 artifact-generated sandbox/replay traces plus a separate external replay subset.

2. Yes, an external trace subset was integrated.

3. The external subset source is saved AgentDojo-style/IPIGuard replay traces from `data/data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl`; `external_trace_subset/raw_manifest.json` records the source hash and normalization rule. Scale: 156 traces across external_workspace 69, external_banking 46, external_chat 31, and external_travel 10. Metrics: UPA 0.000, FDeny 0.000, coverage 0.904, abstain 0.096, atom exact-set match 0.821.

4. B8 is completed.

5. The released-guardrail anchor is ToolSafe/TS-Guard.

6. B8 is a comparable local adapter under this artifact's label-hidden deployable-input contract. It is not an original ToolSafe/TS-Guard benchmark or checkpoint reproduction.

7. B8 results:
   - E55-v2: UPA 0.435, FDeny 0.095, coverage 0.900, abstain 0.100.
   - E60: UPA 0.533, FDeny 0.200, coverage 1.000, abstain 0.000.
   - E61 artifact-generated: UPA 0.189, FDeny 0.222, coverage 1.000, abstain 0.000.
   - E61 external subset: UPA 0.000, FDeny 0.000, coverage 1.000, abstain 0.000.

8. The title should not be changed in this pass.

9. Recommended title remains Title A: `Tool-Effect Binding in LLM Agents: Counterfactual Measurement and Pre-Commit Authorization`. It best covers both measurement and mediation while avoiding production-authorization overclaim.

10. Claims that must remain conservative:
    - E60 is independently specified, not strictly independently authored; `e60_artifact_level_review.json` currently reports `blocked-by-external-human-review`.
    - E61 external subset is saved replay data, not real deployed traces.
    - E61 external labels are metadata-derived and atoms are rule-derived sidecar annotations, not independent human gold labels.
    - B8 is a comparable local adapter, not an original benchmark reproduction.
    - The paper does not establish production safety, real SaaS safety, complete authorization infrastructure, or global superiority over ToolSafe, Safiron, IPIGuard, or CaMeL.

11. Remaining blockers requiring user/human action:
    - Strict E60 independent authorship would require distinct non-E55 author/reviewer evidence; the current validator output is `blocked-by-external-human-review`.
    - Human-labeled external trace validation would require independent annotation of external traces.
    - A true ToolSafe/TS-Guard reproduction would require running the original public protocol/checkpoint and documenting exact compatibility.
    - Final NDSS submission still needs template polish for two-column formatting warnings.

## NDSS Evidence Bar Assessment

This pass materially improves the evidence against "too synthetic", "weak baselines", and "no external traces" objections. It still remains artifact-bounded. The submission is stronger, but the claim boundary must stay strict.
