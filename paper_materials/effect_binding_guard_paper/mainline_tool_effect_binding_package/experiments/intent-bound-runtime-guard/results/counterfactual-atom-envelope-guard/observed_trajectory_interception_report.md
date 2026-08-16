# C1 Observed-Trajectory Interception Diagnostic

- Source: completed Qwen3-32B no-guard AgentDojo v1.1.2 trajectories.
- Benign observed calls blocked: `0/97`.
- Successful benign trajectories blocked: `0/64`.
- Official successful attack trajectories intercepted: `49/53`.
- All attack trajectories with at least one intercepted call: `121/629`.
- Residual successful attack cases: `4`.

The residual cases are reported by key in the JSON artifact. Manual trajectory
inspection is required to distinguish tool-effect misses from output-only goals.
This diagnostic does not estimate live guarded ASR because blocking an earlier
call can change later model behavior.
