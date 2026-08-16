# E78 Headline Benign-Utility Pathway Audit

## Scope

- Frozen capacity-matched benign tasks: 97
- Model calls: 0
- Tool executions: 0
- Official utility labels changed: no

## Paired Decomposition

- Overall: no guard 63/97; guard 33/97; net -30.
- Runtime-feedback stratum: 47 cases, 35->4 successes, net -31.
- No-feedback stratum: 50 cases, 28->29 successes, net 1.
- Discordant losses with observed runtime feedback: 32/37.

## Runtime-Feedback Loss Anatomy

- Initial-plan construction/coverage reason on 16/32 losses.
- Binding/evidence reason on 22/32 losses.
- Non-exclusive reason-case counts: `{"forbidden_field_used": 5, "outside_exact_plan": 7, "resolver_fill_requires_replan": 17, "task_permission_plan_parse_failed": 6, "tool_not_in_initial_permission_plan": 10}`.
- Resolver checks in the literal probe: 85; loss cases with at least one resolver value visible in an earlier benign tool result: 12.

## Interpretation

The headline utility gap is concentrated in trajectories that receive runtime feedback, especially initial-plan and binding/evidence failures. This implicates the current planning, evidence, and recovery interfaces; it does not show that effect decomposition itself requires the observed utility loss.

## Claim Boundary

This is a deterministic post-hoc pathway audit of frozen E78 logs. Runtime feedback is directly observed, but the no-guard and guarded model trajectories are separate stochastic runs, so stratum differences are not randomized causal effects. The literal-grounding probe is a diagnostic sensitivity check, not an authorization oracle. Official AgentDojo utility labels remain unchanged.
