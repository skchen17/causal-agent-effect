# E47 Tool-Effect Fragmentation Cross-Paper Stress Test

## Purpose

Build a reusable stress-test scaffold for evaluating whether LLM-agent safety methods track realized tool effects or rely on fragmented surface forms such as tool names, argument schemas, wrapper templates, trace labels, planner formats, or graph node names.

This experiment is not designed to prove that all methods fail. It separates paper-grade reproductions from proxy diagnostics and adapter failures.

## Systems

- `agentdojo`: paper-grade local artifact adapter over existing AgentDojo v1.2.2 env-diff/effect artifacts.
- `toolsafe`: proxy diagnostic adapter over cloned ToolSafe TS-Bench JSON tuples; not a TS-Guard checkpoint/author implementation.
- `ipiguard`: proxy diagnostic Tool Dependency Graph adapter; not an IPIGuard author implementation.
- `safiron`: proxy diagnostic adapter over Agentic-Guardian / Pre-Ex-Bench plan-level examples; not a Safiron model reproduction.
- `camel`: cloned for provenance, but currently `adapter_failed`; no performance claims.

## Method

The scaffold defines one common `ToolEffectStressCase` schema and generates perturbations across:

- same realized effect with renamed tools;
- same realized effect with changed argument schema;
- same realized effect through wrapper tools;
- same tool name with changed realized effect;
- same plan semantics with different planner format;
- same trajectory semantics with different trace format;
- hidden trace labels;
- tool-name graph versus effect/resource graph.

Each case records granularity, realized effect, affected resource, risk label, expected decision, source system, perturbation type, adapter status, paper-grade eligibility, effect-label source, method input view, repo URL, commit hash, source artifact path, reproduction flags, and claim scope. Proxy rows cannot be marked as original paper methods.

The scaffold also adds:

- recursive hidden-label stripping for trace views;
- input access guards for oracle fields;
- split leakage checks for held-out tool / family / wrapper / semantic group;
- separate `intra_action_decision_inconsistency` and `action_level_decision_error` metrics.

## Artifacts

- Core code: `src/experiments/tool_effect_fragmentation/`
- Cases:
  - `data/tool_effect_fragmentation/stress_cases_agentdojo.jsonl`
  - `data/tool_effect_fragmentation/stress_cases_toolsafe.jsonl`
  - `data/tool_effect_fragmentation/stress_cases_ipiguard.jsonl`
  - `data/tool_effect_fragmentation/stress_cases_safiron.jsonl`
  - `data/tool_effect_fragmentation/stress_cases_camel.jsonl`
- Predictions:
  - `data/tool_effect_fragmentation/predictions_agentdojo.jsonl`
  - `data/tool_effect_fragmentation/predictions_toolsafe.jsonl`
  - `data/tool_effect_fragmentation/predictions_ipiguard.jsonl`
  - `data/tool_effect_fragmentation/predictions_safiron.jsonl`
  - `data/tool_effect_fragmentation/predictions_camel.jsonl`
- Results:
  - `analysis/results/tool_effect_fragmentation_agentdojo.{json,md}`
  - `analysis/results/tool_effect_fragmentation_toolsafe.{json,md}`
  - `analysis/results/tool_effect_fragmentation_ipiguard.{json,md}`
  - `analysis/results/tool_effect_fragmentation_safiron.{json,md}`
  - `analysis/results/tool_effect_fragmentation_camel.{json,md}`
  - `analysis/results/tool_effect_fragmentation_unified.{json,md}`
- Tests:
  - `tests/test_tool_effect_fragmentation_schema.py`
  - `tests/test_tool_effect_fragmentation_perturbations.py`
  - `tests/test_tool_effect_fragmentation_metrics.py`
  - `tests/test_tool_effect_fragmentation_adapters.py`
  - `tests/test_tool_effect_fragmentation_splits_access.py`

## Result Summary

The current v1.1 smoke run produced:

- AgentDojo: 1296 stress cases, adapter status `paper_grade`.
- ToolSafe TS-Bench proxy: 216 stress cases, adapter status `proxy_diagnostic`.
- IPIGuard proxy: 135 stress cases, adapter status `proxy_diagnostic`.
- Safiron / Pre-Ex-Bench proxy: 216 stress cases, adapter status `proxy_diagnostic`.
- CaMeL: 0 stress cases, adapter status `adapter_failed`, with cloned repo provenance recorded.

