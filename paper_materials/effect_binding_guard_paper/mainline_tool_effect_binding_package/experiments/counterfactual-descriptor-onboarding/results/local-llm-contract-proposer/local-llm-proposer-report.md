# E62 Local LLM Effect-Contract Proposer Validation Report

## Summary

- Backend: `static`.
- Model: `test-double`.
- Generation: max_tokens ``, response_format `json_object`.
- Backend health: `True` (static backend).
- Local LLM status: `executed`.
- Held-out tools: `15`.
- Metric rows: `45`.

## Stub Harness

- Rows: `15`.
- Freezeable: `15`.

## Raw Local LLM

- Rows: `15`.
- Parse-valid: `0`.
- Freezeable: `0`.

## Refined Local LLM

- Rows: `15`.
- Parse-valid: `0`.
- Freezeable: `0`.

## Conclusion

Outcome C: local LLM proposals did not pass the strict freeze gate.

## Claim Boundary

E62 supports claims about the configured local LLM backend on this 15-tool held-out mock suite. It does not support production safety, arbitrary-tool contract inference, or real external API behavior.

The stub harness is a validation-path sanity check only and is not counted as local LLM evidence.
