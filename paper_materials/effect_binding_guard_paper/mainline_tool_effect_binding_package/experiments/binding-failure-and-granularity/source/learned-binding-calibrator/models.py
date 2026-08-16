from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import sparse
from sklearn.calibration import calibration_curve
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.svm import LinearSVC

from src.experiments.effect_binding_guard.guards import is_side_effectful, provenance_overlay
from src.experiments.effect_binding_guard.metrics import (
    bootstrap_group_values,
    paired_method_delta,
    row_metrics,
    summarize_method,
)
from src.experiments.effect_binding_guard.schema import EffectBindingRow, TuplePrediction, stable_hash

from .features import FeatureRow


@dataclass
class FittedCalibrator:
    method: str
    vectorizer: Any
    model: Any
    platt: Any | None
    feature_mode: str
    overlay: bool
    text_vectorizer: Any | None = None


def fit_calibrator(
    rows: list[FeatureRow],
    *,
    method: str,
    feature_mode: str = "full",
    overlay: bool = True,
) -> FittedCalibrator:
    y = np.asarray([row.label for row in rows], dtype=int)
    if method == "text_only_classifier_baseline":
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=12000)
        matrix = vectorizer.fit_transform([row.text for row in rows])
        model = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0)
        model.fit(matrix, y)
        return FittedCalibrator(method, None, model, None, feature_mode, overlay, text_vectorizer=vectorizer)

    features = [select_features(row.features, feature_mode) for row in rows]
    vectorizer = DictVectorizer(sparse=True)
    matrix = vectorizer.fit_transform(features)
    if method == "logistic_calibrator":
        model = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0, C=1.0)
        model.fit(matrix, y)
        return FittedCalibrator(method, vectorizer, model, None, feature_mode, overlay)
    if method == "calibrated_linear_fusion":
        base = LinearSVC(class_weight="balanced", random_state=0, C=0.5, max_iter=5000)
        scores = crossfit_linear_scores(matrix, y, [row.split_group_id for row in rows])
        platt = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=0)
        platt.fit(scores.reshape(-1, 1), y)
        base.fit(matrix, y)
        return FittedCalibrator(method, vectorizer, base, platt, feature_mode, overlay)
    if method == "small_gbdt_fusion":
        dense = matrix.toarray() if sparse.issparse(matrix) else matrix
        model = GradientBoostingClassifier(n_estimators=50, max_depth=2, learning_rate=0.05, random_state=0)
        model.fit(dense, y)
        return FittedCalibrator(method, vectorizer, model, None, feature_mode, overlay)
    raise ValueError(f"Unknown E49 calibrator method: {method}")


def crossfit_linear_scores(matrix: Any, y: np.ndarray, groups: list[str]) -> np.ndarray:
    unique_groups = sorted(set(groups))
    if len(unique_groups) < 3:
        model = LinearSVC(class_weight="balanced", random_state=0, C=0.5, max_iter=5000)
        model.fit(matrix, y)
        return model.decision_function(matrix)
    scores = np.zeros(len(y), dtype=float)
    for fold, group in enumerate(unique_groups):
        test_idx = np.asarray([idx for idx, value in enumerate(groups) if value == group])
        train_idx = np.asarray([idx for idx, value in enumerate(groups) if value != group])
        if len(set(y[train_idx])) < 2:
            scores[test_idx] = float(np.mean(y[train_idx])) if len(train_idx) else 0.5
            continue
        model = LinearSVC(class_weight="balanced", random_state=fold, C=0.5, max_iter=5000)
        model.fit(matrix[train_idx], y[train_idx])
        scores[test_idx] = model.decision_function(matrix[test_idx])
    return scores


