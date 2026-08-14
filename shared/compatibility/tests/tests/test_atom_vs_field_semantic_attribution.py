from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "shared/compatibility/scripts/run_atom_vs_field_semantic_attribution.py"


def module():
    spec = importlib.util.spec_from_file_location("atom_vs_field_test", SCRIPT)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


def test_protocol_is_frozen_and_source_hashes_match() -> None:
    value = module()
    protocol = value.verify_protocol()
    assert protocol["status"] == "frozen_before_execution"
    assert protocol["acceptance"]["require_atom_advantage"] is False
    assert protocol["acceptance"]["negative_results_retained"] is True


def test_field_set_control_holds_same_25_tools_and_67_fields() -> None:
    report = module().field_set_control()
    assert report["status"] == "passed"
    assert report["same_tool_and_field_sets"] is True
    assert report["n_tools_raw"] == report["n_tools_validated"] == 25
    assert report["n_fields_raw"] == report["n_fields_validated"] == 67


def test_leaf_expansion_is_deterministic_and_keeps_parent_field() -> None:
    value = module()
    arguments = {"recipients": ["alice", "eve"], "metadata": {"urgent": True}}
    first = value.flatten_leaves(arguments)
    second = value.flatten_leaves(arguments)
    assert first == second
    assert [row["field"] for row in first].count("recipients") == 2
    assert any(row["path"] == ["metadata", "urgent"] for row in first)


def test_candidate_views_do_not_copy_source_oracle() -> None:
    value = module()
    mechanism = value.load_mechanism()
    rows = [value.add_views(row) for row in mechanism.normalize_agentdojo() + mechanism.normalize_toolsandbox()]
    assert len(rows) == 88
    for row in rows:
        views = row["representations"]
        assert set(views) == set(value.REPRESENTATIONS)
        assert "ideal_allow" not in json.dumps(views, sort_keys=True)
        assert views["validated_typed_atoms"] is not views["source_effect_oracle"]


def test_smoke_run_writes_complete_outputs(tmp_path: Path) -> None:
    value = module()
    report = value.run(output_dir=tmp_path, smoke=True)
    assert report["status"] == "passed"
    assert report["n_contexts"] == 16
    assert report["n_policy_result_rows"] > 0
    assert report["n_ordered_decision_rows"] > 0
    assert {row["representation"] for row in report["ordered_authorizer_metrics"]} == set(value.REPRESENTATIONS)
    source = [row for row in report["ordered_authorizer_metrics"] if row["representation"] == "source_effect_oracle"]
    assert source and all(row["unsafe_pre_allow"] == row["false_deny"] == 0 for row in source)
    for name in (
        "atom-vs-field-report.json",
        "atom-vs-field-report.md",
        "policy-representation-metrics.csv",
        "ordered-authorizer-metrics.csv",
        "ordered-authorizer-decisions.jsonl",
        "ambiguity-witnesses.jsonl",
        "field-set-control.json",
        "atom-agreement.csv",
    ):
        assert (tmp_path / name).is_file()
