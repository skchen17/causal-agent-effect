# E78 Context-Fairness Preparation

## Uniform 65,536-token complete-case sensitivity

| Method | BU | UA | ASR |
|---|---:|---:|---:|
| No defense | 0.656 | 0.552 | 0.086 |
| MELON-style | 0.635 | 0.544 | 0.089 |
| Prompt Sandwiching | 0.625 | 0.584 | 0.013 |
| PromptArmor-style | 0.281 | 0.223 | 0.002 |
| Spotlighting | 0.615 | 0.594 | 0.078 |
| Effect-binding runtime guard | 0.333 | 0.332 | 0.003 |

All six methods are compared on the same 714 case keys whose original Qwen3-32B trajectories completed at 65,536 tokens. The 12 excluded keys were selected because the proposed method exceeded that capacity, so this is a disclosed complete-case sensitivity analysis, not an unbiased replacement for a capacity-matched 726-case comparison.

## Capacity-matched repair plan

- Reference cases: 12
- Comparison methods: 5
- Required targeted runs: 60
- Status: ready; no targeted comparison run is counted before all acceptance gates pass.

This protocol matches each comparison method to the larger context capacity used by the proposed method for the same repaired case. Capacities may differ across cases, but never across methods within a case. It is not a globally uniform-context rerun.
