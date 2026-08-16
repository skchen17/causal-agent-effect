# Phase 2 External Reproduction Audit

| System | Status | Repo commit | Artifact | Model/API | Blockers |
|---|---|---|---|---|---|
| `toolsafe` | `adapter_failed_complete` | `46358fa424a927a895c6c8322f99032c4eb5155e` | `/data/CSK/causal-agent-safety-research/external/systems/toolsafe/TS-Bench` | https://huggingface.co/MurrayTom/TS-Guard | configured_local_ts_guard_model_missing:/mnt/shared-storage-user/mouyutao/AShell-ours/verl-main/checkpoints/verl_grpo_ashell_guardian_v2.4.0-rollout16_multitask_uniform/qwen2.5_7b_function_rm/global_step_80/actor_hf |
| `safiron` | `adapter_failed_complete` | `cd4a9fc1d251c2430e21ffce33b4b09c5ebf53b8` | `/data/CSK/causal-agent-safety-research/external/systems/agentic_guardian/Pre-Ex-Bench/dataset.json` | https://huggingface.co/Safiron/Safiron | safiron_model_not_verified_locally:/data/CSK/causal-agent-safety-research/models/Safiron/Safiron |
| `ipiguard` | `adapter_failed_complete` | `4e686ed2f62c135cb12564a4466daa95f3ace878` | `/data/CSK/causal-agent-safety-research/external/systems/ipiguard/eval.sh` | OpenAI-compatible API configured by OPENAI_API_KEY/OPENAI_BASE_URL | OPENAI_API_KEY_missing_for_official_eval; OPENAI_BASE_URL_missing_for_official_eval |
| `camel` | `adapter_failed_complete` | `f083b6b396399d3b3c7f2ddaf613a5945eaf32d8` | `/data/CSK/causal-agent-safety-research/external/systems/camel/main.py` | structural defense code; model selected at runtime | OPENAI_API_KEY_missing_for_camel_eval |

## Claim Boundary

- `adapter_failed_complete` means reproduction was audited and blocked; it is not a negative method result.
- `original_method_runnable` only means the local prerequisites appear present; paper-grade status still requires running and validating outputs.
