from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit_e81_final_protocol_compatibility.py"


def module():
    spec = importlib.util.spec_from_file_location("e81_compatibility", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


def test_final_protocol_audit_blocks_semantically_empty_rows() -> None:
    report = module().build()
    assert report["status"] == "reviewed_inputs_ready_waiting_e77_v3_and_common_runner"
    assert report["kernel_rows"] == ["A1", "A11", "A12", "A13", "A15", "A2", "A7", "A9"]
    assert report["e77_descriptors_with_provenance_or_control_fields"] == 0
    assert report["rows"]["A7"]["status"] == "kernel_ready_common_runner_pending"
    assert report["rows"]["A13"]["status"] == "totalization_catalog_ready_runner_pending"
    assert report["rows"]["A9"]["status"] == "registry_ready_common_runner_pending"
    assert report["e84_trusted_manifests"] == 44
    assert report["e85_trusted_effect_projections"] == 16
    assert report["errors"] == []