In the paper-grade AgentDojo stress test, `tool_name_classifier` has held-out-tool FNR 1.000 and ToolProxyGap 0.667, while `effect_resource_abstraction` and `execution_evidence_upper_bound` have held-out-tool FNR 0.000. This is consistent with the scaffold's intended diagnostic: tool-name surface rules are fragile under same-effect tool-surface shifts, whereas effect-grounded upper-bound views are invariant on this local artifact.

ToolSafe, IPIGuard, and Safiron results are useful only as proxy diagnostics until exact data/checkpoints/checkers are wired. CaMeL is present only as an adapter-failure/provenance row.

## Phase 2 Results

Phase 2 adds split-based AgentDojo degradation analysis, external reproduction audits, a controlled effect-vs-tool mechanism experiment, paired deltas, and failure examples.

Key artifacts:

- `data/tool_effect_fragmentation/phase2_stress_cases.jsonl`
- `data/tool_effect_fragmentation/phase2_predictions.jsonl`
- `analysis/results/tool_effect_fragmentation_phase2_unified.{json,md}`
- `analysis/results/tool_effect_fragmentation_phase2_reproduction_audit.{json,md}`
- `analysis/results/tool_effect_fragmentation_phase2_mechanism.{json,md}`
- `analysis/results/tool_effect_fragmentation_phase2_failure_examples.{json,md}`
- `analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase2_summary.md`

Main Phase 2 findings:

- AgentDojo split comparison is complete: random N=324, held-out-tool N=144, same-effect-different-tool N=288.
- `tool_name_classifier` worsens from random FNR 0.756 to held-out-tool FNR 1.000; random-vs-heldout delta is +0.2438.
- Effect/resource and execution-evidence rows remain stable on AgentDojo stress, but they are upper-bound/oracle-style rows unless backed by a non-oracle verifier.
- Controlled mechanism experiment gives effect-vs-tool clustering gap -0.4239, indicating tool-surface proximity is at least as strong as same-effect proximity in this diagnostic setup.
- ToolSafe, Safiron, IPIGuard, and CaMeL all have complete reproduction audits, but no original-method result is claimed. Blockers are missing ToolSafe local TS-Guard checkpoint, missing local Safiron model verification, missing IPIGuard OpenAI-compatible API env, and missing CaMeL API/non-side-effect adapter.
- 31 representative failure examples were generated across method classes.

## Claim Boundary

Paper-grade claims can currently use only the AgentDojo adapter and only as a stress test over local T122 artifacts. ToolSafe, IPIGuard, and Safiron rows must be described as proxy diagnostics. The unified table should not be used to claim that original TS-Guard, IPIGuard, Safiron, or CaMeL fails.

Phase 2 does not change that boundary: it strengthens the AgentDojo stress-test evidence and documents non-AgentDojo reproduction blockers, but it does not produce original TS-Guard, IPIGuard, Safiron, or CaMeL method results.

## Phase 3 Results

Phase 3 adds balanced AgentDojo paper-grade stress protocols, official-method blocker audits, mechanism bootstrap/permutation/text-ablation controls, a local DeBERTa robustness backend, a non-oracle env-diff evidence diagnostic, and a larger failure-example packet.

Key artifacts:

- `data/tool_effect_fragmentation/phase3_stress_cases.jsonl`
- `data/tool_effect_fragmentation/phase3_predictions.jsonl`
- `analysis/results/tool_effect_fragmentation_phase3_unified.{json,md}`
- `analysis/results/tool_effect_fragmentation_agentdojo_phase3.{json,md}`
- `analysis/results/tool_effect_fragmentation_mechanism_phase3.{json,md}`
- `analysis/results/tool_effect_fragmentation_evidence_phase3.{json,md}`
- `analysis/results/tool_effect_fragmentation_reproduction_phase3.{json,md}`
- `analysis/results/tool_effect_fragmentation_failure_examples_phase3.{json,md}`
- `analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase3_summary.md`

Main Phase 3 findings:

