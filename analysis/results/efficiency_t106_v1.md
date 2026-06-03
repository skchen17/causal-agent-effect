# T106 Efficiency Report

## Local Stage Timings

| stage | n | total_ms | mean_ms | median_ms | p95_ms | max_ms |
| --- | --- | --- | --- | --- | --- | --- |
| T102_compile_validate | 600 | 52.67 | 0.0878 | 0.0836 | 0.1058 | 0.2065 |
| T103_shadow_plan_replay | 600 | 9.83 | 0.0164 | 0.0013 | 0.0688 | 0.1211 |
| T105_divergence_faithful | 200 | 13.68 | 0.0684 | 0.0606 | 0.1041 | 0.1274 |
| T105_divergence_unsafe | 200 | 30.07 | 0.1504 | 0.1357 | 0.1956 | 0.2121 |
| T104_build_precommit_cases | 1000 | 76.00 | 0.0760 | 0.0760 | 0.0760 | 0.0760 |

## Artifact Sizes

| path | bytes |
| --- | --- |
| data/future_constraint_tasks_t102_v1.jsonl | 295174 |
| data/future_constraint_intents_t102_v1.jsonl | 1386541 |
| data/future_constraint_compiler_outputs_t102_v1.jsonl | 1882820 |
| data/future_shadow_replay_traces_t103_v1.jsonl | 645695 |
| data/precommit_blocking_traces_t104_v1.jsonl | 753220 |
| data/shadow_real_divergence_t105_v1.jsonl | 362200 |
| analysis/results/future_constraint_compiler_eval_t102_v1.json | 582854 |
| analysis/results/future_shadow_replay_t103_v1.json | 2191 |
| analysis/results/precommit_blocking_t104_v1.json | 3470 |
| analysis/results/shadow_real_divergence_t105_v1.json | 1780 |

## Claim Boundary

These timings measure the local deterministic Python prototype only. They exclude LLM generation, real provider sandbox latency, HTTP browser automation, human review, and deployed-runtime logging overhead.
