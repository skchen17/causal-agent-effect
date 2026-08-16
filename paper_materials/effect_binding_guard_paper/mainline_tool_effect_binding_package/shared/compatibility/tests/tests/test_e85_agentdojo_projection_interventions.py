from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_e85_agentdojo_projection_interventions.py"
SPEC = importlib.util.spec_from_file_location("e85_projection_interventions", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_state_delta_tracks_changed_values_and_is_order_stable() -> None:
    before = {"b": [1, 2], "a": {"x": 1}}
    after = {"a": {"x": 2}, "b": [1, 2]}
    assert MODULE.state_delta(before, after) == [
        {"path": "a.x", "before": 1, "after": 2}
    ]


def test_atom_instantiation_expands_targets_and_separates_resource() -> None:
    reviewed = {
        "security_effect_projections": [
            {
                "effect": "calendar_participant_added",
                "operation": "add_participant",
                "resource_binding": "param:event_id",
                "target_binding": "each:param:participants",
                "visibility_binding": "literal:private",
                "commit_mode_binding": "literal:commit",
                "provenance_binding": "runtime:provenance",
                "control_source_binding": "runtime:control_source",
                "security_relevant_parameters": ["event_id", "participants"],
                "expansion": "per_target",
            }
        ]
    }
    atoms = MODULE.instantiate_atoms(
        reviewed,
        {"event_id": "7", "participants": ["a@example.com", "b@example.com"]},
        {},
        None,
    )
    assert len(atoms) == 2
    assert {atom["resource"] for atom in atoms} == {"7"}
    assert {atom["target"] for atom in atoms} == {
        "a@example.com",
        "b@example.com",
    }


def test_relation_row_detects_mediation_gap() -> None:
    reviewed = {
        "tool_instance_key": "workspace/append_to_file",
        "security_effect_projections": [
            {
                "effect": "file_content_appended",
                "operation": "append",
                "resource_binding": "param:file_id",
                "target_binding": "literal:file_owner",
                "visibility_binding": "literal:private",
                "commit_mode_binding": "literal:commit",
                "provenance_binding": "runtime:provenance",
                "control_source_binding": "runtime:control_source",
                "security_relevant_parameters": ["file_id", "content"],
                "expansion": "single",
            }
        ],
    }
    base = {
        "args": {"file_id": "1", "content": "a"},
        "before": {},
        "output": None,
        "delta": [{"path": "file.content", "before": "", "after": "a"}],
        "error": None,
    }
    changed = {
        "args": {"file_id": "1", "content": "b"},
        "before": {},
        "output": None,
        "delta": [{"path": "file.content", "before": "", "after": "b"}],
        "error": None,
    }
    row = MODULE.relation_row(
        "case",
        "single_field",
        reviewed,
        base,
        changed,
        ["content"],
        "eight_field_projection",
    )
    assert row["actual_effect_relation_changed"] is True
    assert row["atom_relation_changed"] is False
    assert row["failure_category"] == "mediation_gap"

    refined = MODULE.relation_row(
        "case",
        "single_field",
        reviewed,
        base,
        changed,
        ["content"],
        "typed_qualifier_projection",
    )
    assert refined["atom_relation_changed"] is True
    assert refined["relation_passed"] is True
