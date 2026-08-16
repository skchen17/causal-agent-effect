# E78 Qwen3-32B Strong Baseline Finalization

- Status: `frozen_complete_metrics_with_protocol_caveats`
- Complete direct native-metric rows: `4356 = 6 x 726`
- Frozen rows including provisional AttriGuard: `5082`
- AttriGuard clean protocol attempts: `716/726`; excluded from the strict primary table.
- Direct methods have complete native metrics, but the historical runner did not preserve per-method command diagnostics.
- The proposed-method row is sourced from the strict 714+12 context-repair overlay finalizer.
- The proposed-method overlay is complete but not a uniform-context rerun.

| Method | Protocol | BU | Attack utility | ASR | Primary eligible now |
|---|---|---:|---:|---:|---|
| No defense | complete_726_native_metrics_command_diagnostics_not_frozen | 0.660 | 0.544 | 0.084 | true |
| MELON-style | complete_726_native_metrics_command_diagnostics_not_frozen | 0.639 | 0.541 | 0.089 | true |
| Effect-binding runtime guard | strict_context_repair_overlay_finalizer_passed | 0.340 | 0.329 | 0.005 | true |
| Prompt Sandwiching | complete_726_native_metrics_command_diagnostics_not_frozen | 0.619 | 0.576 | 0.013 | true |
| PromptArmor-style | complete_726_native_metrics_command_diagnostics_not_frozen | 0.278 | 0.219 | 0.002 | true |
| Spotlighting | complete_726_native_metrics_command_diagnostics_not_frozen | 0.619 | 0.590 | 0.076 | true |
| AttriGuard adapted artifact | provisional_10_of_726_protocol_errors | 0.412 | 0.342 | 0.013 | false |

## Claim Boundary

Five baseline rows and the current effect-binding runtime share one Qwen3-32B checkpoint, the same 726 AgentDojo v1.1.2 case keys, native evaluators, and sandbox execution. MELON-style, Prompt Sandwiching, and PromptArmor-style are comparable local adapters, not original-paper reproductions. AttriGuard remains provisional because 10 workspace attempts exceeded the frozen context protocol. The proposed-method row is admitted only after its recovery-normalization strict finalizer passes. It combines 714 original trajectories with 12 disclosed context-capacity repairs; it is therefore a complete native-metric overlay, not a uniform-context rerun.
