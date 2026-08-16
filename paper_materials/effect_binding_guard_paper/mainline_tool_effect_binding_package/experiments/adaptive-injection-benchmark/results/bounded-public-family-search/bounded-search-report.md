# Bounded Public-Family Search

Status: `passed`.

- Locked AgentDojo keys: `40`.
- Executed variant rows: `320`.
- Frozen family order: `tool_knowledge, important_instructions, ignore_previous, injecagent`.

| Method | N | Worst-of-4 attacks | ASR | Terminal utility | Rate |
|---|---:|---:|---:|---:|---:|
| no_guard | 40 | 4 | 0.100 | 18 | 0.450 |
| ours_e77_effect_diff_runtime | 40 | 1 | 0.025 | 12 | 0.300 |

## Paired Exact Tests

- `attack_success`: reference-only `4`, guard-only `1`, exact two-sided McNemar `p=0.375000`.
- `terminal_user_utility`: reference-only `7`, guard-only `1`, exact two-sided McNemar `p=0.070312`.

## Claim Boundary

This is a bounded worst-of-four search over public AgentDojo attack generators on 40 locked benchmark keys. It is stronger than a single fixed template but is not unrestricted adaptive prompt generation, a deployed attack study, or production-safety evidence.
