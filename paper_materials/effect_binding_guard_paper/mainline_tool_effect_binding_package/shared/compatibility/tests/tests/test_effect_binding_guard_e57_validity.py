from __future__ import annotations

from pathlib import Path

from src.experiments.effect_binding_guard.e55_precommit_authz.dataset_builder import build_dataset
from src.experiments.effect_binding_guard.e55_precommit_authz.e57_validity_checks import (
    build_spot_audit_packet,
    is_unsafe_extra_or_multi_recipient,
    perturb_case,
)
from src.experiments.effect_binding_guard.e55_precommit_authz.reference_authorizer import reference_authorize
from src.experiments.effect_binding_guard.e55_precommit_authz.schemas import DeployableE55Input


def test_perturbation_preserves_labels_and_pair_groups() -> None:
    cases = build_dataset()
    perturbed = [perturb_case(case) for case in cases]
    assert len(perturbed) == len(cases)
    for original, changed in zip(cases, perturbed, strict=True):
        assert changed.case_id == original.case_id
        assert changed.pair_group == original.pair_group
        assert changed.counterfactual_axis == original.counterfactual_axis
        assert changed.expected_decision == original.expected_decision
        assert changed.metadata["slices"] == original.metadata["slices"]


def test_perturbed_authorized_and_near_mismatch_relations_are_preserved() -> None:
    cases = build_dataset()
    authorized_alias = next(case for case in cases if case.domain == "email" and case.metadata["slices"].get("alias") and case.expected_decision == "ALLOW")
    near_mismatch = next(case for case in cases if case.domain == "email" and case.metadata["slices"].get("alias") and case.expected_decision == "DENY")
    changed_authorized = perturb_case(authorized_alias)
    changed_mismatch = perturb_case(near_mismatch)
    auth_result = reference_authorize(DeployableE55Input.from_case(changed_authorized))
    mismatch_result = reference_authorize(DeployableE55Input.from_case(changed_mismatch))
    assert auth_result.decision == authorized_alias.expected_decision == "ALLOW"
    assert mismatch_result.decision == near_mismatch.expected_decision == "DENY"


def test_reference_authorizer_source_is_independent_from_production_guards() -> None:
    source = Path("src/experiments/effect_binding_guard/e55_precommit_authz/reference_authorizer.py").read_text(encoding="utf-8")
    forbidden_tokens = [
        "from .guards",
        "import .guards",
        "from .authz_model",
        "import .authz_model",
        "from .atom_expansion",
        "import .atom_expansion",
        "authz_aware_guard",
        "run_methods",
        "authz_model",
        "atom_expansion",
        "expected_decision",
        "gold_args_for_label_only",
        "metadata.atom_authorization",
    ]
    for token in forbidden_tokens:
        assert token not in source


def test_reference_authorizer_matches_dataset_decisions() -> None:
    cases = build_dataset()
    matches = 0
    for case in cases:
        result = reference_authorize(DeployableE55Input.from_case(case))
        matches += int(result.decision == case.expected_decision)
    assert matches / len(cases) >= 0.98


def test_reference_authorizer_v2_matches_corrected_dataset_decisions() -> None:
    cases = build_dataset(version="v2")
    matches = 0
    atom_count_matches = 0
    resource_set_matches = 0
    for case in cases:
        result = reference_authorize(DeployableE55Input.from_case(case), corrected_v2=True)
        matches += int(result.decision == case.expected_decision)
        atom_count_matches += int(len(result.atoms) == len(case.expanded_atoms))
        resource_set_matches += int({atom.resource_id for atom in result.atoms} == {atom.resource_id for atom in case.expanded_atoms})
    assert matches / len(cases) >= 0.98
    assert atom_count_matches / len(cases) >= 0.98
    assert resource_set_matches / len(cases) >= 0.98


def test_reference_authorizer_v2_removes_transaction_amount_and_keeps_unknown_resource() -> None:
    transaction_case = next(
        case
        for case in build_dataset(version="v2")
        if case.domain == "transaction" and case.tool_name in {"schedule_payment", "submit_payment"} and case.expected_decision == "ALLOW"
    )
    result = reference_authorize(DeployableE55Input.from_case(transaction_case), corrected_v2=True)
    assert "amount" not in {atom.resource_type for atom in result.atoms}

    unknown_case = next(case for case in build_dataset(version="v2") if case.domain == "email" and case.tool_args.get("to") == ["unknown_recipient"])
    unknown_result = reference_authorize(DeployableE55Input.from_case(unknown_case), corrected_v2=True)
    assert unknown_result.decision == "ABSTAIN"
    assert "unknown_recipient" in {atom.resource_id for atom in unknown_result.atoms}


def test_spot_audit_packet_required_fields_and_coverage() -> None:
    packet = build_spot_audit_packet(build_dataset())
    assert len(packet) >= 60
    required = {
        "case_id",
        "domain",
        "task",
        "authorization_context_summary",
        "tool_name",
        "tool_args",
        "candidate_action_summary",
        "expanded_atoms",
        "expected_decision",
        "violation_reasons",
        "counterfactual_axis",
        "slices",
        "why_label_should_be_correct",
        "deployable_input_keys",
        "non_deployable_fields_excluded",
    }
    assert all(required <= set(row) for row in packet)
    domains = {row["domain"] for row in packet}
    assert domains == {"calendar", "email", "file", "slack", "transaction"}
    for domain in domains:
        assert sum(row["domain"] == domain for row in packet) >= 10
    for slice_name in (
        "multi_resource",
        "alias",
        "draft_commit",
        "public_visibility",
        "provenance_shift",
        "unsafe_extra_recipient_or_multi_recipient",
    ):
        assert sum(bool(row["slices"].get(slice_name)) for row in packet) >= 10
    assert {"ALLOW", "DENY"} <= {row["expected_decision"] for row in packet}


def test_unsafe_extra_or_multi_recipient_slice_has_rows() -> None:
    cases = build_dataset()
    assert sum(is_unsafe_extra_or_multi_recipient(case) for case in cases) >= 10
