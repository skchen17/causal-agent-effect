# Current Experiment Evidence Audit

Date: 2026-07-21

## Executive Verdict

The repository contains enough evidence to support the bounded problem claim:
tool-call-level signals preserve some effect distinctions but fail joint
effect/resource/authorization/provenance binding under controlled
counterfactual stress. It also contains evidence that atom-level mediation can
work under controlled contracts and that the representation exposes concrete
runtime obligations.

The evidence is not yet sufficient to freeze the final USENIX performance
claim. The final repaired runtime (E77-v3) has not been rerun, the Qwen3-32B
strong-baseline logs have not been finalized under one uniform gate, the
long-horizon full run is invalid, and the final ablation/adaptive-attack rows
have not executed. Old E75--E77 numbers describe earlier runtime versions and
must not be relabeled as the current method.

## Status Vocabulary

- **Main-ready (bounded):** reproducible and suitable for a precisely scoped
  main-text claim.
- **Secondary-ready:** useful supporting or appendix evidence with an explicit
  scope limitation.
- **Diagnostic/superseded:** valid for design history or failure analysis, but
  not a final method result.
- **Incomplete/invalid:** not reportable as a completed experiment.

## 1. Controlled Problem and Bottleneck Evidence

| Experiment | Main result | Status | Paper use and issue |
|---|---|---|---|
| E47 | On 528 controlled rows, tool-name proxy has effect/auth/resource sensitivity 0; TS-Guard and Safiron show partial but non-joint binding. Representative UPA: tool-name 0.292, TS-Guard 0.159, Safiron 0.545, local-Qwen self-audit 0.004. | Main-ready (bounded) | Supports heterogeneous partial binding on custom stress. Released checkpoints were not run under their original paper protocols. Human audit is sampled, with construction-gated remainder. |
| E48 | 822 rows, 6,840 relations. Full hard guard: UPA 13/360 = 0.036, FDeny 30/462 = 0.065, coverage 754/822 = 0.917. Held-out split: UPA 5/98 = 0.051, FDeny 6/126 = 0.048, coverage 214/224 = 0.955. | Main-ready (bounded) | Statistical unit was repaired to group-level bootstrap. Some evidence rows remain simulated counterfactual evidence and must be stratified. |
| E49 | Learned calibrator on resource/auth stress: UPA 0.500, FDeny 0.042, coverage 1.000. | Diagnostic negative result | Shows calibration does not solve the bottleneck; not a positive contribution. |
| E50 | Corrected resource/auth stress: 240 rows, UPA 46/120 = 0.383, FDeny 0/120, coverage 221/240 = 0.921. Provenance stress: 336 rows, UPA 0/144, FDeny 36/192 = 0.188, coverage 183/336 = 0.545. | Main-ready (bounded) | The pre-2026-07-14 resource/auth artifact was semantically invalid and is archived. The repaired result supports resource/authorization as the clearest hard-guard bottleneck, not prevalence in deployed agents. |

Code/tests for E47--E50 have been re-audited. The current bounded conclusion is
supported; claims that all prior methods are tool-name classifiers, or that the
custom stress reproduces original benchmarks, are not supported.

## 2. Controlled Prototype and Audit Evidence

| Experiment | Main result | Status | Paper use and issue |
|---|---|---|---|
| E55-v2 strict | 600 rows. Authorization-aware guard: UPA 0/276, FDeny 0/252, coverage 528/600 = 0.880, abstain 0.120. Existing hard guard coverage is 0.200. | Secondary-ready | Controlled feasibility warm-up only. Do not mix with original E55 coverage 0.920 or human-corrected sensitivity. |
| E55-v2 ablation | Removing multi-resource, operation mode, or provenance each yields aggregate UPA 60/276 = 0.217; no alias resolution yields FDeny 60/252 = 0.238. | Secondary-ready | Aggregate equality does not prove the same failed rows overlap. |
| E56 | Strict replay and decision-path audit pass. | Secondary-ready audit | Validates execution/replay consistency, not independent labels. |
| E57-v2 | Perturbation deltas are zero; independent reference-authorizer agreement is 1.000; 60-row spot packet created. | Secondary-ready audit | Reference authorizer is an independent implementation, not an independent human authority source. |
| E57 human audit | Decision agreement 54/60 = 0.900; all-checks-true 46/60 = 0.767; 6 decision, 13 atom, and 10 reason corrections. | Secondary-ready sensitivity | Demonstrates nontrivial annotation error. It should qualify, not replace, the strict main result. |

