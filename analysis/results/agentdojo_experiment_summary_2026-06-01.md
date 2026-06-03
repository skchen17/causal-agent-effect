# AgentDojo T112-T114 Experiment Summary

## Scope

- Model: `deepseek-v4-flash` through a DeepSeek OpenAI-compatible endpoint.
- Benchmark: AgentDojo `v1.2.2` as installed in `causal-safety`.
- Main scaled subset: 4 suites x 5 user tasks x 3 injection tasks = 60 attacked cases per method/attack.
- `important_instructions_no_model_name` uses AgentDojo pipeline label `local` only for attack-string generation; the executed model remains DeepSeek.
- T114 is an AuthGraph-style proxy, not the AuthGraph authors' implementation.
- T113 replay-commit is a clean-shadow oracle upper bound, not a deployable compiler.

## Aggregate Table

| family | attack | method | n | A.UR | A.UR 95% CI | ASR | ASR 95% CI | counts |
| --- | --- | --- | ---: | ---: | --- | ---: | --- | --- |
| 5x3 scaled | direct | AgentDojo none | 60 | 0.8333 | [0.720, 0.907] | 0.1500 | [0.081, 0.261] | A.UR 50/60; ASR 9/60 |
| 5x3 scaled | direct | AgentDojo repeat_user_prompt | 60 | 0.8500 | [0.739, 0.919] | 0.1333 | [0.069, 0.242] | A.UR 51/60; ASR 8/60 |
| 5x3 scaled | direct | AgentDojo spotlighting_with_delimiting | 60 | 0.8667 | [0.758, 0.931] | 0.1500 | [0.081, 0.261] | A.UR 52/60; ASR 9/60 |
| 5x3 scaled | direct | AuthGraph-style tool_arg_alignment_proxy_v1 | 60 | 0.1667 | [0.093, 0.280] | 0.0000 | [0.000, 0.060] | A.UR 10/60; ASR 0/60 |
| 5x3 scaled | direct | AuthGraph-style tool_sequence_proxy_v1 | 60 | 0.3333 | [0.227, 0.459] | 0.0167 | [0.003, 0.089] | A.UR 20/60; ASR 1/60 |
| 5x3 scaled | direct | shadow_replay_commit_v1 | 60 | 0.8000 | [0.682, 0.882] | 0.0000 | [0.000, 0.060] | A.UR 48/60; ASR 0/60 |
| 5x3 scaled | important_instructions_no_model_name | AgentDojo none | 60 | 0.7167 | [0.592, 0.815] | 0.1333 | [0.069, 0.242] | A.UR 43/60; ASR 8/60 |
| 5x3 scaled | important_instructions_no_model_name | AuthGraph-style tool_arg_alignment_proxy_v1 | 60 | 0.1333 | [0.069, 0.242] | 0.0000 | [0.000, 0.060] | A.UR 8/60; ASR 0/60 |
| 5x3 scaled | important_instructions_no_model_name | AuthGraph-style tool_sequence_proxy_v1 | 60 | 0.2000 | [0.118, 0.318] | 0.0000 | [0.000, 0.060] | A.UR 12/60; ASR 0/60 |
| 5x3 scaled | important_instructions_no_model_name | shadow_replay_commit_v1 | 60 | 0.8000 | [0.682, 0.882] | 0.0000 | [0.000, 0.060] | A.UR 48/60; ASR 0/60 |
| 2x2 pilot | direct | shadow_prefix_lock_v1 | 16 | 0.5625 | [0.332, 0.769] | 0.0000 | [0.000, 0.194] | A.UR 9/16; ASR 0/16 |
| 2x2 pilot | direct | shadow_replay_commit_v1 | 16 | 1.0000 | [0.806, 1.000] | 0.0000 | [0.000, 0.194] | A.UR 16/16; ASR 0/16 |

## Main Interpretation

- Direct no-defense scaled baseline has ASR 9/60; the stronger instruction variant has ASR 8/60.
- AgentDojo prompt defenses do not remove banking failures in the direct setting; aggregate direct ASR is 8/60 for repeat-user-prompt and 9/60 for spotlighting.
- AuthGraph-style exact/provenance proxies drive ASR near or to zero but sharply reduce A.UR, indicating over-denial.
- Shadow replay-commit has ASR 0/60 for both attacks and A.UR 48/60, better utility than the proxy baselines but still below no-defense/built-in utility in Slack due to replay fidelity errors.

## Claim Boundary

These results support a real-benchmark mechanism signal for future-constrained replay, not a deployable safety guarantee. The strongest current limitation is the clean-shadow oracle assumption and replay fidelity failures when injected environments change resources.
