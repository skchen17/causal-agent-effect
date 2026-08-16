from __future__ import annotations

from pathlib import Path

import numpy as np

from src.experiments.effect_binding_calibrator.features import (
    CALIBRATED_E48_METHODS,
    build_feature_rows,
    leakage_audit,
    load_local_qwen_predictions,
)
from src.experiments.effect_binding_calibrator.models import fit_calibrator, predict_risk, risk_predictions
from src.experiments.effect_binding_calibrator.splits import build_e49_splits, rows_for_groups
from src.experiments.effect_binding_calibrator.stress import (
    build_control_provenance_stress,
    build_resource_authorization_stress,
    validate_stress,
)
from src.experiments.effect_binding_guard.dataset import build_unified_dataset


ROOT = Path(__file__).resolve().parents[1]


def load_feature_rows():
    rows, _, _ = build_unified_dataset(ROOT)
    qwen = load_local_qwen_predictions(ROOT / "analysis/results/e48_local_qwen_tuple_predictions.jsonl")
    return rows, build_feature_rows(rows, qwen)


def test_e49_feature_table_count_and_leakage_policy() -> None:
    _, feature_rows = load_feature_rows()
    assert len(feature_rows) == 822
    audit = leakage_audit(feature_rows)
    assert audit["leakage_free"]
    feature_names = {key for row in feature_rows for key in row.features}
    forbidden_tokens = {"pair_role", "counterfactual_axis", "claim_scope", "audit_status", "source_scope", "gold_", "expected_decision"}
    assert not any(any(token in key for token in forbidden_tokens) for key in feature_names)
    assert not any(method in key for method in CALIBRATED_E48_METHODS for key in feature_names)
    assert not any("raw_resource" in key or "resource_value" in key for key in feature_names)


def test_source_balanced_splits_have_no_group_leakage_and_include_sources() -> None:
    _, feature_rows = load_feature_rows()
    splits = build_e49_splits(feature_rows, seeds=[0])
    spec = next(split for split in splits if split.name == "source_balanced_seed0")
    assert not (set(spec.train_groups) & set(spec.validation_groups))
    assert not (set(spec.train_groups) & set(spec.test_groups))
    assert not (set(spec.validation_groups) & set(spec.test_groups))
    for groups in (spec.train_groups, spec.validation_groups, spec.test_groups):
        sources = {row.source_scope for row in rows_for_groups(feature_rows, groups)}
        assert {"phase4", "ipiguard", "camel"} <= sources


def test_model_fit_predicts_without_construction_metadata() -> None:
    _, feature_rows = load_feature_rows()
    spec = next(split for split in build_e49_splits(feature_rows, seeds=[0]) if split.name == "source_balanced_seed0")
    train = rows_for_groups(feature_rows, spec.train_groups)
    test = rows_for_groups(feature_rows, spec.test_groups)
    model = fit_calibrator(train, method="logistic_calibrator")
    risk = predict_risk(model, test)
    assert len(risk) == len(test)
    assert np.all(risk >= 0.0)
    assert np.all(risk <= 1.0)
    names = set(model.vectorizer.get_feature_names_out())
    assert not any("pair_role" in name or "counterfactual_axis" in name or "source_scope" in name for name in names)


def test_provenance_overlay_blocks_private_control_even_with_allow_risk() -> None:
    rows, feature_rows = load_feature_rows()
    row_by_id = {row.case_id: row for row in rows}
    private_row = next(row for row in rows if row.source_scope == "camel" and row.labels["gold_provenance_risk"] == "private_control")
    private_feature = next(row for row in feature_rows if row.case_id == private_row.case_id)
    pred = risk_predictions(
        [private_feature],
        row_by_id,
        np.asarray([0.0]),
        0.2,
        0.8,
        method_name="test_calibrator",
        overlay=True,
    )[0]
    assert pred.decision == "DENY"


def test_stress_sets_have_expected_counts_and_balance() -> None:
    rows, _ = load_feature_rows()
    resauth = build_resource_authorization_stress(rows)
    provenance = build_control_provenance_stress()
    assert validate_stress(resauth, expected_rows=240, name="resource_authorization")["valid"]
    assert validate_stress(provenance, expected_rows=294, name="control_provenance")["valid"]
    assert sum(row.labels["expected_decision"] == "ALLOW" for row in resauth) == 120
    assert sum(row.labels["expected_decision"] == "DENY" for row in resauth) == 120
    assert all(row.metadata["construction_constraint"] == "evaluation_only_not_used_for_training_or_threshold_selection" for row in resauth + provenance)
