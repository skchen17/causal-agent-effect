# E68 Claim Boundary

E68 tests one configured local Qwen GGUF model on saved AgentDojo/IPIGuard-style replay traces. It measures whether the model's atom and decision outputs are sensitive to structured counterfactual field changes and robust to prompt-injected context. Labels and atoms are metadata/rule-derived sidecars, not independent human gold. No real tools are executed and the result is not production-safety evidence. This artifact is a bounded-field run and should not be described as an all-axis full run.
