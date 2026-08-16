# E79 External Long-Horizon Benchmark Gate

Status: `passed`.

No benchmark, model, tool, or external API was executed by this static audit.

| Benchmark | Source | Gate | Intended role |
|---|---|---|---|
| toolsandbox | complete | `ready_for_offline_environment_smoke` | Primary external long-task utility/state-dependency benchmark after an offline subset smoke. |
| agentlab | metadata only | `blocked_pending_full_source_and_local_judge_adapter` | Adaptive long-horizon security extension after dependency and judge replacement smokes. |
| tau2_bench | metadata only | `fallback_pending_full_source_checkout` | Fallback external long-task benchmark when dynamic user interaction is prioritized. |

## Blocking Reasons

### toolsandbox
- Search scenarios require RapidAPI and must be excluded from the offline subset.
- The user simulator must be replaced with the fixed local checkpoint for comparable runs.
- Prompt-injection variants and per-prefix unauthorized-effect validators are not native and must be added.

### agentlab
- Only public metadata is complete locally; the full source checkout has not completed.
- The released default planner and judge use GPT-5.1, so a local replacement must be validated before a comparable run.
- Its judge-based success labels must be separated from deployable agent and guard inputs.

### tau2_bench
- Only public metadata is complete locally; the full source checkout has not completed.
- The benchmark supplies dynamic user interaction but not an indirect-prompt-injection attack protocol.
- Python 3.12+ requires an isolated environment from the current AgentDojo runner.

## Decision

ToolSandbox advances first to an offline environment smoke because its complete local snapshot exposes stateful tools, state snapshots, and milestone-DAG evaluation without requiring real external effects. AgentLAB remains the preferred adaptive-attack extension, but it cannot be reported as executed until the full source and a reproducible local planner/judge path pass. tau2-bench remains the dynamic-user fallback.
