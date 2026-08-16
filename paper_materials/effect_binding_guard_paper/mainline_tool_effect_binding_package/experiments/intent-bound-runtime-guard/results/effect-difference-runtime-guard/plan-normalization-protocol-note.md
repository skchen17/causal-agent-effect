# Plan-Normalization Full-Run Protocol

This run supersedes E77-v3 for evaluating the repaired permission-plan interface. It does not overwrite or relabel the E77-v3 result.

## Change from E77-v3

- Plan JSON schema parsing, semantic authority validation, and final plan acceptance are recorded separately.
- Safe normalizations fill structurally inert omissions, drop read-only permission entries, and totalize omitted security fields to `forbidden`.
- Unknown tools, ungrounded exact values, malformed types, and missing exact values remain fail-closed.
- A semantically rejected plan is a model outcome, not a harness failure. Side-effectful calls under such a plan must not receive an initial `ALLOW`.

## Frozen Run

- Dataset: AgentDojo v1.1.2, 726 official cases across workspace, Slack, travel, and banking.
- Model: local Qwen3-32B Q4_K_M checkpoint, temperature 0.
- Runtime: `effect_diff_runtime_plan_normalization_v1`.
- GPU configuration: 65 GPU layers with tensor split 0.35/0.65.
- Run artifacts: `experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/plan-normalization-qwen32-full/`.
- Final report: `plan-normalization-qwen32-full-report.json` and `.md` in this directory.

The finalizer checks exact benchmark coverage, clean command execution, complete and consistent plan diagnostics, deterministic authorization, and fail-closed handling of rejected plans. Utility, ASR, and plan-acceptance rates remain measured outcomes and are not pass gates.
