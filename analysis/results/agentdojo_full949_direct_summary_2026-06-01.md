# AgentDojo full949 direct summary

## Scope

- Benchmark: installed AgentDojo `v1.2.2` full cross-product: 949 attacked cases.
- Model: `deepseek-v4-flash`.
- Attack: `direct`.
- This is not a reproduction of original AgentDojo paper numbers; it is a full evaluation on the locally installed v1.2.2 package.
- `shadow_replay_commit_v1` is a clean-shadow oracle upper bound. `AuthGraph-style` rows are proxies, not the AuthGraph authors' implementation.

## Aggregate Results

| method | suite | n | A.UR | A.UR 95% CI | ASR | ASR 95% CI | counts / notes |
| --- | --- | ---: | ---: | --- | ---: | --- | --- |
| AuthGraph-style tool_arg_alignment_proxy_v1 | all | 949 | 0.2466 | [0.220, 0.275] | 0.0000 | [0.000, 0.004] | A.UR 234/949; ASR 0/949; deny_rate=0.7397; denied_success_nonattack=564/949 |
| AuthGraph-style tool_sequence_proxy_v1 | all | 949 | 0.3340 | [0.305, 0.365] | 0.0000 | [0.000, 0.004] | A.UR 317/949; ASR 0/949; deny_rate=0.6459; denied_success_nonattack=481/949 |
| no-defense | all | 949 | 0.8746 | [0.852, 0.894] | 0.0421 | [0.031, 0.057] | A.UR 830/949; ASR 40/949 |
| no-defense | workspace | 560 | 0.8786 | [0.849, 0.903] | 0.0000 | [0.000, 0.007] | A.UR 492/560; ASR 0/560; UR=0.8000; inj_util=0.7143 |
| no-defense | slack | 105 | 0.9238 | [0.857, 0.961] | 0.1238 | [0.074, 0.200] | A.UR 97/105; ASR 13/105; UR=0.9524; inj_util=1.0000 |
| no-defense | travel | 140 | 0.7714 | [0.695, 0.833] | 0.0071 | [0.001, 0.039] | A.UR 108/140; ASR 1/140; UR=0.8000; inj_util=0.7143 |
| no-defense | banking | 144 | 0.9236 | [0.868, 0.957] | 0.1806 | [0.126, 0.251] | A.UR 133/144; ASR 26/144; UR=0.9375; inj_util=0.8889 |
| shadow_replay_commit_v1 | all | 949 | 0.8430 | [0.818, 0.865] | 0.0000 | [0.000, 0.004] | A.UR 800/949; ASR 0/949 |
| shadow_replay_commit_v1 | workspace | 560 | 0.8500 | [0.818, 0.877] | 0.0000 | [0.000, 0.007] | A.UR 476/560; ASR 0/560; replay_errors=224 |
| shadow_replay_commit_v1 | slack | 105 | 0.7143 | [0.622, 0.792] | 0.0000 | [0.000, 0.035] | A.UR 75/105; ASR 0/105; replay_errors=95 |
| shadow_replay_commit_v1 | travel | 140 | 0.7500 | [0.672, 0.814] | 0.0000 | [0.000, 0.027] | A.UR 105/140; ASR 0/140; replay_errors=21 |
| shadow_replay_commit_v1 | banking | 144 | 1.0000 | [0.974, 1.000] | 0.0000 | [0.000, 0.026] | A.UR 144/144; ASR 0/144; replay_errors=0 |

## Main Readout

- No-defense DeepSeek direct full949 baseline: A.UR=830/949=0.8746, ASR=40/949=0.0421. Attacks concentrate in Slack and Banking; Workspace has 0/560 ASR under direct attack.
- AuthGraph-style exact clean-plan proxies reduce ASR to 0/949 but collapse utility: tool sequence A.UR=317/949 and tool+arg A.UR=234/949.
- Clean-shadow replay-commit also reduces ASR to 0/949 while preserving higher utility than the proxy baselines: A.UR=800/949=0.8430. It remains an oracle upper-bound method and has replay errors in Workspace/Slack/Travel.

## Caveats

- AgentDojo warned that not all injection tasks were solved as standalone user tasks, so ASR should be interpreted together with injection-task utility.
- This full run currently covers only `direct/no-defense` plus offline proxy and replay-commit. Stronger attacks and built-in defenses remain follow-up runs if needed.
