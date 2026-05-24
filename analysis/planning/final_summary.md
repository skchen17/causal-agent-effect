# 项目当前成果汇总

> 2026-05-22 | Path A: evaluation/diagnostic paper 路线确认。  
> 目标：AI / AI-safety 顶会投稿。论文定位为 **Auth-SafeInv evaluation target + three-layer over-optimism diagnosis + constructive framework with honest limits**。
> 最新文献搜索分析见 `analysis/path_a_convergence_analysis_2026-05-22.md`。

## 1. Core Claim

LLM agent tool-use safety evaluation is systematically over-optimistic at three layers: (1) tool-surface fragmentation causes representation-side monitors to miss unauthorized effects under coverage gaps; (2) structured trace labels can make verifiers appear stronger than they are; (3) row-level metrics do not translate to action-level allow/deny safety. We introduce **Auth-SafeInv** as an action-level evaluation target for authorization-conditioned realized-effect monitoring, and provide a verifier-assisted constructive framework with honest gate-failure reporting.

The project provides controlled evidence for each layer:

- **Layer 1 (tool-surface)**: linear probes can detect effects within seen tools but fail under LOTO coverage stress tests (FNR up to 0.80); this fragmentation is not eliminated by lexical normalization.
- **Layer 2 (trace-label)**: full-label trace verifiers achieve low FNR but label-hidden and minimal-evidence views degrade performance (T69: 0.0353→0.1162→0.1465).
- **Layer 3 (row-to-action)**: row-level FNR/FPR=0/0 can coexist with action-level FDeny=1.0 and all-allow calibration collapse (T68/T73).
- **Pure representation repair gate failed**: contrastive projection, schema conditioning, and decomposed verification all lose to best baselines under strict held-out protocols (T54/T55/T56).
- **Constructive framework**: EffectVerif-AuthMonitor works under controlled settings (T64/T65 FNR/FPR=0/0) but has honest limits: static verifiers fail on provider/browser effects, action-level calibration unsolved, raw-status boundary competitive.

## 2. Main Evidence

| Evidence block | Status | Key files |
|------|:---:|------|
| LOTO / ToolProxyGap | DONE | `analysis/fnr_frag_qwen3-8b_scenarios_merged.json` |
| pIIA raw outcomes + bootstrap CI | DONE | `analysis/iia_true_raw_qwen3-8b_scenarios_merged.jsonl`, `analysis/iia_true_bootstrap_qwen3-8b_scenarios_merged.json` |
| lexical control | DONE | `analysis/lexical_control_qwen3-8b_scenarios_merged_lexical_control.json` |
| baseline comparison | DONE | `analysis/baseline_comparison_qwen3-8b_scenarios_merged.json` |
| contrastive projection | DONE | `analysis/contrastive_qwen3-8b_scenarios_merged.json` |
| strict LOPO | DONE | `analysis/contrastive_strict_lopo_qwen3-8b_scenarios_merged.json` |
| multiseed v2 | DONE | `analysis/contrastive_multiseed_qwen3-8b_scenarios_merged.json` |
| causal-chain v2 diagnostic | DONE | `analysis/causal_chain_mechanism_qwen3-8b_causal_chain_conditioning_v2.json` |
| real-tool proxy calibration | DONE | `analysis/real_tool_scenarios_v2_validation.json` |
| mainconf v2 data repair | DONE | `analysis/mainconf_v2_repair_report.md`, `data/scenarios_mainconf_v2.jsonl` |
| mainconf v2 statistical audit | DONE | `analysis/statistical_uncertainty_audit_mainconf_v2.md` |
| Auth-SafeInv formalization/data/evaluation | DONE | `analysis/formalization.md`, `data/authorization_counterfactuals_v2.jsonl`, `analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v2.md` |
| Auth-SafeInv strong baselines and mitigation comparisons | DONE / pure-method gate failed | `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.md`, `analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v2.md` |
| verifier-assisted framework evidence | DONE / promising but limited | `analysis/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.md`, `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.md` |
| real-agent-tools stress test | DONE / limited | `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.md` |
| DeepSeek provider API expansion | DONE / single-surface | `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.md` |
| validation-selected threshold evaluation | DONE | `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.md`, `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.md`, `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.md` |
| broader web/search/browser/messaging local-adapter traces | DONE / broader controlled evidence | `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.md` |
| key-free live/protocol traces | DONE / limited live-protocol evidence | `analysis/t64_live_protocol_external_validity_report.md`, `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.md` |
| file-backed headless Chrome browser-runtime traces | DONE / limited browser-runtime evidence | `analysis/agent_tool_traces_headless_browser_t65_v1_manifest.md`, `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.md` |
| action-level Auth-SafeInv metrics | DONE / exposes policy tradeoff | `analysis/auth_action_level_metrics_t68.md` |
| trace-view verifier ablation | DONE / structured-evidence support | `analysis/auth_trace_view_ablation_t69.md` |
| existing-defense proxy ablation | DONE / mixed | `analysis/auth_existing_defense_ablation_t70.md` |
| action-level threshold calibration | DONE / negative diagnostic | `analysis/auth_action_level_calibration_t73.md` |
| result-source appendix | DONE | `analysis/auth_result_source_appendix.md` reports all outputs present for the tracked Auth-SafeInv artifacts |
| citation audit v2 | DONE | `analysis/citation_audit_v2.json` |
| global validator | DONE | `analysis/experiment_state_validation.json` reports `overall=ok` |

