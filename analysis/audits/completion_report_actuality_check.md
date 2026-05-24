# Completion Report Actuality Check

> Date: 2026-05-15  
> Checked file: `analysis/completion_report.md`  
> Scope: verify the reported Main-Conference Data Increment against actual files, schemas, counts, and result JSONs.

---

## Verdict

The report is **partially correct but overstates completion**.

Facts verified:

- `data/scenarios_mainconf_increment.jsonl` exists with 138 rows.
- `data/agent_tool_traces_mainconf.jsonl` exists with 13 rows.
- `data/scenarios_mainconf_v1.jsonl` exists with 610 rows.
- Qwen3-8B embeddings for `scenarios_mainconf_v1` exist and match 610 rows.
- Mainconf LOTO/baseline, FNR-frag, strict LOPO, and multiseed contrastive result JSONs exist.
- The tracked effect-tool N+ counts in the completion table are mostly correct.

Main correction:

> T28/T29 should be treated as **partial / DOING**, not complete. The data increment improves the main small-N cells, but it does not yet satisfy the T28/T29 handoff spec or main-conference trace requirement.

---

## Verified Counts

| File | Actual count | Report claim | Status |
|------|---:|---:|:---:|
| `data/scenarios_mainconf_increment.jsonl` | 138 | 138 | OK |
| `data/agent_tool_traces_mainconf.jsonl` | 13 | 13 | OK |
| `data/scenarios_mainconf_v1.jsonl` | 610 | 610 | OK |
| `data/scenarios_merged.jsonl` | 459 | baseline source | OK |

Source markers in `scenarios_mainconf_v1`:

| Source field | Counts | Note |
|------|------|------|
| `_source` | `scenarios_merged=459`, `mainconf_increment=138`, `agent_tool_trace=13` | Present in merged data |
| `source` | `rule_based=138`, `missing=472` | Not normalized across original rows and traces |

The merged file therefore preserves source information via `_source`, but downstream scripts that expect `source` will see most rows as missing.

---

## Cell Count Improvements

The reported new N+ counts are correct for the tracked cells:

| Effect | Tool | Actual N+ | Actual N- | Completion status |
|------|------|---:|---:|------|
| `content_fetched` | `terminal` | 31 | 187 | Target N+ >= 30 met |
| `tool_error` | `web_search` | 34 | 51 | Target N+ >= 30 met |
| `network_egress` | `web_search` | 51 | 34 | Target N+ >= 50 met |
| `file_deleted` | `terminal` | 31 | 187 | Target N+ >= 30 met |
| `file_written` | `terminal` | 42 | 176 | Target N+ >= 30 met |
| `file_written` | `write_file` | 34 | 12 | Already near target; only +1 trace/sample in v1 |
| `file_content_read` | `read_file` | 33 | 13 | Already near target; only +1 trace/sample in v1 |

Important caveat:

- `analysis/select_main_conference_cells.py` incorrectly reports `file_written/write_file` and `file_content_read/read_file` as current N+=0 because it only searches `low_positive_cells`, which excludes cells already above N+=30.
- `generate_main_conference_data_increment.py` only targets 5 cells, not all 7 listed target cells.
- `completion_report.md` says “8/8 tracking cells,” but the table contains 7 cells.

---

## Result JSON Check

### LOTO / Baseline

`analysis/baseline_comparison_qwen3-8b_scenarios_mainconf_v1.json` matches the report's main LOTO/baseline numbers.

Examples:

| Effect/tool | Actual heldout FNR |
|------|---:|
| `content_fetched/terminal` | 0.3871 |
| `tool_error/web_search` | 0.0294 |
| `network_egress/web_search` | 0.4118 |
| `file_deleted/terminal` | 0.3871 |
| `file_written/terminal` | 0.0714 |
| `file_written/write_file` | 0.9412 |
| `file_content_read/read_file` | 0.8485 |

### Strict LOPO

`analysis/contrastive_strict_lopo_qwen3-8b_scenarios_mainconf_v1.json` reports:

- evaluable effects: 2;
- strict tool cases: 68;
- improved: 33/68;
- mean delta FNR: 0.1255.

This is consistent with the completion report, but it is **not** stronger than the previous strict result. The improvement count decreased from 40/68 to 33/68.

### Multiseed Projection

`analysis/contrastive_multiseed_qwen3-8b_scenarios_mainconf_v1.json` exists and uses seeds `[0,1,2,3,4]`.

The report's contrastive table mostly matches the **full-training** multiseed results. It must still be described as observed-pair repair, not unknown-tool mitigation.

### Theorem 1 Table

