# E75 AgentDojo Live Protocol Check

Status: `passed`.
Live full-run ready: `True`.
Recommended live runner: `AgentDojo model=LOCAL with --tool-delimiter user`.
Blocking issue: none

| Model path | Tool delimiter | Return code | Clean protocol | 500 error | tool_call_id schema error | developer-role schema error | post-tool empty assistant | missing utility/security |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `LOCAL` | `tool` | 0 | False | True | True | False | True | False |
| `LOCAL` | `user` | 0 | True | False | False | False | False | False |
| `VLLM_PARSED` | `tool` | 1 | False | True | False | True | False | True |

## Boundary

This protocol check is a smoke test of official AgentDojo runner compatibility. It is not a full 726-case evaluation and should not be reported as a method result.
