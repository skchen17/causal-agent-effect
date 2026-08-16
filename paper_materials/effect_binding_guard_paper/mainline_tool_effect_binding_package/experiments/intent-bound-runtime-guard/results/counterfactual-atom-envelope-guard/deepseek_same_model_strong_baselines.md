# DeepSeek Same-Model Strong Baselines

| Method | Benign utility | Official ASR | Attack utility | Scope-aligned attacks | p vs no guard |
|---|---:|---:|---:|---:|---:|
| `no_guard` | 0.784 | 6/629 | 480/629 | 6/609 | n/a |
| `c1f` | 0.773 | 0/629 | 453/629 | 0/609 | 0.015625 |
| `repeat_user_prompt` | 0.794 | 5/629 | 494/629 | 5/609 | 0.5 |
| `spotlighting` | 0.794 | 0/629 | 477/629 | 0/609 | 0.015625 |

This is a same-model comparison with AgentDojo no defense and two built-in prompting defenses. It can establish relative performance among these rows, but not state of the art across checkpoint detectors, causal-attribution systems, adaptive attacks, other models, or deployed environments.
