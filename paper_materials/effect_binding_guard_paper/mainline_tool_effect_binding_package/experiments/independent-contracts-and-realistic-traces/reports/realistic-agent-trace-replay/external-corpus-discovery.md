# E61 External Corpus Discovery

This discovery searched local saved trace artifacts for external, replay-only traces that can be converted to the E61 deployable-input contract without real side effects.

| Candidate | Rows | Message rows | Replay-only mutating rows | Usable | Reason |
|---|---:|---:|---:|---:|---|
| `data/data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl` | 1452 | 1428 | 156 | True | Usable: saved AgentDojo-style IPIGuard traces contain replay-only messages, four suites, and mutating candidate tool calls. |
| `data/data/tool_effect_fragmentation/camel_phase5_traces.jsonl` | 3138 | 0 | 0 | False | Rows lack message trajectories needed for replay conversion. |
| `data/data/tool_effect_fragmentation/external_pipeline_phase6_traces.jsonl` | 0 | 0 | 0 | False | No rows. |
| `data/data/tool_effect_fragmentation/stress_cases_agentdojo.jsonl` | 1296 | 0 | 0 | False | Rows lack message trajectories needed for replay conversion. |
| `data/data/tool_effect_fragmentation/predictions_agentdojo.jsonl` | 10368 | 0 | 0 | False | Rows lack message trajectories needed for replay conversion. |

Selected subset: `data/data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl`.

Claim boundary: the selected traces are saved AgentDojo-style/IPIGuard replay traces, not real deployed production logs. They are used only after conversion into label-hidden deployable inputs, with labels and sidecar atoms stored separately.
