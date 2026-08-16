# Security Theory Validation

## Theorem 1: Representation Collision

The theorem is a deterministic information lower bound. If two executions share the same monitor representation but an admissible policy authorizes one and rejects the other, a monitor receiving only that representation must return the same decision for both. `ALLOW` is unsafe for one member; `DENY` or `ABSTAIN` withholds the other. The result does not require an LLM assumption and applies equally to tool-name, whole-call, or atom representations.

Executable checks: `test_tool_effect_binding_theory.py`, finite-domain collision tests, and ToolSandbox collision tests. The relevant 17 tests pass.

## Theorem 2: Finite Refinement

Each valid counterexample splits at least one nonempty representation cell and the procedure never merges cells. A partition of finite domain `D` has at most `|D|` cells, so at most `|D|-1` strict splits are possible. Zero mixed cells implies authorization sufficiency only for the enumerated domain and policy family.

Empirical instance: the 56-call, 32-vertex qualifier lattice has zero refinement, separating-pair, or ambiguous-lower-bound monotonicity violations across 211 comparable edges. One five-step trajectory reduces separating pairs `124 -> 60 -> 28 -> 12 -> 4 -> 0` within the bound of 55 splits.

## Theorem 3: Conditional Provenance-Origin Confinement

C1f allows only if a registered effect-bearing value drawn from provenance-marked untrusted evidence is also grounded in the authenticated task, and an untrusted request for the registered effect is also task-grounded. Under descriptor soundness, provenance soundness, complete mediation, and check-use consistency, an allowed commit cannot contain a registered effect or registered value introduced solely by untrusted evidence outside the task.

The proof is conditional. Counterfactual registration supplies bounded evidence for descriptor adequacy; runtime signature reconciliation tests complete mediation and check-use consistency in the sandbox. The implementation does not establish general ACL authorization, delegation, quota safety, authenticated-user safety, or unseen-effect coverage.

## Submission Risk

The first two results are mathematically sound and directly connected to finite source evidence. The third is useful only if presented as a narrow systems invariant with explicit trusted assumptions. Calling it trajectory safety, complete authorization, or a proof of deployed safety would be incorrect.
