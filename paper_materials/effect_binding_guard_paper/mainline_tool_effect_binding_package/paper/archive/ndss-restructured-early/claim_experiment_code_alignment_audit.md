# Claim-Experiment-Code Alignment Audit

Date: 2026-06-26

Scope: `ndss_candidate_restructured/main.tex`, `sections/`, `tables/`, and `appendix/`.

Audit rule: every verifiable paper claim should trace to (1) a paper location, (2) a result/table artifact, and, where applicable, (3) generating code and a test or reproduction entry. This audit does not edit the paper body or experiment code.

## Executive Verdict

- Main E55-v2, original E55, E55 human-corrected sensitivity, E56, and E57-v2/human-audit claims are aligned with current result artifacts and have live-passing E55/E56/E57 tests in this package.
- E48/E50 numeric claims align with their JSON result artifacts, but the current consolidated package layout prevents direct E48/E50 tests or direct `build_unified_dataset()` reproduction without path adaptation. These are marked `结果可追溯但代码链不足`, not numeric errors.
- E47/custom-stress capability claims align with copied tables and canonical result summaries; the code lineage exists under `tool_effect_fragmentation`, but this audit did not live-rerun the full E47 pipeline. These are also marked `结果可追溯但代码链不足`.
- High-risk version boundaries are mostly handled correctly: E55-v2 `0.880` is separated from original E55 `0.920`, E55-v2 FDeny `0.000` is separated from corrected sensitivity FDeny `0.017`, and E57-v2 deterministic agreement is separated from E57 human audit `54/60`.
- Remaining user-confirmation item: Table 5 uses original E55 strict ablations while the main result uses E55-v2. It is explicitly labeled, but canonical ablation policy remains open.

## Static Number Checks

| Check | Paper value | Source value | Verdict |
|---|---:|---:|---|
| E48 rows | 822 | `manifest.n_rows = 822` | OK |
| E48 pairs | 6,840 | `manifest.n_pairs = 6840` | OK |
| E48 full coverage | 0.917 | `754/822 = 0.9172749` | OK |
| E48 full UPA | 0.036 | `13/360 = 0.0361111` | OK |
| E48 full FDeny | 0.065 | `30/462 = 0.0649351` | OK |
| E48 held-out UPA / FDeny / coverage | 0.051 / 0.048 / 0.955 | `0.0510204 / 0.0476190 / 0.9553571` | OK |
| E50 source-balanced UPA / FDeny / coverage | 0.051 / 0.059 / 0.923 | means `0.0513514 / 0.0589474 / 0.9230769` | OK |
| E50 resource/auth rows / UPA / coverage | 240 / 0.383 / 0.921 | `240 / 46/120 / 221/240` | OK after semantic repair and rerun |
| E50 provenance rows / UPA / FDeny / coverage | 336 / 0.000 / 0.188 / 0.545 | `336 / 0/144 / 36/192 / 183/336` | OK |
| E55-v2 existing hard guard | UPA 0.043, FDeny 0.000, coverage 0.200, abstain 0.800 | `12/276`, `0/252`, `120/600`, `480/600` | OK |
| E55-v2 authz-aware guard | UPA 0.000, FDeny 0.000, coverage 0.880, abstain 0.120 | `0/276`, `0/252`, `528/600`, `72/600` | OK |
| Original E55 authz-aware guard | UPA 0.000, FDeny 0.000, coverage 0.920, abstain 0.080 | `0/324`, `0/228`, `552/600`, `48/600` | OK |
| Human-corrected sensitivity | UPA `0/320`, FDeny `4/230 = 0.017`, coverage `552/600 = 0.920` | exact source values | OK |
| Original E55 ablations | 0.333 / 0.148 / 0.148 / 0.211 | exact original E55 strict values | OK, but policy open |
| E55-v2 ablations note | 0.217 / 0.217 / 0.217 / 0.238 | exact E55-v2 strict values | OK |
| E57-v2 perturbation | UPA delta 0, coverage delta 0, changed decisions 0 | exact source values | OK |
| E57-v2 reference authorizer | decision/atom/resource agreement 1.000 | exact source values | OK |
| E57 human audit | decision agreement 54/60, all checks 46/60, corrections 6/13/10 | exact source values | OK |

