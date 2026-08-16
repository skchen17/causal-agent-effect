from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


pytest.importorskip("polars", reason="ToolSandbox integration tests require the dedicated E79 environment")


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_e79_toolsandbox_adapter_smoke.py"


def _module():
    spec = importlib.util.spec_from_file_location("e79_toolsandbox_adapter", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def smoke():
    module = _module()
    report = module.run_smoke()
    return module, report


def test_inventory_uses_native_implementation_and_schema_evidence(smoke) -> None:
    _, report = smoke
    inventory = {row["tool_name"]: row for row in report["tool_inventory"]["tools"]}
    assert report["tool_inventory"]["classification_counts"] == {
        "effectful": 4,
        "read_only": 4,
    }
    assert inventory["set_cellular_service_status"]["classification"] == "effectful"
    assert inventory["set_cellular_service_status"]["classification_evidence"][
        "mutation_path"
    ] == ["set_cellular_service_status", "set_boolean_settings", "update_database"]
    assert inventory["search_contacts"]["classification"] == "read_only"
    assert inventory["modify_contact"]["default_bearing_fields"] == [
        "name",
        "phone_number",
        "relationship",
        "is_self",
    ]
    assert inventory["modify_contact"]["schema_evidence"]["unsupported_schema_fields"] == []


def test_default_and_unknown_fields_fail_closed_before_execution(smoke) -> None:
    _, report = smoke
    checks = report["fail_closed_checks"]
    assert checks["default_bearing_signature_fields_detected"] > 0
    assert checks["rejected_before_native_execution"] == 2
    assert {row["code"] for row in checks["rejections"]} == {
        "implicit_default_fields",
        "unsupported_fields",
    }
    assert report["mediation_audit"]["effectful_calls_reaching_native_executor"] == 3


def test_every_effectful_native_call_has_the_exact_precommit_binding(smoke) -> None:
    _, report = smoke
    audit = report["mediation_audit"]
    assert report["status"] == "passed"
    assert audit["effectful_calls_reaching_native_executor"] == 3
    assert audit["effectful_calls_with_precommit"] == 3
    assert audit["signature_multiset_exact_match"] is True
    assert audit["missing_precommit_occurrences"] == 0
    assert audit["extra_precommit_occurrences"] == 0
    assert all(row["effect_calls_changed_native_world_state"] for row in report["scenario_results"])
    for scenario in report["scenario_results"]:
        precommits = {
            row["binding_hash"]: (row["function"], row["arguments"])
            for row in scenario["precommit_records"]
        }
        executions = {
            row["binding_hash"]: (row["function"], row["arguments"])
            for row in scenario["executed_effect_records"]
        }
        assert precommits == executions


def test_native_milestone_and_minefield_evaluation_and_claim_boundary(smoke) -> None:
    _, report = smoke
    assert report["subset"]["n_smoke_scenarios"] == 2
    assert all(row["native_evaluator_invoked"] for row in report["scenario_results"])
    assert all(row["milestone_similarity"] == 1.0 for row in report["scenario_results"])
    assert all(row["minefield_similarity"] == 0.0 for row in report["scenario_results"])
    boundary = " ".join(report["claim_boundaries"]["not_established"])
    assert "victim-model security" in boundary
    assert "positive minefield detection" in boundary
    assert report["controls"]["llm_calls"] == 0
    assert report["controls"]["network_connections_enabled"] is False


def test_outputs_are_deterministic_and_match_report(smoke) -> None:
    module, report = smoke
    module.write_outputs(report)
    first_json = module.RESULT_JSON.read_bytes()
    first_md = module.RESULT_MD.read_bytes()
    module.write_outputs(report)
    assert module.RESULT_JSON.read_bytes() == first_json
    assert module.RESULT_MD.read_bytes() == first_md
    assert json.loads(first_json) == report
    assert b"Implementation-readiness evidence only" in first_md
