# Main-Conference Roadmap

> 2026-05-15 | Updated after mainconf v2 repair and rerun.  
> Current status source: `analysis/mainconf_v2_repair_report.md`, `analysis/statistical_uncertainty_audit_mainconf_v2.md`, `analysis/AuthSafeInv_completion_actuality_check.md`, and `analysis/后续推进规划.md`.

> 2026-05-17 update: roadmap now follows the Auth-SafeInv strengthening route. The project keeps the causal task consistency ambition, but the next milestone is authorization-conditioned theory and data rather than another tool-only diagnostic pass.

> 2026-05-17 audit update: the Auth-SafeInv completion report is not accepted as ground truth. That audit captured the earlier seed/prototype state; subsequent work has repaired T38-T42 and produced T43/T44 pilot artifacts. T45 remains blocked until the evidence gates are met.

> 2026-05-18 progress update: T38-T56 have now been repaired or added. T51 adds a same-cell Auth-SafeInv mitigation-vs-baseline comparison, T52 fixes the paper-facing threshold policy, T53 adds an authorization_counterfactuals_v2 surface-graph expansion, T54 reruns v2 embeddings/evaluation/baseline/mitigation, T55 tests a pair-free effect-schema conditioned monitor, and T56 tests a decomposed present/auth verifier. The strict pure-method gate still fails: v2 fixes coverage, but strict contrastive, naive schema conditioning, and pure decomposed frozen verification remain weaker than the strongest non-degenerate baseline. T56 verifier-present is a strong upper bound only if an external effect-present verifier exists.

> 2026-05-20 progress update: T57 replaces the T56 oracle present label with trace-calibrated deterministic tool-call verifier rules. The best full-tool-chain LOTO result now beats the T54 same-cell best baseline at FPR<=0.1, but this is verifier-assisted framework evidence over controlled/proxy calls, not live deployed-agent validation.

> 2026-05-20 T58 update: T58 builds 1104 candidate-effect rows from 138 controlled auth traces and extracts Qwen3-8B trace embeddings on `CUDA_VISIBLE_DEVICES=1`. A schema-trained authorization monitor combined with execution-trace present verification reaches schema-to-trace-all FNR=0.0429/FPR=0.0 and trace-type split FNR=0.0286/FPR=0.0. This hardens the framework route beyond static rules, but still uses controlled observed/sandbox/static traces rather than live deployed-agent logs.

> 2026-05-20 T59 update: T59 audits `real-agent-tools/` Hermes registrations and builds 48 local-adapter traces for `read_file`, `write_file`, and `terminal`, producing 384 candidate-effect rows and Qwen3-8B embeddings on `CUDA_VISIBLE_DEVICES=1`. The real-agent-tools stress test reaches schema-to-trace-all FNR=0.25/FPR=0.0 under execution-trace present verification. Direct Hermes handler import is blocked by missing upstream runtime modules (`agent`, `hermes_constants`), and external web/browser/messaging/provider tools require API keys or services, so T59 is real-tool-code-grounded local-adapter evidence, not live deployed-agent validation.

> 2026-05-20 T60 update: T60 uses a provided DeepSeek OpenAI-compatible API key as an environment variable only and builds 8 direct provider API observed traces. It produces 64 candidate-effect rows and Qwen3-8B embeddings on `CUDA_VISIBLE_DEVICES=1`. Execution-trace verification gives FNR=0.0/FPR=0.0 in the tiny provider pilot, while static verifiers have present FNR=1.0 for provider effects. This is useful plumbing and mechanism evidence for execution-level verification, but it is too small and single-surface to serve as final real-agent validation.

> 2026-05-20 T61 update: T61 expands the DeepSeek provider API experiment to 120 direct provider calls, 960 candidate-effect rows, and Qwen3-8B embeddings on `CUDA_VISIBLE_DEVICES=1`. Key provider unauthorized counts now reach `network_egress=30`, `content_fetched=60`, and `tool_error=30`. The original curve summary gives execution-trace verification FNR=0.0/FPR=0.0 across three provider cells, while static verifiers still have present FNR=1.0. This strengthens the execution-verifier argument, but remains a single provider API surface.