## Claim-by-Claim Audit

| ID | Paper location | Claim summary | Source and key | Code/test chain | Status | Notes |
|---|---|---|---|---|---|---|
| C01 | `abstract.tex:2`; `introduction.tex:19`; `tool_effect_binding.tex` | Defines tool-effect binding as pre-commit binding to effect/resource/operation/authorization/provenance. | `method_materials/writing_package_e58/03_method_definition.md`; `08_claim_boundary.md` | E48 schema/row code: `code/src/experiments/effect_binding_guard/schema.py`; E55 atom schema: `e55_precommit_authz/schemas.py` | OK | Conceptual/method claim; no single metric expected. |
| C02 | `abstract.tex:4`; `counterfactual_framework.tex:19` | E48 has 822 rows and 6,840 pairwise relations. | `results/analysis/results/e48_tuple_guard_results.json`: `manifest.n_rows`, `manifest.n_pairs` | `dataset.py`, `run_e48.py`, `pairwise.py`; test intended: `test_effect_binding_guard_e48.py` | 结果可追溯但代码链不足 | JSON aligns; live test fails in consolidated layout because tests look under `tests/analysis/results/...`. |
| C03 | `abstract.tex:4`; `results.tex:13`; Table 2 | E48 hard guard has 0.917 coverage, 0.036 UPA, 0.065 FDeny. | `e48_tuple_guard_results.json`: `methods.effect_binding_guard_full.overall` | `run_e48.py`, `guards.py`, `metrics.py`; `test_effect_binding_guard_e48.py` | OK | Package paths were repaired; E48 tests and result-only rerun pass. Pairwise intervals now bootstrap `split_group_id`. |
| C04 | `results.tex:13`; Table 2 | Held-out E48 and source-balanced E50 metrics are 0.051/0.048/0.955 and 0.051/0.059/0.923. | `e48_tuple_guard_results.json`; `e50_hard_guard_robustness_results.json` | `run_e48.py`; `run_e50.py`; tests `test_effect_binding_guard_e48.py`, `test_effect_binding_guard_e50.py` | OK | Metrics align after live E48/E50 reruns. |
| C05 | `abstract.tex:4`; `results.tex:19`; Table 3 | E50 resource/auth stress exposes 0.383 UPA at 0.921 coverage. | `e50_hard_guard_robustness_results.json`: `resource_authorization_stress...overall` | `run_e50.py` functions `build_resource_authorization_stress`, `run_e50_variants`; `test_effect_binding_guard_e50.py` | OK after repair | The prior 0.617 value came from a semantically inconsistent construction. The repaired policy oracle, materialized aliases, and explicit commit denial yield 46/120 UPA. |
| C06 | `results.tex:19`; Table 3 | E50 provenance stress has 0.000 UPA, 0.188 FDeny, 0.545 coverage. | `e50_hard_guard_robustness_results.json`: `control_provenance_stress...overall` | `run_e50.py` functions `build_control_provenance_stress`, `run_e50_variants`; `test_effect_binding_guard_e50.py` | OK | Live rerun and package tests pass. |
| C07 | `table1_existing_methods.tex`; `results.tex:7` | E47/custom-stress methods are not just tool-name classifiers; TS-Guard, Safiron, Qwen metrics as shown. | `tool_effect_fragmentation_capability_matrix_phase6.json` | `tool_effect_fragmentation/run_tool_effect_fragmentation_phase4.py`; `phase4_inference.py`; `run_tool_effect_fragmentation_phase6.py`; tests under `test_tool_effect_fragmentation_*` | OK with claim boundary | Released checkpoints ran on E47 custom stress, not their original benchmarks. Audit status now distinguishes the sampled human audit from the construction-gated remainder. |
| C08 | `experimental_setup.tex:7`; `discussion.tex:13`; Table 1 caption | Released checkpoints are evaluated on custom stress, not original-paper reproduction. | `tables/tables/official_checkpoint_summary.md`; `method_materials/manifests/*toolsafe*`, `*safiron*` | `phase3_official_stress.py`; `phase4_inference.py`; `phase4_metrics.py` | OK | Wording is appropriately bounded. |
| C09 | `experimental_setup.tex:4`; `appendix/reproduction_notes.tex:10` | Package has 2,424 copied files, two missing expected historical dirs, no core-number issues. | `PACKAGE_SUMMARY.md`; `MISSING_FILES.md` | Package build scripts: `build_mainline_tool_effect_binding_package.py`, `build_e58_consolidated_package.py` | OK | Matches package metadata. |
| C10 | `experimental_setup.tex:13`; Table 3 | E50 resource/auth stress has 240 rows; provenance stress has 336 rows. | `e50_hard_guard_robustness_results.json`: `n_rows` fields | `run_e50.py` stress builders | 结果可追溯但代码链不足 | Source values align; live test not passing due package layout. |
| C11 | `abstract.tex:6`; `experimental_setup.tex:16`; Table 4 | E55-v2 is main pre-commit result over 600 rows and five domains. | `audit/analysis/results/e55_v2_precommit_authz_results_strict.json`: `dataset` | `e55_precommit_authz/run_e55.py`; `dataset_builder.py`; `tests/test_effect_binding_guard_e55_precommit_authz.py` | OK | E55/E56/E57 targeted tests passed. |
| C12 | `abstract.tex:6`; `results.tex:25`; Table 4 | E55-v2 existing hard guard: coverage 0.200, abstain 0.800, UPA 12/276 = 0.043. | `e55_v2_precommit_authz_results_strict.json`: `methods.existing_hard_effect_binding_guard.overall` | `run_e55.py`; `guards.py`; `metrics.py`; `test_effect_binding_guard_e55_precommit_authz.py` | OK | Exact. |
| C13 | `abstract.tex:6`; `results.tex:25`; Table 4 | E55-v2 authz-aware guard: coverage 528/600 = 0.880, abstain 72/600 = 0.120, UPA 0/276, FDeny 0/252. | `e55_v2_precommit_authz_results_strict.json`: `methods.authz_aware_effect_binding_guard.overall` | `run_e55.py`; `atom_expansion.py`; `authz_model.py`; `guards.py`; `metrics.py`; tests E55 | OK | Exact. |
| C14 | `results.tex:25`; Table 4 | Original E55 strict has 0.920 coverage and zero UPA/FDeny. | `results/analysis/results/e55_precommit_authz_results_strict.json` | `e56_audit.py` wrote original strict outputs; tests E55/E56 | OK | Correctly labeled as original E55, not E55-v2. |
| C15 | `abstract.tex:6`; `results.tex:25`; Table 4 | Human-corrected sensitivity preserves zero UPA and introduces 4/230 = 0.017 FDeny. | `results/analysis/results/e55_human_corrected_sensitivity.json`: `full_600_minimal_correction...authz_aware_effect_binding_guard` | `e55_human_corrected_sensitivity.py`; E57 human-audited packet | OK | Exact and safely worded. |
| C16 | `results.tex:31`; Table 5 | Original E55 ablations: no multi-resource 0.333 UPA, no operation 0.148 UPA, no provenance 0.148 UPA, no alias 0.211 FDeny. | `results/analysis/results/e55_precommit_authz_results_strict.json`: original E55 ablation method metrics | `e56_audit.py`; `run_e55.py`; E55 tests | 需用户确认 | Numbers are exact and table says original E55; unresolved policy is whether to switch to E55-v2 ablations. |
| C17 | `appendix/additional_tables.tex:30-33` | E55-v2 ablations differ: 0.217/0.217/0.217/0.238. | `audit/analysis/results/e55_v2_precommit_authz_results_strict.json` | `run_e55.py --corrected-v2`; E55 tests | OK | Correctly used as a version-policy warning. |
| C18 | `atoms.tex:5-44`; `authz_prototype.tex:7-14` | Tool call expands into atoms; ALLOW/DENY/ABSTAIN rule uses authorization context and provenance. | `paper_drafts/e55_precommit_authz/e55_authorization_model.md`; E55 result artifacts | `atom_expansion.py`; `authz_model.py`; `guards.py`; `schemas.py`; tests E55 | OK | Code implements the stated abstraction. |
| C19 | `counterfactual_framework.tex:21-25`; `experimental_setup.tex:18-19` | UPA/FDeny/Coverage definitions are as stated. | E48/E55 metrics JSONs | `effect_binding_guard/metrics.py`; `e55_precommit_authz/metrics.py` | OK | Code defines UPA as ALLOW on unsafe/DENY rows, FDeny as DENY on safe/ALLOW rows, coverage as non-abstain. |
| C20 | `table6_audit_validity.tex:10`; `appendix/audit_details.tex:3-4` | E55-v2 leakage audit is leakage-free. | `audit/analysis/results/e55_v2_precommit_authz_leakage_audit.json`: `leakage_free=true` | `leakage_audit.py`; `run_e55.py` leakage gate | OK | Exact. |
| C21 | `table6_audit_validity.tex:11`; `results.tex:37` | E55 decision-path audit passed. | `audit/analysis/results/e55_decision_path_audit.json`; `audit/analysis/results/e56_final_report.json` | `e56_audit.py`: `decision_path_audit`; tests E56 | OK | Exact; E55/E56/E57 tests passed. |
| C22 | `abstract.tex:6`; `table6_audit_validity.tex:12` | E56 strict label-hidden replay passed. | `audit/analysis/results/e56_final_report.json`: `strict_mode_passed=true`, `sanity.label_hidden_replay.metrics_equal=true` | `e56_audit.py`; `test_effect_binding_guard_e56_audit.py` | OK | Exact; targeted tests passed. |
| C23 | `results.tex:37`; Table 6 | E57-v2 perturbation has UPA delta 0, coverage delta 0, changed decisions 0. | `audit/analysis/results/e57_v2_validity_checks_report.json`: `perturbation` | `e57_validity_checks.py`; tests E57 | OK | Exact; targeted tests passed. |
| C24 | `results.tex:37`; Table 6 | E57-v2 reference authorizer has 1.000 decision, atom-count, atom-resource-set agreement. | `e57_v2_validity_checks_report.json`; `e57_v2_reference_authorizer_agreement.json` | `reference_authorizer.py`; `e57_validity_checks.py`; tests E57 | OK | Exact. |
| C25 | `results.tex:37`; Table 6; appendix | E57 human audit: 54/60 decision agreement, 46/60 all checks true, 6/13/10 corrections. | `audit/analysis/results/e57_human_audit_validation.json` | `e55_human_corrected_sensitivity.py`; human audited packet artifact | OK | Correctly separated from deterministic agreement. |
| C26 | `failure_analysis.tex:13`; `limitations.tex:12-13` | Human audit found corrections and does not perfectly confirm all labels/atoms. | `e57_human_audit_validation.json`; `e55_human_corrected_sensitivity.json` | sensitivity script and audit artifacts | OK | Safe wording. |
| C27 | `discussion.tex:10`; `abstract.tex:6` | E55-v2 improvement is meaningful because coverage rises while UPA falls under strict labels. | E55-v2 strict result | E55 code/tests | OK | Supported under local controlled contract only; boundary is present. |
| C28 | `limitations.tex:3-16`; `introduction.tex:27`; `discussion.tex:13` | No production safety, no complete permission system, no original benchmark reproduction, no deployment generalization. | Claim-boundary files and limitation text | N/A | OK | Overclaim scan found these terms only in negated/boundary contexts. |
| C29 | `related_work.tex`; `references.bib` | Related-work positioning for ToolEmu, AgentDojo, ToolSafe, Safiron, CaMeL, IPIGuard, Progent, MiniScope. | `references.bib`; `paper_rewriting_output/reference_materials/source_index.md` | N/A | OK | Bibliographic, not experiment-code claim. |
| C30 | `ethics_artifact_scope.tex` | Experiments avoid real external side effects. | E55 local mock contract; reproduction notes; claim-boundary files | `mock_tools.py`; `dataset_builder.py`; E55 tests | OK | Consistent with deterministic local mock tools. |

