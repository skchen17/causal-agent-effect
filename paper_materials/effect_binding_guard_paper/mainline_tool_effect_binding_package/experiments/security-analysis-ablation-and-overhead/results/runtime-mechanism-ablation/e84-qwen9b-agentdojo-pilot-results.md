# E84 Qwen-9B AgentDojo Reviewed-Authority Evaluation

| Method | Benign utility | ASR | Utility under attack |
|---|---:|---:|---:|
| No guard | 16/26 (0.615) | 2/26 (0.077) | 16/26 (0.615) |
| E84 reviewed authority | 16/26 (0.615) | 0/26 (0.000) | 17/26 (0.654) |

## Runtime Audit

- Pre-commit checks: `107`
- Decisions: `{'ALLOW': 81, 'ABSTAIN': 26}`
- Blocked calls executed: `0`
- No-guard traces with out-of-manifest committed effects: `1`

## Claim Boundary

On this fixed 26-task AgentDojo v1.1.2 reviewed-authority subset, E84 changes official attack success from 2/26 to 0/26 and benign utility from 16/26 to 16/26. The run uses one official injection per task and is not a full-cross evaluation. It does not establish production safety.
