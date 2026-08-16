from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "analysis/results/e79_agentlab_guard_compatibility.json"


def test_agentlab_guard_schema_gate_is_complete_and_conservative() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["status"] == "schema_compatible_not_runtime_validated"
    assert report["missing_registered_effectful_tools"] == []
    assert report["schema_field_mismatches"] == []
    assert sum(row["n_effectful_tools"] for row in report["suite_inventory"].values()) > 0
    assert "schema gate only" in report["claim_boundary"]
