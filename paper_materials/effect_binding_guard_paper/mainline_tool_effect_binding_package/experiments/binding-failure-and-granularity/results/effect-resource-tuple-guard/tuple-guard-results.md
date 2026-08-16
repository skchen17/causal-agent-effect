# E48 Counterfactual Effect-Binding Guard Feasibility

- Rows: `822`
- Pairs: `6840`
- Local Qwen rows: `822`; parse-valid rate `0.9951338199513382`
- Safety-first calibration gate: `True`
- Deployable-input leakage violations: `0`

## Method And Scope

- `rule_tuple_guard` explicitly infers effect, resource, authorization match, and provenance risk from non-oracle fields.
- `multi_view_disagreement_guard` compares tool, schema, plan/call, masked-tool, canonical, evidence, and optional local-Qwen views.
- `evidence_gated_selective_guard` consults saved/simulated non-oracle evidence only on uncertain or disagreeing cases.
- `control_provenance_minimal_check` blocks private control dependencies and abstains on unresolved untrusted-data control.
- `effect_binding_guard_full` combines selective evidence fallback with the provenance overlay.
- `pairwise_relation_learner` is a grouped counterfactual diagnostic, not a single-case deployable guard.

## Main Metrics

| Method | Unsafe Pre-Allow | Safe False Deny | Abstain | Coverage | Effect Acc | Resource Acc | Auth Acc | Provenance Acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `always_use_evidence` | 0.003 [0.000, 0.016] | 0.032 [0.020, 0.053] | 0.861 [0.836, 0.883] | 0.139 [0.117, 0.164] | 0.102 [0.083, 0.125] | 0.088 [0.070, 0.109] | 0.129 [0.107, 0.154] | 0.000 [0.000, 0.066] |
| `control_provenance_minimal_check` | 0.094 [0.068, 0.129] | 0.097 [0.074, 0.128] | 0.345 [0.314, 0.379] | 0.655 [0.621, 0.686] | 0.792 [0.763, 0.818] | 0.380 [0.347, 0.413] | 0.504 [0.469, 0.539] | 1.000 [0.934, 1.000] |
| `effect_binding_guard_full` | 0.036 [0.021, 0.061] | 0.065 [0.046, 0.091] | 0.083 [0.066, 0.104] | 0.917 [0.896, 0.934] | 0.836 [0.809, 0.860] | 0.726 [0.695, 0.756] | 0.848 [0.821, 0.871] | 1.000 [0.934, 1.000] |
| `evidence_gated_selective_guard` | 0.064 [0.043, 0.094] | 0.065 [0.046, 0.091] | 0.075 [0.059, 0.096] | 0.925 [0.904, 0.941] | 0.836 [0.809, 0.860] | 0.726 [0.695, 0.756] | 0.848 [0.821, 0.871] | 0.722 [0.591, 0.824] |
| `local_qwen_tuple_guard` | 0.106 [0.078, 0.142] | 0.067 [0.048, 0.094] | 0.038 [0.027, 0.053] | 0.962 [0.947, 0.973] | 0.809 [0.781, 0.834] | 0.877 [0.853, 0.898] | 0.930 [0.909, 0.946] | 0.815 [0.692, 0.896] |
| `multi_view_disagreement_guard` | 0.075 [0.052, 0.107] | 0.136 [0.108, 0.171] | 0.002 [0.001, 0.009] | 0.998 [0.991, 0.999] | 0.892 [0.869, 0.911] | 0.753 [0.722, 0.781] | 0.859 [0.833, 0.882] | 0.815 [0.692, 0.896] |
| `never_use_evidence` | 0.075 [0.052, 0.107] | 0.136 [0.108, 0.171] | 0.002 [0.001, 0.009] | 0.998 [0.991, 0.999] | 0.892 [0.869, 0.911] | 0.753 [0.722, 0.781] | 0.859 [0.833, 0.882] | 0.815 [0.692, 0.896] |
| `rule_tuple_guard` | 0.094 [0.068, 0.129] | 0.097 [0.074, 0.128] | 0.345 [0.314, 0.379] | 0.655 [0.621, 0.686] | 0.792 [0.763, 0.818] | 0.380 [0.347, 0.413] | 0.504 [0.469, 0.539] | 1.000 [0.934, 1.000] |
| `rule_tuple_guard_no_provenance` | 0.128 [0.097, 0.166] | 0.097 [0.074, 0.128] | 0.331 [0.300, 0.364] | 0.669 [0.636, 0.700] | 0.792 [0.763, 0.818] | 0.380 [0.347, 0.413] | 0.504 [0.469, 0.539] | 0.000 [0.000, 0.066] |

