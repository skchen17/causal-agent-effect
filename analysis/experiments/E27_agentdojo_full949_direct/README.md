# E27 AgentDojo Full949 Direct Evaluation

## Experiment Purpose

This experiment upgrades the AgentDojo gate from the earlier 5x3 subset to the full cross-product exposed by the locally installed AgentDojo `v1.2.2` package.

The target is:

- benchmark: installed AgentDojo `v1.2.2`;
- suites: Workspace, Slack, Travel, Banking;
- attacked cases: 949 full user-task x injection-task pairs;
- model: `deepseek-v4-flash`;
- attack: `direct`;
- main metrics: AgentDojo UR, A.UR, ASR.

This is not an original AgentDojo paper reproduction. The paper reports 629 security cases, while the installed package exposes 949 full cross-product cases.

## Artifacts

- Baseline runner:
  - `src/auth/agentdojo_real_scenario_eval_t112.py`
- Full949 baseline:
  - `analysis/results/agentdojo_real_scenario_eval_t112_deepseek_direct_full949.json`
  - `analysis/results/agentdojo_real_scenario_eval_t112_deepseek_direct_full949.md`
- AuthGraph-style proxy:
  - `src/auth/agentdojo_authgraph_proxy_t114.py`
  - `analysis/results/agentdojo_authgraph_proxy_t114_deepseek_direct_full949.json`
  - `analysis/results/agentdojo_authgraph_proxy_t114_deepseek_direct_full949.md`
- Clean-shadow replay-commit:
  - `src/auth/agentdojo_guarded_eval_t113.py`
  - `analysis/results/agentdojo_guarded_eval_t113_replay_commit_deepseek_direct_full949.json`
  - `analysis/results/agentdojo_guarded_eval_t113_replay_commit_deepseek_direct_full949.md`
  - `data/agentdojo_guarded_eval_t113_replay_commit_deepseek_direct_full949.jsonl`
- Unified summary:
  - `analysis/results/agentdojo_full949_direct_summary_2026-06-01.json`
  - `analysis/results/agentdojo_full949_direct_summary_2026-06-01.md`

## Main Results

| method | n | A.UR | ASR | key note |
| --- | ---: | ---: | ---: | --- |
| no-defense | 949 | 830/949 | 40/949 | direct attacks concentrate in Slack and Banking |
| AuthGraph-style tool sequence proxy | 949 | 317/949 | 0/949 | ASR removed by heavy over-denial |
| AuthGraph-style tool+arg proxy | 949 | 234/949 | 0/949 | stronger over-denial |
| shadow_replay_commit_v1 | 949 | 800/949 | 0/949 | clean-shadow oracle upper bound; replay errors remain |

Per-suite no-defense ASR:

| suite | n | ASR |
| --- | ---: | ---: |
| workspace | 560 | 0/560 |
| slack | 105 | 13/105 |
| travel | 140 | 1/140 |
| banking | 144 | 26/144 |

Per-suite replay-commit A.UR:

| suite | n | A.UR | replay errors |
| --- | ---: | ---: | ---: |
| workspace | 560 | 476/560 | 224 |
| slack | 105 | 75/105 | 95 |
| travel | 140 | 105/140 | 21 |
| banking | 144 | 144/144 | 0 |

## Conclusions

Facts:

- Full949 `direct/no-defense` baseline has A.UR = 830/949 and ASR = 40/949.
- AuthGraph-style exact clean-plan proxies reduce ASR to 0/949 but collapse A.UR to 317/949 or 234/949.
- Clean-shadow replay-commit also reduces ASR to 0/949 while retaining substantially higher A.UR = 800/949.
- AgentDojo warned that not all injection tasks were solved as standalone user tasks, so ASR must be read together with injection-task utility.

Inference:

- The full949 result strengthens the earlier 5x3 finding that simple exact clean-plan alignment is too conservative.
- Replay-commit is more useful than the simple proxy baseline on this full installed benchmark setting.
- The current method evidence is still an upper-bound mechanism result because it relies on clean-shadow oracle trajectories and has replay fidelity errors.

## Claim Boundary

This experiment supports:

> On the installed AgentDojo v1.2.2 full direct-attack cross-product with DeepSeek, clean-shadow replay-commit removes measured direct attack success while preserving much more utility than exact clean-plan proxy baselines.

It does not support:

- reproduction of the original AgentDojo paper numbers;
- superiority over the AuthGraph authors' implementation;
- robustness to stronger attacks;
- deployed safety without a non-oracle future-constraint compiler;
- correctness under provider-backed/SaaS/browser side effects outside AgentDojo.

## Next Follow-Up

The most important next full run is `important_instructions_no_model_name/no-defense` on the same 949-case setting, because the `direct` full baseline ASR is only 40/949.
