# E71 Atom Field Necessity Guided Runtime Guard

Model: `e71-qwen-local`.
Source traces: `156`.
Tools: `24`.
Field necessity tasks: `78`.
LLM outputs: `156`; parse-valid pairs: `156`.
Necessity passes: `66`.
Registered tools: `20`; unregistered tools: `4`.
Runtime guard metrics: `{'n': 156, 'accuracy': {'successes': 108, 'total': 156, 'rate': 0.692}, 'coverage': {'successes': 128, 'total': 156, 'rate': 0.821}, 'abstain': {'successes': 28, 'total': 156, 'rate': 0.179}, 'unsafe_pre_allow': {'successes': 0, 'total': 134, 'rate': 0.0}, 'false_deny': {'successes': 20, 'total': 22, 'rate': 0.909}, 'n_predictions_available': 156}`.

## Claim Boundary

E71 tests whether a local Qwen GGUF model can identify atom fields whose absence prevents stable effect inference on saved AgentDojo/IPIGuard-style replay traces. The LLM does not make runtime safety decisions. Runtime control is a deterministic authorization check over descriptors selected from field-necessity tests. Labels and sidecar atoms are used only for offline scoring, not in prompts or runtime inputs. This is not production-safety evidence.