## Held-Out Test Split

> Thresholds are selected on validation groups. This table is the primary calibrated-policy result; the overall table above is descriptive custom-stress coverage.

| Method | Rows | Unsafe Pre-Allow | Safe False Deny | Abstain | Coverage |
|---|---:|---:|---:|---:|---:|
| `always_use_evidence` | 224 | 0.000 [0.000, 0.038] | 0.048 [0.022, 0.100] | 0.848 [0.795, 0.889] | 0.152 [0.111, 0.205] |
| `control_provenance_minimal_check` | 224 | 0.092 [0.049, 0.165] | 0.079 [0.044, 0.140] | 0.335 [0.276, 0.399] | 0.665 [0.601, 0.724] |
| `effect_binding_guard_full` | 224 | 0.051 [0.022, 0.114] | 0.048 [0.022, 0.100] | 0.045 [0.024, 0.080] | 0.955 [0.920, 0.976] |
| `evidence_gated_selective_guard` | 224 | 0.051 [0.022, 0.114] | 0.048 [0.022, 0.100] | 0.045 [0.024, 0.080] | 0.955 [0.920, 0.976] |
| `local_qwen_tuple_guard` | 224 | 0.071 [0.035, 0.140] | 0.024 [0.008, 0.068] | 0.036 [0.018, 0.069] | 0.964 [0.931, 0.982] |
| `multi_view_disagreement_guard` | 224 | 0.051 [0.022, 0.114] | 0.103 [0.061, 0.169] | 0.000 [0.000, 0.017] | 1.000 [0.983, 1.000] |
| `never_use_evidence` | 224 | 0.051 [0.022, 0.114] | 0.103 [0.061, 0.169] | 0.000 [0.000, 0.017] | 1.000 [0.983, 1.000] |
| `rule_tuple_guard` | 224 | 0.092 [0.049, 0.165] | 0.079 [0.044, 0.140] | 0.335 [0.276, 0.399] | 0.665 [0.601, 0.724] |
| `rule_tuple_guard_no_provenance` | 224 | 0.092 [0.049, 0.165] | 0.079 [0.044, 0.140] | 0.335 [0.276, 0.399] | 0.665 [0.601, 0.724] |

## Results By Evidence Core