## 3. Held-Out, Trace, Decomposition, and Interface Evidence

| Experiment | Main result | Status | Paper use and issue |
|---|---|---|---|
| E60 held-out | 480 synthetic held-out cases across five domains. UPA 0, FDeny 0.083, coverage 0.854, atom exact 0.812. | Secondary-ready | Independently specified, not independently authored. Reviewer and author IDs are both `A`; strict non-E55 authorship is not certified. |
| E61 artifact traces | 300 generated noisy traces. UPA 0, FDeny 0.053, coverage 0.847, atom exact 0.733. | Secondary-ready | More realistic schema/noise, but still artifact-generated. |
| E61 external subset | 156 saved AgentDojo/IPIGuard-style traces. UPA 0, FDeny 0, coverage 0.904, atom exact 0.821. | Diagnostic for parsing only | Labels are metadata-derived and atoms rule-derived. Selection keeps benign-success and attack-failure mutating calls; it excludes successful attacks and does not define reliable authorization gold. Do not use its UPA as official AgentDojo safety evidence. |
| E62 decomposition | Gold atoms/context outperform extracted atoms; degraded context sharply raises FDeny (E60 0.533, E61 0.439) while UPA remains 0. | Secondary-ready | Useful mechanism decomposition, but the extractor/context are tied to the constructed contracts. |
| E63 interface burden | Five domains each report two tools, eight atom rules, eight auth fields, 312 aliases, and 74 estimated minutes. Context degradation keeps UPA 0 but often causes near-total FDeny. | Diagnostic, needs correction/validation | Repeated per-domain counts and identical estimated authoring time indicate generated accounting rather than measured independent onboarding. Alias counts are case-derived, not clearly distinct maintained entries. Do not claim bounded human cost from this table. |
| E64 B0--B7 | Full atom mediation has UPA 0 with coverage 0.880/0.854/0.847 on E55/E60/E61; strongest non-atom UPA is 0.043/0.311/0.189 with lower coverage. | Secondary-ready | Controlled common-view comparison. B7 receives atom-equivalent capability context, and several baselines are local proxies rather than original-system reproductions. |

## 4. Real-Model Supplement

| Experiment | Main result | Status | Paper use and issue |
|---|---|---|---|
| E65 real LLM judge | Qwen 9B judge UPA: E55 0.261, E60 0.039, E61 artifact 0, E61 external 0. FDeny reaches 0.909 on external. | Secondary-ready baseline | Real inference, label-hidden, no tool execution. Shows a judge can be unsafe or highly over-conservative depending on the data. |
| E66 real LLM atom extractor | Atom exact-set match is 0 on E60, E61 artifact, and E61 external. UPA is 0.344, 0.189, and 0.067 respectively. | Main-relevant negative evidence | Strong evidence that unconstrained Qwen extraction is not reliable enough for direct runtime trust. Resource/control F1 alone hides complete-set failure. |
| E67/B8 official checkpoints | TS-Guard and Safiron released checkpoints completed on E55/E60/E61 adapted inputs. Results vary widely; e.g., TS-Guard E60 UPA 1.000, Safiron E60 UPA 0.917. | Secondary-ready baseline | Adapted common-input stress only, not original ToolSafe/TS-Guard/Safiron benchmark reproduction. Prompt/interface mismatch may dominate some rows. |

The E60--E67 reproduction gate currently passes with 573 machine-traceable
rows. This gate checks artifact/key availability; it does not upgrade the
independence or realism of the underlying labels.

### Colliding E60/E62/E63 Prototype Line

Separate artifacts reuse the same experiment numbers and must not be confused
with the held-out/decomposition/interface experiments above:

- The E60 effect-contract prototype covers five mock tools, 33 counterfactual
  cases, and 32 frozen-runtime examples. Its sensitivity/invariance and required
  binding checks pass, with no post-freeze proposer calls. This is a useful unit
  prototype, not independent or realistic evaluation.
- The current E62 local-proposer report uses `backend=static` and
  `model=test-double`. Although the report says `local_llm_status=executed`, its
  15/15 stub freezeability is harness evidence, not local-LLM evidence. Its raw
  and refined proposal rows are both parse-valid 0/15.
