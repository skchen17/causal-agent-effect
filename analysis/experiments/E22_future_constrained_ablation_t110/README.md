# E22 Future-Constrained Ablation T110

## Experiment Purpose

Evaluate which components of the Future-Constrained CEG-Auth / AuthTrace-Guard prevention pipeline matter at action level.

The experiment reuses the T102/T109 local case taxonomy and compares the full local pipeline against ablations and baselines:

- full future-constrained pipeline;
- no shadow but prefix guard retained;
- T108 independent text-rule compiler with full guard;
- effect+resource status boundary;
- effect-only status boundary;
- tool-name whitelist;
- no replay lock / no prefix guard;
- no staging / post-hoc guard;
- allow-all and deny-all extremes.

## Main Conclusion

T110 supports a limited local prevention claim:

> On the controlled T102/T109 local cases, future constraints plus prefix-guarded staged commit can prevent unauthorized commits, and removing replay-lock/prefix-guard or staging produces severe action-level failures.

Key counts from `analysis/results/future_constrained_ablation_t110_v1.md`:

- `full_future_constrained`: unauthorized commit `0/800`, Wilson 95% CI upper `0.0048`; authorized false denial `0/200`, Wilson upper `0.0188`.
- `no_replay_lock_or_prefix_guard`: unauthorized commit `400/800`; all 400 deviation-under-authorized-constraint cases commit unauthorized effects.
- `no_staging_posthoc_guard`: unauthorized commit `800/800`; post-hoc detection can flag violations, but the unsafe effects have already crossed the commit boundary.
- `tool_whitelist_only`: unauthorized commit `750/800`; tool names are insufficient.
- `effect_status_only`: unauthorized commit `120/800`; effect type alone misses resource/scope violations.
- `t108_text_rule_full_system`: unauthorized commit `0/800`, but authorized false denial `25/200`, concentrated in the known T108 API dry-run compiler failure mode.

Important negative result:

- `no_shadow_prefix_guard_only` matches the full pipeline on this local benchmark.
- `effect_resource_status_boundary` also matches the full pipeline.

Therefore, T110 does **not** prove that shadow execution is independently necessary, nor that the current full system is superior to a handcrafted resource-aware boundary in this controlled local setting.

## Key Artifacts

- Script: `src/auth/future_constrained_ablation_t110.py`
- Action-level row output: `data/future_constrained_ablation_t110_v1.jsonl`
- Machine-readable result: `analysis/results/future_constrained_ablation_t110_v1.json`
- Readable report: `analysis/results/future_constrained_ablation_t110_v1.md`

## Paper Claims Supported

- In a mediated local prototype, pre-commit prefix guards and staged/two-phase commit are necessary to block real-stage drift before side effects commit.
- Tool-name-only controls are inadequate for authorization-conditioned realized-effect safety.
- Effect-type-only raw status is stronger than tool names but still misses scope/resource violations.
- Independent future-constraint compilation quality affects utility: the T108 text-rule compiler preserves zero unauthorized commits but induces false denials.

## Claims Not Supported

- This does not validate provider-backed services, SaaS messaging, HTTP browser automation, or deployed-agent runtime logs.
- This does not prove method superiority over handcrafted resource-aware guards.
- This does not prove the independent necessity of shadow execution; the current benchmark is too simple because prefix guards alone match the full local pipeline.
- This does not evaluate the GGUF LLM compiler; it uses the T108 deterministic text-rule compiler as the independent compiler ablation.