| Method | Core | Unsafe Pre-Allow | Safe False Deny | Abstain | Coverage |
|---|---|---:|---:|---:|---:|
| `always_use_evidence` | `camel` | 0.000 [0.000, 0.138] | 0.000 [0.000, 0.114] | 1.000 [0.934, 1.000] | 0.000 [0.000, 0.066] |
| `always_use_evidence` | `ipiguard` | 0.000 [0.000, 0.051] | 0.000 [0.000, 0.022] | 1.000 [0.984, 1.000] | 0.000 [0.000, 0.016] |
| `always_use_evidence` | `phase4` | 0.004 [0.001, 0.021] | 0.057 [0.035, 0.092] | 0.784 [0.747, 0.817] | 0.216 [0.183, 0.253] |
| `control_provenance_minimal_check` | `camel` | 0.000 [0.000, 0.138] | 0.000 [0.000, 0.114] | 0.222 [0.132, 0.349] | 0.778 [0.651, 0.868] |
| `control_provenance_minimal_check` | `ipiguard` | 0.250 [0.164, 0.361] | 0.065 [0.037, 0.113] | 0.517 [0.454, 0.579] | 0.483 [0.421, 0.546] |
| `control_provenance_minimal_check` | `phase4` | 0.061 [0.038, 0.096] | 0.129 [0.094, 0.175] | 0.280 [0.244, 0.320] | 0.720 [0.680, 0.756] |
| `effect_binding_guard_full` | `camel` | 0.000 [0.000, 0.138] | 0.000 [0.000, 0.114] | 0.222 [0.132, 0.349] | 0.778 [0.651, 0.868] |
| `effect_binding_guard_full` | `ipiguard` | 0.125 [0.067, 0.221] | 0.083 [0.050, 0.135] | 0.108 [0.075, 0.154] | 0.892 [0.846, 0.925] |
| `effect_binding_guard_full` | `phase4` | 0.015 [0.006, 0.038] | 0.061 [0.038, 0.096] | 0.057 [0.040, 0.080] | 0.943 [0.920, 0.960] |
| `evidence_gated_selective_guard` | `camel` | 0.417 [0.245, 0.612] | 0.000 [0.000, 0.114] | 0.111 [0.052, 0.222] | 0.889 [0.778, 0.948] |
| `evidence_gated_selective_guard` | `ipiguard` | 0.125 [0.067, 0.221] | 0.083 [0.050, 0.135] | 0.108 [0.075, 0.154] | 0.892 [0.846, 0.925] |
| `evidence_gated_selective_guard` | `phase4` | 0.015 [0.006, 0.038] | 0.061 [0.038, 0.096] | 0.057 [0.040, 0.080] | 0.943 [0.920, 0.960] |
| `local_qwen_tuple_guard` | `camel` | 0.833 [0.641, 0.933] | 0.167 [0.073, 0.336] | 0.111 [0.052, 0.222] | 0.889 [0.778, 0.948] |
| `local_qwen_tuple_guard` | `ipiguard` | 0.194 [0.120, 0.300] | 0.083 [0.050, 0.135] | 0.017 [0.006, 0.042] | 0.983 [0.958, 0.994] |
| `local_qwen_tuple_guard` | `phase4` | 0.015 [0.006, 0.038] | 0.045 [0.026, 0.078] | 0.040 [0.026, 0.060] | 0.960 [0.940, 0.974] |
| `multi_view_disagreement_guard` | `camel` | 0.500 [0.314, 0.686] | 0.000 [0.000, 0.114] | 0.000 [0.000, 0.066] | 1.000 [0.934, 1.000] |
| `multi_view_disagreement_guard` | `ipiguard` | 0.139 [0.077, 0.237] | 0.137 [0.093, 0.197] | 0.000 [0.000, 0.016] | 1.000 [0.984, 1.000] |
| `multi_view_disagreement_guard` | `phase4` | 0.019 [0.008, 0.044] | 0.152 [0.113, 0.200] | 0.004 [0.001, 0.014] | 0.996 [0.986, 0.999] |
| `never_use_evidence` | `camel` | 0.500 [0.314, 0.686] | 0.000 [0.000, 0.114] | 0.000 [0.000, 0.066] | 1.000 [0.934, 1.000] |
| `never_use_evidence` | `ipiguard` | 0.139 [0.077, 0.237] | 0.137 [0.093, 0.197] | 0.000 [0.000, 0.016] | 1.000 [0.984, 1.000] |
| `never_use_evidence` | `phase4` | 0.019 [0.008, 0.044] | 0.152 [0.113, 0.200] | 0.004 [0.001, 0.014] | 0.996 [0.986, 0.999] |
| `rule_tuple_guard` | `camel` | 0.000 [0.000, 0.138] | 0.000 [0.000, 0.114] | 0.222 [0.132, 0.349] | 0.778 [0.651, 0.868] |
| `rule_tuple_guard` | `ipiguard` | 0.250 [0.164, 0.361] | 0.065 [0.037, 0.113] | 0.517 [0.454, 0.579] | 0.483 [0.421, 0.546] |
| `rule_tuple_guard` | `phase4` | 0.061 [0.038, 0.096] | 0.129 [0.094, 0.175] | 0.280 [0.244, 0.320] | 0.720 [0.680, 0.756] |
| `rule_tuple_guard_no_provenance` | `camel` | 0.500 [0.314, 0.686] | 0.000 [0.000, 0.114] | 0.000 [0.000, 0.066] | 1.000 [0.934, 1.000] |
| `rule_tuple_guard_no_provenance` | `ipiguard` | 0.250 [0.164, 0.361] | 0.065 [0.037, 0.113] | 0.517 [0.454, 0.579] | 0.483 [0.421, 0.546] |
| `rule_tuple_guard_no_provenance` | `phase4` | 0.061 [0.038, 0.096] | 0.129 [0.094, 0.175] | 0.280 [0.244, 0.320] | 0.720 [0.680, 0.756] |

