# E79 DeepSeek C1f-PN Comparison Pilot

Status: `passed_security_difference_inconclusive`.

| Method | Official attack success | Utility |
|---|---:|---:|
| No guard | 0/24 (0.0%) | 21/24 (87.5%) |
| C1f-PN | 0/24 (0.0%) | 18/24 (75.0%) |

C1f-PN mediated all 159 executed tool-result calls and issued 25 deterministic denials. The denials covered fund transfer and Slack messaging tools. All three additional utility failures occurred on user tasks whose guarded trajectories contained denials.

## Interpretation

The repair is active beyond the development examples: an outcome-blind four-suite sample produced normalized provenance and deterministic denials for multiple effectful tool families. Security benefit is inconclusive because DeepSeek had zero official attack successes without a guard. C1f-PN lost three additional utility cases, all associated with denied trajectories, so recovery after a correct denial remains an engineering and evaluation requirement.

## Claim boundary

This 24-case pilot validates adapter activity, complete mediation, and matched utility behavior. It is not a confirmatory ASR result, does not reproduce AgentLAB attack optimization, and cannot establish a security improvement when the no-guard denominator contains zero attack successes.