def predict_risk(model: FittedCalibrator, rows: list[FeatureRow]) -> np.ndarray:
    if model.method == "text_only_classifier_baseline":
        matrix = model.text_vectorizer.transform([row.text for row in rows])
        return model.model.predict_proba(matrix)[:, 1]
    features = [select_features(row.features, model.feature_mode) for row in rows]
    matrix = model.vectorizer.transform(features)
    if model.method in {"logistic_calibrator"}:
        return model.model.predict_proba(matrix)[:, 1]
    if model.method == "calibrated_linear_fusion":
        scores = model.model.decision_function(matrix)
        return model.platt.predict_proba(scores.reshape(-1, 1))[:, 1]
    if model.method == "small_gbdt_fusion":
        return model.model.predict_proba(matrix.toarray() if sparse.issparse(matrix) else matrix)[:, 1]
    raise ValueError(model.method)


def select_features(features: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode == "full":
        return dict(features)
    selected = {}
    for key, value in features.items():
        if mode == "no_provenance" and ("provenance" in key or "control_" in key or "side_effectful" in key or "data_private" in key):
            continue
        if mode == "no_evidence" and "evidence" in key:
            continue
        if mode == "no_disagreement" and ("disagreement" in key or "vote_count" in key or "vote_ratio" in key):
            continue
        if mode == "no_local_qwen" and "local_qwen" in key:
            continue
        if mode == "decision_votes_only" and not ("vote_count" in key or "vote_ratio" in key or "__decision__" in key):
            continue
        if mode == "tuple_fields_only" and not any(token in key for token in ("predicted_effect", "authorization_match", "provenance_risk", "resource_type", "__auth__", "__provenance__", "__effect__")):
            continue
        selected[key] = value
    return selected


def calibrate_thresholds(
    feature_rows: list[FeatureRow],
    original_rows: dict[str, EffectBindingRow],
    risk: np.ndarray,
    *,
    method_name: str,
    alpha: float = 0.10,
    overlay: bool = True,
    objective: str = "safety_first",
) -> dict[str, Any]:
    candidates = [round(value, 2) for value in np.linspace(0.0, 1.0, 21)]
    scored = []
    for allow in candidates:
        for deny in candidates:
            if allow > deny:
                continue
            preds = risk_predictions(feature_rows, original_rows, risk, allow, deny, method_name=method_name, overlay=overlay)
            metrics = row_metrics([original_rows[row.case_id] for row in feature_rows], {pred.case_id: pred for pred in preds})
            upa = rate(metrics["unsafe_pre_allow"])
            fd = rate(metrics["safe_false_deny"])
            coverage = rate(metrics["coverage"])
            scored.append(
                {
                    "allow_threshold": allow,
                    "deny_threshold": deny,
                    "unsafe_pre_allow": upa,
                    "safe_false_deny": fd,
                    "coverage": coverage,
                    "abstain": rate(metrics["abstain_rate"]),
                    "safe_allowed_rate": rate(metrics["safe_allowed_rate"]),
                    "metrics": metrics,
                }
            )
    if objective == "utility_first":
        feasible = [row for row in scored if row["unsafe_pre_allow"] <= max(alpha, 0.15)]
        key = lambda row: (row["coverage"], -row["unsafe_pre_allow"], -row["safe_false_deny"])
    elif objective == "balanced":
        feasible = scored
        key = lambda row: (-(row["unsafe_pre_allow"] + row["safe_false_deny"] + row["abstain"]), row["coverage"])
    else:
        feasible = [row for row in scored if row["unsafe_pre_allow"] <= alpha]
        key = lambda row: (row["coverage"], -row["safe_false_deny"], -row["unsafe_pre_allow"])
    if not feasible:
        feasible = scored
        gate = False
        key = lambda row: (-row["unsafe_pre_allow"], row["coverage"], -row["safe_false_deny"])
    else:
        gate = True
    selected = max(feasible, key=key)
    return {
        "alpha": alpha,
        "objective": objective,
        "gate_passed": gate,
        "selected": {k: v for k, v in selected.items() if k != "metrics"},
        "n_candidates": len(scored),
    }


def risk_predictions(
    feature_rows: list[FeatureRow],
    original_rows: dict[str, EffectBindingRow],
    risk: np.ndarray,
    allow_threshold: float,
    deny_threshold: float,
    *,
    method_name: str,
    overlay: bool = True,
) -> list[TuplePrediction]:
    preds = []
    for row, score in zip(feature_rows, risk):
        if score <= allow_threshold:
            decision, reason = "ALLOW", "risk_below_allow_threshold"
        elif score >= deny_threshold:
            decision, reason = "DENY", "risk_above_deny_threshold"
        else:
            decision, reason = "ABSTAIN", "risk_in_selective_band"
        tuple_fields = row.majority_tuple
        pred = TuplePrediction(
            case_id=row.case_id,
            method=method_name,
            source_scope=row.source_scope,
            split_group_id=row.split_group_id,
            predicted_effect=tuple_fields["predicted_effect"],
            predicted_resource=tuple_fields["predicted_resource"],
            authorization_match=tuple_fields["authorization_match"],
            provenance_risk=tuple_fields["provenance_risk"],
            decision=decision,
            confidence=float(max(score, 1.0 - score)),
            uncertainty=float(min(score, 1.0 - score)),
            abstain_reason=reason if decision == "ABSTAIN" else "",
            accessed_fields=["e49_non_oracle_fusion_features", "provenance_summary"],
            decision_inputs_hash=stable_hash(
                {
                    "feature_input_hash": row.metadata.get("feature_input_hash"),
                    "risk": round(float(score), 6),
                    "allow": allow_threshold,
                    "deny": deny_threshold,
                }
            ),
            metadata={
                "risk_score": float(score),
                "allow_threshold": allow_threshold,
                "deny_threshold": deny_threshold,
                "decision_reason": reason,
                "provenance_hard_overlay": overlay,
            },
        )
        if overlay:
            pred = provenance_overlay(original_rows[row.case_id], pred, method=method_name)
            pred.metadata = {
                **pred.metadata,
                "risk_score": float(score),
                "allow_threshold": allow_threshold,
                "deny_threshold": deny_threshold,
                "provenance_hard_overlay": True,
            }
        preds.append(pred)
    return preds


def evaluate_model_on_split(
    model: FittedCalibrator,
    train_rows: list[FeatureRow],
    validation_rows: list[FeatureRow],
    test_rows: list[FeatureRow],
    original_rows: dict[str, EffectBindingRow],
    *,
    alpha: float = 0.10,
    objective: str = "safety_first",
    bootstrap_iters: int = 500,
) -> dict[str, Any]:
    validation_risk = predict_risk(model, validation_rows)
    selected = calibrate_thresholds(
        validation_rows,
        original_rows,
        validation_risk,
        method_name=model_name(model),
        alpha=alpha,
        overlay=model.overlay,
        objective=objective,
    )
    test_risk = predict_risk(model, test_rows)
    preds = risk_predictions(
        test_rows,
        original_rows,
        test_risk,
        selected["selected"]["allow_threshold"],
        selected["selected"]["deny_threshold"],
        method_name=model_name(model),
        overlay=model.overlay,
    )
    original_test_rows = [original_rows[row.case_id] for row in test_rows]
    summary = summarize_method(original_test_rows, preds, [], bootstrap_iters=bootstrap_iters, seed=0)
    y_true = np.asarray([row.label for row in test_rows], dtype=int)
    brier = brier_score_loss(y_true, test_risk) if len(set(y_true)) > 1 else None
    ece = expected_calibration_error(y_true, test_risk) if len(set(y_true)) > 1 else None
    return {
        "method": model_name(model),
        "feature_mode": model.feature_mode,
        "overlay": model.overlay,
        "alpha": alpha,
        "objective": objective,
        "calibration": selected,
        "summary": summary,
        "brier_score": brier,
        "ece": ece,
        "risk_summary": {
            "test_min": float(np.min(test_risk)) if len(test_risk) else None,
            "test_mean": float(np.mean(test_risk)) if len(test_risk) else None,
            "test_max": float(np.max(test_risk)) if len(test_risk) else None,
        },
        "predictions": [pred.to_dict() for pred in preds],
    }


def model_name(model: FittedCalibrator) -> str:
    suffix = "" if model.feature_mode == "full" else f"__{model.feature_mode}"
    suffix += "" if model.overlay else "__no_provenance_overlay"
    return f"{model.method}{suffix}"


def risk_curve(
    feature_rows: list[FeatureRow],
    original_rows: dict[str, EffectBindingRow],
    risk: np.ndarray,
    *,
    method_name: str,
    overlay: bool,
) -> dict[str, Any]:
    points = []
    for threshold in [round(value, 2) for value in np.linspace(0, 1, 51)]:
        preds = risk_predictions(
            feature_rows,
            original_rows,
            risk,
            threshold,
            threshold,
            method_name=method_name,
            overlay=overlay,
        )
        metrics = row_metrics([original_rows[row.case_id] for row in feature_rows], {pred.case_id: pred for pred in preds})
        points.append(
            {
                "threshold": threshold,
                "unsafe_pre_allow": rate(metrics["unsafe_pre_allow"]),
                "safe_false_deny": rate(metrics["safe_false_deny"]),
                "coverage": rate(metrics["coverage"]),
                "abstain": rate(metrics["abstain_rate"]),
            }
        )
    return {"method": method_name, "points": points}


def threshold_heatmap(
    feature_rows: list[FeatureRow],
    original_rows: dict[str, EffectBindingRow],
    risk: np.ndarray,
    *,
    method_name: str,
    overlay: bool,
) -> list[dict[str, Any]]:
    rows = []
    grid = [round(value, 2) for value in np.linspace(0, 1, 21)]
    for allow in grid:
        for deny in grid:
            if allow > deny:
                continue
            preds = risk_predictions(feature_rows, original_rows, risk, allow, deny, method_name=method_name, overlay=overlay)
            metrics = row_metrics([original_rows[row.case_id] for row in feature_rows], {pred.case_id: pred for pred in preds})
            rows.append(
                {
                    "allow_threshold": allow,
                    "deny_threshold": deny,
                    "unsafe_pre_allow": rate(metrics["unsafe_pre_allow"]),
                    "safe_false_deny": rate(metrics["safe_false_deny"]),
                    "coverage": rate(metrics["coverage"]),
                    "abstain": rate(metrics["abstain_rate"]),
                }
            )
    return rows


def expected_calibration_error(y_true: np.ndarray, risk: np.ndarray, *, n_bins: int = 10) -> dict[str, Any]:
    bins = np.linspace(0, 1, n_bins + 1)
    total = len(risk)
    ece = 0.0
    records = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (risk >= lo) & (risk < hi if i < n_bins - 1 else risk <= hi)
        if not np.any(mask):
            continue
        conf = float(np.mean(risk[mask]))
        acc = float(np.mean(y_true[mask]))
        weight = float(np.sum(mask) / total)
        ece += weight * abs(acc - conf)
        records.append({"bin_low": float(lo), "bin_high": float(hi), "mean_risk": conf, "empirical_deny_rate": acc, "n": int(np.sum(mask))})
    return {"ece": ece, "bins": records}


def rate(metric: dict[str, Any]) -> float:
    value = metric.get("rate") if isinstance(metric, dict) else metric
    return 0.0 if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)


def paired_delta_summary(
    rows: list[EffectBindingRow],
    left: list[TuplePrediction],
    right: list[TuplePrediction],
    *,
    bootstrap_iters: int,
) -> dict[str, Any]:
    return {
        metric: paired_method_delta(rows, left, right, metric=metric, bootstrap_iters=bootstrap_iters)
        for metric in ("unsafe_pre_allow", "safe_false_deny", "coverage", "safe_allowed_rate")
    }


def coefficients(model: FittedCalibrator, top_k: int = 30) -> list[dict[str, Any]]:
    if not hasattr(model.model, "coef_") or model.vectorizer is None:
        return []
    names = model.vectorizer.get_feature_names_out()
    coef = model.model.coef_[0]
    order = np.argsort(np.abs(coef))[::-1][:top_k]
    return [{"feature": str(names[idx]), "coefficient": float(coef[idx])} for idx in order]
