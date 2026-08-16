# E63 Iterative Counterfactual Contract Refinement Report

## Summary

- Backend: `transformers_gemma4_text_only`.
- Model: `gemma4-26b-a4b-it-text-only`.
- Generation: max_tokens `128`, response_format `json_object`, max refinement rounds `0`.
- Backend health: `True` ({"bnb_compute_dtype": "bf16", "bnb_double_quant": true, "bnb_quant_type": "nf4", "device_map_sample": [["model.embed_tokens", 0], ["model.norm", 0], ["model.layers.0", 0], ["model.layers.1", 0], ["model.layers.2", 0], ["model.layers.3", 0], ["model.layers.4", 0], ["model.layers.5", 0], ["model.layers.6", 0], ["model.layers.7", 0], ["model.layers.8", 0], ["model.layers.9", 0], ["model.layers.10", 0], ["model.layers.11", 0], ["model.layers.12", 0], ["model.layers.13", 1], ["model.layers.14", 1], ["model.layers.15", 1], ["model.layers.16", 1], ["model.layers.17", 1], ["model.layers.18", 1], ["model.layers.19", 1], ["model.layers.20", 1], ["model.layers.21", 1], ["model.layers.22", 1], ["model.layers.23", 1], ["model.layers.24", 1], ["model.layers.25", 1], ["model.layers.26", 1], ["model.layers.27", 1]], "eager_expert_modules": 153, "experts_implementation": "eager", "language_weight_keys": 657, "last_layer_on_gpu0": true, "layer_split": 13, "max_memory": {"cpu": "100GiB", "gpu0": "16GiB", "gpu1": "16GiB"}, "missing_non_lm_head": 0, "model_path": "/data/CSK/causal-agent-safety-research/.hf_cache/hub/models--google--gemma-4-26B-A4B-it/snapshots/462a98a12e28e2cbcfccaf78fe41e3e50235e6ae", "quantization": "4bit", "unexpected_language_keys": 0}).
- Local LLM status: `executed`.
- Held-out tools: `1`.
- Candidate records: `1`.
- Prompt leakage violations: `0`.
- Feedback leakage violations: `0`.

## Final Selection

- Freezeable tools: `0/1`.
- Human-review required: `1`.
- Mean required atom coverage: `0.0`.
- Mean resource binding coverage: `0.0`.
- Mean target-principal coverage: `0.0`.

## E62 Comparison

{
  "available": true,
  "conclusion": "Outcome C: local LLM proposals did not pass the strict freeze gate.",
  "raw_freezeable": 0,
  "raw_parse_valid": 15,
  "refined_freezeable": 0,
  "refined_parse_valid": 15
}

## Conclusion

Outcome C: iterative counterfactual feedback did not produce freezeable contracts; validation routed all tools to human review.

## Claim Boundary

E63 evaluates one configured local LLM backend on a 15-tool held-out mock suite with up to four sanitized counterfactual feedback rounds. It froze 0/1 tools. It does not support production safety, arbitrary-tool inference, live deployment safety, or real external API behavior.
