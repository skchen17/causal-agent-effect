# E78 Per-Case Capacity-Matched Comparison

| Method | BU (evaluable) | UA (evaluable) | ASR (evaluable) | Errors |
|---|---:|---:|---:|---:|
| No defense | 0.649 (97/97) | 0.550 (627/629) | 0.086 (627/629) | 2 |
| MELON-style | 0.635 (96/97) | 0.542 (627/629) | 0.089 (627/629) | 3 |
| Prompt Sandwiching | 0.629 (97/97) | 0.581 (627/629) | 0.013 (627/629) | 2 |
| PromptArmor-style | 0.278 (97/97) | 0.219 (629/629) | 0.002 (629/629) | 0 |
| Spotlighting | 0.619 (97/97) | 0.590 (627/629) | 0.077 (627/629) | 2 |
| Effect-binding runtime guard | 0.340 (97/97) | 0.329 (629/629) | 0.005 (629/629) | 0 |

All-key uncertainty bounds are recorded in the JSON report.

Every method uses 65,536 tokens on the 714 base cases and the same larger capacity as the proposed method on each of the 12 repaired cases. The two 122,880-token cases use Q8_0 KV cache for every method.

This is a per-case capacity-matched AgentDojo v1.1.2 comparison under one Qwen3-32B checkpoint. It is not globally uniform in context capacity across cases, but capacity and KV-cache type are identical across methods within every case. Reported point rates use only rows with complete native AgentDojo metrics; all-key lower and upper bounds retain capacity-exhausted or otherwise non-evaluable trajectories.
