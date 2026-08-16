# E71 Claim Boundary

E71 tests whether a local Qwen GGUF model can identify atom fields whose absence prevents stable effect inference on saved AgentDojo/IPIGuard-style replay traces. The LLM does not make runtime safety decisions. Runtime control is a deterministic authorization check over descriptors selected from field-necessity tests. Labels and sidecar atoms are used only for offline scoring, not in prompts or runtime inputs. This is not production-safety evidence.