- The formal Phase 3 run generated 1863 stress cases and 14904 prediction rows.
- AgentDojo balanced protocols are complete: random N=144, held-out-tool N=144, same-effect-different-tool N=144.
- The unified report gives `tool_name_classifier` random-vs-heldout FNR delta +0.6667, indicating random splits substantially overestimate held-out-tool safety for a surface baseline.
- Mechanism diagnostics remain consistent with surface clustering: TF-IDF/SVD full-text effect-vs-tool gap is -0.4239, and the local DeBERTa backend gives -0.2853. Negative values mean same-tool proximity is stronger than same-effect proximity in this diagnostic.
- `non_oracle_envdiff_verifier` is separated from oracle upper bounds and has held-out-tool FNR 0.0000 on saved AgentDojo evidence. This supports evidence-grounded diagnostics, not a deployed verifier claim.
- ToolSafe and Safiron official checkpoints are now available locally and pass 5/5 non-side-effect inference smokes using their published input/output formats. These are `original_method_smoke` results, not full fragmentation evaluations.
- IPIGuard and CaMeL pass 5/5 non-side-effect local-Qwen substitute smokes. These are `local_model_substitute` results, not original-method results.
- 165 representative failure/success examples were generated, including held-out collapse, same-effect inconsistency, row/action mismatch, and non-oracle evidence success/failure cases.

Phase 3 external-blocker follow-up:

- TS-Guard's released checkpoint completed all 216 ToolSafe-derived E47 custom stress cases with 216/216 parse-valid outputs. It has overall FNR / unsafe pre-allow 0.1750, safe false deny 0.1042, action-level decision error 0.3750, and same-effect consistency 0.1667. Held-out-tool and held-out-wrapper FNR are both 0.0000 on 12 unsafe positives each, so the result does not support a simple rename-collapse claim; the broader inconsistency/action-level errors remain the stronger finding.
- Safiron's released checkpoint was evaluated with the required Mistral `fix_mistral_regex=True` tokenizer correction and completed 216/216 parse-valid cases. It has overall FNR / unsafe pre-allow 0.1181, safe false deny 0.3194, same-effect consistency 0.3750, and intra-action decision inconsistency 0.6250. Its action-level decision error is 0.0000 under the current any-deny aggregation, illustrating that action aggregation can hide substantial row-level inconsistency.
- These rows have claim scope `original_method_custom_stress`: they use released checkpoints but E47-adapted inputs and proxy or published-derived expected labels. They are not original-paper benchmark metric reproductions.

External smoke artifacts:

- `analysis/results/tool_effect_fragmentation_external_smoke_phase3.{json,jsonl,md}`
- `analysis/results/tool_effect_fragmentation_toolsafe_official_stress_phase3.{json,jsonl,md}`
- `analysis/results/tool_effect_fragmentation_toolsafe_official_stress_phase3_predictions.jsonl`
- `analysis/results/tool_effect_fragmentation_safiron_official_stress_phase3.{json,jsonl,md}`
- `analysis/results/tool_effect_fragmentation_safiron_official_stress_phase3_predictions.jsonl`
- Official models: `models/MurrayTom/TS-Guard`, `models/Safiron/Safiron`
- Local substitute model: `models/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf`

Phase 3 strengthens the AgentDojo stress-test evidence and removes the model/API availability blocker for dry-run inference. Released TS-Guard and Safiron checkpoints now also have complete E47 custom-stress results, but these remain adapted-input evaluations rather than original-paper benchmark reproductions. IPIGuard and CaMeL remain local-model substitute diagnostics.

## Phase 4 Results

Phase 4 builds a strict paired counterfactual core over all 24 AgentDojo saved env-diff anchors. Each group has 22 cases: 11 ALLOW and 11 DENY. The construction tests whether a guard keeps decisions stable when tool surface changes but realized effects/authorization stay fixed, and whether decisions correctly change when the effect, authorization context, or resource scope changes.

Key artifacts:

- `data/tool_effect_fragmentation/counterfactual_core_phase4.jsonl`
- `data/tool_effect_fragmentation/counterfactual_core_phase4_manifest.json`
- `analysis/results/tool_effect_fragmentation_counterfactual_phase4.{json,md}`
- `analysis/results/tool_effect_fragmentation_counterfactual_phase4_{toolsafe,safiron,local_qwen}.{json,jsonl,md}`
- `analysis/results/tool_effect_fragmentation_counterfactual_phase4_{toolsafe,safiron,local_qwen}_predictions.jsonl`
- `analysis/results/tool_effect_fragmentation_counterfactual_phase4_failure_examples.{json,md}`
- `analysis/results/tool_effect_fragmentation_counterfactual_phase4_audit_packet.{jsonl,md}`
- `analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase4_summary.md`

