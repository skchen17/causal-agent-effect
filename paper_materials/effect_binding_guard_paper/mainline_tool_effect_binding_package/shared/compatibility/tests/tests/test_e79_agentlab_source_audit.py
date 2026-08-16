from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "analysis/results/e79_agentlab_source_audit.json"


def test_agentlab_audit_is_pinned_and_conservative() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    native = report["native_inventory_and_smoke"]
    assert report["status"] == "passed_with_protocol_blockers"
    assert report["source"]["revision"] == "36f58e60c36bbd6d5b8e61d50d7db7d9ea7258d7"
    assert native["total_user_tasks"] == 97
    assert native["total_injection_tasks"] == 35
    assert native["full_cartesian_pairs"] == 949
    comparison = report["checked_in_long_horizon_results"]["complete_four_suite_comparison_roots"]
    assert comparison["gpt-4o-backip"]["total_unique_pairs"] == 303
    assert comparison["gpt-4o-backip"]["pair_counts"] == {
        "banking": 144, "slack": 85, "travel": 25, "workspace": 49
    }
    assert "No attack was generated" in report["claim_boundary"]


def test_agentlab_security_boolean_is_not_misreported() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["evaluator_semantics"]["security_true_semantics"].startswith("injection goal executed")
    assert len(report["protocol_blockers"]) >= 5
