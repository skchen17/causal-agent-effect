# Auth-SafeInv Completion Actuality Check

> Date: 2026-05-17  
> Checked file: `analysis/completion_report.md`  
> Scope: verify the reported Auth-SafeInv full round T38-T45 against actual files, schemas, counts, scripts, and result artifacts.

> Subsequent progress note: after this audit, T38-T42 were repaired by Codex and T43 was upgraded to partial controls. Current live status is maintained in `analysis/后续推进规划.md` and `analysis/current_status_and_gaps.md`; the former standalone AI execution guide was later deleted per user request, so this file remains only the audit record for the overclaimed external-AI report.

---

## Verdict

The completion report is **partially correct but substantially overstates completion**.

The round produced useful seed artifacts:

- authorization counterfactual data exists;
- Qwen3-8B embeddings for that data exist and are length-consistent;
- a small auth execution trace file exists;
- first-pass Auth-SafeInv, pIIA-control-like, and auth baseline JSONs exist;
- `analysis/formalization.md` contains an Auth-SafeInv section.

However, by the acceptance gates that were later consolidated into `analysis/后续推进规划.md`, the round is **not complete**. It is a prototype / seed pass, not a main-conference-sufficient Auth-SafeInv implementation.

Main blockers:

1. T40 is far below the required execution-trace bar: only 10 traces, with 6 sandbox and 4 static replay; manifest itself says `main_conference_sufficient=false`.
2. T42 is unsupported: no `analyze_surface_graph_alignment.py` or `analysis/surface_graph_alignment_*.json/.md` exists.
3. T43 is only directional cosine analysis, not pIIA controls with matched norm, layer sweep, token aggregation, or intervention outcomes.
4. T44 is not strong-baseline complete: no domain-adversarial, supervised contrastive, true GroupDRO, IRM, or real abstention/open-set baseline.
5. T41 does not implement LOTO Auth-SafeInv, AuthToolProxyGap, CI, threshold sweep, or seed variance.
6. T45 modified the paper before the T39-T44 evidence gate was met, and the old abstract / safety theorem language remains.

---

## Task-by-Task Actual Status

| Task | Reported | Actual | Evidence |
|---|---:|---:|---|
| T38 Auth-SafeInv formalization | Done | **Partial / DOING** | `analysis/formalization.md` adds Auth-SafeInv, but old safety system and Theorem 1 sections still use `critical effects`; `paper/main.tex` still says `Safety Theorems` and old policy. |
| T39 authorization counterfactual dataset | Done | **Partial / DOING** | 960 rows exist, but all 960 rows miss `split_group`; unauthorized counts are below 30 for most focus effects. |
| T40 sandbox/observed execution verifier | Done | **Partial / DOING** | 10 traces only; 6 sandbox + 4 static; only 1 unauthorized trace; manifest says `main_conference_sufficient=false`. |
| T41 Auth-SafeInv evaluation | Done | **Partial / DOING** | JSON exists for 7 effects, but uses one 80/20 split; no LOTO, AuthToolProxyGap, CI, seed variance, or threshold sweep. |
| T42 surface graph alignment | Done | **Not Done / TODO** | No `analyze_surface_graph_alignment.py` and no `analysis/surface_graph_alignment_*.json/.md`. |
| T43 pIIA controls | Done | **Partial / DOING** | JSON exists but reports direction cosine proxies only; no actual intervention controls, matched norm, layer sweep, or token aggregation ablation. |
| T44 strong baselines | Done | **Partial / DOING** | JSON exists for pooled / simplified IRM-style / calibrated threshold only; no domain-adversarial, supervised contrastive, true GroupDRO, IRM objective, or real abstention. |
| T45 paper rewrite | Done | **Premature / BLOCKED** | Paper intro has one auth paragraph, but old abstract, title, `Safety Theorems`, and critical-effect formalism remain. Gate required T39-T44 first. |

---

## Verified Files

### Data and Embeddings

| Artifact | Actual status |
|---|---|
| `data/authorization_counterfactuals_v1.jsonl` | exists, 960 rows |
| `analysis/authorization_counterfactuals_v1_manifest.json` | exists |
| `embeddings/embeddings_qwen3-8b_authorization_counterfactuals_v1.npy` | exists, shape `(960, 4096)` |
| `embeddings/effects_qwen3-8b_authorization_counterfactuals_v1.npy` | exists, shape `(960, 11)` |
| `embeddings/texts_qwen3-8b_authorization_counterfactuals_v1.jsonl` | exists, 960 rows |
| `data/agent_tool_traces_auth_v1.jsonl` | exists, 10 rows |
| `analysis/agent_tool_traces_auth_v1_manifest.json` | exists |

### Result JSONs

| Artifact | Actual status |
|---|---|
| `analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v1.json` | exists |
| `analysis/auth_baselines_qwen3-8b_authorization_counterfactuals_v1.json` | exists |
| `analysis/piia_controls_qwen3-8b_scenarios_mainconf_v2.json` | exists |
| `analysis/surface_graph_alignment_*.json` | **missing** |

### Missing Markdown Reports

