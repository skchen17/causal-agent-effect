#!/usr/bin/env python3
"""Build and scan the anonymous result-reproduction package."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
ROOT = PAPER.parents[1]
OUTPUT = HERE / "anonymous_package"
ARCHIVE = HERE / "anonymous_effect_binding_artifact.tar.gz"

TEXT_SUFFIXES = {
    ".bib", ".csv", ".json", ".jsonl", ".md", ".py", ".sh", ".sty", ".tex", ".txt"
}
FORBIDDEN = {
    "local_workspace_path": re.compile(r"/(?:data/CSK|home/user)(?:/|\b)"),
    "credential": re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    "private_project_label": re.compile(r"causal-agent-safety-research", re.I),
    "todo_marker": re.compile(r"\b(?:TODO|FIXME)\b"),
    "windows_user_path": re.compile(r"[A-Za-z]:\\Users\\"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest_module():
    path = HERE / "build_manifest.py"
    spec = importlib.util.spec_from_file_location("current_artifact_manifest", path)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load artifact manifest builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def paper_sources() -> list[Path]:
    paths = [
        PAPER / "main.tex",
        PAPER / "main.pdf",
        PAPER / "references.bib",
        PAPER / "usenix.sty",
        PAPER / "claim_to_source.md",
        PAPER / "writing_report.md",
        PAPER / "submission_readiness_report.md",
        PAPER / "open_questions_for_user.md",
        PAPER / "page_budget_report.json",
        PAPER / "page_budget_report.md",
        PAPER / "submission_source_audit.json",
        PAPER / "submission_source_audit.md",
        PAPER / "reference_verification_report.json",
        PAPER / "reference_verification_report.md",
        ROOT / "EXPERIMENT_NOTES.md",
    ]
    for directory in ("sections", "tables", "figures", "appendix"):
        paths.extend(sorted((PAPER / directory).glob("*.tex")))
    paths.extend(
        [
            PAPER / "reproduction/reproduce_main_claims.py",
            PAPER / "reproduction/export_final_case_outcomes.py",
            PAPER / "reproduction/render_final_tables.py",
            PAPER / "reproduction/generate_final_result_section.py",
            PAPER / "reproduction/generate_final_readiness_and_review.py",
            PAPER / "reproduction/extract_sanitized_fixed_support.py",
            PAPER / "reproduction/audit_references.py",
            PAPER / "reproduction/check_page_budget.py",
            PAPER / "reproduction/sanitized_fixed_support.json",
            PAPER / "reproduction/main_claims.json",
            PAPER / "reproduction/main_claims.csv",
            PAPER / "reproduction/main_claims.md",
            PAPER / "reproduction/reproduction_status.json",
            HERE / "README.md",
            HERE / "environment.lock",
        ]
    )
    optional_final_reports = [
        PAPER / "final_experiment_completion_report.md",
        PAPER / "simulated_review_round2.md",
    ]
    paths.extend(path for path in optional_final_reports if path.is_file())
    return paths


def fixed_support_files() -> list[Path]:
    relative_paths = [
        "experiments/human-authority-and-causal-validation/evaluation/agentdojo-tool-effect-prevalence/protocol.json",
        "experiments/human-authority-and-causal-validation/results/agentdojo-tool-effect-prevalence/official-call-effects.jsonl",
        "experiments/human-authority-and-causal-validation/results/agentdojo-tool-effect-prevalence/compound-effect-witnesses.jsonl",
        "experiments/human-authority-and-causal-validation/results/agentdojo-tool-effect-prevalence/agentdojo-tool-effect-prevalence-report.json",
        "experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation/finite-contexts.jsonl",
        "experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation/authorization-separating-witnesses.jsonl",
        "experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation/representation-summary.csv",
        "experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation/finite-domain-validation-report.json",
        "experiments/human-authority-and-causal-validation/evaluation/heldout-toolsandbox-effect-binding-validation/preregistration.json",
        "experiments/human-authority-and-causal-validation/evaluation/heldout-toolsandbox-effect-binding-validation/heldout-contexts.jsonl",
        "experiments/human-authority-and-causal-validation/results/heldout-toolsandbox-effect-binding-validation/authorization-separating-witnesses.jsonl",
        "experiments/human-authority-and-causal-validation/results/heldout-toolsandbox-effect-binding-validation/representation-summary.csv",
        "experiments/human-authority-and-causal-validation/results/heldout-toolsandbox-effect-binding-validation/heldout-validation-report.json",
        "experiments/human-authority-and-causal-validation/evaluation/state-aware-authority-interface/protocol-lock.json",
        "experiments/human-authority-and-causal-validation/evaluation/state-aware-authority-interface/request-adapter-contract.json",
        "experiments/human-authority-and-causal-validation/evaluation/state-aware-authority-interface/view-contract.json",
        "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface/report.json",
        "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface/metrics.csv",
        "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface/collision-metrics.csv",
        "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface/representation-rows.jsonl",
        "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface/source-executions.jsonl",
        "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface/state-dependent-collisions.json",
        "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface/state-aware-failure-taxonomy.jsonl",
        "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface/reproduction-status.json",
        "experiments/human-authority-and-causal-validation/results/executable-failure-certificates/report.json",
        "experiments/human-authority-and-causal-validation/results/executable-failure-certificates/failure-certificates.jsonl",
        "experiments/human-authority-and-causal-validation/results/executable-failure-certificates/failure-certificates.csv",
        "experiments/human-authority-and-causal-validation/results/executable-failure-certificates/failure-certificates.md",
        "experiments/human-authority-and-causal-validation/evaluation/third-party-authorization-interface-validation/source_manifest.json",
        "experiments/human-authority-and-causal-validation/evaluation/third-party-authorization-interface-validation/protocol_manifest.json",
        "experiments/human-authority-and-causal-validation/evaluation/third-party-authorization-interface-validation/descriptors_v1.json",
        "experiments/human-authority-and-causal-validation/evaluation/third-party-authorization-interface-validation/authority_manifest.json",
        "experiments/human-authority-and-causal-validation/evaluation/third-party-authorization-interface-validation/registration_contexts.jsonl",
        "experiments/human-authority-and-causal-validation/evaluation/third-party-authorization-interface-validation/post_freeze_contexts.jsonl",
        "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation/third_party_validation_report.json",
        "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation/registration_source_executions.jsonl",
        "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation/post_freeze_source_executions.jsonl",
        "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation/post_freeze_authorization_rows.jsonl",
        "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation/representation_collision_metrics.csv",
        "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation/authorization_metrics.csv",
        "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation/registration_failures.jsonl",
        "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation/post_freeze_descriptor_failures.jsonl",
        "experiments/human-authority-and-causal-validation/evaluation/authorization-interface-economy/protocol_manifest.json",
        "experiments/human-authority-and-causal-validation/results/authorization-interface-economy/interface_economy_metrics.json",
        "experiments/human-authority-and-causal-validation/results/authorization-interface-economy/interface_economy_report.json",
        "experiments/human-authority-and-causal-validation/results/authorization-interface-economy/interface_economy_report.md",
        "experiments/human-authority-and-causal-validation/results/authorization-interface-economy/interface_economy_summary.csv",
        "experiments/human-authority-and-causal-validation/evaluation/native-delta-mechanical-validation/protocol_manifest.json",
        "experiments/human-authority-and-causal-validation/evaluation/native-delta-mechanical-validation/mutation_manifest.json",
        "experiments/human-authority-and-causal-validation/results/native-delta-mechanical-validation/native_delta_validation_report.json",
        "experiments/human-authority-and-causal-validation/results/native-delta-mechanical-validation/native_delta_validation_report.md",
        "experiments/human-authority-and-causal-validation/results/native-delta-mechanical-validation/native_decision_rows.jsonl",
        "experiments/human-authority-and-causal-validation/results/native-delta-mechanical-validation/mutant_results.jsonl",
        "experiments/human-authority-and-causal-validation/results/native-delta-mechanical-validation/mutation_summary.csv",
        "experiments/human-authority-and-causal-validation/results/native-delta-mechanical-validation/mutation_failure_certificates.jsonl",
        "experiments/human-authority-and-causal-validation/evaluation/small-typed-effect-runtime-case-study/protocol_manifest.json",
        "experiments/human-authority-and-causal-validation/evaluation/small-typed-effect-runtime-case-study/tasks.jsonl",
        "experiments/human-authority-and-causal-validation/results/small-typed-effect-runtime-case-study/runtime_case_study_report.json",
        "experiments/human-authority-and-causal-validation/results/small-typed-effect-runtime-case-study/runtime_trajectories.jsonl",
        "experiments/binding-failure-and-granularity/results/hard-guard-granularity-stress/same-core-comparisons.json",
        "experiments/binding-failure-and-granularity/results/hard-guard-granularity-stress/reproduced-e48-main-table.json",
        "experiments/binding-failure-and-granularity/results/hard-guard-granularity-stress/resource-authorization-stress.json",
        "experiments/binding-failure-and-granularity/results/hard-guard-granularity-stress/control-provenance-stress.json",
        "experiments/binding-failure-and-granularity/results/authorization-separating-collision-audit/collision-audit-report.json",
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/registration_sufficiency_counterfactual_rows_v2.jsonl",
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/registration_sufficiency_field_summary_v2.csv",
        "experiments/intent-bound-runtime-guard/evaluation/counterfactual-atom-envelope-guard/c1f_frozen_candidate_2026-08-08.json",
        "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl",
        "experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/registered_relation_catalog.json",
        "experiments/security-analysis-ablation-and-overhead/evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json",
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/qwen32_matched_protocol.json",
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/deepseek_same_model_strong_baselines.json",
        "experiments/long-horizon-transfer/results/long-horizon-cross-environment-transfer/agentlab-saved-transfer-no-guard-results.json",
        "experiments/long-horizon-transfer/results/long-horizon-cross-environment-transfer/agentlab-saved-transfer-e77-results.json",
        "experiments/adaptive-injection-benchmark/evaluation/usenix-heldout-public-families/protocol.json",
        "experiments/adaptive-injection-benchmark/evaluation/usenix-heldout-public-families/locked_manifest.jsonl",
        "experiments/adaptive-injection-benchmark/evaluation/bounded-public-family-search/preregistration.json",
        "experiments/adaptive-injection-benchmark/evaluation/bounded-public-family-search/locked-case-manifest.jsonl",
        "experiments/adaptive-injection-benchmark/results/bounded-public-family-search/predictions.jsonl",
        "evaluation/e79_long_horizon/agentlab_saved_attack_manifest.json",
        "evaluation/e79_long_horizon/agentlab_saved_attack_cases.jsonl",
        "experiments/security-analysis-ablation-and-overhead/evaluation/representation-closed-loop-attribution/selection-manifest.json",
        "experiments/security-analysis-ablation-and-overhead/evaluation/representation-closed-loop-attribution/selected-cases.jsonl",
        "experiments/security-analysis-ablation-and-overhead/evaluation/representation-closed-loop-attribution/raw-field-attribution-protocol.json",
        "code/shadow_atom_envelope_c1f/src/experiments/effect_binding_guard/e77_effect_diff_runtime_guard/atom_envelope_policy.py",
        "code/shadow_atom_envelope_c1f/src/experiments/effect_binding_guard/e77_effect_diff_runtime_guard/agentdojo_e77_runtime_patch.py",
        "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard/deepseek-confirmation-c1f-attack-r1/banking/runtime_audit.jsonl",
        "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard/deepseek-confirmation-c1f-attack-r1/slack/runtime_audit.jsonl",
        "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard/deepseek-confirmation-c1f-attack-r1/travel/runtime_audit.jsonl",
        "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard/deepseek-confirmation-c1f-attack-r1/workspace/runtime_audit.jsonl",
        "shared/compatibility/scripts/run_agentdojo_tool_effect_prevalence.py",
        "shared/compatibility/scripts/run_finite_domain_effect_binding_validation.py",
        "shared/compatibility/scripts/run_toolsandbox_heldout_validation.py",
        "shared/compatibility/scripts/state_aware_authority_baseline.py",
        "shared/compatibility/scripts/independent_authority_benchmark/state_aware_view.py",
        "shared/compatibility/scripts/independent_authority_benchmark/state_aware_request_adapter.py",
        "shared/compatibility/scripts/extract_executable_failure_certificates.py",
        "shared/compatibility/scripts/run_third_party_authorization_interface_validation.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/__init__.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/mcp_client.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/sources.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/scenario_data.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/registration_generator.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/evaluation_generator.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/source_oracle.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/descriptor_compiler.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/policy.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/representations.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/state_aware_adapter.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/native_delta_oracle.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/native_policy.py",
        "shared/compatibility/scripts/third_party_authorization_interface_validation/descriptor_mutations.py",
        "shared/compatibility/scripts/run_authorization_interface_economy_audit.py",
        "shared/compatibility/scripts/run_native_delta_mechanical_validation.py",
        "shared/compatibility/scripts/run_small_typed_effect_runtime_case_study.py",
        "shared/compatibility/scripts/small_typed_effect_runtime_case_study/__init__.py",
        "shared/compatibility/scripts/small_typed_effect_runtime_case_study/cases.py",
        "shared/compatibility/scripts/small_typed_effect_runtime_case_study/local_llm.py",
        "shared/compatibility/scripts/small_typed_effect_runtime_case_study/runtime_engine.py",
        "experiments/security-analysis-ablation-and-overhead/source/refinement-monotonicity-check/run_refinement_monotonicity_check.py",
        "experiments/security-analysis-ablation-and-overhead/results/refinement-monotonicity-check/refinement-monotonicity-report.json",
        "experiments/intent-bound-runtime-guard/scripts/counterfactual-atom-envelope-guard/run_registration_sufficiency_audit_v2.py",
        "experiments/intent-bound-runtime-guard/scripts/counterfactual-atom-envelope-guard/reproduce_deepseek_guard_repair.py",
        "shared/compatibility/scripts/run_c1f_closed_loop_four_view_extension.py",
        "shared/compatibility/scripts/run_c1f_raw_field_attribution.py",
        "code/shadow_atom_envelope_c1f/src/experiments/effect_binding_guard/representation_closed_loop_attribution/agentdojo_raw_field_c1f_patch.py",
        "shared/compatibility/code/shadow_atom_envelope_c1f/src/experiments/effect_binding_guard/representation_closed_loop_attribution/agentdojo_effect_only_c1f_patch.py",
        "shared/compatibility/code/shadow_atom_envelope_c1f/src/experiments/effect_binding_guard/representation_closed_loop_attribution/agentdojo_whole_call_c1f_patch.py",
        "shared/compatibility/tests/tests/test_agentdojo_tool_effect_prevalence.py",
        "shared/compatibility/tests/tests/test_finite_domain_effect_binding_validation.py",
        "shared/compatibility/tests/tests/test_toolsandbox_heldout_validation.py",
        "shared/compatibility/tests/tests/test_state_aware_authority_baseline.py",
        "shared/compatibility/tests/tests/test_executable_failure_certificates.py",
        "shared/compatibility/tests/tests/test_third_party_authorization_interface_validation.py",
        "shared/compatibility/tests/tests/test_authorization_interface_economy.py",
        "shared/compatibility/tests/tests/test_native_delta_mechanical_validation.py",
        "shared/compatibility/tests/tests/test_small_typed_effect_runtime_case_study.py",
        "shared/compatibility/tests/tests/test_registration_sufficiency_v2_artifact.py",
        "shared/compatibility/tests/tests/test_c1f_closed_loop_four_view_extension.py",
        "shared/compatibility/tests/tests/test_c1f_raw_field_attribution.py",
        "shared/compatibility/tests/tests/test_counterfactual_atom_envelope_policy.py",
        "shared/compatibility/tests/tests/test_counterfactual_atom_envelope_structured_provenance.py",
        "shared/compatibility/tests/tests/test_usenix_main_reproduction.py",
        "shared/compatibility/tests/tests/test_render_usenix_final_tables.py",
        "shared/compatibility/tests/tests/test_generate_final_readiness_and_review.py",
    ]
    return [ROOT / path for path in relative_paths]


def final_row_files() -> list[Path]:
    paths = [
        PAPER / "reproduction/final_case_outcomes.jsonl",
        PAPER / "reproduction/final_case_outcomes.csv",
        PAPER / "reproduction/final_case_outcomes_summary.json",
        PAPER / "reproduction/generated_final_validation_manifest.json",
    ]
    bounded = ROOT / (
        "experiments/adaptive-injection-benchmark/results/"
        "bounded-public-family-search-current-c1f/predictions.jsonl"
    )
    if bounded.is_file():
        paths.append(bounded)
    return paths


def relative(path: Path) -> Path:
    return path.resolve().relative_to(ROOT.resolve())


def copy_one(source: Path, staging: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(relative(source))
    destination = staging / relative(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def scan(staging: Path) -> list[dict[str, str]]:
    violations = []
    for path in sorted(item for item in staging.rglob("*") if item.is_file()):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        value = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in FORBIDDEN.items():
            if pattern.search(value):
                violations.append({"path": str(path.relative_to(staging)), "pattern": name})
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()

    module = load_manifest_module()
    readiness = module.build()
    if not args.allow_pending and not readiness["release_gates"]["paper_evidence_gates_passed"]:
        raise RuntimeError("paper evidence is incomplete; use --allow-pending only for a preview package")

    evidence = []
    for row in readiness["required_evidence"].values():
        path = ROOT / row["path"]
        if path.exists():
            evidence.append(path)
        elif not args.allow_pending:
            raise FileNotFoundError(row["path"])

    with tempfile.TemporaryDirectory(prefix="effect-binding-anon-") as temporary:
        staging = Path(temporary) / "effect-binding-artifact"
        support = fixed_support_files()
        for path in support:
            if not path.is_file():
                raise FileNotFoundError(relative(path))
        final_rows = [path for path in final_row_files() if path.is_file()]
        if not args.allow_pending and len(final_rows) != len(final_row_files()):
            raise RuntimeError("final row-level outcome exports are incomplete")
        for path in [*paper_sources(), *evidence, *support, *final_rows]:
            copy_one(path, staging)
        stable_entry = staging / "scripts/reproduce_usenix_main.py"
        stable_entry.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "scripts/reproduce_usenix_main.py", stable_entry)

        rows = [
            {
                "path": str(path.relative_to(staging)),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(item for item in staging.rglob("*") if item.is_file())
        ]
        release_manifest = {
            "artifact": "anonymous_effect_binding_result_reproduction",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "preview_pending_results" if args.allow_pending else "ready_for_author_upload",
            "files": rows,
            "source_readiness_status": readiness["status"],
            "claim_boundary": (
                "This package reproduces paper numbers from frozen result artifacts. "
                "It does not rerun model inference or external services."
            ),
        }
        (staging / "RELEASE_MANIFEST.json").write_text(
            json.dumps(release_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        violations = scan(staging)
        scan_report = {
            "status": "passed" if not violations else "failed",
            "n_files": len(rows) + 1,
            "violations": violations,
            "patterns": sorted(FORBIDDEN),
        }
        (staging / "ANONYMIZATION_REPORT.json").write_text(
            json.dumps(scan_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if violations:
            raise RuntimeError(f"anonymous package scan failed: {violations[:5]}")

        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        shutil.copytree(staging, OUTPUT)
        with tarfile.open(ARCHIVE, "w:gz") as archive:
            archive.add(staging, arcname="effect-binding-artifact")

    summary = {
        "status": "preview_pending_results" if args.allow_pending else "ready_for_author_upload",
        "package": str(OUTPUT.relative_to(ROOT)),
        "archive": str(ARCHIVE.relative_to(ROOT)),
        "archive_sha256": sha256(ARCHIVE),
        "anonymization_scan": "passed",
    }
    (HERE / "anonymous_package_build_report.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
