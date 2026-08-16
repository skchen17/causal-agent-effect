# E69 Counterfactually Selected Atomized Tool Contracts

Model: `e69-qwen-local`.
Source traces: `156`.
Tools: `24`.
Candidate rows: `24`; valid: `23`.
Counterfactual tasks: `960`.
Pair outputs: `1920`.
Overall pair pass: `{'successes': 308, 'total': 1920, 'rate': 0.16}`.
Unsafe pre-allow: `{'successes': 337, 'total': 1920, 'rate': 0.176}`.
Selected top-k contracts: `23`.
Strictly freezeable selected contracts: `0`.
Replay atomized metrics: `{'n': 156, 'accuracy': {'successes': 33, 'total': 156, 'rate': 0.212}, 'coverage': {'successes': 137, 'total': 156, 'rate': 0.878}, 'abstain': {'successes': 19, 'total': 156, 'rate': 0.122}, 'unsafe_pre_allow': {'successes': 103, 'total': 134, 'rate': 0.769}, 'false_deny': {'successes': 1, 'total': 22, 'rate': 0.045}, 'n_predictions_available': 152}`.

## Claim Boundary

E69 evaluates one configured local Qwen GGUF model on saved AgentDojo/IPIGuard-style replay traces. The model proposes atomized tool contracts from label-hidden deployable tool views; hidden sidecar labels/atoms are used only for scoring. Top-k selected contracts are experimental descriptors, not safety-certified frozen contracts unless strictly_freezeable=true. No real tools are executed, and the result is not production-safety or deployed-system evidence.
