# E63 Iterative Counterfactual Contract Refinement Report

## Summary

- Backend: `openai_compatible`.
- Model: `deepseek-v4-flash`.
- Generation: max_tokens `4096`, response_format `json_object`, max refinement rounds `4`.
- Backend health: `True` (openai-compatible endpoint reachable).
- Local LLM status: `executed`.
- Held-out tools: `15`.
- Candidate records: `71`.
- Prompt leakage violations: `0`.
- Feedback leakage violations: `0`.

## Final Selection

- Freezeable tools: `1/15`.
- Human-review required: `14`.
- Mean required atom coverage: `0.067`.
- Mean resource binding coverage: `0.133`.
- Mean target-principal coverage: `0.133`.

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

Outcome B: iterative counterfactual feedback produced some freezeable contracts; remaining tools require human review.

## Claim Boundary

E63 evaluates one configured local LLM backend on a 15-tool held-out mock suite with up to four sanitized counterfactual feedback rounds. It froze 1/15 tools. It does not support production safety, arbitrary-tool inference, live deployment safety, or real external API behavior.