## Human-Audited Subset

| Method | Rows | Unsafe Pre-Allow | Safe False Deny | Coverage |
|---|---:|---:|---:|---:|
| `always_use_evidence` | 222 | 0.000 [0.000, 0.040] | 0.023 [0.008, 0.066] | 0.108 [0.074, 0.156] |
| `control_provenance_minimal_check` | 222 | 0.065 [0.030, 0.134] | 0.062 [0.032, 0.118] | 0.644 [0.579, 0.704] |
| `effect_binding_guard_full` | 222 | 0.032 [0.011, 0.091] | 0.047 [0.021, 0.098] | 0.896 [0.849, 0.930] |
| `evidence_gated_selective_guard` | 222 | 0.140 [0.084, 0.225] | 0.047 [0.021, 0.098] | 0.923 [0.881, 0.952] |
| `local_qwen_tuple_guard` | 222 | 0.258 [0.180, 0.355] | 0.070 [0.037, 0.127] | 0.941 [0.902, 0.965] |
| `multi_view_disagreement_guard` | 222 | 0.161 [0.100, 0.249] | 0.085 [0.048, 0.146] | 0.995 [0.975, 0.999] |
| `never_use_evidence` | 222 | 0.161 [0.100, 0.249] | 0.085 [0.048, 0.146] | 0.995 [0.975, 0.999] |
| `rule_tuple_guard` | 222 | 0.065 [0.030, 0.134] | 0.062 [0.032, 0.118] | 0.644 [0.579, 0.704] |
| `rule_tuple_guard_no_provenance` | 222 | 0.194 [0.126, 0.285] | 0.062 [0.032, 0.118] | 0.698 [0.635, 0.755] |

## Evidence-Origin Stratification

| Method | Evidence Origin | Unsafe Pre-Allow | Safe False Deny | Coverage |
|---|---|---:|---:|---:|---:|
| `always_use_evidence` | `actual_saved_envdiff` | 0.000 [0.000, 0.138] | 0.625 [0.427, 0.788] | 0.875 [0.753, 0.941] |
| `always_use_evidence` | `counterfactual_simulated_evidence` | 0.021 [0.004, 0.109] | 0.000 [0.000, 0.074] | 0.750 [0.655, 0.826] |
| `always_use_evidence` | `no_execution_evidence` | 0.000 [0.000, 0.013] | 0.000 [0.000, 0.010] | 0.000 [0.000, 0.006] |
| `evidence_gated_selective_guard` | `actual_saved_envdiff` | 0.000 [0.000, 0.138] | 0.000 [0.000, 0.138] | 1.000 [0.926, 1.000] |
| `evidence_gated_selective_guard` | `counterfactual_simulated_evidence` | 0.083 [0.033, 0.196] | 0.000 [0.000, 0.074] | 1.000 [0.962, 1.000] |
| `evidence_gated_selective_guard` | `no_execution_evidence` | 0.066 [0.043, 0.101] | 0.077 [0.054, 0.108] | 0.909 [0.884, 0.928] |
| `effect_binding_guard_full` | `actual_saved_envdiff` | 0.000 [0.000, 0.138] | 0.000 [0.000, 0.138] | 1.000 [0.926, 1.000] |
| `effect_binding_guard_full` | `counterfactual_simulated_evidence` | 0.083 [0.033, 0.196] | 0.000 [0.000, 0.074] | 1.000 [0.962, 1.000] |
| `effect_binding_guard_full` | `no_execution_evidence` | 0.031 [0.017, 0.058] | 0.077 [0.054, 0.108] | 0.900 [0.875, 0.920] |

## Targeted Diagnostics

