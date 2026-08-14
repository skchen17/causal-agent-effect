from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
SCRIPT = ROOT / "scripts/run_toolsandbox_heldout_validation.py"
RESULT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "heldout-toolsandbox-effect-binding-validation/heldout-validation-report.json"
)
CONTEXTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "heldout-toolsandbox-effect-binding-validation/heldout-contexts.jsonl"
)


def load_module():
    spec = importlib.util.spec_from_file_location("toolsandbox_heldout", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_partition_audit_detects_collision() -> None:
    module = load_module()
    rows = [
        {
            "case_id": "a",
            "source_effect_atoms": [{"effect": "x"}],
            "representations": {"coarse": "same"},
        },
        {
            "case_id": "b",
            "source_effect_atoms": [{"effect": "y"}],
            "representations": {"coarse": "same"},
        },
    ]
    summary, witnesses = module.representation_audit(rows, "coarse")
    assert summary["authorization_collision_cells"] == 1
    assert summary["authorization_separating_pairs"] == 1
    assert len(witnesses) == 1


def test_heldout_result_matches_frozen_acceptance_gate() -> None:
    report = json.loads(RESULT.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["n_tools"] == 5
    assert report["source_verification_errors"] == []
    assert report["typed_relation_agreement"]["successes"] == report["n_contexts"]
    typed = next(
        row
        for row in report["representations"]
        if row["representation"] == "typed_contract"
    )
    assert typed["authorization_collision_cells"] == 0
    assert typed["authorization_separating_pairs"] == 0
    assert typed["finite_partition_exact"] is True


def test_all_frozen_contexts_are_retained() -> None:
    rows = [
        json.loads(line)
        for line in CONTEXTS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == len({row["case_id"] for row in rows})
    assert len(rows) == 32
    assert {row["tool_name"] for row in rows} == {
        "add_contact",
        "remove_contact",
        "add_reminder",
        "set_location_service_status",
        "set_low_battery_mode_status",
    }