Expected by the original acceptance plan but missing at the time:

- `analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v1.md`
- `analysis/auth_baselines_qwen3-8b_authorization_counterfactuals_v1.md`
- `analysis/piia_controls_qwen3-8b_scenarios_mainconf_v2.md`
- `analysis/surface_graph_alignment_*.md`

---

## T39 Dataset Audit

`authorization_counterfactuals_v1` has 960 rows and four families:

| Family | Rows | Gate |
|---|---:|---|
| `same_task_tool_swap` | 210 | >=100 met |
| `same_tool_auth_flip` | 196 | >=100 met |
| `same_effect_reframing` | 400 | >=100 met |
| `same_task_effect_substitution` | 154 | >=100 met |

Required schema issue:

| Field | Missing rows |
|---|---:|
| `split_group` | 960 |

The guide required `split_group` to prevent counterfactual-family leakage. This is currently absent.

Authorized effect counts:

| Effect | Authorized count |
|---|---:|
| `network_egress` | 242 |
| `file_content_read` | 200 |
| `file_deleted` | 200 |
| `file_written` | 186 |
| `content_fetched` | 128 |
| `message_sent` | 58 |
| `tool_error` | 30 |
| `search_performed` | 28 |

Unauthorized effect counts:

| Effect | Unauthorized count | Gate >=30? |
|---|---:|---:|
| `network_egress` | 112 | yes |
| `tool_error` | 28 | no |
| `file_deleted` | 14 | no |
| `file_written` | 14 | no |
| `message_sent` | 14 | no |
| `command_executed` | 14 | no |
| `content_fetched` | 14 | no |

Conclusion:

- The dataset is a useful seed dataset.
- It does **not** satisfy the stated requirement that each focus effect have authorized and unauthorized positives >= 30.
- Most unauthorized positives are concentrated in `network_egress`, mostly through `terminal`.

---

## T40 Trace Audit

`agent_tool_traces_auth_v1` has 10 traces:

| Trace type | Count |
|---|---:|
| `sandbox_simulated` | 6 |
| `static_replay` | 4 |

Manifest states:

```json
"main_conference_sufficient": false
```

Unauthorized effect coverage:

| Unauthorized effect | Count |
|---|---:|
| `network_egress` | 1 |

Conclusion:

- This is far below the required `observed_execution + sandbox_simulated >= 50`.
- It cannot support main-conference claims about execution-level causal effects.
- It should be described as a trace schema prototype, not as T40 completion.

---

## T41 Auth-SafeInv Evaluation Audit

The JSON reports:

| Effect | Unauthorized N | Unauth FNR | Unsafe-Allow LB |
|---|---:|---:|---:|
| `network_egress` | 112 | 0.4444 | 0.1788 |
| `tool_error` | 28 | 0.0000 | 0.0000 |
| `file_deleted` | 14 | 0.0000 | 0.0000 |
| `file_written` | 14 | 0.0000 | 0.0000 |
| `message_sent` | 14 | 0.0000 | 0.0000 |
| `content_fetched` | 14 | 0.0000 | 0.0000 |
| `command_executed` | 14 | 0.0000 | 0.0000 |

Limitations:

- Only one random 80/20 split.
- No leave-one-tool-out unauthorized FNR.
- No leave-one-counterfactual-family-out.
- No leave-one-trace-type-out.
- No AuthToolProxyGap.
- No Wilson CI.
- No seed mean/std.
- No validation-selected FNR/FPR tradeoff curve.
- No markdown report.

Conclusion:

- It provides an initial smoke test.
- It is not the Auth-SafeInv evaluation specified in the guide.

---

## T42 Surface Graph Alignment Audit

Completion report claims:

> Surface graph alignment (6 effects) done.

Actual:

- No `analyze_surface_graph_alignment.py`.
- No `analysis/surface_graph_alignment_qwen3-8b_mainconf_v2.json`.
- No `analysis/surface_graph_alignment_qwen3-8b_mainconf_v2.md`.

Conclusion:

> T42 is not completed.

---

## T43 pIIA Controls Audit

The existing `piia_controls_qwen3-8b_scenarios_mainconf_v2.json` contains:

- random direction norm / cosine;
- wrong-effect direction cosine;
- cross-tool direction cosine for some effects.

Missing required controls:

- actual pIIA intervention outcomes;
- matched-norm random intervention outcome;
- same-effect wrong-form intervention control;
- different-effect same-form intervention control;
- layer sweep;
- token aggregation ablation;
- pIIA-Drop correlation with AuthToolProxyGap or unauthorized FNR;
- markdown report.

Conclusion:

- This is a direction-cosine diagnostic, not pIIA controls.
- T43 remains partial.

---

## T44 Strong Baseline Audit

The existing `auth_baselines_qwen3-8b_authorization_counterfactuals_v1.json` reports only:

- pooled logistic;
- `irm_style_fnr`;
- calibrated threshold FNR.

Issues:

- `irm_style_fnr` is not true IRM; the script implements a simplified sample-weighted logistic probe.
- No domain-adversarial representation learning.
- No supervised contrastive with held-out domains.
- No true GroupDRO / worst-group optimization.
- No calibrated abstention or open-set detection output.
- No LOTO / family holdout split.
- No seed variance.
- No markdown report.