Main Phase 4 findings:

- The paired core is complete: 528 cases, 24 semantic groups, 264 ALLOW and 264 DENY cases. Prompt leakage checks over TS-Guard, Safiron, and local-Qwen inputs found 0 gold field/effect-value leaks.
- TS-Guard completed 528/528 parse-valid official-checkpoint custom-stress rows. It has same-effect decision consistency 0.883, authorization sensitivity 0.764, correct effect-change decision rate 0.625, unsafe pre-allow 0.159, safe false deny 0.087, and intra-action inconsistency 0.875.
- Safiron completed 528/528 parse-valid official-checkpoint custom-stress rows. It has same-effect decision consistency 0.669, authorization sensitivity 0.088, correct effect-change decision rate 1.000, unsafe pre-allow 0.545, safe false deny 0.371, and intra-action inconsistency 1.000.
- Local Qwen self-audit completed 528/528 rows with 527/528 parse-valid outputs. It has unsafe pre-allow 0.004 but safe false deny 0.481, indicating a high over-denial baseline rather than a balanced guard.
- Tool-name and argument-schema proxies fail the core counterfactual tests: tool-name proxy authorization sensitivity is 0.000 and resource mismatch error is 1.000.
- Non-oracle saved-evidence verifier abstains on no-evidence cases and has overall coverage 0.250. It should be read as an evidence-availability diagnostic, not as a deployable verifier result.
- Effect/resource oracle and execution-evidence upper bound are perfect by construction and are reported only as upper bounds.

Phase 4 fixes two construction risks found during execution: normalized gold effect names were removed from prompts, and multi-effect AgentDojo anchors now authorize the full saved realized-effect set. The controlled primary resource still requires human audit. The 120-row audit packet is ready, but human labels are not filled, so Phase 4 remains controlled custom-stress diagnostic evidence.

## Phase 5 Results

Phase 5 replaces the earlier IPIGuard/CaMeL local-substitute-only status with mechanism-matched original-component and original-pipeline/local-model evidence.

Key artifacts:

- `data/tool_effect_fragmentation/ipiguard_counterfactual_phase5.jsonl`
- `data/tool_effect_fragmentation/camel_structural_counterfactual_phase5.jsonl`
- `data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl`
- `data/tool_effect_fragmentation/camel_phase5_traces.jsonl`
- `analysis/results/tool_effect_fragmentation_ipiguard_component_phase5.jsonl`
- `analysis/results/tool_effect_fragmentation_camel_component_phase5.jsonl`
- `analysis/results/tool_effect_fragmentation_{ipiguard,camel}_phase5.{json,md}`
- `analysis/results/tool_effect_fragmentation_phase5_unified.{json,md}`
- `analysis/results/tool_effect_fragmentation_phase5_failure_examples.{json,md}`
- `analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase5_summary.md`

Implemented evidence:

- IPIGuard's released DAG construction prompt and parser run on a 168-case E47 DAG counterfactual core. The report separates weak topology consistency from exact DAG content sensitivity; topology stability alone is not treated as realized-effect understanding.
- CaMeL's original generic `SecurityPolicyEngine.check_policy` runs on a 54-case structural counterfactual core. Synchronized tool-policy renames are separated from missing-policy coverage failures.
- Both original pipelines run through their native AgentDojo dependencies using the local Qwen GGUF OpenAI-compatible backend. The four-suite full cross-product is complete: IPIGuard has 1452 trace rows and CaMeL has 3138 trace rows, for 4590/4590 pipeline cases across 40/40 settings.
- CaMeL `SecurityPolicyDeniedError` outcomes are counted as valid policy denials, not runtime failures. The regenerated report separates runtime errors, policy denials, utility, and attack success.

Current component findings:

