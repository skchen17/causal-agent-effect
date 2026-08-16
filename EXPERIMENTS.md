# Main Experiment Map

The map follows the paper's evidence chain. Every listed final result is frozen
and admitted by `paper/current-usenix/reproduction/reproduce_main_claims.py`.

| Evidence | Main question | Runner | Frozen result |
|---|---|---|---|
| Effect prevalence | Do benchmark calls commit compound or heterogeneous effects? | `shared/compatibility/scripts/run_agentdojo_tool_effect_prevalence.py` | `experiments/human-authority-and-causal-validation/results/agentdojo-tool-effect-prevalence/agentdojo-tool-effect-prevalence-report.json` |
| Finite collisions | Do coarse views merge policy-distinct source executions? | `shared/compatibility/scripts/run_finite_domain_effect_binding_validation.py` | `experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation/finite-domain-validation-report.json` |
| Failure certificates | Can collisions be reconstructed as executable witnesses? | `shared/compatibility/scripts/extract_executable_failure_certificates.py` | `experiments/human-authority-and-causal-validation/results/executable-failure-certificates/report.json` |
| Third-party tools | Does validation transfer to pinned public MCP implementations? | `shared/compatibility/scripts/run_third_party_authorization_interface_validation.py` | `experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation/third_party_validation_report.json` |
| Mechanical separation | Does a native-delta policy agree with the typed path, and which descriptor faults are detected? | `shared/compatibility/scripts/run_native_delta_mechanical_validation.py` | `experiments/human-authority-and-causal-validation/results/native-delta-mechanical-validation/native_delta_validation_report.json` |
| Explicit authority | Which interfaces preserve decisions under shared ACL, capability, and delegation state? | `shared/compatibility/scripts/independent_authority_benchmark/run_experiment.py` | `experiments/human-authority-and-causal-validation/results/protocol-separated-authority-representation/report.json` |
| State-aware baseline | Can totalized arguments plus trusted pre-state also be sufficient? | `shared/compatibility/scripts/state_aware_authority_baseline.py` | `experiments/human-authority-and-causal-validation/results/state-aware-authority-interface/report.json` |
| Interface economy | Where do typed and state-aware paths place state exposure, adaptation code, overpartition, and latency? | `shared/compatibility/scripts/run_authorization_interface_economy_audit.py` | `experiments/human-authority-and-causal-validation/results/authorization-interface-economy/interface_economy_report.json` |
| Concrete runtime | Can a frozen descriptor drive check--use-consistent authorization? | `shared/compatibility/scripts/run_small_typed_effect_runtime_case_study.py` | `experiments/human-authority-and-causal-validation/results/small-typed-effect-runtime-case-study/runtime_case_study_report.json` |
| Registration coverage | Which AgentDojo fields have valid effect-changing witnesses? | `experiments/intent-bound-runtime-guard/scripts/counterfactual-atom-envelope-guard/run_registration_sufficiency_audit_v2.py` | `experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/registration_sufficiency_audit_v2.json` |
| Runtime mechanism | Does validated semantics differ from generic raw-field taint? | `shared/compatibility/scripts/run_c1f_raw_field_attribution.py` | `experiments/security-analysis-ablation-and-overhead/results/c1f-raw-field-attribution/raw-field-attribution-report.json` |
| Strong baselines | How do five methods compare under one checkpoint and exact key set? | `shared/compatibility/scripts/run_current_c1f_qwen32_strong_baseline_rerun.py` | `experiments/unified-agent-security-baselines/results/current-c1f-strong-baseline-rerun/results.json` |

## Deterministic Verification

```bash
python scripts/verify_release.py
python scripts/reproduce_usenix_main.py
python -m pytest \
  shared/compatibility/tests/tests/test_usenix_main_reproduction.py \
  shared/compatibility/tests/tests/test_render_usenix_final_tables.py \
  shared/compatibility/tests/tests/test_authorization_interface_economy.py \
  shared/compatibility/tests/tests/test_native_delta_mechanical_validation.py \
  shared/compatibility/tests/tests/test_third_party_authorization_interface_validation.py -q
```

Live model and source-replay reruns require the separately documented benchmark
and model environments. The repository-level reproduction command regenerates
all reported paper numbers from hash-frozen artifacts without model inference.