## High-Risk Boundary Checks

| Boundary | Result |
|---|---|
| E55-v2 `0.880` vs original E55 `0.920` | Correctly separated in Abstract, Results, Table 4, and appendix. |
| E55-v2 FDeny `0.000` vs corrected sensitivity FDeny `0.017` | Correctly separated in Abstract, Results, Table 4. |
| Table 5 original E55 ablations vs E55-v2 ablations | Explicitly labeled, but still requires user policy confirmation before final submission. |
| E57-v2 reference-authorizer `1.000` vs E57 human audit `54/60` | Correctly separated in Experimental Setup, Results, Table 6, appendix. |
| Custom stress vs original benchmark reproduction | Correctly bounded in Table 1 caption, Experimental Setup, Discussion, Limitations. |
| Production-safety / complete-permission overclaim | No positive overclaim found; occurrences are negated or boundary statements. |

## Test and Reproduction Checks

Commands run:

```bash
cd code
PYTHONPATH=. python -m pytest \
  ../tests/tests/test_effect_binding_guard_e48.py \
  ../tests/tests/test_effect_binding_guard_e50.py \
  ../tests/tests/test_effect_binding_guard_e55_precommit_authz.py \
  ../tests/tests/test_effect_binding_guard_e56_audit.py \
  ../tests/tests/test_effect_binding_guard_e57_validity.py -q
```

