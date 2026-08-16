# E80 Compound-Effect Contract Checks

Status: `passed_with_scope_boundary`.

- AgentDojo tool cases: `4`.
- Templates checked: event creation and per-recipient invitation disclosure.
- Every observed sandbox effect is covered by the explicit contract in the enumerated cases.
- A conjunction-triggered synthetic effect is invisible to isolated one-field tests.

## Claim Boundary

The check executes four schema-valid create_calendar_event calls in fresh AgentDojo sandbox states and shows coverage by a two-template contract with explicit-recipient and implicit-owner expansion. It does not prove coverage for other tools or states. The synthetic conjunction demonstrates that E77's one-field base-state tests are insufficient and motivates pairwise or condition-aware registration.
