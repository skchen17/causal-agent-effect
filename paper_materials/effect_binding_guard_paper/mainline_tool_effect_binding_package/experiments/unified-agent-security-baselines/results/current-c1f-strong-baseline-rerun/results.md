# Current C1f Qwen32 Strong-Baseline Rerun

| Method | Benign utility | Attack utility | Attack success |
|---|---:|---:|---:|
| No guard | 60/97 | 324/629 | 63/629 |
| Spotlighting | 64/97 | 345/629 | 60/629 |
| Prompt Sandwiching | 66/97 | 374/629 | 6/629 |
| PromptArmor-style | 27/97 | 152/629 | 0/629 |
| Current C1f | 59/97 | 318/629 | 18/629 |

Same Qwen3-32B checkpoint, 65,536-token context, exact 726 AgentDojo v1.1.2 keys, native validators, and sandbox execution. Prompt Sandwiching and PromptArmor-style are comparable local adapters, not original-paper reproductions.
