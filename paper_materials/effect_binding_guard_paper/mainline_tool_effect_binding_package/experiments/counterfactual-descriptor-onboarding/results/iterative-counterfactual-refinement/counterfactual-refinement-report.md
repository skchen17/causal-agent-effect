# E63 Iterative Counterfactual Contract Refinement Report

## Summary

- Backend: `static`.
- Model: `test-double`.
- Generation: max_tokens ``, response_format `json_object`, max refinement rounds `2`.
- Backend health: `True` (static backend).
- Local LLM status: `executed`.
- Held-out tools: `1`.
- Candidate records: `1`.
- Prompt leakage violations: `0`.
- Feedback leakage violations: `0`.

## Final Selection

- Freezeable tools: `1/1`.
- Human-review required: `0`.
- Mean required atom coverage: `1.0`.
- Mean resource binding coverage: `1.0`.
- Mean target-principal coverage: `1.0`.

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

Outcome A: iterative counterfactual feedback produced freezeable contracts for all held-out tools.

## Claim Boundary

E63 evaluates one configured local LLM backend on a 15-tool held-out mock suite with up to four sanitized counterfactual feedback rounds. It froze 1/1 tools. It does not support production safety, arbitrary-tool inference, live deployment safety, or real external API behavior.