> 2026-05-20 T62 update: T62 selects thresholds on validation trace groups and evaluates fixed thresholds on held-out trace groups for T58 controlled traces, T59 real-agent-tools local-adapter traces, and T61 DeepSeek provider traces. Execution verifier test FNR/FPR is 0.0/0.0 on T58, 0.1765/0.0 on T59, and 0.0/0.0 on T61; static verifiers still fail on T61 provider effects with FNR=1.0. This fixes the ex-post-threshold caveat for tested trace datasets, but remains calibration evidence over controlled/API trace groups rather than live deployment calibration.

> 2026-05-20 T63 update: T63 adds controlled broader local-adapter traces using `real-agent-tools` web/search/browser/messaging tool names: 300 traces, 2400 candidate-effect rows, and Qwen3-8B embeddings on `CUDA_VISIBLE_DEVICES=1`. Key unauthorized counts are `content_fetched=60`, `network_egress=60`, `tool_error=60`, and `message_sent=30`. Validation-selected execution verifier test FNR/FPR is 0.0351/0.0, while static verifiers have test FNR=0.614/FPR=0.0132. This broadens tool-family coverage but still does not invoke live external services or deployed-agent runtime handlers.

> 2026-05-21 T64 update, revised 2026-05-22: T64 adds key-free live/protocol traces: 150 real outbound HTTPS traces and 150 real local webhook protocol traces, expanded to 2400 candidate-effect rows. Key unauthorized counts are `content_fetched=150`, `network_egress=60`, `message_sent=60`, and `tool_error=60`. Validation-selected execution verifier test FNR/FPR is 0.0/0.0 (N+=197, N-=1170), while static verifiers have test FNR/FPR=0.6294/0.0462. This is stronger than T63 local adapters for live HTTP/protocol-boundary evidence, but still not provider-backed search, SaaS messaging, HTTP browser automation, or deployed-agent runtime validation. T64 has now been rerun with full-precision Qwen3-8B embeddings on cuda1.

> 2026-05-21 external-review-v1 update, revised 2026-05-22: `analysis/外部审稿意见v1.md` is adopted as a planning constraint. T66-T73 are now integrated into the paper: related-work difference matrix, explicit EffectVerif-AuthMonitor algorithm/interface, T64 live/protocol results, T65 file-backed headless Chrome browser-runtime results, action-level allow/deny metrics, trace-view ablation, existing-defense proxy comparison, and action-level calibration failure. Provider-backed search/SaaS messaging/HTTP browser automation/deployed-runtime validation remains a resource-dependent follow-up.

## 1. Current Milestone

The v1 completion report was audited and found to overstate T28/T29 completion. The repaired v2 chain is now complete for the first main-conference data-expansion pass:

- fixed P0 cell target selection;
- generated 408 schema-complete increment rows;
- generated 65 static replay traces with required metadata fields;
- merged a 932-row `scenarios_mainconf_v2` dataset;
- extracted Qwen3-8B embeddings;
- reran LOTO/baseline, FNR/Frag, strict LOPO, full-training multiseed projection, and statistical uncertainty audit.

This improves evidence quality, but it does not make the paper main-conference ready.