- The default E63 iterative report is also a static one-tool test-double run and
  cannot support model-quality claims.
- The real DeepSeek-v4-flash E63 run evaluates 15 tools over 71 candidates and
  freezes only 1/15; 14 require human review. This is valid negative evidence
  that sanitized iterative feedback rarely repairs arbitrary contract
  synthesis under the current schema.
- Gemma4 produced only incomplete/failed smokes. No Gemma4 full run exists; GPU
  memory, unsupported 4-bit MoE kernels, and very low eager-MoE throughput block
  the experiment.

The paper should refer to these by descriptive names rather than bare E62/E63
IDs, and should not list the static test-double reports as real-LLM results.

## 5. Descriptor and Runtime Design Exploration

| Experiment | Result | Status and interpretation |
|---|---|---|
| E68 | 156 traces, only resource/operation axes observed; overall pair pass 0.487; injection robustness 0.045; zero frozen fragments. | Diagnostic failure. Bounded two-axis run, not the intended all-axis experiment. |
| E69 | 23 valid candidates, zero strictly freezeable; replay UPA 0.769. | Superseded failure. Demonstrates that top-k LLM contract selection is unsafe. |
| E70 | 0/24 descriptors registered; runtime abstains on 156/156. | Superseded fail-closed result with no utility. |
| E71 | 20/24 tools registered; UPA 0 but FDeny 20/22 = 0.909. | Superseded; safety comes with unacceptable false denial under sidecar labels. |
| E72 | Coverage 0.314, abstain 0.686, FDeny 0.318. | Superseded; exposes missing/symbolic task-envelope fields. |
| E73 | Initial coverage 0.032; LLM-authority policy coverage 0.423. Sidecar labels disagree with official-ASR labels on 134/156 rows. | Diagnostic only. The sidecar DENY definition is not AgentDojo attack success and cannot be used as UPA gold. |
| E74 | Saved no-guard source reports ASR 0/629, while IPIGuard-normal reports 4/629. | Diagnostic only. This saved run has a weak/non-triggering attack distribution and is not a live baseline. |

These experiments explain why the final architecture moved from per-call LLM
atom extraction toward offline registration plus deterministic runtime checks.
They should not appear as a sequence of positive contributions in the paper.

## 6. Official AgentDojo End-to-End Runs

| Experiment/runtime | Model and protocol | ASR | Benign utility | Attack utility | Status/problem |
|---|---|---:|---:|---:|---|
| E75 full-atom runtime | Qwen 9B, AgentDojo v1.1.2, 726 keys | 17/629 = 0.027 | 48/97 = 0.495 | 270/629 = 0.429 | Legacy. Contains 452 explicit overrides and context diagnostics; superseded by stricter designs. |
| E76 LLM descriptor runtime | Qwen 9B, 726 keys | 10/629 = 0.016 | 34/97 = 0.351 | 207/629 = 0.329 | Legacy. 21/24 tools register; three fail closed. Useful intermediate ablation, not final method. |
| E77 effect-diff runtime | Qwen 9B, 726 keys | 0/629 | 32/97 = 0.330 | 191/629 = 0.304 | Valid behavior of the old runtime, but O1/O2/O5 remain partial. Code audit led to E77-v3; old numbers cannot represent v3. |
| E77-v3 | Repaired runtime | Running | Running | Running | Implemented and unit-tested. A clean 2-case Qwen3-32B smoke completed on July 21; the separate 726-key full run is now active. No full-run metric may be claimed until its strict finalizer passes. |

The old E77 audit does support sandbox-local complete mediation/check--use for
3,173 executed valid calls, because the executed and pre-commit signature
multisets match. It does not establish sound contracts, independent authority,
or totalized unknown defaults.

## 7. Qwen3-32B Strong-Baseline Frozen Metrics (E78)

The following values were recomputed directly by joining raw logs to the 726
official AgentDojo v1.1.2 keys. The July 21 finalizer now freezes 4,356 direct
rows, 5,082 rows including provisional AttriGuard, Wilson intervals, and paired
bootstrap/McNemar statistics. The historical runner overwrote its per-method
command-status artifact, so the direct rows have complete native metrics but do
not constitute a command-level clean-protocol certificate.

