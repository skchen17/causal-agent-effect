# E70 Counterfactually Guided Atom Descriptor Runtime Guard

Model: `e70-qwen-local`.
Source traces: `156`.
Tools: `24`.
Descriptor candidates: `96`; parse-valid: `91`.
Counterfactual tasks: `966`.
Registered tools: `0`; unregistered tools: `24`.
Runtime guard metrics: `{'n': 156, 'accuracy': {'successes': 0, 'total': 156, 'rate': 0.0}, 'coverage': {'successes': 0, 'total': 156, 'rate': 0.0}, 'abstain': {'successes': 156, 'total': 156, 'rate': 1.0}, 'unsafe_pre_allow': {'successes': 0, 'total': 134, 'rate': 0.0}, 'false_deny': {'successes': 0, 'total': 22, 'rate': 0.0}, 'n_predictions_available': 156}`.
Rule-derived sidecar reference: `{'n': 156, 'accuracy': {'successes': 156, 'total': 156, 'rate': 1.0}, 'coverage': {'successes': 156, 'total': 156, 'rate': 1.0}, 'abstain': {'successes': 0, 'total': 156, 'rate': 0.0}, 'unsafe_pre_allow': {'successes': 0, 'total': 134, 'rate': 0.0}, 'false_deny': {'successes': 0, 'total': 22, 'rate': 0.0}, 'n_predictions_available': 156}`.

## Claim Boundary

E70 evaluates a local Qwen GGUF model as an offline proposer of atomized tool-effect descriptors over saved AgentDojo/IPIGuard-style replay traces. The LLM does not make runtime safety decisions. Runtime control is a deterministic atom extraction and authorization check over registered descriptors. Labels and rule-derived atom sidecars are used only for offline scoring, not in prompts or runtime inputs. This is not production-safety or deployed-system evidence.
