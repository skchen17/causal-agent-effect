from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/analyze_e78_trajectory_overhead_and_recovery.py"


def module():
    spec = importlib.util.spec_from_file_location("e78_trajectory_overhead", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


def test_duration_and_recovery_reconcile_with_frozen_artifacts() -> None:
    report = module().build()
    assert report["status"] == "passed_with_observational_timing_caveat"
    assert report["protocol"]["paired_case_keys"] == 726
    assert report["verification"] == {
        "same_726_case_keys": True,
        "strict_e77_report_passed": True,
        "failure_taxonomy_reconciles": True,
        "positive_finite_duration": True,
    }
    for mode, n in (("all", 726), ("benign", 97), ("attack", 629)):
        assert report["duration"][mode]["no_guard"]["n"] == n
        assert report["duration"][mode]["ours"]["n"] == n
        assert report["duration"][mode]["paired"]["n"] == n
    recovery = report["recovery"]
    assert recovery["precommit_checks"] == 2930
    assert sum(recovery["initial_decisions"].values()) == 2930
    assert sum(recovery["recovery_states"].values()) == 2930
    assert recovery["checks_transitioned_to_allow"] == 32


def test_percentile_uses_nearest_rank() -> None:
    loaded = module()
    assert loaded.percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.0
    assert loaded.percentile([1.0, 2.0, 3.0, 4.0], 0.95) == 4.0