| Method | Keys | ASR | Benign utility | Attack utility | Current issue |
|---|---:|---:|---:|---:|---|
| No guard | 726 | 53/629 = 0.084 | 64/97 = 0.660 | 342/629 = 0.544 | Native metrics frozen; historical per-method request diagnostics unavailable. |
| MELON-style local | 726 | 56/629 = 0.089 | 62/97 = 0.639 | 340/629 = 0.541 | Comparable local adapter, not official MELON reproduction. |
| Spotlighting | 726 | 48/629 = 0.076 | 60/97 = 0.619 | 371/629 = 0.590 | Native metrics frozen with the same historical diagnostic caveat. |
| Prompt sandwiching | 726 | 8/629 = 0.013 | 60/97 = 0.619 | 362/629 = 0.576 | Strong frozen metric tradeoff; command-level diagnostic caveat remains. |
| PromptArmor-style local | 726 | 1/629 = 0.002 | 27/97 = 0.278 | 138/629 = 0.219 | Low ASR is coupled to severe utility loss. |
| AttriGuard adapted artifact | 726 files | 8/629 = 0.013 | 40/97 = 0.412 | 215/629 = 0.342 | Ten workspace cases are marked protocol errors despite log files; not uniform/final. |
| Old E77 runtime | 726 | 1/629 = 0.002 | 33/97 = 0.340 | 208/629 = 0.331 | Earlier runtime, not E77-v3. |
| PIGuard / PI detector | 0 | -- | -- | -- | No full logs. |

This is currently the strongest comparative evidence in the repository, but it
cannot yet support a final superiority claim. Prompt sandwiching has a much
better observed utility/security tradeoff than old E77, while PromptArmor
matches its ASR only by losing substantially more utility. The final method
must be compared against these rows using the same model and keys.

## 8. Long-Horizon, Theory, Ablation, Overhead, and Review

| Experiment | Result | Status/problem |
|---|---|---|
| E79 ToolSandbox | 30 scenarios; no-guard and guard both similarity/milestone 0.223, minefield 0, two errors. | Secondary diagnostic only. No injected attack layer and no long-horizon confinement evidence. |
| E79 AgentLAB | One-case smokes pass for no-guard and E77. The 303-pair full commands completed but tool-message schema errors produced invalid post-tool continuations. | Full result invalid; must rerun after adapter repair. |
| E80 security model | Exhaustive finite models, concrete counterexamples, compound calendar checks, and isolated hardening checks pass. | Main-ready as conditional formal/finite evidence. It is not implementation-wide proof. |
| E81 ablations | A1/A2/A7/A9/A11/A12/A13/A15 kernels and counterexamples are ready. | Not evaluated. Its compatibility status is stale because E84 review has since completed; the full common-protocol runner still has not run. |
| E82 adaptive attacks | T1--T12 protocol and budgets validated. | Protocol-only; no victim results. E88 later materializes four static families but does not replace all T1--T12. |
| E83 overhead | 18 configurations x 2,000 iterations = 36,000 ALLOW decisions. p50 remains below roughly 0.36 ms for up to 32 fields/64 noise entries. | Secondary-ready microbenchmark. Excludes LLM, sandbox, I/O, recovery, and trajectory latency. |
| E84 authority review | 97 rows reviewed; 44 accepted, 53 rejected; authority coverage 0.454; 161 bindings approved, 126 rejected. | Main-relevant burden/feasibility evidence. It shows the independent authority interface is currently the dominant coverage constraint. |
| E85 projection review | 28 tool instances reviewed; 16 approved, 12 rejected. Finite causal-mediation model has 54 rows. | Review is complete, but approved AgentDojo projections have not yet been executed through the frozen intervention protocol. |

## 9. E88 Stronger Attack Dataset

- Dataset construction passes: 2,516 static attack cases, 97 benign controls,
  and 480 adaptive-strategy indices.
- Development smoke (80 cases): no guard succeeds on 11/80 attacks with utility
  48/80; old E77 has 0/80 attack successes with utility 28/80. This smoke is
  development-only and not paper-eligible.
- Full no-guard run currently has 1,665/2,516 official attack cases (66.18%) plus
  27 auxiliary rows. Banking, Slack, and Travel are complete; Workspace has
  109/960 cases.
