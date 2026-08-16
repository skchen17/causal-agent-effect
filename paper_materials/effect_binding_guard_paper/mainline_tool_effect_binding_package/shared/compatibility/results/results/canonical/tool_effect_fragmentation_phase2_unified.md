# Tool-Effect Fragmentation Phase 2 Unified Report

## Required Questions

- **Does performance degrade from random split to held-out-tool split?** tool_name_classifier random-vs-heldout FNR delta = 0.2438; held-out stress worsens relative to the random subset.
- **Do methods cluster by tool surface or by realized effect?** Effect-vs-tool clustering gap is -0.4239, indicating tool-surface proximity is at least as strong as same-effect proximity in this controlled diagnostic.
- **Does looking at plan/step/trajectory text solve fragmentation?** No automatic guarantee in this diagnostic: text/plan/step/trajectory proxy baselines are reported separately and must be compared against held-out-tool FNR and action-level errors.
- **Do graph/evidence/provenance methods reduce fragmentation?** Effect/resource and execution-evidence rows are more stable in current tests, but they are marked upper-bound unless implemented as non-oracle verifiers.
- **Where do row-level metrics disagree with action-level safety?** See paired_deltas.row_vs_action and failure examples; row FNR and action-level decision error are reported separately.
- **Which results are paper-grade, original-method, proxy-only, or upper-bound?** AgentDojo is paper-grade environment only; current non-AgentDojo systems are proxy diagnostics or complete adapter-failure audits unless reproduction_audit reports original_method_runnable.
- **What still prevents a top-tier paper claim?** Missing exact original-method reproductions, proxy labels for non-AgentDojo systems, upper-bound effect/evidence rows, and limited mechanism evidence prevent broad cross-paper claims.

## AgentDojo Split Comparison

