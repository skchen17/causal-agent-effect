# Experiment Notes

This file records the four evidence additions implemented without modifying the frozen 1,024-context benchmark.

## State-Aware Authority Interface

- Runner: `shared/compatibility/scripts/state_aware_authority_baseline.py`
- Result: `experiments/human-authority-and-causal-validation/results/state-aware-authority-interface/report.json`
- Outcome: 1,024 contexts, 669 cells, zero mixed cells, zero state-dependent collisions, and exact decisions through a separately disclosed request adapter.
- Boundary: the adapter contains static tool-specific operation knowledge. The result establishes another sufficient finite-domain interface, not typed-effect uniqueness.

## Executable Failure Certificates

- Extractor: `shared/compatibility/scripts/extract_executable_failure_certificates.py`
- Result: `experiments/human-authority-and-causal-validation/results/executable-failure-certificates/failure-certificates.jsonl`
- Outcome: six deterministic certificates covering target expansion, compound effects, qualifiers, state dependence, repeated effects, and resource/authority distinctions.
- Gate: each row recomputes `source differs`, `policy differs`, `coarse representation equal`, and `refined representation differs`.

## Third-Party MCP Validation

- Runner: `shared/compatibility/scripts/run_third_party_authorization_interface_validation.py`
- Result: `experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation/third_party_validation_report.json`
- Outcome: 11 tools from three pinned public MCP projects; 264 registration executions and 264 descriptor-blind post-freeze contexts; no source, compile, or descriptor failures.
- Collision pairs: tool-name 1,552; raw-call 100; common-field 200; state-aware 0; typed 0.
- Boundary: source implementations are independently authored, but descriptors, policies, and protocol are project-authored. No independent human review is claimed.

## Small Runtime Case Study

- Runner: `shared/compatibility/scripts/run_small_typed_effect_runtime_case_study.py`
- Result: `experiments/human-authority-and-causal-validation/results/small-typed-effect-runtime-case-study/runtime_case_study_report.json`
- Outcome: all 30 local-model calls parsed; 10 authorized calls committed and 20 unauthorized calls denied; zero check--use and reconciliation failures.
- Boundary: this is a scenario-balanced copied-sandbox integration case study, not an open-world agent benchmark.

The first development runtime report compared JSON encodings of integral and floating-point numbers and incorrectly flagged six reconciliation failures (`100` versus `100.0`). Structural numeric comparison fixed the checker without changing model outputs. The development artifacts remain archived under the experiment's evaluation and result directories.

## Authorization Interface Economy

- Runner: `shared/compatibility/scripts/run_authorization_interface_economy_audit.py`
- Result: `experiments/human-authority-and-causal-validation/results/authorization-interface-economy/interface_economy_report.json`
- Outcome: typed and state-aware paths make exact decisions with no mixed cell in both the 1,024- and 264-context domains. Typed views have fewer cells and no source-equivalent overpartition; state-aware requests expose more raw tool pre-state at the policy-facing boundary.
- Boundary: latency and executable code size do not consistently favor typed effects. The 1,024-context typed interpreter is generic and descriptor-driven; the third-party typed compiler remains tool-specific.

## Native-Delta Mechanical Validation

- Runner: `shared/compatibility/scripts/run_native_delta_mechanical_validation.py`
- Result: `experiments/human-authority-and-causal-validation/results/native-delta-mechanical-validation/native_delta_validation_report.json`
- Outcome: native-policy and typed-path decisions agree on all 264 registration and 264 held-out contexts. Registration detects 37 of 47 systematic mutants; 10 are decision-equivalent on both frozen domains, and none fails only after freeze.
- Boundary: the implementations are mechanically role-separated but project-authored. This is not independent semantic certification or independent descriptor authorship.
