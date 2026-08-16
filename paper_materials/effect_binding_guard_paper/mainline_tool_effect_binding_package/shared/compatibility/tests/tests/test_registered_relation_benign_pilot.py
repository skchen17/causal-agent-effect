from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = next(
    candidate
    for candidate in (
        Path.cwd().resolve(),
        *Path(__file__).resolve().parents,
    )
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)


def load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


manifest_builder = load_module(
    "registered_relation_benign_pilot_manifest",
    (
        "experiments/security-analysis-ablation-and-overhead/source/"
        "headline-benign-utility-pathway-audit/"
        "build_registered_relation_benign_pilot_manifest.py"
    ),
)
runner = load_module(
    "recovery_normalization_qwen32_runner",
    (
        "experiments/intent-bound-runtime-guard/scripts/"
        "effect-difference-runtime-guard/"
        "run-recovery-normalization-qwen32.py"
    ),
)
analyzer = load_module(
    "registered_relation_benign_pilot_analyzer",
    (
        "experiments/security-analysis-ablation-and-overhead/source/"
        "headline-benign-utility-pathway-audit/"
        "analyze_registered_relation_benign_pilot.py"
    ),
)
gap_analyzer = load_module(
    "registered_relation_onboarding_gap_analyzer",
    (
        "experiments/security-analysis-ablation-and-overhead/source/"
        "headline-benign-utility-pathway-audit/"
        "analyze_registered_relation_onboarding_gaps.py"
    ),
)


def test_manifest_freezes_all_diagnosed_cases_and_four_controls() -> None:
    manifest = manifest_builder.build_manifest()
    assert manifest["status"] == "frozen_before_v8_pilot_execution"
    assert manifest["runtime_version"] == runner.RUNTIME_VERSION
    assert manifest["modes"] == ["benign"]
    assert manifest["n_cases"] == 16
    assert manifest["n_target_cases"] == 12
    assert manifest["n_control_cases"] == 4
    assert len({row["case_key"] for row in manifest["cases"]}) == 16
    assert manifest["selection_policy"]["selected_using_v8_outcomes"] is False
    assert (
        manifest["selection_policy"]["outcome_conditioned_on_historical_e78"]
        is True
    )


def test_target_cases_have_a_historical_trusted_source_relation() -> None:
    manifest = manifest_builder.build_manifest()
    targets = [
        row
        for row in manifest["cases"]
        if row["stratum"] == "historical_trusted_source_resolver_loss"
    ]
    assert len(targets) == 12
    for row in targets:
        assert row["historical_relations"]
        for relation in row["historical_relations"]:
            assert relation["target_tool"]
            assert relation["target_field"]
            assert relation["observed_source_tools"]


def test_manifest_live_command_is_benign_only_and_repeats_task_flags() -> None:
    command = runner.live_command(
        "pilot",
        ROOT / "runs/test",
        18087,
        0,
        suite="slack",
        user_tasks=["user_task_5", "user_task_7"],
        live_modes="benign",
    )
    modes_index = command.index("--live-modes")
    assert command[modes_index + 1] == "benign"
    assert command.count("--live-user-task") == 2
    assert "--live-injection-task" not in command


def test_outcome_summary_retains_failures_and_errors() -> None:
    summary = analyzer.summarize_outcomes(
        [
            {"utility": True, "error": None},
            {"utility": False, "error": None},
            {"utility": False, "error": "timeout"},
        ]
    )
    assert summary == {
        "cases": 3,
        "utility_successes": 1,
        "utility_failures": 2,
        "errors": 1,
    }


def test_completed_pilot_retains_fixed_denominator_negative_result() -> None:
    report = analyzer.build_report()
    assert report["status"] == "passed_fixed_denominator_outcomes_retained"
    assert report["v8_outcomes"]["target"]["utility_successes"] == 1
    assert report["v8_outcomes"]["target"]["cases"] == 12
    assert report["v8_outcomes"]["control"]["utility_successes"] == 4
    assert report["v8_outcomes"]["control"]["cases"] == 4
    assert report["v8_outcomes"]["overall"]["errors"] == 0
    assert report["runtime_audit"]["executed_non_allow_checks"] == 0
    assert report["failure_anatomy"]["runtime_relation_failure_case_count"] == 7
    assert report["failure_anatomy"]["plan_construction_failure_case_count"] == 4


def test_onboarding_gap_inventory_is_complete_and_non_authorizing() -> None:
    report = gap_analyzer.build_report()
    assert report["status"] == "passed"
    assert report["counts"]["exact_source_target_field_groups"] == 14
    assert report["counts"]["groups_observed_in_recovered_cases"] == 2
    assert report["counts"]["groups_observed_in_failed_cases"] == 12
    assert report["counts"]["relation_case_rows"] == 17
    assert "does not infer authorization" in report["claim_boundary"]