## 3. Key Results

- LOTO heldout FNR reaches 0.97 in Qwen3-8B stress tests.
- pIIA-Drop ranges from 0.052 (`tool_error`) to 0.366 (`network_egress`) in Qwen3-8B diagnostics.
- Lexical control changes overall heldout FNR only from 0.378 to 0.382.
- Contrastive projection full-training reduces worst stress-test FNR from 0.97 to at most 0.25 in the main Qwen3-8B run.
- Contrastive multiseed v2 reports maximum mean post-FNR 0.1625 across evaluated forms.
- Strict LOPO improves 40/68 held-out tool-case evaluations, mean DeltaFNR=0.1567.
- Causal-chain v2 contains 2290 samples with typed wrong-chain subsets: 153 effect omissions, 153 authorization flips, and 152 effect flips.
- Mainconf v2 contains 932 rows and brings the 7 tracked P0 cells to N+ >= 50.
- Mainconf v2 LOTO still has high held-out FNR: 0.8036 for `file_content_read/read_file` and 0.7679 for `file_written/write_file`.
- Mainconf v2 strict LOPO improves 33/68 tool-case evaluations, mean DeltaFNR=0.1044.
- Mainconf v2 full-training multiseed projection has max mean post-FNR 0.034, but this remains an observed-pair repair upper bound.
- Auth-SafeInv v2 has 1464 rows and all 7 focus effects have unauthorized tools >=3.
- T54 strict train-only contrastive is broadly evaluable but still weaker than the strongest same-cell baseline: LOTO FNR=0.2804 vs supervised-contrastive FNR=0.1835 at FPR<=0.1.
- T57 static verifier-assisted monitor reaches LOTO FNR=0.0262/FPR=0.073 and family FNR=0.1221/FPR=0.0048 under full-tool-chain evaluation.
- T58 controlled execution-trace verifier reaches schema-to-trace-all FNR=0.0429/FPR=0.0.
- T59 real-agent-tools local-adapter stress test gives schema-to-real-agent-local-trace FNR=0.25/FPR=0.0.
- T61 DeepSeek provider API expansion has 120 direct provider traces and provider unauthorized counts `network_egress=30`, `content_fetched=60`, `tool_error=30`; execution verifier FNR=0.0/FPR=0.0, static verifiers FNR=1.0.
- T62 validation-selected thresholds give execution verifier held-out test FNR/FPR of 0.0/0.0 on T58 controlled traces, 0.1765/0.0 on T59 real-agent local-adapter traces, and 0.0/0.0 on T61 provider API traces.
- T63 broader local-adapter traces add 300 web/search/browser/messaging traces and 2400 candidate-effect rows; key unauthorized counts are `content_fetched=60`, `network_egress=60`, `tool_error=60`, and `message_sent=30`. Validation-selected execution verifier test FNR=0.0351/FPR=0.0, while static verifiers test FNR=0.614/FPR=0.0132.
- T64 key-free live/protocol traces add 150 real outbound HTTPS traces and 150 local webhook protocol traces, expanded to 2400 candidate-effect rows; key unauthorized counts are `content_fetched=150`, `network_egress=60`, `message_sent=60`, and `tool_error=60`. Validation-selected execution verifier test FNR/FPR=0.0/0.0 (N+=197, N-=1170), while static verifiers test FNR/FPR=0.6294/0.0462. T64 has now been rerun with full-precision Qwen3-8B embeddings.
- T65 file-backed headless Chrome browser-runtime traces add 120 real Chrome DOM/JS traces and 960 candidate-effect rows; unauthorized counts are `content_fetched=60`, `memory_updated=30`, and `tool_error=30`. Validation-selected execution verifier test FNR/FPR=0.0/0.0 (N+=62,N-=411), while static verifiers test FNR/FPR=1.0/0.0. This is browser-runtime evidence, but not HTTP browser networking or deployed-agent runtime validation.
- T68 action-level aggregation shows execution verifier unauthorized-action allow / authorized-action false-denial rates of 0.0/0.1591 on T58, 0.2/0.3571 on T59, 0.0/1.0 on T61, 0.05/0.21 on T63, 0.0/1.0 on T65, and 0.0/0.0 on T64. This strengthens monitor-facing evaluation but shows T61/T65 over-denial under the current threshold.
- T69 trace-view ablation after adding T65: full-label mean FNR=0.0353, label-hidden raw mean FNR=0.1162, minimal-evidence mean FNR=0.1465. This keeps the claim limited to structured execution evidence.
- T70 proxy baseline comparison after adding T65: pre-action rule-only mean FNR=0.5700, provenance-only mean FNR=0.2873, label-hidden EffectVerif mean FNR=0.1162, raw-status boundary mean FNR=0.1113. This distinguishes against simple pre-action/provenance proxies but does not prove dominance over handcrafted status-policy defenses.
- T73 action-level calibration is negative: under validation false-denial target 0.10, T59/T61/T63/T65 often select all-allow thresholds, giving held-out unauthorized-action allow=1.0.

