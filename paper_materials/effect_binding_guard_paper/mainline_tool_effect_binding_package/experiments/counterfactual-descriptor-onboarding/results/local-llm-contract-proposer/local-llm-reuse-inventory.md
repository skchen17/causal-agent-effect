# E62 Reuse Inventory

## Reused From E60

- `ToolSpec`, `ToolEffectContract`, `EffectTemplate`, `EffectAtom`, `AuthorizationContext`, `CounterfactualCase`, and `ValidationResult`.
- Counterfactual validator metrics: UPA, FDeny, coverage, required atom coverage, required resource binding coverage, and required target-principal coverage.
- Frozen-contract runtime and `freeze_contract` gate.

## New In E62

- Fifteen held-out mock tool specs disjoint from the E60 five-tool prototype.
- Prompt construction and leakage scanning for local LLM contract proposal.
- Strict JSON parser from local LLM text to E60-compatible contracts.
- One-step validation-summary refinement that does not expose hidden reference contracts or expected atoms.
- Local backend adapters for Ollama and OpenAI-compatible endpoints.
- Report artifacts for prompts, failures, per-tool metrics, claim boundary, and reuse inventory.

## Boundary

E62 validates local proposal quality for mock contracts. It does not replace E55/E60 deterministic runtime authorization and does not execute real external side effects.
