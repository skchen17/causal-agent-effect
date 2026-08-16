# E63 Iterative Counterfactual Contract Refinement Report

## Summary

- Backend: `openai_compatible`.
- Model: `deepseek-v4-flash`.
- Generation: max_tokens `4096`, response_format `json_object`, max refinement rounds `0`.
- Backend health: `True` (openai-compatible endpoint reachable).
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
  "raw_parse_valid": 0,
  "refined_freezeable": 0,
  "refined_parse_valid": 0
}

## Conclusion

Outcome C: iterative counterfactual feedback did not produce freezeable contracts; validation routed all tools to human review.

## Claim Boundary

E63 evaluates one configured local LLM backend on a 15-tool held-out mock suite with up to four sanitized counterfactual feedback rounds. It froze 0/1 tools. It does not support production safety, arbitrary-tool inference, live deployment safety, or real external API behavior.
