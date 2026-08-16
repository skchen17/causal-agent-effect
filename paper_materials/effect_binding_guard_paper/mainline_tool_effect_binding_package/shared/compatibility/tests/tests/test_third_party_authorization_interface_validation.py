from __future__ import annotations

import ast
from pathlib import Path

import pytest

from shared.compatibility.scripts.third_party_authorization_interface_validation.descriptor_compiler import (
    compile_descriptor, initial_descriptors,
)
from shared.compatibility.scripts.third_party_authorization_interface_validation.evaluation_generator import generate_evaluation_rows
from shared.compatibility.scripts.third_party_authorization_interface_validation.policy import authority_manifest, authorize_all
from shared.compatibility.scripts.third_party_authorization_interface_validation.registration_generator import generate_registration_rows
from shared.compatibility.scripts.third_party_authorization_interface_validation.source_oracle import source_effects
from shared.compatibility.scripts.third_party_authorization_interface_validation.sources import execute


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation"


def test_frozen_context_counts_and_value_separation():
    registration = generate_registration_rows()
    evaluation = generate_evaluation_rows()
    assert len(registration) == 264
    assert len(evaluation) == 264
    assert len({row["case_id"] for row in registration + evaluation}) == 528
    assert all("reg" in str(row["fixture"]) + str(row["arguments"]) for row in registration)
    assert all("eval" in str(row["fixture"]) + str(row["arguments"]) for row in evaluation)


def test_evaluation_generator_has_no_forbidden_imports():
    tree = ast.parse((PACKAGE / "evaluation_generator.py").read_text())
    names = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    joined = " ".join(names)
    for forbidden in ("descriptor", "policy", "oracle", "registration"):
        assert forbidden not in joined


def test_oracle_and_compiler_do_not_import_each_other():
    for filename, forbidden in (("source_oracle.py", "descriptor_compiler"),
                                ("descriptor_compiler.py", "source_oracle")):
        tree = ast.parse((PACKAGE / filename).read_text())
        imported = " ".join((node.module or "") for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
        assert forbidden not in imported


@pytest.mark.parametrize("source", ["filesystem", "sqlite", "memory"])
def test_real_mcp_execution_yields_state_delta(source):
    descriptors = {item["tool_name"]: item for item in initial_descriptors()}
    row = next(row for row in generate_registration_rows() if row["source"] == source and row["case_id"].endswith("-00-0"))
    executed = {**row, **execute(row)}
    assert executed["execution_error"] is None
    observed = source_effects(executed)
    assert observed
    assert compile_descriptor(descriptors[row["tool_name"]], executed) == observed


def test_policy_is_resource_authority_not_case_atom_allowlist():
    manifest = authority_manifest()
    assert "allowed_effects" not in str(manifest)
    safe = [{"operation": "sqlite.record.update", "resource_type": "sqlite_record",
             "resource_id": "records:1", "target_principal": "alice",
             "attributes": {"table": "records", "visibility": "internal"}, "commit_mode": "commit"}]
    denied = [{**safe[0], "target_principal": "eve"}]
    assert authorize_all(safe, manifest, partial=False)[0] == "ALLOW"
    assert authorize_all(denied, manifest, partial=False)[0] == "DENY"


def test_incomplete_descriptor_fails_closed():
    row = generate_registration_rows()[0]
    with pytest.raises((KeyError, ValueError)):
        compile_descriptor({"tool_name": row["tool_name"], "schema_version": 2}, {**row, "before": {"entries": {}}})
