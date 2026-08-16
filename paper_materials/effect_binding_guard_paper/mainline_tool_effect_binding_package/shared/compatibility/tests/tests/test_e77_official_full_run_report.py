from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "analysis/results/e77_agentdojo_official_full_run_report.json"


def test_e77_official_result_has_exact_protocol_denominators() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    metrics = report["metrics"]
    assert report["status"] == "passed"
    assert report["official_case_keys"] == metrics["n_total"] == 726
    assert metrics["n_benign"] == 97
    assert metrics["n_attack"] == 629
    assert metrics["suite_counts"] == {
        "workspace": 280,
        "slack": 126,
        "travel": 160,
        "banking": 160,
    }
    assert metrics["attack_successes"] == 0
    assert metrics["n_error"] == 0
    assert all(report["verification_gates"].values())


def test_e77_runtime_audit_excludes_auxiliary_injection_utility_runs() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    audit = report["runtime_audit"]
    assert audit["auxiliary_task_plan_events_excluded"] == 20
    assert audit["auxiliary_precommit_checks_excluded"] == 80
    assert audit["official_checks_without_plan"] == 0
    assert audit["official_task_plan_parse_invalid"] == 0
    assert audit["guard_llm_calls_after_task_plan"] == 0
    assert sum(audit["decision_counts"].values()) == audit["official_precommit_checks"]


def test_e77_report_is_reproducible_and_path_anonymous() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["model"]["sha256"] == "9be227448d319e6a7acca8056b71bf7d9a2c6b2811986e6658a9dedc208d0ada"
    assert report["model"]["bytes"] == 5_629_105_408
    for key in ("logdir", "audit_path"):
        assert not report[key].startswith("/")
    assert not report["registration"]["registered_descriptor_path"].startswith("/")