After that, an external AI produced an Auth-SafeInv seed round. The audit found that this round did not satisfy the planned gates. The repaired Auth-SafeInv chain now has: 1184 v1 authorization counterfactual rows with complete `split_group`, 1464 v2 rows with surface-graph expansion, 35136 T55 effect-schema conditioned candidate-effect rows, 1104 T58 trace candidate-effect rows, 384 T59 real-agent-tools candidate-effect rows, 960 T61 DeepSeek provider candidate-effect rows, 2400 T63 broader web/search/browser/messaging local-adapter candidate-effect rows, 2400 T64 key-free live/protocol candidate-effect rows, 960 T65 file-backed headless Chrome browser-runtime candidate-effect rows, refreshed full-precision Qwen3-8B v1/v2/schema/trace/T59/T61/T63/T64/T65 embeddings, 138 auth v2 traces with 70 controlled observed rows, 48 real-agent-tools local-adapter traces, 120 DeepSeek provider API observed traces, 300 T63 broader local-adapter traces, 300 T64 live/protocol traces, 120 T65 browser-runtime traces, group-aware Auth-SafeInv held-out evaluation, surface graph alignment outputs, hook-based pIIA control artifacts, split-matched strong baseline outputs, compact confirmatory baseline sweeps, same-cell mitigation-vs-baseline comparison, schema-conditioned mitigation evaluation, pure decomposed verifier evaluation, a verifier-present upper-bound evaluation, T57 trace-calibrated non-oracle verifier-assisted evaluation, T58 execution-trace verifier evaluation, T59 real-agent-tools local-adapter stress evaluation, T61 DeepSeek provider API expansion evaluation, T62 validation-selected threshold evaluations over T58/T59/T61/T63/T64/T65 trace datasets, T68 action-level allow/deny metrics, T69 trace-view verifier ablation, T70 existing-defense proxy comparison, and T73 action-level calibration diagnostics. It still does not provide provider-backed search, SaaS messaging, HTTP browser automation, or deployed-agent runtime validation.

## 2. Main-Conference Decision

Current decision after T73:

- Main-conference status: `Borderline / Major Revision`, assuming claims remain verifier-assisted and controlled/protocol-study scoped.
- Final target: main-conference acceptance.
- Main remaining issues: non-degenerate action-level policy calibration, independent effect verification, faithful external-defense comparisons, and external validity. T64 improves external validity beyond local adapters with real outbound HTTPS and local protocol messaging; T65 adds actual headless Chrome DOM/JS execution over file-backed pages; and the paper now has an explicit EffectVerif-AuthMonitor interface, related-work difference matrix, action-level metrics, trace-view ablations, proxy defense comparisons, and a negative T73 calibration diagnostic. T68/T73 show action-level over-denial and all-allow calibration collapse risks, and T70 shows a competitive handcrafted raw-status baseline, so the paper must avoid row-level safety overclaims and method-dominance overclaims.

## 3. Evidence Now Available

