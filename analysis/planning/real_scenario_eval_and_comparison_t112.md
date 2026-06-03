# T112 Real-Scenario Evaluation and Comparison Plan

> Date: 2026-05-31  
> Decision: pause paper rewriting. Current local results look too constructed to support a main-conference method claim. The next gate is real-scenario evaluation, aligned with AgentDojo and AuthGraph-style metrics.

## 1. Why T111 Is Not Enough

T111 is useful as a mechanism stress test, but it is still constructed by us:

- the six drift families are hand-designed same-resource cases;
- the agent behavior is not generated inside a public adversarial benchmark;
- the evaluation does not report AgentDojo-style benign utility, utility under attack, or targeted attack success rate;
- there is no clean comparison to AuthGraph's dual-graph authorization/provenance setting;
- results can still be attacked as "the method solves the cases it was designed to solve."

Therefore T102-T111 should be treated as local prototype and mechanism evidence only. They should not be used as the basis for a paper rewrite until the method is evaluated on an external task/attack environment.

## 2. External Comparison Targets

### AgentDojo

AgentDojo is the primary real-scenario benchmark target because it evaluates LLM agents in dynamic, stateful tool environments with untrusted tool-returned data. Its paper reports 97 realistic user tasks and 629 security test cases across Workspace, Slack, Travel, and Banking. Its key metrics are:

- **Benign Utility / UR**: task success without attack.
- **Utility Under Attack / A.UR**: task success under attack without adversarial side effects.
- **Targeted ASR**: attacker goal success rate.

Our evaluation must use these metrics directly, then add our own action-level metrics only as secondary analysis.

### AuthGraph

AuthGraph is the most direct method comparison. It proposes:

- injected reasoning graph from actual execution trajectory;
- authorization graph from a clean user-intent context;
- graph alignment checker with tool-level and parameter-source checks;
- AgentDojo / AgentDyn reporting in ASR, UR, and A.UR.

Important boundary: if we do not run the authors' code, we must call our comparator **AuthGraph-style proxy**, not AuthGraph. Direct numeric comparison is valid only under the same benchmark version, suites, attacks, and model family.

## 3. Evaluation Questions

The real-scenario gate should answer these questions before any paper rewrite:

1. Does the future-constrained / trace-locked framework reduce **AgentDojo ASR** on external benchmark tasks?
2. Does it preserve enough **UR** and **A.UR**, or does it collapse into over-blocking?
3. Does it improve over simple AgentDojo baselines such as no defense, repeat-user-prompt, spotlighting, and tool filtering?
4. Does it improve over an AuthGraph-style clean-plan/provenance alignment proxy on the same logs?
5. Are remaining failures due to compiler over-permission, insufficient provenance, unsafe substitution, missing staging support, or model task failure?

## 4. Required Artifacts

New executable entry:

- `src/auth/agentdojo_real_scenario_eval_t112.py`

Current generated inventory artifacts:

- `analysis/results/agentdojo_real_scenario_eval_t112_v1.json`
- `analysis/results/agentdojo_real_scenario_eval_t112_v1.md`
- `analysis/results/agentdojo_real_scenario_eval_t112_pilot_deepseek_direct.json`
- `analysis/results/agentdojo_real_scenario_eval_t112_pilot_deepseek_direct.md`
- `analysis/results/agentdojo_real_scenario_eval_t112_pilot_deepseek_direct_builtin_defenses.json`
- `analysis/results/agentdojo_real_scenario_eval_t112_pilot_deepseek_direct_builtin_defenses.md`
- `analysis/results/agentdojo_real_scenario_eval_t112_pilot_summary.md`

The inventory confirms AgentDojo v1.2.2 is installed and exposes:

| Suite | User tasks | Injection tasks | Tools |
| --- | ---: | ---: | ---: |
| workspace | 40 | 14 | 24 |
| slack | 21 | 5 | 11 |
| travel | 20 | 7 | 28 |
| banking | 16 | 9 | 11 |

This matches the external evaluation shape we need: 97 user tasks, 35 current-version injection task definitions in the installed package, and 74 total tools across suites.

Completed DeepSeek pilot:

- Model: `deepseek-v4-flash`.
- Attack: `direct`; `tool_knowledge` was not used because AgentDojo's attack implementation requires recognized model-family names.
- Scope: 4 suites × 2 user tasks × 2 injection tasks.
- Corrected metric semantics: AgentDojo injection-task `security` is attack success. Earlier local notes inverted this value.
- No-defense ASR: workspace 0/4, slack 0/4, travel 0/4, banking 2/4.
- Built-in prompt-defense ASR: repeat-user-prompt has workspace/slack/travel 0/4 and banking 2/4; spotlighting has workspace 0/4, slack 1/4, travel 0/4, banking 2/4.
- Travel injection-task utility is low, so travel ASR should be interpreted cautiously.

## 5. Execution Protocol

### Phase 0: Integration Smoke Test

Goal: verify AgentDojo can run from this repo and produce logs.

Command template:

```bash
conda run -n causal-safety python src/auth/agentdojo_real_scenario_eval_t112.py \
  --max-user-tasks 2 \
  --max-injection-tasks 2
```

This is inventory-only and does not call a model.

### Phase 1: Small Real-Scenario Pilot