Conclusion:

- T44 is partial and should not be described as strong baselines completed.

---

## T45 Paper Sync Audit

`paper/main.tex` gained an authorization-conditioned paragraph in the introduction, but old high-risk wording remains:

- title still says `Safety Theorems`;
- abstract still claims `safe only if`;
- abstract still uses old 459-row and 40/68 strict result as headline;
- contribution list still says `Two safety theorems`;
- safety system definition still uses `critical effects`, not `A(c)`;
- Theorem 1 still conditions on `E critical`, not `E notin A(c)`;
- metrics section still reports old LOTO stress-test quantities, not Auth-SafeInv metrics.

Conclusion:

- T45 is premature and incomplete.
- The paper should not yet be rewritten around Auth-SafeInv results until T39-T44 are corrected.

---

## Corrected Task Status

| Task | Corrected status |
|---|---|
| T38 | DOING / partial |
| T39 | DOING / partial |
| T40 | DOING / partial; main-conference insufficient |
| T41 | DOING / smoke test only |
| T42 | TODO / missing |
| T43 | DOING / direction-cosine prototype only |
| T44 | DOING / weak baseline prototype only |
| T45 | BLOCKED until T39-T44 pass gates |

---

## Required Next Fixes

1. Add `split_group` to every authorization counterfactual row and manifest leakage checks.
2. Rebalance unauthorized effect counts so each focus effect has unauthorized N >= 30 and at least two tool surfaces where feasible.
3. Expand `agent_tool_traces_auth_v1` to at least 50 sandbox/observed traces; static replay does not count toward that gate.
4. Implement real LOTO / family-holdout Auth-SafeInv evaluation and compute AuthToolProxyGap.
5. Add CI, seed variance, and validation-selected threshold / FNR-FPR curves.
6. Implement `analyze_surface_graph_alignment.py` and produce JSON/MD artifacts.
7. Replace direction-cosine pIIA controls with actual intervention controls, layer sweep, and token aggregation ablations.
8. Implement genuine strong baselines or rename current outputs as weak prototypes.
9. Do not use current `completion_report.md` as a source of truth for paper writing.

---

## Subsequent Codex Progress Update (2026-05-17)

This audit remains the record of the earlier overclaim, but several findings have since been repaired:

- T38-T42 were rerun and now have auditable outputs listed in `analysis/后续推进规划.md`.
- T43 now has a hook-based control pilot: `interchange_intervention_hook_controls.py` and `analysis/piia_hook_controls_qwen3-8b_scenarios_mainconf_v2.{json,md}`. It covers matched-norm random, same-effect wrong-form, different-effect same-form, layer sweep, and token aggregation, but only at pilot scale.
- T44 now has a split-matched strong baseline pilot: `experiment_auth_baselines.py` and `analysis/auth_baselines_qwen3-8b_authorization_counterfactuals_v1.{json,md}` with 678 method rows across random group, LOTO, and family-holdout splits.
- T47 adds a compact confirmatory baseline sweep: `experiment_auth_baseline_confirmatory.py` and `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v1.{json,md}` with 504 fixed-threshold rows and 9408 threshold-curve rows.
- T48 adds a compact pIIA hook-control scale-up: `analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.{json,md}` with 864 raw hook rows and 6 effects.
- T49 adds controlled observed local-sandbox traces: `data/agent_tool_traces_auth_observed_v1.jsonl` has 70 observed rows and `data/agent_tool_traces_auth_v2.jsonl` has 138 combined rows.
- T50 adds reproducibility artifacts: `reproduce_auth_safeinv.sh` and `analysis/auth_result_source_appendix.{json,md}` with `all_outputs_present=True`.
- T51 adds same-cell mitigation-vs-baseline comparison: `experiment_auth_mitigation_comparison.py` and `analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v1.{json,md}`. The task is completed, but the strict mitigation gate fails: strict train-only projection covers only 4/14 LOTO cells and cannot support a broad main-method claim.
- T52 adds threshold reporting policy: `analysis/auth_threshold_policy.md`.
- T53 adds authorization surface-graph expansion: `build_authorization_counterfactuals_v2.py`, `data/authorization_counterfactuals_v2.jsonl`, and `analysis/authorization_counterfactuals_v2_manifest.{json,md}`. v2 has 1464 rows and all 7 focus effects have unauthorized tools >=3.
- T54 adds v2 embeddings and reruns: `embeddings/*qwen3-8b_authorization_counterfactuals_v2*`, `analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v2.{json,md}`, `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.{json,md}`, and `analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v2.{json,md}`. The strict train-only LOTO coverage improves to 21/21 cells, but strict contrastive still loses to the best non-degenerate baseline at FPR <= 0.10.

Remaining caveat: these are not final paper-grade artifacts for a strong method paper until T55/T56 produce a mitigation that beats T47/T54 baselines under identical held-out cells. The observed traces are controlled local sandbox executions, not live deployed-agent logs.
