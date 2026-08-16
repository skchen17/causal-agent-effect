# Full-Benign Abstain Root-Cause Audit

- Tasks: `97`
- Pre-commit decisions: `{'ABSTAIN': 152, 'ALLOW': 270, 'DENY': 4}`
- Guard/no-guard utility: `26/97` / `64/97`
- Missing-authority abstains: `107`
- Unproven-resolver abstains: `43`
- Unbound-field abstains: `3`
- Outside-plan abstains: `2`

## Failed-Task Correlates

- `authority_manifest_unavailable`: `34`
- `no_guard_intervention`: `21`
- `outside_exact_authority`: `3`
- `resolver_value_unproven`: `13`

## Claim Boundary

This is a mechanical correlation audit over paired task keys, not a causal decomposition of utility. No-guard and guarded trajectories were separate deterministic-temperature runs, and a blocking event need not be the sole reason a task failed. Task text, arguments, and model output are excluded from the artifact.