Result: `19 failed, 29 passed`.

Interpretation: all failures are in E48/E50 tests and share the same package-layout failure. The tests set `ROOT = Path(__file__).resolve().parents[1]`, which resolves to the package `tests/` directory; they then look for `tests/analysis/results/tool_effect_fragmentation_capability_matrix_phase6.json`. In this consolidated package the file exists at `results/analysis/results/tool_effect_fragmentation_capability_matrix_phase6.json`, not under `tests/analysis/results/`. This is a current-package reproduction-layout issue, not a mismatch in paper numbers.

E55/E56/E57 targeted command:

```bash
cd code
PYTHONPATH=. python -m pytest \
  ../tests/tests/test_effect_binding_guard_e55_precommit_authz.py \
  ../tests/tests/test_effect_binding_guard_e56_audit.py \
  ../tests/tests/test_effect_binding_guard_e57_validity.py -q
```

Result: `28 passed`.

Direct E48/E50 code import check from package root also fails without layout adaptation because `build_unified_dataset(Path("."))` expects `analysis/results/...`, while the consolidated package stores result artifacts under `results/analysis/results/...`.

## Required Follow-Up

1. Decide whether Table 5 should remain original E55 strict ablations or be replaced by E55-v2 ablations.
2. Add a small reproduction shim or documented command for E48/E50 in the consolidated package layout, or run E48/E50 from the original project root where `analysis/results/...` exists.
3. If final paper wants stronger code-chain evidence for E47/custom-stress methods, rerun or at least smoke-test `tool_effect_fragmentation` phase 4/6 scripts in the original layout.
4. Keep the current claim boundary language; it is doing useful work and prevents the main overclaims.