- Full guard pair resource sensitivity: `0.853 [0.795, 0.906]`.
- Full guard pair authorization sensitivity: `0.905 [0.867, 0.939]`.
- Full guard pair provenance sensitivity: `1.000 [1.000, 1.000]`.
- Multi-view high-disagreement error: `0.465 [0.325, 0.611]`; low-disagreement error: `0.092 [0.074, 0.115]`.
- Evidence-gated coverage: `0.925 [0.904, 0.941]`; unsafe pre-allow: `0.064 [0.043, 0.094]`.
- CaMeL provenance-check unsafe pre-allow: `0.000 [0.000, 0.138]`; safe false deny: `0.000 [0.000, 0.114]`.
- Pairwise direct relation accuracy: `0.8666666666666667`; independent x->y relation accuracy: `0.8619883040935673`.
- Pairwise-vs-independent group-paired delta: `{'rate': 0.02318840579710145, 'ci_low': 0.005676328502415459, 'ci_high': 0.04315619967793881, 'n_groups': 30}`.
- Safety-first selected validation unsafe pre-allow: `0.08108108108108109`; coverage: `1.0`.
- Calibration split independent-group counts: `{'train': 17, 'validation': 6, 'test': 7}`.
- Split source-row counts: `{'train': {'phase4': 264, 'ipiguard': 120, 'camel': 45}, 'validation': {'phase4': 110, 'ipiguard': 50, 'camel': 9}, 'test': {'phase4': 154, 'ipiguard': 70}}`; CaMeL has no hashed test group and is reported separately by source/provenance stress.
- Full-vs-IPIGuard-local-Qwen unsafe-pre-allow paired delta: `{'rate': -0.20833333333333334, 'ci_low': -0.2916666666666667, 'ci_high': -0.13888888888888887, 'n_groups': 24}`.

## Input-Field Leakage Audit

- Labels are physically separated under `labels`; deployable guards receive only `deployable_input`.
- Phase 4/IPIGuard shared anchors use the same normalized split group.
- IPIGuard input uses saved label-hidden parsed DAGs, not construction-time effect signatures.
- Actual saved evidence, simulated evidence, and no-evidence rows are reported separately.

## Feasibility Questions

- **Q1**: On held-out test groups, full tuple guard unsafe pre-allow=0.05102040816326531, safe false deny=0.047619047619047616, coverage=0.9553571428571429.
- **Q2**: High-disagreement error=0.46511627906976744; low-disagreement error=0.09242618741976893.
- **Q3**: Evidence-gated coverage=0.9245742092457421 and unsafe pre-allow=0.06388888888888888; evidence availability remains stratified.
- **Q4**: CaMeL provenance-check unsafe pre-allow=0.0, safe false deny=0.0.
- **Q5**: Pairwise relation accuracy=0.8666666666666667; independent x->y relation accuracy=0.8619883040935673.
- **Q6**: E48 capability rows are reported beside E47 custom-stress checkpoint/component rows; scopes are not averaged.
- **Q7**: Remaining bottlenecks are non-oracle resource binding, evidence availability, authorization semantics, and coverage-preserving abstention.

## Acceptance Gates

- `unified_dataset_822_rows`: `True`
- `deployable_input_no_oracle_leakage`: `True`
- `deployable_input_no_string_marker_leakage`: `True`
- `minimum_guards_complete`: `True`
- `local_qwen_full_822_and_parse_valid_ge_98pct`: `True`
- `pairwise_complete`: `True`
- `safety_first_calibration_gate`: `True`
- `camel_control_dependency_fixed`: `True`
- `camel_safe_false_deny_le_05`: `True`
- `full_coverage_ge_05`: `True`
- `full_test_unsafe_pre_allow_le_10pct`: `True`
- `full_test_coverage_ge_05`: `True`
- `pairwise_improves_relation`: `True`
- `full_unsafe_below_ipiguard_local_semantic`: `True`
- `full_unsafe_significantly_below_ipiguard_local_semantic`: `True`
- `full_coverage_above_deterministic_semantic`: `True`
- `resource_sensitivity_above_ipiguard_local_semantic`: `True`
- `at_least_two_capabilities_improved`: `True`

## Claim Boundary

- E48 is a simulated/custom-stress feasibility study, not a production permission system.
- Pairwise learning is a relation diagnostic, not a single-case deployable guard.
- Oracle/upper-bound and original checkpoint/component scopes remain separate.
- No real side effects or external APIs are used.
