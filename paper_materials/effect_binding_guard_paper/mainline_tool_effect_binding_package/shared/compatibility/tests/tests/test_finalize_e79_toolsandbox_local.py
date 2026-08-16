from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/finalize_e79_toolsandbox_local.py"


def module():
    spec = importlib.util.spec_from_file_location("finalize_e79_toolsandbox", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


def test_finalizer_fails_fast_before_full_30_pair_exists(tmp_path: Path, monkeypatch) -> None:
    helper = module()
    monkeypatch.setattr(helper, "RUN_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        helper.build()


def test_guard_audit_rejects_execution_without_allowed_precommit(tmp_path: Path, monkeypatch) -> None:
    helper = module()
    monkeypatch.setattr(helper, "RUN_ROOT", tmp_path)
    expected = {"case"}
    path = tmp_path / "effect_guard" / "guard_audit" / "case.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"event": "effect_executed", "call_signature": "x"}) + "\n")
    report = helper.audit_guard(expected)
    assert report["every_effect_execution_precommitted"] is False
    assert report["executions_without_allowed_precommit"] == 1
