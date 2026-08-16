from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not find root")


ROOT = find_root(Path(__file__))
SCRIPT = ROOT / "shared/compatibility/scripts/run_deployment_style_authorization_interface.py"


def load_module():
    spec = importlib.util.spec_from_file_location("deployment_authz", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluated_rows(module):
    policy_rows = module.policies()
    rows = []
    for row in module.build_contexts():
        after = module.execute_tool(row)
        source = module.source_effects(row, after)
        typed = module.instantiate_descriptor(row)
        item = {**row, "source_effects": source, "typed_effects": typed}
        item["ideal_decision"] = module.policy_decision(source, policy_rows[row["policy_id"]])
        item["representations"] = {name: module.representation(item, typed, name) for name in module.REPRESENTATIONS}
        rows.append(item)
    return rows


def test_frozen_design_has_four_domains_and_balanced_48_contexts() -> None:
    module = load_module()
    rows = evaluated_rows(module)
    assert len(rows) == 48
    assert len({row["domain"] for row in rows}) == 4
    assert len({row["tool_name"] for row in rows}) == 4
    assert Counter(row["ideal_decision"] for row in rows) == {"ALLOW": 24, "DENY": 24}


def test_descriptor_matches_independent_source_state_diff() -> None:
    module = load_module()
    for row in module.build_contexts():
        assert module.instantiate_descriptor(row) == module.source_effects(row, module.execute_tool(row))


def test_source_execution_uses_a_copied_state() -> None:
    module = load_module()
    for row in module.build_contexts():
        before = module.canonical(row["pre_state"])
        module.execute_tool(row)
        assert module.canonical(row["pre_state"]) == before


def test_same_consumer_exposes_coarse_collisions_and_typed_conformance() -> None:
    module = load_module()
    rows = evaluated_rows(module)
    for name in module.REPRESENTATIONS[:-1]:
        summary, _ = module.collision_audit(rows, name)
        assert summary["n_mixed_cells"] > 0
    typed, _ = module.collision_audit(rows, "validated_typed_effects")
    assert typed["n_mixed_cells"] == 0
    primary = module.metrics(rows, "validated_typed_effects", "ABSTAIN")
    assert primary["unsafe_pre_allow"]["successes"] == 0
    assert primary["false_denial"]["successes"] == 0
    assert primary["coverage"]["rate"] == 1.0


def test_raw_arguments_collide_when_pre_state_changes() -> None:
    module = load_module()
    rows = evaluated_rows(module)
    _, witnesses = module.collision_audit(rows, "canonical_raw_arguments")
    state_ids = {row["case_id"] for row in rows if "pre_state" in row["axis"]}
    assert any(state_ids.intersection(witness["case_ids"]) for witness in witnesses)


def test_uniform_mixed_cell_resolution_exposes_both_error_sides() -> None:
    module = load_module()
    rows = evaluated_rows(module)
    fail_open = module.metrics(rows, "tool_name", "ALLOW")
    fail_closed = module.metrics(rows, "tool_name", "DENY")
    assert fail_open["unsafe_pre_allow"]["successes"] > 0
    assert fail_closed["false_denial"]["successes"] > 0


def test_smoke_writes_traceable_outputs(tmp_path: Path) -> None:
    module = load_module()
    # Input hashing is covered by the full runner; isolate artifact generation here.
    report = module.run("smoke", tmp_path)
    assert report["status"] == "passed"
    assert report["n_contexts"] == 8
    for name in (
        "source-executions.jsonl",
        "authorization-decisions.jsonl",
        "representation-collision-witnesses.jsonl",
        "deployment-authorization-report.json",
        "deployment-authorization-report.md",
        "representation-metrics.csv",
        "table_deployment_authorization_interface.tex",
    ):
        assert (tmp_path / name).is_file()
