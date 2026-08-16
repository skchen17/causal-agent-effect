from __future__ import annotations

import json
from pathlib import Path

from src.experiments.effect_binding_guard.dataset import build_unified_dataset
from src.experiments.effect_binding_guard.guards import (
    evidence_gated,
    infer_evidence_tuple,
    provenance_overlay,
    rule_tuple,
    view_predictions,
)
from src.experiments.effect_binding_guard.local_qwen import parse_output
from src.experiments.effect_binding_guard.metrics import bootstrap_group_values, pair_metrics
from src.experiments.effect_binding_guard.pairwise import run_pairwise_diagnostic
from src.experiments.effect_binding_guard.run_e48 import calibrate_policy, failure_examples, split_name
from src.experiments.effect_binding_guard.schema import EffectBindingRow, contains_forbidden_key


ROOT = Path(__file__).resolve().parents[2]


def load_rows() -> tuple[list[EffectBindingRow], list[dict], dict]:
    return build_unified_dataset(ROOT)


def test_unified_dataset_counts_and_no_leakage() -> None:
    rows, pairs, manifest = load_rows()
    assert len(rows) == 822
    assert len(pairs) == 6840
    assert manifest["source_counts"] == {"phase4": 528, "ipiguard": 240, "camel": 54}
    assert not manifest["deployable_input_leakage_violations"]
    assert not manifest["deployable_input_string_marker_violations"]
    assert all(not contains_forbidden_key(row.deployable_input) for row in rows)


def test_shared_phase4_ipiguard_anchor_uses_same_split_group() -> None:
    rows, _, manifest = load_rows()
    by_split: dict[str, set[str]] = {}
    for row in rows:
        by_split.setdefault(row.split_group_id, set()).add(row.source_scope)
    shared = [group for group, scopes in by_split.items() if {"phase4", "ipiguard"} <= scopes]
    assert len(shared) == 24
    assert manifest["shared_split_group_count"] == 24
    assert all(split_name(group) in {"train", "validation", "test"} for group in shared)


def test_audit_status_and_corrected_camel_labels() -> None:
    rows, _, _ = load_rows()
    assert sum(row.audit_status != "audit_gated_construction" for row in rows) == 222
    corrected = [row for row in rows if row.audit_status == "corrected_label_audited"]
    assert len(corrected) == 6
    assert all(row.labels["gold_effect"] == "no_external_side_effect" for row in corrected)


def test_masked_tool_view_preserves_arguments() -> None:
    rows, _, _ = load_rows()
    row = next(item for item in rows if item.source_scope == "phase4" and item.deployable_input["candidate_action"].get("arguments"))
    masked = row.deployable_input["masked_tool_view"]
    assert masked["tool_name"] == "<MASKED_TOOL>"
    assert masked["arguments"] == row.deployable_input["candidate_action"]["arguments"]


def test_rule_tuple_authorization_pair_changes_decision() -> None:
    rows, _, _ = load_rows()
    group = next(row.counterfactual_group_id for row in rows if row.source_scope == "phase4")
    items = {row.pair_role: row for row in rows if row.counterfactual_group_id == group}
    allowed = rule_tuple(items["authorized_match_original"])
    denied = rule_tuple(items["unauthorized_same_effect_original"])
    assert allowed.decision in {"ALLOW", "ABSTAIN"}
    assert denied.decision == "DENY"


def test_provenance_check_denies_private_control_and_abstains_untrusted_data() -> None:
    rows, _, _ = load_rows()
    private = next(row for row in rows if row.source_scope == "camel" and row.pair_role == "control_dependency_private")
    untrusted = next(row for row in rows if row.source_scope == "camel" and row.pair_role == "untrusted_source")
    private_result = provenance_overlay(private, rule_tuple(private, use_provenance=False), method="test")
    untrusted_result = provenance_overlay(untrusted, rule_tuple(untrusted, use_provenance=False), method="test")
    assert private_result.decision == "DENY"
    assert untrusted_result.decision == "ABSTAIN"


def test_evidence_guard_only_accesses_non_oracle_evidence() -> None:
    rows, _, _ = load_rows()
    row = next(item for item in rows if item.deployable_input["evidence_summary"])
    result = infer_evidence_tuple(row)
    assert set(result.accessed_fields) <= {"evidence_summary", "provenance_summary", "user_task"}
    assert not contains_forbidden_key({key: row.deployable_input.get(key) for key in result.accessed_fields})


