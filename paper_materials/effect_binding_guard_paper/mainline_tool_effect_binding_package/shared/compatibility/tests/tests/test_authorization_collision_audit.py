from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path.cwd()
if not (ROOT / "paper/current-usenix").is_dir():
    ROOT = Path(__file__).absolute().parents[2]
SCRIPT = ROOT / "scripts" / "run_authorization_collision_audit.py"
SPEC = importlib.util.spec_from_file_location("collision_audit", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_policy_signature_excludes_raw_task_text() -> None:
    row = AUDIT.read_jsonl(AUDIT.E50_ROWS)[0]
    policy = AUDIT.policy_from_e50(row)
    assert set(policy) == {
        "authorized_effects",
        "authorized_resources",
        "commit_allowed",
        "resource_aliases",
    }


def test_e50_tool_name_has_separating_collisions() -> None:
    rows = AUDIT.read_jsonl(AUDIT.E50_ROWS)
    predictions = AUDIT.regenerate_e50_predictions(rows)
    result, witnesses = AUDIT.audit_dataset(
        dataset="test",
        rows=rows,
        policy_builder=AUDIT.policy_from_e50,
        predictions=predictions,
    )
    tool = next(
        row
        for row in result["representations"]
        if row["representation_name"] == "tool_name"
    )
    assert tool["n_mixed_authorization_cells"] > 0
    assert tool["unit_cost_collision_lower_bound"] > 0
    assert witnesses


def test_ideal_effect_resource_separates_observed_e50_rows() -> None:
    rows = AUDIT.read_jsonl(AUDIT.E50_ROWS)
    predictions = AUDIT.regenerate_e50_predictions(rows)
    result, _ = AUDIT.audit_dataset(
        dataset="test",
        rows=rows,
        policy_builder=AUDIT.policy_from_e50,
        predictions=predictions,
    )
    combined = next(
        row
        for row in result["representations"]
        if row["representation_name"] == "ideal_effect_resource"
    )
    assert combined["authorization_sufficient_on_observed_rows"] is True
