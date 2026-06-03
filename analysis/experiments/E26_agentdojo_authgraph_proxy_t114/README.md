# E26 AgentDojo AuthGraph-Style Proxy T114

## Experiment Purpose

T114 provides a same-log clean-authorization/provenance alignment baseline inspired by AuthGraph. It is not the AuthGraph authors' implementation.

The proxy reads AgentDojo logs and compares:

- clean no-injection trajectory as an authorization graph;
- attacked trajectory as an execution/provenance graph.

Two proxy variants are reported:

- `tool_sequence_proxy_v1`: exact tool-name sequence match;
- `tool_arg_alignment_proxy_v1`: exact tool-name and argument signature match.

## Artifacts

- Runner: `src/auth/agentdojo_authgraph_proxy_t114.py`
- 2x2 direct pilot:
  - `analysis/results/agentdojo_authgraph_proxy_t114_pilot_deepseek_direct.{json,md}`
- 5x3 direct no-defense proxy:
  - `analysis/results/agentdojo_authgraph_proxy_t114_deepseek_direct_5x3.{json,md}`
- 5x3 direct built-in-defense logs proxy:
  - `analysis/results/agentdojo_authgraph_proxy_t114_deepseek_direct_5x3_builtin_defenses.{json,md}`
- 5x3 stronger-attack no-defense proxy:
  - `analysis/results/agentdojo_authgraph_proxy_t114_deepseek_important_no_model_5x3.{json,md}`
- Unified summary:
  - `analysis/results/agentdojo_experiment_summary_2026-06-01.{json,md}`

## Main Results

| attack/logs | proxy | n | A.UR | ASR | deny rate |
| --- | --- | ---: | ---: | ---: | ---: |
| direct no-defense | tool_arg_alignment | 60 | 10/60 | 0/60 | 50/60 |
| direct no-defense | tool_sequence | 60 | 20/60 | 1/60 | 40/60 |
| important no-defense | tool_arg_alignment | 60 | 8/60 | 0/60 | 52/60 |
| important no-defense | tool_sequence | 60 | 12/60 | 0/60 | 48/60 |

## Conclusions

Facts:

- Clean-plan/provenance alignment can reduce or eliminate ASR on the scaled subset.
- It does so by denying most attacked trajectories, causing A.UR collapse.
- This makes it a useful strong over-denial baseline rather than a sufficient method.

Inference:

- The project method must beat this baseline on A.UR, not merely ASR.
- T113 replay-commit currently does: A.UR 48/60 with ASR 0/60 on both scaled attacks.

## Claim Boundary

Do not call this result AuthGraph. It is an AuthGraph-style proxy over the same AgentDojo logs. Direct comparison to AuthGraph requires the authors' implementation, same benchmark version, same attacks, same model, and same metrics.