| Method | Protocol | N | FNR | Held-out-tool FNR | Unsafe pre-allow | Action error | ToolProxyGap |
|---|---|---:|---:|---:|---:|---:|---:|
| `tool_name_classifier` | `random` | 324 | 0.756 [0.707, 0.800] | 1.000 [0.904, 1.000] | 0.756 [0.707, 0.800] | 0.333 [0.180, 0.533] | 0.6207 |
| `tool_name_classifier` | `held_out_tool` | 144 | 1.000 [0.974, 1.000] | 1.000 [0.974, 1.000] | 1.000 [0.974, 1.000] | 1.000 [0.862, 1.000] | NA |
| `tool_name_classifier` | `same_effect_different_tool` | 288 | 1.000 [0.987, 1.000] | 1.000 [0.974, 1.000] | 1.000 [0.987, 1.000] | 1.000 [0.862, 1.000] | NA |
| `arg_schema_classifier` | `random` | 324 | 0.815 [0.769, 0.853] | 0.639 [0.476, 0.775] | 0.815 [0.769, 0.853] | 0.500 [0.314, 0.686] | 0.0872 |
| `arg_schema_classifier` | `held_out_tool` | 144 | 0.500 [0.419, 0.581] | 0.500 [0.419, 0.581] | 0.500 [0.419, 0.581] | 0.500 [0.314, 0.686] | NA |
| `arg_schema_classifier` | `same_effect_different_tool` | 288 | 0.750 [0.697, 0.796] | 0.500 [0.419, 0.581] | 0.750 [0.697, 0.796] | 0.500 [0.314, 0.686] | NA |
| `static_llm_self_audit` | `random` | 324 | 0.519 [0.464, 0.572] | 0.639 [0.476, 0.775] | 0.519 [0.464, 0.572] | 0.000 [0.000, 0.138] | 0.0000 |
| `static_llm_self_audit` | `held_out_tool` | 144 | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `static_llm_self_audit` | `same_effect_different_tool` | 288 | 0.312 [0.262, 0.368] | 0.625 [0.544, 0.700] | 0.312 [0.262, 0.368] | 0.000 [0.000, 0.138] | NA |
| `plan_level_llm_judge` | `random` | 324 | 0.519 [0.464, 0.572] | 0.639 [0.476, 0.775] | 0.519 [0.464, 0.572] | 0.000 [0.000, 0.138] | 0.0000 |
| `plan_level_llm_judge` | `held_out_tool` | 144 | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `plan_level_llm_judge` | `same_effect_different_tool` | 288 | 0.312 [0.262, 0.368] | 0.625 [0.544, 0.700] | 0.312 [0.262, 0.368] | 0.000 [0.000, 0.138] | NA |
| `step_level_classifier` | `random` | 324 | 0.519 [0.464, 0.572] | 0.639 [0.476, 0.775] | 0.519 [0.464, 0.572] | 0.000 [0.000, 0.138] | 0.0000 |
| `step_level_classifier` | `held_out_tool` | 144 | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `step_level_classifier` | `same_effect_different_tool` | 288 | 0.312 [0.262, 0.368] | 0.625 [0.544, 0.700] | 0.312 [0.262, 0.368] | 0.000 [0.000, 0.138] | NA |
| `trajectory_level_classifier` | `random` | 324 | 0.519 [0.464, 0.572] | 0.639 [0.476, 0.775] | 0.519 [0.464, 0.572] | 0.000 [0.000, 0.138] | 0.0000 |
| `trajectory_level_classifier` | `held_out_tool` | 144 | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.544, 0.700] | 0.625 [0.427, 0.788] | NA |
| `trajectory_level_classifier` | `same_effect_different_tool` | 288 | 0.312 [0.262, 0.368] | 0.625 [0.544, 0.700] | 0.312 [0.262, 0.368] | 0.000 [0.000, 0.138] | NA |
| `effect_resource_abstraction` | `random` | 324 | 0.000 [0.000, 0.012] | 0.000 [0.000, 0.096] | 0.000 [0.000, 0.012] | 0.000 [0.000, 0.138] | 0.0000 |
| `effect_resource_abstraction` | `held_out_tool` | 144 | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.138] | NA |
| `effect_resource_abstraction` | `same_effect_different_tool` | 288 | 0.000 [0.000, 0.013] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.013] | 0.000 [0.000, 0.138] | NA |
| `execution_evidence_upper_bound` | `random` | 324 | 0.000 [0.000, 0.012] | 0.000 [0.000, 0.096] | 0.000 [0.000, 0.012] | 0.000 [0.000, 0.138] | 0.0000 |
| `execution_evidence_upper_bound` | `held_out_tool` | 144 | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.138] | NA |
| `execution_evidence_upper_bound` | `same_effect_different_tool` | 288 | 0.000 [0.000, 0.013] | 0.000 [0.000, 0.026] | 0.000 [0.000, 0.013] | 0.000 [0.000, 0.138] | NA |

## External Reproduction Audit

- `toolsafe`: `adapter_failed_complete`; blockers: configured_local_ts_guard_model_missing:/mnt/shared-storage-user/mouyutao/AShell-ours/verl-main/checkpoints/verl_grpo_ashell_guardian_v2.4.0-rollout16_multitask_uniform/qwen2.5_7b_function_rm/global_step_80/actor_hf
- `safiron`: `adapter_failed_complete`; blockers: safiron_model_not_verified_locally:/data/CSK/causal-agent-safety-research/models/Safiron/Safiron
- `ipiguard`: `adapter_failed_complete`; blockers: OPENAI_API_KEY_missing_for_official_eval, OPENAI_BASE_URL_missing_for_official_eval
- `camel`: `adapter_failed_complete`; blockers: OPENAI_API_KEY_missing_for_camel_eval

## Mechanism Experiment

- Effect-vs-tool clustering gap: `-0.4239`
- Interpretation: positive means records are closer by realized effect than by same tool surface

## Claim Boundary

- Can claim: Tool-surface baselines fail under AgentDojo custom stress when reported as paper-grade local stress evidence.
- Can claim: Text/plan/step/trajectory views do not automatically remove fragmentation in current proxy tests.
- Can claim: Effect/resource and execution-evidence upper bounds are more stable in current tests.
- Can claim: Proxy diagnostics identify likely failure modes for step-level, graph-level, and plan-level systems.
- Cannot claim: ToolSafe, IPIGuard, Safiron, or CaMeL original method failure unless an official-method adapter is actually run.
- Cannot claim: Graph/provenance methods generally fail.
- Cannot claim: Execution evidence is a deployable complete safety solution.
