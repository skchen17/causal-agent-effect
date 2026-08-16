from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_pact_compatible_representation_comparison.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pact_comparison", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_argument_role_maps_cover_frozen_inputs():
    module = load_module()
    for row in module.normalize_finite() + module.normalize_heldout():
        role_map = module.ARGUMENT_ROLES[row["tool_name"]]
        assert set(row["arguments"]) <= set(role_map)


def test_maximal_argument_view_preserves_fresh_state_finite_domain():
    module = load_module()
    summary, _ = module.analyze_representation(
        module.normalize_finite(), "pact_value_role_provenance"
    )
    assert summary["n_contexts"] == 56
    assert summary["finite_collision_complete"] is True


def test_prestate_separates_effect_occurrences_from_call_arguments():
    module = load_module()
    rows = module.normalize_heldout()
    argument_summary, witnesses = module.analyze_representation(
        rows, "pact_value_role_provenance"
    )
    typed_summary, _ = module.analyze_representation(
        rows, "typed_effect_occurrence"
    )
    assert argument_summary["n_contexts"] == 32
    assert argument_summary["authorization_collision_cells"] > 0
    assert argument_summary["authorization_separating_pairs"] > 0
    assert typed_summary["authorization_collision_cells"] == 0
    assert typed_summary["overpartition_pairs"] == 0
    assert any(
        row["same_arguments"] and row["left_state"] != row["right_state"]
        for row in witnesses
    )


def test_full_run_emits_traceable_artifacts():
    module = load_module()
    report = module.run()
    assert report["status"] == "passed"
    assert report["datasets"] == {
        "agentdojo_finite_56": 56,
        "toolsandbox_heldout_32": 32,
    }
    assert report["n_same_argument_state_witnesses"] > 0
    for path in (
        module.REPORT_JSON,
        module.REPORT_MD,
        module.SUMMARY_CSV,
        module.WITNESSES_JSONL,
    ):
        assert path.exists()
