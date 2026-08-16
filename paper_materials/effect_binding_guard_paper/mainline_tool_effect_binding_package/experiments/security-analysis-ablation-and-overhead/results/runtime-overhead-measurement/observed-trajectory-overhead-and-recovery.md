# Observed Trajectory Cost and Recovery

- Status: `passed_with_observational_timing_caveat`
- Paired official keys: `726`
- No guard duration: median `53.27s`, p95 `158.84s`.
- E77 duration: median `85.54s`, p95 `266.56s`.
- Paired median ratio: `1.360`; paired median delta: `18.95s`.
- Pre-commit checks: `2930`.
- Revision-model calls: `738`.
- Checks transitioned from replan to allow: `32`.
- Trajectories with feedback: `359/726`; utility `51/359`.

## Claim Boundary

Duration is a post-hoc paired observation from historical sequential runs. It includes model inference, sandbox work, and any recovery calls, but server load and execution order were not randomized. Twelve E77 rows also use disclosed larger-context repairs. The duration difference therefore describes observed trajectory cost and must not be interpreted as the causal latency added by the guard. Recovery counts are mechanistic audit totals; feedback/utility rates are associations, not causal effects.
