from __future__ import annotations

from pathlib import Path

from src.experiments.effect_binding_guard.dataset import build_unified_dataset
from src.experiments.effect_binding_guard.run_e50 import (
    FIXED_POLICY,
    build_control_provenance_stress,
    build_resource_authorization_stress,
    leakage_audit,
    loso_splits,
    run_e50_variants,
    select_policy,
    source_balanced_splits,
    validate_stress,
)
from src.experiments.effect_binding_guard.schema import contains_forbidden_key


ROOT = Path(__file__).resolve().parents[2]


def load_rows():
    rows, pairs, manifest = build_unified_dataset(ROOT)
    return rows, pairs, manifest


def test_e50_loads_e48_core_and_leakage_is_zero() -> None:
    rows, pairs, manifest = load_rows()
    assert len(rows) == 822
    assert len(pairs) == 6840
    assert not manifest["deployable_input_leakage_violations"]
    audit = leakage_audit(rows)
    assert audit["leakage_free"]
    assert all(not contains_forbidden_key(row.deployable_input) for row in rows)


def test_e50_variants_emit_required_methods_for_each_row() -> None:
    rows, _, _ = load_rows()
    sample = rows[:8]
    predictions = run_e50_variants(sample, qwen_predictions={}, policy=FIXED_POLICY)
    methods = {prediction.method for prediction in predictions}
    required = {
        "rule_tuple_guard",
        "multi_view_disagreement_guard",
        "evidence_gated_selective_guard",
        "control_provenance_minimal_check",
        "effect_binding_guard_full",
        "full_without_provenance_overlay",
        "full_without_evidence_fallback",
        "full_without_multi_view_disagreement",
        "full_without_local_qwen_view",
        "always_use_evidence",
        "allow_all",
        "deny_all",
    }
    assert required <= methods
    for method in required:
        assert sum(pred.method == method for pred in predictions) == len(sample)


def test_source_balanced_splits_have_no_overlap_and_include_sources() -> None:
    rows, _, _ = load_rows()
    spec = source_balanced_splits(rows, seeds=[0])[0]
    assert not (set(spec.train_groups) & set(spec.validation_groups))
    assert not (set(spec.train_groups) & set(spec.test_groups))
    assert not (set(spec.validation_groups) & set(spec.test_groups))
    for groups in (spec.train_groups, spec.validation_groups, spec.test_groups):
        sources = {row.source_scope for row in rows if row.split_group_id in groups}
        assert {"phase4", "ipiguard", "camel"} <= sources


def test_loso_splits_hold_out_each_source() -> None:
    rows, _, _ = load_rows()
    specs = loso_splits(rows)
    assert {spec.name for spec in specs} == {"strict_loso_camel", "strict_loso_ipiguard", "strict_loso_phase4"}
    for spec in specs:
        target = spec.name.removeprefix("strict_loso_")
        assert any(row.source_scope == target and row.split_group_id in spec.test_groups for row in rows)
        assert all(row.source_scope != target for row in rows if row.split_group_id in spec.train_groups and target == "camel")


def test_select_policy_uses_only_supplied_validation_rows() -> None:
    rows, _, _ = load_rows()
    validation = rows[:12]
    result = select_policy(validation, {}, objective="safety_first")
    assert result["selected"]["policy"]
    assert len(result["candidates"]) > 1


def test_resource_authorization_stress_count_balance_and_metadata() -> None:
    rows, _, _ = load_rows()
    stress = build_resource_authorization_stress(rows)
    validation = validate_stress(stress, expected_rows=240, name="resource_authorization")
    assert validation["valid"]
    assert validation["label_counts"] == {"ALLOW": 120, "DENY": 120}
    assert all(row.source_scope == "e50_resource_authorization_stress" for row in stress)
    assert all(row.metadata["audit_required"] is True for row in stress)
    assert all(not contains_forbidden_key(row.deployable_input) for row in stress)
    assert all(
        row.metadata["policy_oracle"]["expected_decision"] == row.labels["expected_decision"]
        for row in stress
    )
    assert all(
        row.metadata["authorized_effects"] == row.metadata["policy_oracle"]["authorized_effects"]
        and row.metadata["authorized_resources"] == row.metadata["policy_oracle"]["authorized_resources"]
        for row in stress
    )
    aliases = [row for row in stress if row.counterfactual_axis == "authorized_resource_alias"]
    assert aliases
    assert all((row.deployable_input["authorization_context"]["resource_aliases"]) for row in aliases)
    assert all(
        row.labels["gold_resource"] in row.deployable_input["authorization_context"]["resource_aliases"]
        for row in aliases
    )
    alternate = [row for row in stress if row.counterfactual_axis == "same_resource_different_effect"]
    assert all(row.labels["gold_effect"] not in row.metadata["policy_oracle"]["authorized_effects"] for row in alternate)
    commit = [row for row in stress if row.counterfactual_axis == "commit_not_authorized"]
    assert all(row.metadata["policy_oracle"]["commit_allowed"] is False for row in commit)
    assert all("Committing external effects is not authorized" in row.deployable_input["user_task"] for row in commit)


def test_control_provenance_stress_count_and_policy_axes() -> None:
    stress = build_control_provenance_stress()
    validation = validate_stress(stress, expected_rows=336, name="control_provenance")
    assert validation["valid"]
    assert all(row.source_scope == "e50_control_provenance_stress" for row in stress)
    action_types = {row.metadata["action_type"] for row in stress}
    assert "side_effectful_create" in action_types
    assert "side_effectful_cancel" in action_types
    private_side_effect = [
        row
        for row in stress
        if row.metadata["control_source"] == "private_tool_output"
        and row.metadata["action_type"].startswith("side_effectful")
    ]
    assert private_side_effect
    assert all(row.labels["expected_decision"] == "DENY" for row in private_side_effect)