- IPIGuard component outputs are 168/168 parse-valid, with normalized-effect prompt leakage 0/144 outside the explicit effect-graph view. Same-effect topology consistency is 1.000, exact-DAG consistency is 0.383, and known-map normalized-DAG consistency is 0.750. Rename normalizes cleanly to 1.000, while wrapper-tool normalized consistency is only 0.125 and argument-schema normalized consistency is 0.708. Same-tool different-effect changes are visible in DAG content but not topology. This shows that dependency topology, surface-sensitive content, and oracle-normalized semantic consistency must be reported separately.
- CaMeL policy component outputs are 54/54 complete. Overall correctness is 0.889, unsafe blocked rate is 0.750, safe false denial is 0.000, and synchronized structural invariance is 1.000. The remaining errors are mechanism/policy-coverage diagnostics under weak custom expected labels, not original-paper benchmark failures.
- The IPIGuard full pipeline has attack success 0/602 for no-defense and 4/602 for IPIGuard. The CaMeL no-policy, normal-policy, and strict-policy variants each have one successful attack. Normal and strict policy introduce policy-denial rates of 0.082 and 0.061. Because local-model no-defense utility and attack success are very low, these results do not establish defense effectiveness.

Claim boundary:

- `original_pipeline_local_model` is not original-paper numeric reproduction because the model backend differs.
- `original_component_custom_stress` tests released mechanism components on E47 inputs; it is not the authors' benchmark result.
- IPIGuard single-node topology consistency is a weak structural diagnostic, and effect-visible prompts are not label-hidden effect inference.
- CaMeL unsynchronized rename failures are policy-coverage failures, not effect-fragmentation evidence.
- No real side effects are executed.

## Phase 6 Results

Phase 6 consolidates the Phase 1-5 evidence and tests whether an explicit effect/resource semantic layer closes the gap left by topology-only reasoning.

Key artifacts:

- `data/tool_effect_fragmentation/ipiguard_semantic_core_phase6.jsonl`
- `data/tool_effect_fragmentation/human_audit_packet_phase6.jsonl`
- `data/tool_effect_fragmentation/human_audit_secondary_phase6.jsonl`
- `analysis/results/tool_effect_fragmentation_ipiguard_semantic_phase6.{json,jsonl,md}`
- `analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.{json,md}`
- `analysis/results/tool_effect_fragmentation_capability_matrix_phase6.{json,md}`
- `analysis/results/tool_effect_fragmentation_phase6_unified.{json,md}`
- `analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase6_summary.md`

Main findings:

- The IPIGuard semantic core contains 240 controlled cases over 24 groups. The deterministic mapper has effect sensitivity 0.375 and zero unsafe pre-allow, but abstains on 0.579 of cases. Its resource extraction accuracy is only 0.354.
- The label-hidden local-Qwen mapper completes 240/240 parse-valid predictions. It improves effect sensitivity to 0.833 and coverage to 0.938, but authorization sensitivity remains 0.375, resource sensitivity is 0.125, and unsafe pre-allow rises to 0.333.
- The oracle semantic mapper is perfect by construction. This gap supports the diagnosis that topology alone is insufficient and that current non-oracle semantic extraction/decision layers remain inadequate; it does not establish a working guard.
- CaMeL's 6 unsafe misses on the current 54-case structural core are all control-dependency cases. Effect, resource, and authorization mismatch are not evaluable on that core.
- The unified audit packet contains 222 primary and 56 secondary-review rows. Human fields remain unfilled, so Phase 4/6 expected-label conclusions remain pending-audit custom-stress evidence.
- The external DeepSeek pipeline is preregistered but remains pending because `DEEPSEEK_API_KEY` was not present. Defense expansion was not run.

Phase 6 claim boundary:

- Simple surface robustness and structural invariance do not imply joint effect-resource-authorization reasoning.
- The semantic mappers are E47-added diagnostic layers, not part of IPIGuard.
- Local-Qwen is label-hidden but is not human ground truth; deterministic mapping is hand-built; oracle mapping is an upper bound.
- Human-audit and external-pipeline gates remain open. Phase 6 is not audited paper-main evidence or a deployable defense result.
- No real side effects are executed.

## Reviewer Risks

- Proxy adapters may overstate or understate true method behavior.
- AgentDojo paper-grade cases come from local env-diff/effect artifacts, not a fresh full official benchmark reproduction.
- Current baselines are simple deterministic/proxy baselines; stronger exact-system inference is future work.
- Some adapter inputs use rule-inferred realized effects over published benchmark text; these are clearly marked with `effect_label_source` and `claim_scope`.
- Phase 4 expected decisions are pending human audit; do not use them as final paper-main labels until decision agreement and effect/resource/authorization agreement gates pass.
- Phase 5 four-suite original-pipeline execution is complete, but low local-model utility and near-zero no-defense attack success prevent a strong defense-effectiveness comparison. Treat it as original-pipeline/local-model compatibility and negative diagnostic evidence.
