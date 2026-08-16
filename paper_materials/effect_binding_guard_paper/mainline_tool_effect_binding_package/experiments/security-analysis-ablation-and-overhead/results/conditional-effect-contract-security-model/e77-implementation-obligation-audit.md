# E80 E77 Implementation-Obligation Audit

Status: `passed_with_conditional_gaps`.

- Official cases: 726.
- Valid structured calls emitted: 3235.
- Calls without a tool-result event: 62.
- Calls reaching the executor: 3173.
- Matching pre-commit checks: 3173.
- Signature multiset exact match: `True`.

| Obligation | Status | Remaining gap |
|---|---|---|
| O1_contract_soundness | `partial` | Finite base-state field tests do not prove that every reachable compound effect is covered. |
| O2_envelope_soundness | `partial` | The LLM-generated envelope has no independent semantic soundness proof for every task. |
| O3_complete_mediation | `passed_for_official_agentdojo_run` | None within stated scope. |
| O4_check_use_integrity | `passed_for_sandbox_call_object` | No claim is made for concurrent remote services or post-check mutation outside this executor. |
| O5_fail_closed_uncertainty | `partial` | Other tool ecosystems may have effect-bearing nonempty defaults and require explicit default instantiation. |

## Claim Boundary

This audit establishes exact pre-commit interception for executed valid calls in the completed AgentDojo run. It does not establish global contract or envelope soundness, nor mediation of remote services outside the sandbox.