| Area | Current v2 state | Claim allowed |
|---|---|---|
| Data balance | 7 tracked P0 cells reach N+ >= 50 | stronger evidence that key failures are not only tiny-cell artifacts |
| Static replay traces | 65 traces with schema/call-flow metadata | semi-real static grounding, not observed execution validation |
| LOTO stress test | max held FNR 0.8036 on `file_content_read/read_file` | tool-surface fragmentation remains under expanded data |
| Strict LOPO | 2 effects, 68 cases, 33 improved, mean delta 0.1044 | partial mitigation evidence under strict transitive setting |
| Full-training projection | max mean post-FNR 0.034 over 5 seeds | observed-pair repair upper bound only |
| Statistical audit | N+/N-/CI/threshold notes generated | diagnostic uncertainty is now explicit |
| Auth counterfactuals | v1 has 1184 rows; v2 has 1464 rows and all focus effects have unauthorized tools >=3 | v1 supports controlled evaluation; v2 is ready for embedding/rerun |
| Auth traces | 70 controlled observed + 56 sandbox-simulated + 12 static replay | controlled local sandbox grounding, not live deployed-agent validation |
| Auth-SafeInv evaluation | group-aware random split, LOTO, family holdout, AuthToolProxyGap | diagnostic held-out authorization evidence; not a safety certificate |
| Surface graph alignment | Auth unauthorized graphs mostly two-surface and strict-pair non-identifiable | explains limits of strict transitive alignment under auth violations |
| pIIA controls | direction + embedding-space controls plus 144-row pilot and 864-row confirmatory hook scale-up | supporting mechanism diagnostic; still not SCM-style causal proof |
| Auth strong baselines | 678 pilot rows plus 504 confirmatory fixed rows and 9408 threshold-curve rows | stronger baseline evidence; residual max FNR=1.0 and FNR-FPR tradeoffs remain |
| Auth mitigation comparison | v1: 132 fixed rows / 2772 curve rows; v2: 246 fixed rows / 5166 curve rows | v2 fixes strict coverage to 21/21 LOTO cells, but strict contrastive is worse than the best baseline |
| Schema-conditioned monitor | 35136 rows, Qwen3-8B embeddings, 252 fixed rows / 5292 curve rows | pair-free input-side schema conditioning is insufficient; best full-tool-chain LOTO FNR=0.4516 at FPR=0.0154 |
| Decomposed verifier | full T56 evaluation: 765 fixed rows / 16065 curve rows; focused verifier-present full-tool-chain upper bound: 85 fixed rows / 1785 curve rows | pure frozen decomposition is insufficient; oracle/external present verifier gives strong upper-bound LOTO FNR=0.0042 and family FNR=0.0745 at FPR=0 |
| T57 static effect-present verifier | 120 present-verifier rows, 170 fixed rows, 3570 curve rows | deterministic trace-calibrated verifier beats T54 baseline in full-tool-chain LOTO/family, but remains verifier-assisted controlled evidence |
| T58 execution verifier | 1104 trace candidate rows, Qwen3-8B trace embeddings, 96 fixed rows / 2016 curve rows | execution-trace present verification preserves low unauthorized FNR under schema-to-trace evaluation, but traces are controlled and setting-shifted |
| T59 real-agent-tools stress test | 74 statically registered Hermes tools, 48 local file/terminal traces, 384 candidate rows, Qwen3-8B embeddings, 96 fixed rows / 2016 curve rows | real tool-code grounding reveals schema-to-real-agent-local-trace FNR=0.25/FPR=0.0; useful stress evidence, but direct handlers/API tools were not invoked |
| T61 DeepSeek provider API expansion | 120 direct provider API traces, 960 candidate rows, Qwen3-8B embeddings, 9 best-tradeoff rows | execution verifier succeeds on provider API effects and static verifiers miss them; still single-surface |
| T62 validation-selected thresholds | T58 controlled traces: test FNR/FPR 0.0/0.0; T59 real-agent local-adapter: 0.1765/0.0; T61 provider API: 0.0/0.0 | fixes ex-post-threshold caveat for tested trace datasets; not live deployment calibration |
| T63 broader local-adapter traces | 300 web/search/browser/messaging local-adapter traces, 2400 candidate rows, Qwen3-8B embeddings | execution verifier validation-selected test FNR=0.0351/FPR=0.0 while static verifier FNR=0.614; broader controlled tool-family evidence, not live external-service validation |
| T64 key-free live/protocol traces | 150 live outbound HTTPS traces + 150 local webhook protocol traces, 2400 candidate rows, full-precision Qwen3-8B embeddings | execution verifier validation-selected test FNR/FPR=0.0/0.0 while static verifier FNR/FPR=0.6294/0.0462; stronger than local adapters, but not provider-backed search/SaaS messaging/deployed runtime |
| T65 file-backed headless Chrome browser-runtime traces | 120 real Chrome DOM/JS traces over file-backed pages, 960 candidate rows, full-precision Qwen3-8B embeddings | execution verifier validation-selected test FNR/FPR=0.0/0.0 while static verifier FNR/FPR=1.0/0.0; browser-runtime evidence, but not HTTP browser networking or deployed runtime |
| T73 action-level calibration | validation trace-group thresholding under false-denial constraint | negative result: T59/T61/T63/T65 can select all-allow thresholds, so simple thresholding is not a deployable policy |
| Threshold policy | fixed / validation / ex-post FPR-constrained rules documented | prevents deploy FNR and stress-test FNR from being silently mixed; T62/T63/T64/T65 are the current validation-selected trace evidence |
| Reproducibility | reproduction entrypoint and result-source appendix exist | `all_outputs_present=True`; now maps T39-T73 artifacts |

## 4. Near-Term Priority

### P0: Auth-SafeInv Formalization

Goal: connect the original causal task consistency claim to task authorization.

Tasks:

- define authorized effect envelope `A(c)`;
- define realized effect set `Omega(a,t)`;
- define unauthorized effect set `U(c,a,t)=Omega(a,t)\A(c)`;
- replace SafeInv with Auth-SafeInv;
- rewrite risk accounting as authorization-conditioned FNR risk.

### P1: Authorization Counterfactuals and Execution Traces