- The partial no-guard slice has 122/1,665 attack successes (0.073) and
  843/1,665 utility successes (0.506), but this number is selection-biased by
  the unfinished suite/family order and must not be reported as the final E88
  result.
- The run stopped because `systemd-oomd` killed the service at 88.34% user-slice
  memory pressure. The last request and JSON are valid, so missing-key resume is
  possible.

## 10. Cross-Cutting Problems

1. **Experiment identifier collisions.** E60 names both the held-out contract
   and a separate effect-contract prototype; E62 names decomposition and a
   local-LLM proposer; E63 names interface burden and iterative refinement.
   Paper tables need stable aliases or renumbering before final freeze.
2. **Final method/result mismatch.** The paper's normative Method is stronger
   than old E77. E77-v3 passed a clean 2-case smoke and its 726-key Qwen3-32B
   run is active, but no completed full result exists yet. E84/E85 reviewed
   interfaces remain separate analyses and are intentionally not leaked into
   the automatic-plan main run.
3. **Derived-label circularity.** E61 external and E68--E73 reuse metadata/rule
   sidecars. They are useful for extraction diagnostics but not independent
   authorization or official-ASR gold.
4. **Synthetic evidence concentration.** E47--E67 establish controlled
   mechanisms, but they cannot substitute for same-protocol live agent results.
5. **Baseline protocol-diagnostics gap.** Six Qwen3-32B direct methods now have
   frozen 726-key metric rows and paired statistics. Historical command-level
   diagnostics were overwritten, AttriGuard has ten explicit protocol-error
   cases, and PIGuard/PI Detector full logs are missing.
6. **Utility remains the main empirical weakness.** Old E77 reaches near-zero
   ASR but roughly one-third utility. Prompt sandwiching is provisionally much
   stronger on utility at 1.3% ASR. The repaired runtime must show a better
   Pareto point, not only another low ASR.
7. **Long-horizon evidence is absent.** ToolSandbox has no attack layer and the
   AgentLAB full run is invalid.
8. **Interface burden is real and larger than the early E63 table suggests.**
   E84 accepts only 44/97 authority manifests and E85 approves 16/28 effect
   projections. These reviewed rates are more credible than uniform estimated
   authoring minutes.

## Recommended Next Sequence

1. **Runtime definition frozen for the main run.** E77-v3 uses generated task
   plans plus deterministic completeness, grounding, exact-call, totalization,
   and bounded-revision checks. E84 accepted manifests are a separate authority
   interface analysis and are not injected into this main benchmark row.
2. **E78 metric finalization completed.** Six direct methods have 4,356 frozen
   rows and paired statistics; AttriGuard's ten protocol errors are isolated.
   Preserve the historical command-diagnostic caveat in all tables.
3. **E77-v3 full run active.** The clean 2-case smoke records v3 on every audit
   event, deterministic authorization after revision, no HTTP/context errors,
   and a blocked attack goal. The 726-key run must finish and pass
   `finalize_e77_v3_qwen32_full.py` before any result is reported.
4. **Run the final E81 ablations only after E77-v3 freezes.** Integrate the 44
   accepted E84 manifests and 16 approved E85 projections where applicable;
   fail closed outside their certified scope and report coverage explicitly.
5. **Resume E88 by missing keys with memory-bounded services.** Split by
   suite/attack family and restart the model per shard so one service does not
   accumulate 77 processes and trigger `systemd-oomd`. First finish no guard,
   then run E77-v3 and the strongest two or three baselines rather than all weak
   adapters.
6. **Repair and smoke AgentLAB before another full run.** Require valid tool
   message IDs and nonempty post-tool continuation on multiple cases, then run
   no guard and E77-v3 on identical 303 keys.
7. **Execute E85 interventions and E82 adaptive tests.** These come after the
   runtime and authority interfaces are frozen; otherwise they test obsolete
   code.
8. **Freeze paper tables and claim map last.** Remove E68--E74 from the main
   evidence chain, retain selected negative results in failure analysis, and
   keep E47--E50 as controlled motivation rather than end-to-end safety proof.

## Submission Readiness

The project has a defensible problem statement, controlled mechanism evidence,
real-model negative evidence, a conditional security analysis, and promising
official AgentDojo runs. It is not yet evidence-complete for a USENIX submission
because the current final method lacks a same-protocol result and the strongest
comparison, ablation, adaptive, and long-horizon rows are not frozen.
