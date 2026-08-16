from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = next(
    candidate
    for candidate in Path(__file__).resolve().parents
    if (candidate / "paper/current-usenix").exists()
)
SCRIPT = ROOT / "scripts/audit_agentdojo_effectful_defaults.py"
SPEC = importlib.util.spec_from_file_location("default_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_nonempty_default_classification() -> None:
    assert MODULE.is_nonempty_default(None) is False
    assert MODULE.is_nonempty_default("") is False
    assert MODULE.is_nonempty_default([]) is False
    assert MODULE.is_nonempty_default("public") is True
    assert MODULE.is_nonempty_default(["owner@example.com"]) is True


def test_full_audit_artifact_is_conservative() -> None:
    report_path = (
        ROOT
        / "experiments/security-analysis-ablation-and-overhead/results/"
        "conditional-effect-contract-security-model/"
        "agentdojo-effectful-default-audit.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed_no_effect_bearing_nonempty_defaults"
    assert report["n_nonempty_static_defaults"] == 0
    assert report["n_dynamic_defaults"] == 0
    assert report["n_omitted_explicit_equivalent_tools"] == report[
        "n_default_bearing_effectful_tool_instances"
    ]
