# E81 Qwen3-32B Runtime-Mechanism Ablation

- Status: `passed_with_nonapplicable_a13`
- Exact-key cases per row: `195`

| Row | Variant | Benign utility | ASR | Utility under attack |
|---|---|---:|---:|---:|
| A0 | No guard | 20/26 (0.769) | 5/169 (0.030) | 121/169 (0.716) |
| A1 | Full reviewed effect-contract guard | 15/26 (0.577) | 1/169 (0.006) | 124/169 (0.734) |
| A2 | Tool-call-level only | 15/26 (0.577) | 1/169 (0.006) | 124/169 (0.734) |
| A7 | No provenance/control binding | 15/26 (0.577) | 1/169 (0.006) | 122/169 (0.722) |
| A9 | Schema-description-only registration | 13/26 (0.500) | 1/169 (0.006) | 107/169 (0.633) |
| A11 | No task authority envelope | 15/26 (0.577) | 3/169 (0.018) | 121/169 (0.716) |
| A12 | No authorized-read grounding | 14/26 (0.538) | 1/169 (0.006) | 116/169 (0.686) |
| A13 | Omitted fields permissive | 15/26 (0.577) | 1/169 (0.006) | 122/169 (0.722) |
| A15 | No replan recovery | 15/26 (0.577) | 0/169 (0.000) | 120/169 (0.710) |

## Claim Boundary

This is a paired Qwen3-32B AgentDojo v1.1.2 ablation on 26 reviewed tasks and 169 official task-injection pairs. A7 is an operational ablation of typed/provenance-bound resolver evidence; it is not a general provenance-system evaluation.
