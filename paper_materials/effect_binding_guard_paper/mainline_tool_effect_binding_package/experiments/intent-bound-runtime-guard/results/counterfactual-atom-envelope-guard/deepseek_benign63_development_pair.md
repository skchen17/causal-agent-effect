# C1 DeepSeek Benign-63 Development Pair

- No guard: `53/63`.
- C1 atom envelope: `50/63`.
- Paired difference: `-0.0476`.
- Paired task bootstrap 95% interval: `[-0.1905, 0.0794]`.
- C1 gains/losses: `8/11`.
- Executed without `ALLOW`: `0`.
- Runtime guard LLM calls: `0`.
- Guard deny/abstain: `0/0`.
- Explicit untrusted control segments on benign calls: `0`.
- Development utility gate passed: `True`.
- Full development gate passed: `True`.
- C1b is path-equivalent to C1 for these observed benign calls: `True`.

This is a one-repetition development comparison, not the final non-inferiority
test. A task-level gain or loss between separate remote-model runs is not, by
itself, attributed to the guard. Direct guard-induced loss requires a deny or
abstain on the execution path.