Goal: run a small but real AgentDojo subset using the same model and attack across all suites.

Suggested coverage:

- suites: workspace, slack, travel, banking;
- 5 user tasks per suite;
- 3 injection tasks per suite;
- attack: `tool_knowledge`;
- defenses: `none`, `repeat_user_prompt`, `spotlighting_with_delimiting`;
- optional: `tool_filter` if the model/API supports OpenAI-style function calling robustly.

Command template:

```bash
export DEEPSEEK_API_KEY=...  # do not write this into files
conda run -n causal-safety python src/auth/agentdojo_real_scenario_eval_t112.py \
  --run-agentdojo \
  --max-user-tasks 5 \
  --max-injection-tasks 3 \
  --attack tool_knowledge \
  --defense none \
  --defense repeat_user_prompt \
  --defense spotlighting_with_delimiting \
  --model deepseek-v4-flash \
  --base-url https://api.deepseek.com \
  --api-key-env DEEPSEEK_API_KEY \
  --logdir runs/agentdojo_t112_pilot
```

If DeepSeek's OpenAI-compatible endpoint fails on tool-call formatting, switch to an OpenAI/Anthropic model already supported by AgentDojo, or start a local OpenAI-compatible server for the GGUF model. Do not compare results across different models as if they were equivalent.

### Phase 2: Method Integration

Goal: evaluate the actual method, not just baseline AgentDojo defenses.

Implementation requirements:

1. Add a guarded `ToolsExecutor` wrapper around AgentDojo tool execution.
2. Build an authorization envelope from the clean user task using either:
   - AgentDojo ground-truth tool sequence as an oracle upper bound, clearly labeled, or
   - an independent compiler from user prompt + tool catalog, closer to deployable use.
3. Add an AuthGraph-style proxy:
   - clean expected tool sequence and parameter-source policy;
   - actual trajectory tool calls and tool observations;
   - tool mismatch and parameter-source mismatch detection.
4. Add our method:
   - future constraint `F_c`;
   - shadow/staged execution where possible;
   - trace-locked real replay or pre-tool-call gate inside AgentDojo;
   - action-level ALLOW/DENY/ABSTAIN logging.
5. Report both AgentDojo metrics and project metrics:
   - UR, A.UR, ASR;
   - U-Commit, FDeny, Abstain/Coverage if implemented;
   - failure type taxonomy.

### Phase 3: Full Real-Scenario Gate

Minimum main-paper gate:

- all four AgentDojo suites;
- at least one strong attack (`tool_knowledge` or `important_instructions`);
- at least one model with stable tool calling;
- at least no-defense, AgentDojo built-in defenses, AuthGraph-style proxy, and our method;
- exact task/injection counts, confidence intervals, and per-suite breakdown.

No paper rewrite should be treated as main-conference ready before this gate is complete.

## 6. Decision Rules

Proceed to paper writing only if:

- our method lowers ASR compared with no defense and at least one simple built-in defense;
- UR/A.UR does not collapse into deny-all behavior;
- failures are interpretable and tied to method components;
- comparison to AuthGraph-style proxy shows a meaningful difference, not just rephrasing the same plan/provenance check.

Downgrade or redesign if:

- the method cannot be inserted before AgentDojo side effects;
- UR or A.UR collapses below the strongest baseline;
- AuthGraph-style proxy matches or beats the method with simpler assumptions;
- DeepSeek/local models have too low benign utility to make security conclusions meaningful.

## 7. Completion Update 2026-06-01

Current planned AgentDojo experiments are complete for the scoped 5x3 gate:

- T112 direct no-defense and built-in prompt-defense baselines;
- T112 `important_instructions_no_model_name` no-defense baseline;
- T113 replay-commit method for both attacks;
- T114 AuthGraph-style log-based proxy for direct and stronger-attack logs;
- unified count/CI summary in `analysis/results/agentdojo_experiment_summary_2026-06-01.md`.

Main aggregate results:

- direct no-defense ASR=9/60, A.UR=50/60;
- direct repeat-user-prompt ASR=8/60, A.UR=51/60;
- direct spotlighting ASR=9/60, A.UR=52/60;
- stronger-attack no-defense ASR=8/60, A.UR=43/60;
- AuthGraph-style proxy ASR is 0/60 or 1/60 but A.UR collapses to 8/60-20/60;
- shadow replay-commit has ASR=0/60 and A.UR=48/60 on both attacks.

The gate now supports a real-benchmark mechanism signal for future-constrained replay, but still not a deployable defense claim because the method uses clean-shadow oracle trajectories and has replay fidelity errors in Slack/travel.

Until full benchmark or non-oracle follow-up is complete, the safe claim is:

> On scoped AgentDojo 5x3 subsets, clean-shadow replay provides a real-benchmark mechanism signal: it reduces measured ASR to 0/60 on direct and stronger instruction attacks while preserving A.UR=48/60. This is not yet a deployable defense because the replay trajectory is clean-shadow oracle derived and replay fidelity failures remain.

Do not claim:

- main-conference method effectiveness;
- superiority over the full AgentDojo benchmark;
- superiority over the AuthGraph authors' implementation;
- deployed safety;
- external validity beyond the completed AgentDojo subset.