Goal: make causal task consistency empirically testable.

Tasks:

- build `data/authorization_counterfactuals_v1.jsonl`;
- include task context, authorized effects, verified effects, unauthorized effects;
- add same-task tool swaps, auth flips, semantic reframings, and effect substitutions;
- build sandbox/observed execution traces with effect verifier output.

### P2: Auth-SafeInv Evaluation and Strong Baselines

Goal: evaluate unauthorized-effect safety, not only effect detection.

Tasks:

- compute unauthorized-effect FNR and authorized-effect FPR;
- compute AuthToolProxyGap;
- compute unsafe-allow lower bound `[beta_auth-alpha_auth]+`;
- compare against domain-adversarial, supervised contrastive, true GroupDRO/IRM-style, and calibrated abstention baselines.

### P3: pIIA Controls and Graph Alignment

Goal: prevent pIIA from being dismissed as probe calibration or norm artifact.

Tasks:

- random-direction control;
- matched-norm control;
- same-effect wrong-form and different-effect same-form controls;
- layer sweep;
- token aggregation ablation;
- pIIA-Drop vs LOTO ToolProxyGap correlation.
- surface-form graph connectivity analysis for strict LOPO identifiability.

### P4: Reproducibility

Goal: make the artifact reviewable.

Tasks:

- add one mainconf reproduction script/config;
- freeze exact commands, seeds, split names, model names, and output paths;
- generate a result-source appendix table from artifacts;
- extend the audit entrypoint to authorization-conditioned datasets.

### P5: Paper Rewrite

Goal: rewrite only after Auth-SafeInv evidence is stable.

Tasks:

- make authorization-conditioned unsafe-effect results primary;
- retain tool-surface fragmentation as the mechanism behind Auth-SafeInv failure;
- demote full-training projection to upper-bound repair setting unless strict Auth-SafeInv results support stronger claims;
- keep static replay, sandbox, and observed execution clearly separated.

### P6: Verifier-Assisted Mitigation Gate

Goal: decide whether the T57/T58/T59/T61 verifier-assisted route is strong enough for the main method, or add representation learning only if verifier external validity remains too narrow.

Tasks:

- keep v2 as the expanded surface-graph dataset for further method work;
- treat naive effect-schema conditioning and pure decomposed frozen verification as failed;
- treat T57/T58 as promising verifier-assisted framework evidence, T59 as a real-tool-code-grounded stress test, T61 as expanded single-provider API evidence, and T62 as trace-group validation calibration; none are deployed validation or pure representation repair;
- next broaden the execution verifier beyond current controlled observed/sandbox/static/local-adapter/provider traces and apply validation-selected thresholds to new tool families;
- compare against T47/T54-style strong baselines under identical cells and FPR <= 0.10;
- only unblock a strong T45 paper rewrite if the verifier-assisted framing is explicit and the remaining real-trace limitations are not overclaimed.
- add T64/T65 to the verifier-assisted evidence stack as key-free live/protocol and file-backed browser-runtime evidence; keep provider-backed search/SaaS messaging/HTTP browser automation and deployed-runtime validation as the next external-validity gap.

### P7: External Review v1 Method-Shape Hardening

Goal: make the verifier-assisted route read as a distinct effect-verification framework rather than a generic runtime defense.

Tasks:

- add Related Work difference matrix for AgentDojo, ToolEmu, AgentHarm, ASB, AttriGuard, CausalArmor, ClawGuard, and ARGUS;
- define EffectVerif-AuthMonitor with pseudocode, inputs, trace schema, effect taxonomy, and failure modes;
- add action-level metrics: Unauthorized Action Allow Rate and Authorized Action False Denial Rate (T68 done; use results to discuss false-denial tradeoffs);
- run or specify verifier independence ablations over full, label-hidden, and minimal-evidence traces (T69 done);
- add conceptual/empirical baselines for pre-action rule-only, provenance-only, and action-attribution-proxy monitors (T70 proxy comparison done);
- integrate T64/T65/T73 into the paper with full-precision T64, file-backed-browser, non-HTTP-browser, non-provider-backed, and action-level-calibration caveats.
