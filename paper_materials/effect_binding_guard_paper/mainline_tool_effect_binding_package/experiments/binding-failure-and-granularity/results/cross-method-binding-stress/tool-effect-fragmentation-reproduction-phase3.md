# Phase 3 External Reproduction Audit

| System | Status | Repo commit | Artifact | Model/API | Blockers |
|---|---|---|---|---|---|
| `toolsafe` | `original_method_custom_stress_available` | `46358fa424a927a895c6c8322f99032c4eb5155e` | `/data/CSK/causal-agent-safety-research/external/systems/toolsafe/TS-Bench` | https://huggingface.co/MurrayTom/TS-Guard | original_paper_benchmark_metric_reproduction_not_run; custom_stress_expected_labels_are_proxy_or_published_derived |
| `safiron` | `original_method_custom_stress_available` | `cd4a9fc1d251c2430e21ffce33b4b09c5ebf53b8` | `/data/CSK/causal-agent-safety-research/external/systems/agentic_guardian/Pre-Ex-Bench/dataset.json` | https://huggingface.co/Safiron/Safiron | original_paper_benchmark_metric_reproduction_not_run; custom_stress_expected_labels_are_proxy_or_published_derived |
| `ipiguard` | `local_model_substitute_result_available` | `4e686ed2f62c135cb12564a4466daa95f3ace878` | `/data/CSK/causal-agent-safety-research/external/systems/ipiguard/eval.sh` | OpenAI-compatible API configured by OPENAI_API_KEY/OPENAI_BASE_URL | official_api_backed_method_not_run; full_tool_effect_fragmentation_evaluation_not_run |
| `camel` | `local_model_substitute_result_available` | `f083b6b396399d3b3c7f2ddaf613a5945eaf32d8` | `/data/CSK/causal-agent-safety-research/external/systems/camel/main.py` | structural defense code; model selected at runtime | official_api_backed_method_not_run; full_tool_effect_fragmentation_evaluation_not_run |

## Claim Boundary

- `adapter_failed_complete` means reproduction was audited and blocked; it is not a negative method result.
- `original_method_runnable` only means the local prerequisites appear present; paper-grade status still requires running and validating outputs.

## Phase 3 Smoke Status

- `toolsafe`: `smoke_passed`; claim scope: `original_method_smoke`; reason: completed
- `safiron`: `smoke_passed`; claim scope: `original_method_smoke`; reason: completed
- `ipiguard`: `smoke_passed`; claim scope: `local_model_substitute`; reason: completed
- `camel`: `smoke_passed`; claim scope: `local_model_substitute`; reason: completed

## Official-Checkpoint Custom Stress

- `toolsafe`: `216` E47 custom cases, `216` parse-valid; scope `original_method_custom_stress`.
- `safiron`: `216` E47 custom cases, `216` parse-valid; scope `original_method_custom_stress`.
- `ipiguard`: not available
- `camel`: not available

## Phase 3 Claim Boundary

- `original_method_custom_stress` uses a released checkpoint with its published prompt/output format on E47-adapted inputs.
- It is stronger than a runnable smoke, but it is not an original-paper benchmark metric reproduction.
- IPIGuard and CaMeL local-model substitutes validate adapter feasibility only and do not establish original-method behavior.