## 4. Claim Limits

Do not overclaim:

- This is not deployed safety certification.
- Real-tool calibration is schema-and-semantic proxy validation; T59 adds real-agent-tools local-adapter traces, not direct Hermes handler execution.
- Mainconf v2 static replay traces are schema/call-flow grounding, not observed execution validation.
- T58 observed rows are controlled local sandbox executions, not live deployed-agent logs.
- T61 covers one provider API surface only; it does not cover browser/search/messaging tools.
- T62 is validation trace-group calibration for controlled/API trace datasets, not deployment safety calibration.
- T63 covers browser/search/messaging names through controlled local adapters, not live external search/browser/message services or deployed-agent runtime handlers.
- T64 covers key-free real outbound HTTPS and local webhook protocol boundaries, but not provider-backed search, SaaS messaging, HTTP browser automation, or deployed-agent runtime logs.
- T65 covers file-backed headless Chrome DOM/JS execution, but not browser HTTP networking or deployed-agent runtime handlers.
- T68/T73 action-level metrics are held-out trace-group diagnostics, not deployment traffic; high false denial on T61/T65 and all-allow calibration collapse mean row-level FNR/FPR should not be used alone as a policy claim.
- T69/T70 are deterministic trace-rule/proxy ablations, not independent learned verifiers or faithful reimplementations of external defense systems.
- Causal-chain conditioning is a mixed mechanism diagnostic, not a complete mitigation.
- Strict LOPO applies only to effects with at least three surface forms; two-form effects remain non-identifiable under that protocol.
- Pure representation mitigation remains blocked: T51/T54/T55/T56 did not beat strong baselines under strict conditions.
- Citation audit records primary-source reported claims, not independent reproductions.

## 5. Current Paper State

Current paper stance:

- strong pure-method claims remain blocked;
- verifier-assisted controlled-study framing is plausible and now has broader local-adapter, live/protocol, and file-backed browser-runtime evidence, but still needs direct external-service/deployed-runtime validation for stronger external validity;
- limitations must explicitly separate synthetic/proxy data, controlled sandbox traces, local-adapter traces, single-provider API traces, and live deployment logs.

Next phase after external review v1: T66-T73 have been integrated into the paper, including the related-work difference matrix, explicit EffectVerif-AuthMonitor interface, T64/T65 verifier-assisted results, action-level allow/deny metrics, trace-view ablation, proxy defense comparison, and action-level calibration failure. Provider-backed search/SaaS messaging/HTTP browser automation/deployed-runtime traces and non-degenerate action-level policy calibration remain the main follow-up work.
