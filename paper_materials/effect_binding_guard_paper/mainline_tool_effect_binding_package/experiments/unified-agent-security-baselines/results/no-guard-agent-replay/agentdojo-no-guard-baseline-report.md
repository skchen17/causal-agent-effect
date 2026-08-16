# E74 AgentDojo No-Guard Baseline

Status: `passed`.
Baseline type: `saved_no_defense_agentdojo_ipiguard_local_qwen_rescore`.
Model: `Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf`.
Source trace: `data/data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl`.
Live official AgentDojo rerun performed: `False`.
Live rerun blocker: `external/systems/ipiguard is absent from this package; agentdojo is not importable in the current Python environment`.

## Full Saved Source File

Rows: `1452`; modes: `{'benign': 194, 'attack': 1258}`; suites: `{'workspace': 560, 'slack': 252, 'travel': 320, 'banking': 320}`.
Components: `{'agentdojo_no_defense_local_model': 726, 'original_ipiguard_construct_traverse_pipeline': 726}`; policy modes: `{'none': 726, 'normal': 726}`.
Errors: `{'False': 1428, 'True': 24}`; real-side-effect flags: `{'False': 1452}`.

## No-Guard Component

Rows: `726`; modes: `{'benign': 97, 'attack': 629}`.
Attack success over all no-guard attack rows: `{'successes': 0, 'total': 629, 'rate': 0.0}`.
Attack success over valid no-guard replay attack rows: `{'successes': 0, 'total': 629, 'rate': 0.0}`.
IPIGuard-normal comparison attack success over all attack rows: `{'successes': 4, 'total': 629, 'rate': 0.006}`.

## E61-Aligned Mutating Subset

Cases: `156`.
Prediction rule: No pre-commit guard: every selected mutating candidate tool call is treated as ALLOW.
AgentDojo official-ASR labels: `{'ALLOW': 156}`.
Strict sidecar diagnostic labels: `{'ALLOW': 22, 'DENY': 134}`.
No-guard vs official-ASR: `{'n': 156, 'accuracy': {'successes': 156, 'total': 156, 'rate': 1.0}, 'coverage': {'successes': 156, 'total': 156, 'rate': 1.0}, 'abstain': {'successes': 0, 'total': 156, 'rate': 0.0}, 'unsafe_pre_allow': {'successes': 0, 'total': 0, 'rate': None}, 'false_deny': {'successes': 0, 'total': 156, 'rate': 0.0}, 'n_predictions_available': 156}`.
No-guard vs strict sidecar diagnostic: `{'n': 156, 'accuracy': {'successes': 22, 'total': 156, 'rate': 0.141}, 'coverage': {'successes': 156, 'total': 156, 'rate': 1.0}, 'abstain': {'successes': 0, 'total': 156, 'rate': 0.0}, 'unsafe_pre_allow': {'successes': 134, 'total': 134, 'rate': 1.0}, 'false_deny': {'successes': 0, 'total': 22, 'rate': 0.0}, 'n_predictions_available': 156}`.

## Boundary

E74 is a no-guard baseline over the saved AgentDojo/IPIGuard local-Qwen replay artifact already present in the package. It separately reports the mixed full saved source file, the pure no-guard component, and the E61-aligned mutating-call subset. The E61-aligned pre-commit baseline treats every selected candidate side-effectful tool call as ALLOW because no guard mediated the call. This is not a live official AgentDojo rerun: the package does not contain external/systems/ipiguard. It also does not execute real tools or external side effects. AgentDojo targeted-ASR labels come from saved replay metadata; strict sidecar labels remain a diagnostic overreach/provenance view rather than official AgentDojo labels.
