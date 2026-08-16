from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_tool_effect_binding_theory.py"
SPEC = importlib.util.spec_from_file_location("theory_check", SCRIPT)
assert SPEC and SPEC.loader
THEORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(THEORY)


def test_insufficient_representations_have_separating_collisions() -> None:
    representation = {
        "none": 0,
        "create": 1,
        "create_and_invite": 1,
    }
    assert not THEORY.authorization_sufficient(representation)
    assert THEORY.separating_collisions(representation)


def test_no_decision_is_both_sound_and_permissive_on_collision() -> None:
    outcomes = THEORY.collision_decision_check(
        "create",
        "create_and_invite",
        frozenset({"create_event"}),
    )
    assert outcomes == {"ALLOW": False, "DENY": False, "ABSTAIN": False}


def test_finite_model_enumeration_passes() -> None:
    result = THEORY.run_checks()
    assert result["status"] == "passed"
    assert result["enumeration"]["n_representations"] == 27
    assert result["multi_policy_sufficiency_verified"] is True
    assert result["conditional_mediation"]["sound_cases_checked"] > 0
    assert (
        result["conditional_mediation"][
            "policy_snapshot_mismatch_counterexample"
        ]["authorized_at_check"]
        is True
    )
    assert result["provenance_profile"][
        "missing_effect_extraction_counterexample"
    ] is True
    assert result["provenance_profile"][
        "unsound_grounding_counterexample"
    ] is True
    assert result["provenance_sensitive_collision"] == {
        "same_effect_multiset": True,
        "opposite_provenance_policy_decisions": True,
        "effect_only_representation_insufficient": True,
    }
    assert result["confinement_chain_verified"] is True
