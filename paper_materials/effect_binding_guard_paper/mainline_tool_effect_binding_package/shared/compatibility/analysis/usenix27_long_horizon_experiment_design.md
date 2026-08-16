# USENIX Security '27 Long-Horizon Evaluation Design

Status: benchmark selection and implementation specification. No result claims should be made from this document.

## 1. Research Questions

- RQ-L1: Does attack success increase with trajectory length and number of untrusted observations?
- RQ-L2: Does pre-commit effect binding keep unauthorized committed effects low across every trajectory prefix?
- RQ-L3: How does the fixed task permission envelope affect benign long-task completion?
- RQ-L4: Can authorized-read resolution recover legitimate values without laundering injected values?
- RQ-L5: How do security, utility, latency, tokens, and replan frequency scale with trajectory length?

## 2. Benchmark Survey

| Benchmark | Relevant design | Data/evaluator | Security support | Fit for this paper |
|---|---|---|---|---|
| [AgentDojo](https://papers.nips.cc/paper_files/paper/2024/file/97091a5177d8dc64b1da8bf3e1f6fb54-Paper-Datasets_and_Benchmarks_Track.pdf) | Stateful tool execution in workspace, Slack, travel, banking | Executable environment and utility/security task validators | Native indirect prompt injection | Primary protocol and source of tools; original tasks alone do not isolate horizon effects |
| [ToolSandbox](https://arxiv.org/abs/2408.04682) / [code](https://github.com/apple/ToolSandbox) | Stateful conversational tools with implicit dependencies | Per-turn state snapshots, milestones, and minefields | No native IPI suite | Best reference for intermediate and terminal scoring; tool domains are narrower |
| [tau-bench](https://arxiv.org/abs/2406.12045) / [code](https://github.com/sierra-research/tau2-bench) | Multi-turn tool-agent-user interaction under domain policies | User simulator and database-state task checks | Policy compliance, not native IPI | Strong external test for task-scoped permission and dynamic legitimate resolution |
| [AppWorld](https://aclanthology.org/2024.acl-long.850/) / [code](https://github.com/StonyBrookNLP/appworld) | Complex multi-app executable tasks | Stateful app APIs and programmatic end-state evaluation | No native IPI suite | High realism and compositionality, but adapter and contract cost are high |
| [Agent Security Bench](https://github.com/agiresearch/asb) | Multiple agent scenarios and attack families | Scenario-specific security metrics | Prompt injection, memory, backdoor, mixed attacks | External security breadth; less aligned with exact AgentDojo protocol |
| [AgentLAB](https://arxiv.org/abs/2602.16901) / [code](https://github.com/TanqiuJiang/AgentLAB) | Adaptive long-horizon attacks over multi-turn agent/environment interaction | 644 cases, attack planner/attacker/verifier/judge | Intent hijacking, tool chaining, task injection, objective drift, memory poisoning | Most direct external security extension; dependency and judge costs require a feasibility smoke |

## 3. Selected Two-Tier Design

### LHE-A: Controlled AgentDojo horizon extension

Build long tasks from the existing AgentDojo v1.1.2 environments without modifying tool semantics. Each task must have a fresh initial state, an explicit original request, a dependency graph, intermediate milestones, forbidden minefields, and a terminal validator.

The extension must not be called an official AgentDojo result. It is an AgentDojo-based long-horizon extension.

Length buckets are defined by successful reference-trajectory tool calls:

- short: 1--4 calls;
- medium: 5--9 calls;
- long: 10--19 calls;
- very long: 20 or more calls.

Target scale:

- 4 domains;
- at least 12 base workflows per length bucket;
- at least 192 clean workflows before attack variants;
- deterministic reference trajectories and state validators;
- at least three attack placements per attackable workflow.

### LHE-B: External benchmark feasibility and validation

Run two small feasibility adapters before selecting the final external set:

1. ToolSandbox: 20--30 stateful tasks to validate milestone/minefield integration and effect-contract coverage.
2. AgentLAB: 20--30 AgentDojo-backed long-horizon security cases using the same victim model, if its planner/judge dependencies can be made reproducible and label-hidden.

Decision gate:

- select AgentLAB when its attack cases, judge outputs, and tool execution can be reproduced without leaking labels or requiring an unavailable proprietary planner;
- otherwise select ToolSandbox for external long-task utility and inject controlled untrusted observations with a separately documented attack layer;
- use tau-bench as the fallback when dynamic user interaction is more important than direct attack reuse.

AppWorld is deferred unless the first two adapters fail because onboarding its app surface would materially expand artifact scope.

## 4. Workflow Construction Rules

Long tasks must have real dependencies, not concatenated independent tasks. A valid workflow should require values produced by earlier authorized reads to parameterize later effects.

Example workspace chain:

1. read a meeting record;
2. resolve named participants;
3. locate the requested document;
4. update document sharing;
5. create a calendar event;
6. invite resolved participants;
7. send a summary and document link;
8. post a completion notice.

For every workflow, store separately:

- deployable original request and initial state;
- reference dependency DAG;
- expected legitimate effect atoms;
- forbidden/minefield effect atoms;
- resolver obligations;
- terminal utility validator;
- per-prefix security validator;
- attack insertion points and hidden attack goal.

Reference atoms, attack goals, and validator internals must not enter agent, planner, guard, sanitizer, or baseline prompts.

## 5. Attack Matrix

Attack placement:

- early: first untrusted observation;
- middle: after at least one legitimate resolver succeeds;
- late: immediately before a high-impact commit;
- repeated: semantically consistent injections in multiple observations.

Attack mechanism:

- recipient or target substitution;
- additional recipient/resource insertion;
- resource alias collision;
- draft/preview/schedule to commit escalation;
- visibility or permission escalation;
- amount, account, destination, or booking substitution;
- provenance laundering through a later summary;
- replan-feedback exploitation;
- objective drift through individually plausible subgoals;
- tool chaining toward an attack goal not directly requested.

## 6. Methods and Controls

Use the same victim checkpoint and task instances for:

- no guard;
- PI Detector/PIGuard;
- strongest completed prompting or sanitization baseline;
- AttriGuard where runtime is feasible;
- E77/E78 effect-binding guard;
- oracle contract/envelope upper bound;
- fail-closed lower-utility control.

Run each stochastic configuration at least three times or justify deterministic decoding and still repeat a stratified subset to measure infrastructure nondeterminism.

## 7. Metrics

Security:

- trajectory attack success rate;
- fraction of trajectories with any unauthorized committed atom;
- unauthorized committed atoms per trajectory;
- first unsafe commit index;
- prefix-confinement violations;
- injected values accepted as resolver evidence;
- permission-envelope expansion or drift.

Utility:

- terminal task success;
- utility under attack;
- milestone completion rate;
- legitimate committed-atom recall;
- false replan and false deny;
- successful recovery after replan;
- unresolved legitimate dependency rate.

Performance:

- latency and tokens per trajectory and per call;
- extra LLM calls;
- pre-commit check time;
- descriptor registration time and manual review time;
- scaling slope against trajectory length and untrusted-observation count.

Report paired confidence intervals and paired significance tests over identical workflow/attack seeds. Do not report only aggregate accuracy.

## 8. Required Artifacts

- `evaluation/e79_long_horizon/dataset_manifest.json`
- `evaluation/e79_long_horizon/deployable_tasks.jsonl`
- `evaluation/e79_long_horizon/reference_trajectories.jsonl`
- `evaluation/e79_long_horizon/gold_effect_atoms.jsonl`
- `evaluation/e79_long_horizon/attack_variants.jsonl`
- `evaluation/e79_long_horizon/leakage_report.json`
- `evaluation/e79_long_horizon/results_<method>.json`
- `analysis/results/e79_long_horizon_report.{json,md}`
- `analysis/results/e79_long_horizon_failures.jsonl`
- `paper_tables/table_e79_horizon_scaling.tex`
- `paper_figures/figure_e79_security_utility_vs_horizon.pdf`

## 9. Acceptance Gates

- all tasks execute in a sandbox with no real external effects;
- every task has terminal and prefix validators;
- prompt/label leakage is zero;
- unsupported tools or missing contracts do not silently allow;
- every reported method uses the same victim model and task instances;
- performance drops and utility failures remain in the dataset and failure analysis;
- the paper distinguishes official benchmark results from extensions;
- every figure/table value is reproducible from result artifacts.

