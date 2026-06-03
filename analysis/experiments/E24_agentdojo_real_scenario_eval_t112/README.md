# E24 AgentDojo Real-Scenario Evaluation Gate T112

## Experiment Purpose

T102-T111 are local prototype and mechanism experiments. T112 moves the project to an external AgentDojo benchmark gate before further paper claims.

This block evaluates DeepSeek `deepseek-v4-flash` on AgentDojo v1.2.2 with official UR, A.UR, and ASR semantics. It is baseline/integration evidence, not method evidence.

## Artifacts

- Runner: `src/auth/agentdojo_real_scenario_eval_t112.py`
- Inventory:
  - `analysis/results/agentdojo_real_scenario_eval_t112_v1.json`
  - `analysis/results/agentdojo_real_scenario_eval_t112_v1.md`
- 2x2 pilot:
  - `analysis/results/agentdojo_real_scenario_eval_t112_pilot_deepseek_direct.{json,md}`
  - `analysis/results/agentdojo_real_scenario_eval_t112_pilot_deepseek_direct_builtin_defenses.{json,md}`
  - `analysis/results/agentdojo_real_scenario_eval_t112_pilot_summary.md`
- 5x3 scaled direct:
  - `analysis/results/agentdojo_real_scenario_eval_t112_deepseek_direct_5x3.{json,md}`
  - `analysis/results/agentdojo_real_scenario_eval_t112_deepseek_direct_5x3_builtin_defenses.{json,md}`
- 5x3 stronger attack:
  - `analysis/results/agentdojo_real_scenario_eval_t112_deepseek_important_no_model_5x3.{json,md}`
- Unified summary:
  - `analysis/results/agentdojo_experiment_summary_2026-06-01.{json,md}`

## Inventory Result

AgentDojo v1.2.2 inventory from the installed package:

| suite | user tasks | injection tasks | tools |
| --- | ---: | ---: | ---: |
| workspace | 40 | 14 | 24 |
| slack | 21 | 5 | 11 |
| travel | 20 | 7 | 28 |
| banking | 16 | 9 | 11 |

## Scaled Baseline Results

Main scaled subset: 4 suites x 5 user tasks x 3 injection tasks = 60 attacked cases per method/attack.

Correct metric semantics: AgentDojo injection-task `security` is attack success; higher ASR is worse.

| attack | defense | A.UR | ASR |
| --- | --- | ---: | ---: |
| direct | none | 50/60 | 9/60 |
| direct | repeat_user_prompt | 51/60 | 8/60 |
| direct | spotlighting_with_delimiting | 52/60 | 9/60 |
| important_instructions_no_model_name | none | 43/60 | 8/60 |

The `important_instructions_no_model_name` run uses AgentDojo pipeline label `local` only so the attack generator can infer a valid local-model name. The executed model remains `deepseek-v4-flash`.

## Conclusions

Facts:

- The DeepSeek + AgentDojo harness is now stable for direct and `important_instructions_no_model_name` attacks.
- Direct no-defense failures are concentrated in Slack and Banking in the 5x3 subset.
- Built-in prompt defenses do not remove direct ASR; repeat-user-prompt is 8/60 and spotlighting is 9/60.
- Stronger instruction attack has lower A.UR and nonzero ASR across Workspace/Slack/Banking.

Claim boundary:

- This is still a subset, not full AgentDojo.
- It supports real-benchmark baseline viability and failure presence.
- It does not by itself prove Future-Constrained CEG-Auth / AuthTrace-Guard effectiveness.
