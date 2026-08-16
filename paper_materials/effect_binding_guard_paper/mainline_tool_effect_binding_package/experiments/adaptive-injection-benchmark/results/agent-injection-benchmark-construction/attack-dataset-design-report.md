# E88 AgentDojo Attack Dataset Design

## Status

`passed` for dataset construction and public-template materialization. Victim-model execution is queued behind E78/E79 under a stage gate; no E88 ASR is available yet.

## Dataset

| Tier | Scale | Role |
|---|---:|---|
| Fixed public attacks | 2,516 | 629 AgentDojo task pairs under four registry attacks |
| Benign controls | 97 | Official user-task utility |
| Bounded adaptive index | 480 | 40 frozen attack keys crossed with E82 T1--T12 |

The fixed families are `ignore_previous`, `injecagent`, `important_instructions`, and `tool_knowledge`. Counts by suite before crossing with attack families are banking 144, Slack 105, travel 140, and workspace 240.

## Verification

- Dataset validation: passed with zero errors.
- In-memory public-template materialization: 2,516/2,516, zero errors.
- Raw injection text persisted in E88 manifests: no.
- Security scoring: official environment validators or explicit post-state predicates; no LLM judge.
- Real external side effects: none.
- Adaptive split: grouped by suite and injection-task ID; five attack-goal groups are development-only and 22 are locked-test-only.

## Interpretation

E88 removes the single-template limitation of E78 while retaining AgentDojo comparability. It does not yet provide attack-success results. The fixed suite must be executed under the same checkpoint and method configurations, and E82 variants must be generated and evaluated before adaptive-robustness claims are available.

The artifact does not attempt to evade hosted-model safety systems. It uses local public benchmark implementations by default and treats provider refusals as recorded outcomes.

## Execution Queue

The transient user service `e88-agentdojo-staged.service` waits for the existing E79 GPU queue. It first runs the 80-case smoke with no guard and the E77 runtime. Full execution is authorized only if logs are complete and error-free and at least two attack families achieve nonzero official attack success against no guard. A failed gate stops the queue without launching the full experiment.
