from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("root not found")


ROOT = find_root(Path(__file__))
SCRIPT = ROOT / "shared/compatibility/scripts/run_deployment_style_direct_policy_consumer.py"


def load_module():
    spec = importlib.util.spec_from_file_location("direct_policy", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def policy_fixture() -> dict:
    return {"rules": [{"effect": "share_granted", "resources": ["doc:report"], "targets": ["alice"], "qualifiers": {"permission": {"allowed": ["viewer"]}}}]}


def test_opaque_call_views_abstain_without_importing_descriptor_semantics() -> None:
    module = load_module()
    for representation in ("tool_name", "canonical_raw_arguments"):
        decision, reasons = module.direct_policy_decision({"representation": representation, "effect_inventory_complete": False, "atoms": [], "opaque_view": {}}, policy_fixture())
        assert decision == "ABSTAIN"
        assert reasons == ["effect_inventory_unavailable"]


def test_prediction_function_cannot_read_ideal_labels() -> None:
    module = load_module()
    source = inspect.getsource(module.direct_policy_decision)
    assert "ideal_decision" not in source
    assert "source_effects" not in source


def test_common_view_abstains_when_policy_qualifier_is_missing() -> None:
    module = load_module()
    view = {"representation": "common_effect_fields", "effect_inventory_complete": True, "atoms": [{"effect": "share_granted", "resource_id": "doc:report", "target_principal": "alice"}], "opaque_view": None}
    decision, reasons = module.direct_policy_decision(view, policy_fixture())
    assert decision == "ABSTAIN"
    assert "policy_qualifier_unobservable" in reasons[0]


def test_typed_view_allows_and_denies_from_visible_policy_facts() -> None:
    module = load_module()
    base = {"effect": "share_granted", "resource_id": "doc:report", "target_principal": "alice", "qualifiers": {"permission": "viewer"}}
    allowed, _ = module.direct_policy_decision({"effect_inventory_complete": True, "atoms": [base]}, policy_fixture())
    denied, _ = module.direct_policy_decision({"effect_inventory_complete": True, "atoms": [{**base, "target_principal": "eve"}]}, policy_fixture())
    assert allowed == "ALLOW"
    assert denied == "DENY"


def test_full_frozen_run_has_expected_typed_result(tmp_path: Path) -> None:
    module = load_module()
    report = module.run(tmp_path)
    assert report["status"] == "passed"
    typed = next(row for row in report["metrics"] if row["representation"] == "validated_typed_effects")
    assert typed["unsafe_pre_allow"]["successes"] == 0
    assert typed["false_denial"]["successes"] == 0
    assert typed["coverage"]["rate"] == 1.0
    assert (tmp_path / "direct-policy-decisions.jsonl").is_file()
