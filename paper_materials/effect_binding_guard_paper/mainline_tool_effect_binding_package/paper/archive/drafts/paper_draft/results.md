# Results

Key measured anchors:

- Phase 4 lattice: 528 cases across 24 paired groups.
- TS-Guard official-checkpoint custom stress: same-effect consistency 0.883, effect-change correctness 0.625, authorization sensitivity 0.764, resource mismatch error 0.167, unsafe pre-allow 0.159, safe false denial 0.087.
- Safiron official-checkpoint custom stress: same-effect consistency 0.669, effect-change correctness 1.000, authorization sensitivity 0.088, resource mismatch error 0.833, unsafe pre-allow 0.545, safe false denial 0.371.
- Tool-name proxy: same-effect consistency 1.000 but effect-change correctness 0.000, authorization sensitivity 0.000, resource mismatch error 1.000, unsafe pre-allow 0.292, safe false denial 0.708.
- IPIGuard topology-only: topology/surface stability 1.000, but no realized-effect authorization decision interface; report effect sensitivity as `N/I`.
- IPIGuard deterministic mapper: effect sensitivity 0.375, authorization sensitivity 0.375, resource sensitivity 0.375, unsafe pre-allow 0.000, safe false denial 0.060, abstain 0.579.
- IPIGuard local-Qwen semantic mapper: surface invariance 0.992, effect sensitivity 0.833, authorization sensitivity 0.375, resource sensitivity 0.125, unsafe pre-allow 0.333, safe false denial 0.018, abstain 0.062.
- CaMeL structural policy component: 54-case component stress, unsafe blocked 0.750, safe false denial 0.000, 6 unsafe misses concentrated in control-dependency violations.
- Human audit: 222/222 primary rows and 56/56 secondary rows complete; decision/effect/resource/authorization agreement all 1.0; upgrade gate true.

RQ takeaways:

1. Surface-level stability can coexist with complete failure on effect changes.
2. Official-checkpoint rows are not simple tool-name proxies, but remain incomplete under the paired lattice.
3. Checkpoints should be described by per-axis capability profiles, not aggregate pass/fail labels.
4. Graph topology is stable but semantically incomplete; structural policy misses control-dependency violations.
5. Evidence and semantic grounding are useful diagnostics, but this package supports only incomplete non-oracle rows or non-deployable upper bounds.
6. Human audit supports the reported E47 labels while remaining limited to the constructed custom/component stress distribution.

Central interpretation:

Weak surface baselines fail under counterfactual and held-out shifts. Stronger checkpoints and structural methods resist some simple surface changes and are not merely tool-name classifiers. The evaluated non-oracle methods remain incomplete for joint effect-resource-authorization-provenance reasoning under this controlled audit.
