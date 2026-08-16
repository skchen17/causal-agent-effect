from __future__ import annotations

import copy
import importlib.util
import inspect
import sys
from collections import Counter
from pathlib import Path


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("root not found")


ROOT = find_root(Path(__file__))
SCRIPT_DIR = ROOT / "shared/compatibility/scripts"
CORE_PATH = SCRIPT_DIR / "full_scale_deployment_authorization_core.py"
RUNNER_PATH = SCRIPT_DIR / "run_full_scale_deployment_authorization.py"


def load(name: str, path: Path):
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def evaluated(core, phase: str):
    policies = core.policy_manifests()
    rows = []
    for row in core.build_contexts(phase):
        after = core.execute_tool(row)
        source = core.source_effects(row, after)
        typed = core.instantiate_descriptor(row)
        rows.append({**row, "source_effects": source, "typed_effects": typed, "ideal_decision": core.ideal_decision(source, policies[row["policy_id"]])})
    return rows


def test_frozen_design_scale_and_balance() -> None:
    core = load("full_authz_core_scale", CORE_PATH)
    registration = core.build_contexts("registration")
    evaluation = evaluated(core, "evaluation")
    assert len(registration) == 144
    assert len(evaluation) == 192
    assert len({row["domain"] for row in evaluation}) == 8
    assert len({row["tool_name"] for row in evaluation}) == 8
    assert Counter(row["ideal_decision"] for row in evaluation) == {"ALLOW": 96, "DENY": 96}
    assert all(len([row for row in evaluation if row["domain"] == domain]) == 24 for domain in core.DOMAINS)


def test_registration_and_evaluation_ids_are_disjoint() -> None:
    core = load("full_authz_core_split", CORE_PATH)
    registration = core.build_contexts("registration")
    evaluation = core.build_contexts("evaluation")
    assert {row["case_id"] for row in registration}.isdisjoint({row["case_id"] for row in evaluation})
    invariant = [row for row in registration if row["expected_relation"] == "invariant"]
    assert len(invariant) == 16
    assert len({row["pair_id"] for row in invariant}) == 8


def test_source_execution_uses_copied_state_and_descriptor_matches() -> None:
    core = load("full_authz_core_conformance", CORE_PATH)
    for phase in ("registration", "evaluation"):
        for row in core.build_contexts(phase):
            frozen = core.canonical(row["pre_state"])
            after = core.execute_tool(row)
            assert core.canonical(row["pre_state"]) == frozen
            assert core.source_effects(row, after) == core.instantiate_descriptor(row)


def test_all_heldout_pairs_are_policy_separating() -> None:
    core = load("full_authz_core_pairs", CORE_PATH)
    rows = evaluated(core, "evaluation")
    by_pair = {}
    for row in rows:
        by_pair.setdefault(row["pair_id"], []).append(row)
    assert len(by_pair) == 96
    assert all({row["ideal_decision"] for row in pair} == {"ALLOW", "DENY"} for pair in by_pair.values())


def test_policy_engine_does_not_read_labels_or_source_effects() -> None:
    core = load("full_authz_core_no_label", CORE_PATH)
    source = inspect.getsource(core.authorize_observation) + inspect.getsource(core.authorize_atoms) + inspect.getsource(core._rule_status)
    assert "ideal_decision" not in source
    assert "source_effects" not in source
    assert "pair_role" not in source


def test_incomplete_views_abstain_and_known_violations_deny() -> None:
    core = load("full_authz_core_tristate", CORE_PATH)
    policy = core.policy_manifests()[core.POLICY_IDS["workspace"]]
    for name in ("tool_name", "canonical_raw_arguments"):
        decision, _ = core.authorize_observation({"representation": name, "effect_inventory_complete": False, "atoms": [], "opaque": {}}, policy)
        assert decision == "ABSTAIN"
    unsafe = core.atom("share_granted", "grant", "document", "doc:report", target="eve", qualifiers={"permission": "viewer"})
    decision, _ = core.authorize_observation({"effect_inventory_complete": True, "atoms": [unsafe]}, policy)
    assert decision == "DENY"


def test_common_view_is_partial_but_typed_view_is_decisive() -> None:
    core = load("full_authz_core_views", CORE_PATH)
    policies = core.policy_manifests()
    rows = evaluated(core, "evaluation")
    common_decisions, typed_decisions = [], []
    for row in rows:
        common_decisions.append(core.authorize_observation(core.observation(row, "common_effect_fields"), policies[row["policy_id"]])[0])
        typed_decisions.append(core.authorize_observation(core.observation(row, "validated_typed_effects"), policies[row["policy_id"]])[0])
    assert "ABSTAIN" in common_decisions
    assert all(decision in {"ALLOW", "DENY"} for decision in typed_decisions)
    assert typed_decisions == [row["ideal_decision"] for row in rows]


def test_coarse_collisions_and_state_dependent_raw_collisions() -> None:
    core = load("full_authz_core_collision", CORE_PATH)
    runner = load("full_authz_runner_collision", RUNNER_PATH)
    rows = evaluated(core, "evaluation")
    for name in core.REPRESENTATIONS[:-1]:
        summary, _ = runner.collision_audit(rows, name)
        assert summary["n_mixed_cells"] > 0
    typed, _ = runner.collision_audit(rows, "validated_typed_effects")
    assert typed["n_mixed_cells"] == 0
    pairs = runner.pair_audit(rows)
    state_pairs = [row for row in pairs if row["state_dependent"]]
    assert len(state_pairs) >= 20
    assert all(row["representations"]["canonical_raw_arguments"]["collision"] for row in state_pairs)
    assert not any(row["representations"]["validated_typed_effects"]["collision"] for row in state_pairs)


def test_surface_only_registration_variants_preserve_atoms() -> None:
    core = load("full_authz_core_surface", CORE_PATH)
    rows = evaluated(core, "registration")
    by_pair = {}
    for row in rows:
        by_pair.setdefault(row["pair_id"], []).append(row)
    invariant = [pair for pair in by_pair.values() if pair[0]["expected_relation"] == "invariant"]
    assert len(invariant) == 8
    for left, right in invariant:
        assert left["source_effects"] == right["source_effects"]
        assert left["typed_effects"] == right["typed_effects"]
        assert left["ideal_decision"] == right["ideal_decision"]


def test_full_runner_writes_traceable_outputs(tmp_path: Path) -> None:
    runner = load("full_authz_runner_output", RUNNER_PATH)
    report = runner.run("full", tmp_path)
    assert report["status"] == "passed"
    assert report["evaluation"]["n_contexts"] == 192
    assert report["registration"]["n_contexts"] == 144
    for name in (
        "registration-source-executions.jsonl",
        "registration-pair-validation.jsonl",
        "heldout-source-executions.jsonl",
        "authorization-decisions.jsonl",
        "representation-collision-witnesses.jsonl",
        "policy-separating-pair-audit.jsonl",
        "full-scale-authorization-report.json",
        "full-scale-authorization-report.md",
        "direct-policy-metrics.csv",
        "representation-capacity.csv",
        "table_full_scale_deployment_authorization.tex",
        "claim-boundary.md",
        "claim-to-source.md",
        "reproduction-status.json",
    ):
        assert (tmp_path / name).is_file(), name
