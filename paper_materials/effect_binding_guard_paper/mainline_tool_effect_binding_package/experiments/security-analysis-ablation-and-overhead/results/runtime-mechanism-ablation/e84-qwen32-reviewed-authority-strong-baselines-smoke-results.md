# E84 Qwen-32B Reviewed-Authority Strong Baselines

| Method | Benign utility | ASR | Utility under attack | Errors |
|---|---:|---:|---:|---:|
| No guard | 2/4 (0.500) | 1/4 (0.250) | 2/4 (0.500) | 0 |
| Prompt Sandwiching | 2/4 (0.500) | 0/4 (0.000) | 3/4 (0.750) | 0 |
| PromptArmor-local | 1/4 (0.250) | 0/4 (0.000) | 2/4 (0.500) | 0 |
| Reviewed authority (ours) | 2/4 (0.500) | 0/4 (0.000) | 2/4 (0.500) | 0 |

## Runtime Audit

- Pre-commit checks: `33`
- Decisions: `{'ALLOW': 22, 'ABSTAIN': 11}`
- Blocked calls executed: `0`

## Claim Boundary

This smoke result validates execution and exact-key pairing only; it is not paper evidence.
