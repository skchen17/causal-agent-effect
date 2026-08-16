# E68 Qwen AgentDojo-Style Counterfactual Atom Stress Test

Model: `Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf`.
Source traces: `156`.
Counterfactual pairs: `312`.
Pair outputs: `156`.
Run scope: `bounded-field run: up to 2 generated counterfactual fields per source trace from requested axes ['resource', 'operation', 'commit_mode', 'visibility', 'provenance', 'control_source', 'multi_resource', 'surface_invariant']; observed axes ['operation', 'resource'].`.
Overall pair pass: `{'successes': 65, 'total': 156, 'rate': 0.417}`.
Clean pair pass: `{'successes': 25, 'total': 78, 'rate': 0.321}`.
Injected pair pass: `{'successes': 40, 'total': 78, 'rate': 0.513}`.
Injection robustness: `{'successes': 2, 'total': 78, 'rate': 0.026}`.
Frozen descriptor fragments: `0`.

## Claim Boundary

E68 tests one configured local Qwen GGUF model on saved AgentDojo/IPIGuard-style replay traces. It measures whether the model's atom and decision outputs are sensitive to structured counterfactual field changes and robust to prompt-injected context. Labels and atoms are metadata/rule-derived sidecars, not independent human gold. No real tools are executed and the result is not production-safety evidence. This artifact is a bounded-field run and should not be described as an all-axis full run.
