from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit_e79_long_horizon_benchmarks.py"


def _module():
    spec = importlib.util.spec_from_file_location("e79_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_e79_static_gate_separates_execution_from_feasibility() -> None:
    module = _module()
    report = module.write_outputs(module.build_audits())
    assert report["status"] == "passed"
    assert report["execution_claim"].startswith("No benchmark")
    rows = {row["benchmark_id"]: row for row in report["benchmarks"]}
    assert rows["toolsandbox"]["source_complete"] is True
    assert rows["toolsandbox"]["current_gate"] == "ready_for_offline_environment_smoke"
    assert rows["agentlab"]["source_complete"] is False
    assert rows["agentlab"]["proprietary_model_required_by_default"] is True
    assert rows["tau2_bench"]["current_gate"].startswith("fallback")


def test_e79_gate_records_security_and_utility_capabilities() -> None:
    module = _module()
    rows = {row.benchmark_id: row for row in module.build_audits()}
    assert rows["toolsandbox"].prefix_or_milestone_validator is True
    assert rows["toolsandbox"].native_long_horizon_attacks is False
    assert rows["agentlab"].native_long_horizon_attacks is True
    assert rows["agentlab"].label_hidden_adapter_feasible is True
    assert all(row.real_external_side_effects_required is False for row in rows.values())