def test_local_qwen_parse_failure_is_abstain() -> None:
    rows, _, _ = load_rows()
    result = parse_output(rows[0], "not json")
    assert result.decision == "ABSTAIN"
    assert result.metadata["parse_valid"] is False


def test_local_qwen_valid_json_parses_required_tuple() -> None:
    rows, _, _ = load_rows()
    result = parse_output(
        rows[0],
        '{"effect":"message_sent","resource":"alice@example.com","authorization_match":"denied",'
        '"provenance_risk":"trusted","decision":"DENY","confidence":0.9,"reason":"not authorized"}',
    )
    assert result.decision == "DENY"
    assert result.predicted_effect == "message_sent"
    assert result.authorization_match == "denied"
    assert result.metadata["parse_valid"] is True


def test_pair_labels_and_changed_fields_are_consistent() -> None:
    rows, pairs, _ = load_rows()
    row_by_id = {row.case_id: row for row in rows}
    for pair in pairs[:300]:
        left = row_by_id[pair["left_case_id"]]
        right = row_by_id[pair["right_case_id"]]
        expected_relation = (
            "should_same_decision"
            if left.labels["expected_decision"] == right.labels["expected_decision"]
            else "should_flip_decision"
        )
        assert pair["relation_label"] == expected_relation
        assert pair["split_group_id"] == left.split_group_id == right.split_group_id


def test_pairwise_folds_have_no_group_leakage() -> None:
    rows, pairs, _ = load_rows()
    result = run_pairwise_diagnostic(rows, pairs)
    assert all(not fold["group_overlap"] for fold in result["folds"])
    assert result["paired_delta_pairwise_vs_independent"]["n_groups"] == len(
        {row.split_group_id for row in rows}
    )


def test_calibration_only_reads_validation_groups(monkeypatch) -> None:
    rows, _, _ = load_rows()
    observed = []

    def fake_summary(items, predictions, pairs, bootstrap_iters=50):
        del predictions, pairs, bootstrap_iters
        observed.extend(item.split_group_id for item in items)
        metric = {"rate": 0.0}
        return {
            "calibration_candidate": {
                "overall": {
                    "unsafe_pre_allow": metric,
                    "safe_false_deny": metric,
                    "coverage": metric,
                }
            }
        }

    monkeypatch.setattr("src.experiments.effect_binding_guard.run_e48.summarize_predictions", fake_summary)
    result = calibrate_policy(rows, None)
    assert result["n_candidates"] == 64
    assert observed
    assert all(split_name(group) == "validation" for group in observed)


def test_bootstrap_and_failure_examples_schema() -> None:
    interval = bootstrap_group_values({"a": 0.0, "b": 1.0}, bootstrap_iters=50, seed=0)
    assert interval["ci_low"] <= interval["rate"] <= interval["ci_high"]
    rows, _, _ = load_rows()
    denied = next(row for row in rows if row.labels["expected_decision"] == "DENY")
    prediction = parse_output(
        denied,
        '{"effect":"unknown","resource":"unknown","authorization_match":"allowed",'
        '"provenance_risk":"trusted","decision":"ALLOW","confidence":0.9,"reason":"allowed"}',
        method="effect_binding_guard_full",
    )
    example = failure_examples([denied], [prediction], limit=1)[0]
    assert {
        "method",
        "failure_type",
        "case_id",
        "source_scope",
        "expected_decision",
        "predicted_decision",
        "predicted_tuple",
        "interpretation",
        "claim_scope",
    } <= set(example)


def test_pair_metrics_bootstrap_independent_split_groups() -> None:
    rows, pairs, _ = load_rows()
    predictions = [rule_tuple(row) for row in rows]
    result = pair_metrics(pairs, {prediction.case_id: prediction for prediction in predictions}, bootstrap_iters=50)
    relation = result["pair_relation_accuracy"]
    assert result["n_groups"] == len({pair["split_group_id"] for pair in pairs})
    assert relation["statistical_unit"] == "split_group_id"
    assert relation["n_groups"] == result["n_groups"]
    assert relation["total"] == len(pairs)
