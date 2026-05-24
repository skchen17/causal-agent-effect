# Mainconf v2 Repair Report

> Date: 2026-05-15  
> Purpose: record the follow-up repair after `analysis/completion_report_actuality_check.md` found that the v1 completion report overstated T28/T29 completion.

## Verdict

The v1 main-conference increment was useful but incomplete. The repaired **mainconf v2** chain is now the current data/experiment state for T28/T29 Phase 1.

Current status:

- T28 data expansion / key-cell rebalance: **DONE for Phase 1 v2**.
- T29 real/semi-real traces: **DONE for static-replay Phase 1**, not observed execution.
- T30 strict mitigation: **PARTIAL**. v2 strict LOPO and full-training multiseed are complete, but strong OOD/domain-generalization baselines are still missing.
- T33 artifact/reproducibility: **PARTIAL**. Merge and audit scripts exist, but no single main-conference reproduction entrypoint exists yet.

## Repaired Artifacts

| Component | v2 artifact | Status |
|---|---|---|
| Cell target selection | `analysis/main_conference_cell_targets.json/.md` | fixed to read all cells, not only low-N cells |
| Increment generator | `generate_main_conference_data_increment.py` | outputs v2 rows with `tool_call` and `call_flow` |
| Increment data | `data/scenarios_mainconf_increment_v2.jsonl` | 408 rows |
| Increment manifest | `analysis/scenarios_mainconf_increment_v2_manifest.json` | all 7 tracked P0 cells projected to N+ = 50 |
| Static replay traces | `data/agent_tool_traces_mainconf_v2.jsonl` | 65 rows |
| Trace manifest | `analysis/agent_tool_traces_mainconf_v2_manifest.json` | no required schema field missing |
| Merge script | `merge_main_conference_data.py` | new reproducible merge entrypoint |
| Merged data | `data/scenarios_mainconf_v2.jsonl` | 932 rows |
| Merged manifest | `analysis/scenarios_mainconf_v2_manifest.json` | source/schema/cell-count audit |
| Embeddings | `embeddings/*qwen3-8b_scenarios_mainconf_v2*` | 932 x 4096 Qwen3-8B embeddings |
| LOTO/baseline | `analysis/baseline_comparison_qwen3-8b_scenarios_mainconf_v2.json` | complete |
| FNR/Frag | `analysis/fnr_frag_qwen3-8b_scenarios_mainconf_v2.json` | complete |
| Strict LOPO | `analysis/contrastive_strict_lopo_qwen3-8b_scenarios_mainconf_v2.json` | complete |
| Multiseed projection | `analysis/contrastive_multiseed_qwen3-8b_scenarios_mainconf_v2.json/.md` | complete |
| Statistical audit | `analysis/statistical_uncertainty_audit_mainconf_v2.json/.md` | complete |

## Dataset Summary

`data/scenarios_mainconf_v2.jsonl` has 932 rows:

| Source | Rows |
|---|---:|
| `scenarios_merged` | 459 |
| `mainconf_increment` | 408 |
| `agent_tool_trace` | 65 |

Tracked P0 cells in v2:

| Effect | Tool | N+ | N- |
|---|---:|---:|---:|
| `content_fetched` | `terminal` | 53 | 294 |
| `tool_error` | `web_search` | 78 | 98 |
| `network_egress` | `web_search` | 98 | 78 |
| `file_deleted` | `terminal` | 53 | 294 |
| `file_written` | `terminal` | 54 | 293 |
| `file_written` | `write_file` | 56 | 29 |
| `file_content_read` | `read_file` | 56 | 31 |

Residual data caveat:

- 27 / 44 positive effect-tool cells are still below N+ = 30, mostly outside the first P0 tracked set.
- `tool_error/send_message` remains LOTO-evaluable but small (N+ = 11).

## Trace Fidelity

`data/agent_tool_traces_mainconf_v2.jsonl` has 65 static replay traces with:

- `tool_schema`
- `tool_call`
- `pre_state`
- `authorization_scope`
- `predicted_call_flow`
- `observed_or_simulated_effects`
- `effects`

Limit:

> These are static replays derived from real tool registrations and call-flow semantics. They are not observed runtime execution traces and should not be described as real execution validation.

## Main v2 Experimental Results

LOTO stress-test worst held-out FNRs:

| Effect | Worst tool | N+ | Held FNR |
|---|---:|---:|---:|
| `file_content_read` | `read_file` | 56 | 0.8036 |
| `file_written` | `write_file` | 56 | 0.7679 |
| `content_fetched` | `web_fetch` | 44 | 0.5682 |
| `network_egress` | `send_message` | 34 | 0.3824 |
| `file_deleted` | `terminal` | 53 | 0.3774 |
| `tool_error` | `terminal` / `web_fetch` | 28 / 16 | 0.2500 |

Interpretation:

- Increasing N+ did not eliminate surface-form fragmentation.
- The strongest remaining failures are `file_content_read/read_file`, `file_written/write_file`, and `content_fetched/web_fetch`.
- v2 reduces some small-N uncertainty but does not by itself make the paper main-conference ready.

Strict LOPO contrastive projection:

- Evaluable effects: 2.
- Tool-case rows: 68.
- Improved: 33 / 68.
- Mean delta FNR: 0.1044.

Full-training multiseed projection:

- Seeds: 5.
- Max mean post-FNR: 0.034.
- Max population std: 0.0141.
- This is an upper-bound observed-pair repair setting, not unknown-tool mitigation.

## Updated Reviewer-Risk Assessment

Reduced risks:

- The v1 schema gaps for increment rows are repaired.
- The missing merge script and mainconf statistical audit are repaired.
- P0 tracked key cells now meet N+ >= 50 in v2.
- Static replay traces now meet the 50+ count and required metadata-field gate.

Remaining main-conference blockers:

- No observed execution trace subset yet.
- Strong OOD/domain-generalization baselines are not implemented.
- pIIA controls are still missing for v2.
- Strict LOPO remains evaluable for only 2 effects because most effects have only two positive tools.
- Threshold calibration remains default `LogisticRegression.predict`, so results are diagnostics rather than deployment estimates.

