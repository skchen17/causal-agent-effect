from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/finalize_e78_qwen32_strong_baselines.py"


def load_module():
    spec = importlib.util.spec_from_file_location("finalize_e78", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_attriguard_protocol_failures_reject_context_errors() -> None:
    module = load_module()
    rows = []
    for index in range(module.EXPECTED_CASES):
        rows.append(
            {
                "suite": "workspace",
                "mode": "attack",
                "user_task_id": f"user_task_{index}",
                "injection_task_id": "injection_task_0",
                "unified_case_id": f"case-{index}",
                "status": "passed",
                "returncode": 0,
                "timed_out": False,
                "server_400_error": False,
                "server_500_error": False,
                "context_length_exceeded": False,
                "log_exists_after": True,
                "log_metrics_complete": True,
            }
        )
    rows[17].update(status="protocol_error", server_400_error=True, context_length_exceeded=True)
    failures = module.attriguard_protocol_failures(rows)
    assert len(failures) == 1
    assert failures[0]["unified_case_id"] == "case-17"


def test_paired_statistics_uses_exact_case_keys_and_direction() -> None:
    module = load_module()
    left = [
        {"unified_case_id": "a", "mode": "attack", "attack_success": True, "utility": True},
        {"unified_case_id": "b", "mode": "attack", "attack_success": False, "utility": False},
    ]
    right = [
        {"unified_case_id": "a", "mode": "attack", "attack_success": False, "utility": True},
        {"unified_case_id": "b", "mode": "attack", "attack_success": False, "utility": True},
    ]
    left_map = module.metric_vector(left, "attack_success")
    right_map = module.metric_vector(right, "attack_success")
    keys = sorted(left_map)
    comparison = module.paired_bootstrap(
        [left_map[key] for key in keys],
        [right_map[key] for key in keys],
        samples=200,
        seed=7,
    )
    assert comparison["difference_method_minus_no_guard"] == -0.5


def test_scrubbed_rows_do_not_retain_absolute_paths() -> None:
    module = load_module()
    row = {
        "unified_case_id": "case-a",
        "suite": "banking",
        "mode": "benign",
        "user_task_id": "user_task_0",
        "injection_task_id": None,
        "method_id": module.NO_GUARD,
        "utility": True,
        "attack_success": False,
        "error": False,
        "source_file": str(module.ROOT / "runs/example.json"),
    }
    scrubbed = module.scrub_import_row(row)
    assert scrubbed["source_file"] == "runs/example.json"
    assert not scrubbed["source_file"].startswith("/")


def test_current_method_summary_must_match_strict_report() -> None:
    module = load_module()
    summary = {
        "method_id": "agentdojo_live_ours_e77_effect_diff_runtime",
        "n_total": 726,
        "n_benign": 97,
        "n_attack": 629,
        "n_error": 0,
        "benign_utility_successes": 33,
        "attack_utility_successes": 207,
        "attack_successes": 3,
    }
    report = {
        "metrics": {
            "method_id": "agentdojo_live_ours_e77_effect_diff_runtime",
            "n_total": 726,
            "n_benign": 97,
            "n_attack": 629,
            "n_error": 0,
            "benign_utility_successes": 33,
            "attack_user_utility_successes": 207,
            "attack_successes": 3,
        }
    }
    module.validate_current_method_summary(summary, report)
    report["metrics"]["attack_successes"] = 2
    try:
        module.validate_current_method_summary(summary, report)
    except ValueError as exc:
        assert "attack_successes" in str(exc)
    else:
        raise AssertionError("mismatched method metrics must fail the finalizer")


def test_current_method_uses_context_repaired_overlay() -> None:
    module = load_module()
    assert "context-repaired" in str(module.CURRENT_METHOD_LOG_ROOT)
    assert "context-repaired" in str(module.CURRENT_METHOD_REPORT)
