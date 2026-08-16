# E84 Exact-Only AgentDojo Wiring Smoke

- Status: `passed`
- Reviewed manifests: `25`
- Read-only task manifests: `24`
- Effectful task manifests: `1`
- Exact-authority ALLOW checks: `1`
- Outside-authority DENY checks: `1`
- External side effects: `0`

## Claim Boundary

This smoke validates task-hash selection and deterministic exact-authority mediation against the reviewed AgentDojo manifests and frozen runtime catalog. Twenty-four manifests are read-only and only one contains an effectful authority tool, so this artifact is wiring evidence, not an end-to-end security or utility result. Resolver-dependent tasks remain blocked by independent human review.
