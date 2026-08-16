# E81 Runtime Ablation Kernel Readiness

Status: `implementation_ready_not_evaluated`.

- `A1` diff: `{}`
- `A2` diff: `{"field_granularity": [true, false]}`
- `A7` diff: `{"provenance_control_binding": [true, false]}`
- `A9` diff: `{"counterfactual_registration": [true, false]}`
- `A11` diff: `{"task_envelope": [true, false]}`
- `A12` diff: `{"authorized_read_grounding": [true, false]}`
- `A13` diff: `{"omitted_fields_fail_closed": [true, false]}`
- `A15` diff: `{"replan_enabled": [true, false]}`

## Claim Boundary

The pure kernels and single-component counterexamples pass unit tests. No AgentDojo, ToolSandbox, long-horizon, security, utility, or overhead result is claimed until these rows run on one frozen protocol.
