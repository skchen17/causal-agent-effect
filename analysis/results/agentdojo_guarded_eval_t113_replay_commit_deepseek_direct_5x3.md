# T113 AgentDojo Future-Constrained Guard

## Scope

- Evaluated methods: `shadow_prefix_lock_v1` and/or `shadow_replay_commit_v1`.
- A clean no-injection shadow trajectory is generated for each user task.
- `shadow_prefix_lock_v1` lets the attacked model continue but commits only exact next-step matches.
- `shadow_replay_commit_v1` skips attacked replanning and commits the clean shadow trajectory in the injected environment.
- This is an oracle/shadow pilot, not an independent future-constraint compiler.

## Results

| method | suite | n | shadow UR | A.UR | ASR | A.UR count | ASR count | block-any | allowed | blocked | replay errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| shadow_replay_commit_v1 | workspace | 15 | 0.8000 | 0.8000 | 0.0000 | 12/15 | 0/15 | 0.0000 | 39 | 0 | 0 |
| shadow_replay_commit_v1 | slack | 15 | 1.0000 | 0.6000 | 0.0000 | 9/15 | 0/15 | 0.0000 | 78 | 0 | 18 |
| shadow_replay_commit_v1 | travel | 15 | 0.8000 | 0.8000 | 0.0000 | 12/15 | 0/15 | 0.0000 | 117 | 0 | 0 |
| shadow_replay_commit_v1 | banking | 15 | 1.0000 | 1.0000 | 0.0000 | 15/15 | 0/15 | 0.0000 | 66 | 0 | 0 |

## Interpretation Boundary

- ASR follows AgentDojo injection-task success semantics: higher is worse.
- `shadow_UR` is clean-shadow task utility, not deploy-time user satisfaction.
- A low ASR with low A.UR indicates over-blocking or replay utility loss, not a useful defense.
- `shadow_replay_commit_v1` assumes the clean shadow trajectory is available and safe to replay; it is an upper-bound mechanism test, not a complete deployed system.
