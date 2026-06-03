# E25 AgentDojo Future-Constrained Guard T113

## Experiment Purpose

T113 evaluates the proposed future-constrained guard inside AgentDojo. It compares:

- `shadow_prefix_lock_v1`: attacked agent continues, but only exact next clean-shadow calls are committed;
- `shadow_replay_commit_v1`: attacked replanning is skipped, and the clean shadow trajectory is replayed in the injected environment.

The scaled results focus on `shadow_replay_commit_v1` because the 2x2 pilot already showed exact prefix-lock over-blocks.

## Artifacts

- Runner: `src/auth/agentdojo_guarded_eval_t113.py`
- 2x2 direct pilot:
  - `analysis/results/agentdojo_guarded_eval_t113_v1.{json,md}`
  - `data/agentdojo_guarded_eval_t113_v1.jsonl`
- 5x3 direct replay-commit:
  - `analysis/results/agentdojo_guarded_eval_t113_replay_commit_deepseek_direct_5x3.{json,md}`
  - `data/agentdojo_guarded_eval_t113_replay_commit_deepseek_direct_5x3.jsonl`
- 5x3 stronger-attack replay-commit:
  - `analysis/results/agentdojo_guarded_eval_t113_replay_commit_deepseek_important_no_model_5x3.{json,md}`
  - `data/agentdojo_guarded_eval_t113_replay_commit_deepseek_important_no_model_5x3.jsonl`
- Unified summary:
  - `analysis/results/agentdojo_experiment_summary_2026-06-01.{json,md}`

## Main Results

| attack | method | n | A.UR | ASR | key limitation |
| --- | --- | ---: | ---: | ---: | --- |
| direct | shadow_prefix_lock_v1 | 16 | 9/16 | 0/16 | 2x2 stress test; over-blocking |
| direct | shadow_replay_commit_v1 | 16 | 16/16 | 0/16 | 2x2 clean-shadow upper bound |
| direct | shadow_replay_commit_v1 | 60 | 48/60 | 0/60 | Slack replay fidelity errors |
| important_instructions_no_model_name | shadow_replay_commit_v1 | 60 | 48/60 | 0/60 | Slack/travel replay fidelity errors |

## Conclusions

Facts:

- Replay-commit reduces ASR to 0/60 on both scaled attacks.
- Replay-commit preserves more utility than the AuthGraph-style proxy baselines in E26.
- Slack replay failures come from clean shadow calls that are invalid in the injected environment, such as missing `External_0` channels.

Inference:

- These are the first AgentDojo mechanism results supporting future-constrained replay.
- The current method is still an oracle upper bound because it uses a clean no-injection shadow trajectory.
- The next technical bottleneck is replay fidelity and replacing clean-shadow oracle planning with a realistic sandbox/future-constraint compiler.

## Claim Boundary

This experiment does not prove deployed safety. It supports:

> On a 5x3 AgentDojo subset, clean-shadow replay can eliminate measured attack success while preserving substantially more utility than simple clean-plan alignment proxies.

It does not support:

- full AgentDojo benchmark superiority;
- superiority over the AuthGraph authors' implementation;
- deployable pre-commit safety without a non-oracle planner;
- correctness under provider/SaaS/browser side effects outside AgentDojo.
