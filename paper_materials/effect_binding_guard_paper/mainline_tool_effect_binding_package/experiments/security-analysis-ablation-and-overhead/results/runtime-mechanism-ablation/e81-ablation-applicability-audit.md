# E81 Ablation Applicability Audit

- Status: `passed_with_nonapplicable_a13`
- Reviewed tasks: `26`
- Reviewed effectful authority rows: `2`

| Row | Applicable support |
|---|---:|
| A2 | 2 reviewed tool rows |
| A7 | 1 resolver rows |
| A9 | 2 reviewed tool rows; 0 round-0 registered |
| A11 | dynamic; count from runtime proposals |
| A12 | 1 resolver rows |
| A13 | 0 dynamic security defaults |
| A15 | 69 blocked A1 precommit checks |

## Claim Boundary

A13 has no applicable dynamic security-default field in this reviewed AgentDojo slice and cannot support an empirical default-handling claim. A2, A7, A9, and A12 also have narrow applicability because only two reviewed tasks authorize effectful calls and one uses a typed resolver.
