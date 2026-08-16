# E84 Qwen-32B Reviewed-Authority Strong Baselines

| Method | Benign utility | ASR | Utility under attack | Errors |
|---|---:|---:|---:|---:|
| No guard | 20/26 (0.769) | 5/169 (0.030) | 121/169 (0.716) | 0 |
| Prompt Sandwiching | 18/26 (0.692) | 2/169 (0.012) | 130/169 (0.769) | 0 |
| PromptArmor-local | 4/26 (0.154) | 0/169 (0.000) | 23/169 (0.136) | 0 |
| Reviewed authority (ours) | 15/26 (0.577) | 1/169 (0.006) | 124/169 (0.734) | 0 |

## Runtime Audit

- Pre-commit checks: `404`
- Decisions: `{'ALLOW': 335, 'ABSTAIN': 69}`
- Blocked calls executed: `0`

## Claim Boundary

This is a common-checkpoint comparison on the 26-task reviewed-authority AgentDojo v1.1.2 subset and its complete official injection cross-product. It is not the full 726-case benchmark and does not establish production safety.
