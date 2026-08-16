from __future__ import annotations

import ast
import json
from pathlib import Path

from shared.compatibility.scripts.independent_authority_benchmark import (
    context_generator,
    state_aware_request_adapter,
    state_aware_view,
)


def rows():
    return context_generator.generate_evaluation(context_generator.generator_config())


def test_state_aware_view_has_no_oracle_or_descriptor_imports():
    tree = ast.parse(Path(state_aware_view.__file__).read_text(encoding="utf-8"))
    imports = " ".join(
        ast.unparse(node) for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    )
    assert "transition_oracle" not in imports
    assert "descriptor" not in imports
    assert "authority_model" not in imports


def test_view_exposes_only_request_and_referenced_pre_state():
    forbidden = {"post_state", "source_transitions", "typed_effects", "ideal_decision"}
    for row in rows():
        view = state_aware_view.build_view(row)
        encoded = json.dumps(view)
        assert not any(name in encoded for name in forbidden)
        assert set(view) == {
            "schema_version", "tool_name", "totalized_arguments",
            "resolved_defaults", "referenced_resources",
        }
        assert view["referenced_resources"]


def test_alias_resolution_and_state_defaults_are_visible():
    calendar = next(row for row in rows() if row["domain"] == "calendar" and row["arguments"]["calendar_ref"] == "primary")
    view = state_aware_view.build_view(calendar)
    assert view["referenced_resources"][0]["canonical_id"] in {"calendar:team", "calendar:external"}
    assert "visibility" in view["totalized_arguments"]
    assert "recurrence" in view["totalized_arguments"]


def test_adapter_is_separate_and_returns_authority_request_fields():
    required = {"operation", "resource_type", "resource_id", "target_principal", "qualifiers", "commit_mode"}
    for row in rows()[:64]:
        atoms = state_aware_request_adapter.requests(state_aware_view.build_view(row))
        assert all(required.issubset(atom) for atom in atoms)


def test_view_does_not_serialize_unreferenced_resource_state():
    workspace = next(row for row in rows() if row["domain"] == "workspace" and row["arguments"].get("doc_ref") == "doc:report" and "doc_refs" not in row["arguments"])
    view = state_aware_view.build_view(workspace)
    ids = {item["canonical_id"] for item in view["referenced_resources"]}
    assert ids == {"doc:report"}
    assert "doc:external" not in json.dumps(view)
