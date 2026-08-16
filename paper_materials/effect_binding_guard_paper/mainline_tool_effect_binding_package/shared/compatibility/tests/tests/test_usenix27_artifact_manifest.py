from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "paper/current-usenix/artifact/build_manifest.py"


def module():
    spec = importlib.util.spec_from_file_location("artifact_manifest", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def test_manifest_is_fail_fast_and_uses_relative_paths() -> None:
    loaded = module()
    manifest = loaded.build()
    expected_failed = set()
    for name, (relative, status_ok) in loaded.REQUIRED.items():
        path = loaded.PACKAGE_ROOT / relative
        if not path.is_file():
            expected_failed.add(name)
            continue
        try:
            status = json.loads(path.read_text(encoding="utf-8")).get("status", "unrecorded")
        except json.JSONDecodeError:
            expected_failed.add(name)
            continue
        if not status_ok(status):
            expected_failed.add(name)
    assert expected_failed == {
        name for name, row in manifest["required_evidence"].items() if not row["gate_passed"]
    }
    assert manifest["status"] == (
        "paper_evidence_ready_artifact_release_pending"
        if not expected_failed
        else "paper_evidence_incomplete"
    )
    for row in manifest["required_evidence"].values():
        assert not Path(row["path"]).is_absolute()
    assert manifest["release_gates"]["paper_evidence_gates_passed"] is (not expected_failed)
    assert not manifest["release_gates"]["anonymous_stable_url_inserted"]