Most risk table values match `analysis/fnr_frag_qwen3-8b_scenarios_mainconf_v1.json`, but one value is inconsistent:

- Report: `content_fetched/terminal` alpha = 0.806.
- Actual `alpha_loto`: 0.5806.
- Actual `alpha_deployed_aux`: 1.0.

The final `[beta-alpha]+` remains 0 either way, but the reported alpha value should be corrected before paper use.

---

## Schema / Handoff Spec Check

### Task B Increment Data

`data/scenarios_mainconf_increment.jsonl` fails part of the required schema:

| Required field | Missing rows |
|------|---:|
| `tool_call` | 138 |
| `call_flow` | 138 |

Additional quality issue:

- 7 rows contain unresolved brace placeholders such as `{endpoint}`.

### Task C Trace Data

`data/agent_tool_traces_mainconf.jsonl` is useful as a seed set, but fails the T29 main-conference trace requirement:

| Requirement | Actual |
|------|------|
| total traces | 13, required 50-100 |
| trace types | all `static_replay`; no observed execution or sandbox simulation |
| `tool_schema` | missing in 13/13 |
| `pre_state` | missing in 13/13 |
| `authorization_scope` | missing in 13/13 |
| `observed_or_simulated_effects` | missing in 13/13 |

Therefore T29 is not complete. It is a small static-replay seed set.

### Task D Merge / Audit

Problems:

- `merge_main_conference_data.py` does not exist in the repository.
- `analysis/statistical_uncertainty_audit.py` has no `--data` argument and is hard-coded to `scenarios_merged`.
- No `analysis/statistical_uncertainty_audit_mainconf_v1.json` or `.md` exists.

Therefore the report's claim that the new dataset passed the mainconf FNR/statistical audit is not supported by a T27-style audit artifact. Existing LOTO/FNR-frag result JSONs exist, but that is not the same as the planned statistical audit.

---

## Actual Task Status

| Task | Reported implication | Actual status | Reason |
|------|------|------|------|
| T28 data expansion | P0 complete | DOING / partial | Key N+ cells improved, but schema incomplete and target script has bugs |
| T29 real/semi-real traces | P0 complete | DOING / partial | Only 13 static replay traces; missing required fields |
| T30 strict mitigation / baselines | implied partial complete | TODO / partial evidence only | strict and multiseed rerun exist, but strong baselines not implemented |
| T33 artifact/repro | not complete | TODO | merge script missing; mainconf audit unsupported |

---

## Required Corrections Before Next Phase

1. Fix `analysis/select_main_conference_cells.py` to read all dataset cells, not only `low_positive_cells`.
2. Add `tool_call` and `call_flow` to every row in `data/scenarios_mainconf_increment.jsonl`.
3. Remove unresolved placeholders from generated scenario text.
4. Expand `data/agent_tool_traces_mainconf.jsonl` from 13 static traces to at least 50 traces, with required fields.
5. Add `merge_main_conference_data.py` or document the exact merge script/command used to produce `data/scenarios_mainconf_v1.jsonl`.
6. Extend `analysis/statistical_uncertainty_audit.py` with `--data scenarios_mainconf_v1` and output `analysis/statistical_uncertainty_audit_mainconf_v1.{json,md}`.
7. Correct `content_fetched/terminal` alpha in `analysis/completion_report.md` if it will be used as a source for paper writing.
8. Do not claim “P0 all complete” until the above checks pass.

---

## Follow-up Repair Status

> Updated: 2026-05-15  
> Current repaired chain: `scenarios_mainconf_v2`. See `analysis/mainconf_v2_repair_report.md`.

The above v1 defects have been addressed in a new v2 chain rather than by silently overwriting v1 artifacts.

| v1 defect | v2 repair |
|---|---|
| target selection missed cells already above N+ = 30 | `analysis/select_main_conference_cells.py` now reads all cell counts |
| increment rows lacked `tool_call` / `call_flow` | `data/scenarios_mainconf_increment_v2.jsonl` includes both fields |
| unresolved placeholders in increment text | v2 manifest reports zero unresolved brace placeholders |
| only 13 static replay traces | `data/agent_tool_traces_mainconf_v2.jsonl` contains 65 static replay traces |
| trace rows missed required metadata | v2 trace manifest reports no missing required schema fields |
| merge script absent | `merge_main_conference_data.py` added |
| mainconf statistical audit absent | `analysis/statistical_uncertainty_audit.py --data scenarios_mainconf_v2` now emits v2 JSON/MD |

Current caution:

- v2 traces are still **static replay**, not observed execution.
- v2 repairs T28 and the static-replay phase of T29, but does not complete strong baselines, pIIA controls, or observed trace validation.
