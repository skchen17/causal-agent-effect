# E70 Claim Boundary

E70 evaluates a local Qwen GGUF model as an offline proposer of atomized tool-effect descriptors over saved AgentDojo/IPIGuard-style replay traces. The LLM does not make runtime safety decisions. Runtime control is a deterministic atom extraction and authorization check over registered descriptors. Labels and rule-derived atom sidecars are used only for offline scoring, not in prompts or runtime inputs. This is not production-safety or deployed-system evidence.
