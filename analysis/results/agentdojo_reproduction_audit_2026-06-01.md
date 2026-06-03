# AgentDojo Reproduction Audit

Date: 2026-06-01

Update: after this audit, the project adopted the installed AgentDojo `v1.2.2` 949-case full cross-product as the local full-evaluation target and completed a `deepseek-v4-flash` `direct/no-defense` full run. See `analysis/results/agentdojo_full949_direct_summary_2026-06-01.md`. This still is not a reproduction of the original AgentDojo paper's 629-case setting.

## Verdict

The local AgentDojo experiments are **API- and metric-consistent scoped evaluations** on the installed AgentDojo package, but they are **not a reproduction of the original AgentDojo paper numbers**.

Use the results as:

> DeepSeek + AgentDojo v1.2.2 scoped 5x3 real-scenario gate results.

Do not use them as:

> Reproduced AgentDojo paper results.

## Source Comparison

Original AgentDojo paper:

- 4 suites: Workspace, Slack, Travel, Banking.
- Table 1 / dataset-card style reporting gives 70 tools; the paper body also contains a 74-tools statement, so tool count should be treated as a paper/version nuance rather than the main reproduction criterion.
- 97 user tasks.
- 27 injection targets.
- 629 security test cases.
- Main full-suite evaluation uses 97 user tasks and 629 security test cases.
- Main reported defense table focuses on GPT-4o and the Important message attack.

Local installed package:

- package: `agentdojo==0.1.35`
- benchmark version: `v1.2.2`
- 4 suites: Workspace, Slack, Travel, Banking.
- 74 tools.
- 97 user tasks.
- 35 injection tasks.
- Full cross-product in this installed package: 949 security cases.

Local suite inventory:

| suite | local user tasks | local injection tasks | local tools | local cross-product |
| --- | ---: | ---: | ---: | ---: |
| workspace | 40 | 14 | 24 | 560 |
| slack | 21 | 5 | 11 | 105 |
| travel | 20 | 7 | 28 | 140 |
| banking | 16 | 9 | 11 | 144 |
| total | 97 | 35 | 74 | 949 |

The largest dataset mismatch is Workspace: the paper table has 6 injection targets, while the installed v1.2.2 package exposes 14 Workspace injection tasks. The decisive mismatch is benchmark coverage and setup: 27 paper injection targets / 629 security cases versus 35 installed injection tasks / 949 local full cross-product, plus different model, attacks, defenses, and task selection.

## Local Experiment Scope

The main local scaled runs at the time of this audit used:

- model: `deepseek-v4-flash`
- API: DeepSeek OpenAI-compatible endpoint
- suites: all four AgentDojo suites
- subset: 5 user tasks x 3 injection tasks per suite
- attacked cases: 60 per attack/method
- selected user IDs by lexicographic sort:
  - `user_task_0`, `user_task_1`, `user_task_10`, `user_task_11`, `user_task_12`
- selected injection IDs:
  - workspace: `injection_task_0`, `injection_task_1`, `injection_task_10`
  - slack: `injection_task_1`, `injection_task_2`, `injection_task_3`
  - travel: `injection_task_0`, `injection_task_1`, `injection_task_2`
  - banking: `injection_task_0`, `injection_task_1`, `injection_task_2`

This is not a random sample, not the full cross-product, and not the original 629-case suite.

Subsequent local full run:

- `analysis/results/agentdojo_real_scenario_eval_t112_deepseek_direct_full949.{json,md}`
- `analysis/results/agentdojo_full949_direct_summary_2026-06-01.{json,md}`
- coverage: installed AgentDojo `v1.2.2` full cross-product, 949 attacked cases;
- model: `deepseek-v4-flash`;
- attack/defense: `direct/no-defense`;
- still not numerically comparable to the original paper because the paper setting is 629 security cases with different model/attack/defense protocol.

## Metric Correctness

The corrected local metric mapping is consistent with AgentDojo:

- `benign_utility` maps to UR.
- `utility_under_attack` maps to A.UR.
- `security_results` / injection-task `security` maps to attack success, so higher is worse and equals ASR.

An earlier local summary inverted `security_results`; that has been corrected in the artifacts and planning documents.

## Methodological Differences From The Paper

| Dimension | Original AgentDojo paper | Local experiments |
| --- | --- | --- |
| Benchmark size | full 97 user tasks / 629 security cases | scoped 5x3 subset / 60 attacked cases per setting |
| Dataset version | paper table reports 70 tools and 27 injection targets; paper body also says 74 tools | installed v1.2.2: 74 tools, 35 injection tasks |
| Main model | GPT-4o for detailed attack/defense ablations; multiple closed/open models for baseline | DeepSeek `deepseek-v4-flash` via custom wrapper |
| Main attack | Important message and variants; Max/adaptive analysis | `direct`; plus `important_instructions_no_model_name` using pipeline label `local` |
| Defenses | no defense, delimiters, PI detector, repeat prompt, tool filter | no defense, repeat-user-prompt, spotlighting-with-delimiting; plus our proxy/method |
| Full-suite CI | paper reports full-suite confidence intervals | local summary reports Wilson CI over scoped subset |
| Goal | benchmark paper evaluation | method gate for Future-Constrained CEG-Auth |

## Reproduction Correctness Assessment

Correct:

- The local runner calls AgentDojo's official suite loader and benchmark checks.
- The local runner computes UR, A.UR, and ASR with corrected AgentDojo semantics.
- The local logs are generated by AgentDojo environments and tool execution, not synthetic replay data.
- The direct and `important_instructions_no_model_name` results are valid scoped AgentDojo measurements for DeepSeek.

Not correct as original-paper reproduction:

- It does not use the original paper's exact benchmark cardinality.
- It does not run all original 629 security cases.
- It does not use GPT-4o or the paper's full model/defense matrix.
- It does not reproduce the paper's Important message full attack setup exactly.
- It uses a lexicographic task subset, which includes `user_task_10/11/12` before `user_task_2`.
- T114 is an AuthGraph-style proxy, not AuthGraph.
- T113 replay-commit uses clean-shadow oracle trajectories, not an AgentDojo paper baseline.

## Safe Wording

Use:

> We evaluate on a scoped AgentDojo v1.2.2 subset using the official AgentDojo task suites and metrics. The installed package exposes 97 user tasks and 35 injection tasks; our main gate samples 5 user tasks and 3 injection tasks per suite.

Avoid:

> We reproduce the AgentDojo benchmark results.

Use:

> Our results are comparable in metric semantics, but not numerically comparable to the AgentDojo paper because model, attack, defense, dataset version, and benchmark coverage differ.

## Next Steps For Paper-Grade Reproduction

1. Decide whether to target the paper's 629-case benchmark or the installed v1.2.2 949-case benchmark.
2. Replace lexicographic subset selection with numeric sorting or a fixed stratified seed.
3. Run all user-task x injection-task pairs for at least one attack.
4. Add the paper's GPT-4o-compatible setting if cost and API access permit.
5. Add the paper's defense set where supported: no defense, delimiting/spotlighting, PI detector, repeat prompt, tool filter.
6. Report full-suite exact/Wilson CIs and per-suite breakdowns.
7. Keep our T113/T114 methods separate from AgentDojo paper reproduction tables.

## Source Anchors

- AgentDojo paper PDF: https://proceedings.neurips.cc/paper_files/paper/2024/file/97091a5177d8dc64b1da8bf3e1f6fb54-Paper-Datasets_and_Benchmarks_Track.pdf
- AgentDojo arXiv: https://arxiv.org/abs/2406.13352
- AgentDojo benchmark API docs: https://agentdojo.spylab.ai/api/benchmark/
- AgentDojo GitHub benchmark script: https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/scripts/benchmark.py
