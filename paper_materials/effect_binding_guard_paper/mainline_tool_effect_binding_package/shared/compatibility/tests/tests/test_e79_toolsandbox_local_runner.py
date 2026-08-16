from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


pytest.importorskip("polars")
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_e79_toolsandbox_local.py"


def module():
    spec = importlib.util.spec_from_file_location("e79_toolsandbox_local", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


def test_frozen_30_scenario_manifest_has_no_drift() -> None:
    manifest, scenarios = module().frozen_scenarios()
    assert manifest["n_selected"] == len(scenarios) == 30
    assert set(scenarios) == {row["scenario_name"] for row in manifest["scenarios"]}


def test_localhost_gate_rejects_remote_addresses() -> None:
    helper = module()
    with helper.localhost_only():
        sock = __import__("socket").socket()
        with pytest.raises(RuntimeError, match="non-localhost"):
            sock.connect(("example.com", 443))


def test_configure_imports_includes_repository_root_for_script_helpers() -> None:
    helper = module()
    helper.configure_imports()
    assert str(ROOT) in __import__("sys").path


def test_incomplete_summary_retains_all_missing_scenarios(tmp_path: Path) -> None:
    _, scenarios = module().frozen_scenarios()
    report = module().summarize("no_guard", sorted(scenarios), tmp_path)
    assert report["status"] == "incomplete"
    assert report["n_rows"] == 0
    assert len(report["missing_scenarios"]) == 30
