from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from src.experiments.effect_binding_guard.guards import run_nonmodel_guards
from src.experiments.effect_binding_guard.metrics import paired_method_delta, row_metrics, summarize_method
from src.experiments.effect_binding_guard.schema import EffectBindingRow, TuplePrediction
from src.experiments.tool_effect_fragmentation.io_utils import read_jsonl, write_json, write_jsonl

from .features import (
    FeatureRow,
    build_feature_rows,
    leakage_audit,
    load_local_qwen_predictions,
    write_feature_artifacts,
)
from .models import (
    coefficients,
    evaluate_model_on_split,
    fit_calibrator,
    paired_delta_summary,
    predict_risk,
    risk_curve,
    risk_predictions,
    threshold_heatmap,
)
from .splits import SplitSpec, build_e49_splits, rows_for_groups, split_summary
from .stress import write_stress_sets


ROOT = Path(__file__).resolve().parents[3]
E48_ROWS = ROOT / "data/e48_effect_binding_unified.jsonl"
E48_PAIRS = ROOT / "data/e48_effect_binding_pairs.jsonl"
E48_QWEN = ROOT / "analysis/results/e48_local_qwen_tuple_predictions.jsonl"
E48_PREDICTIONS = ROOT / "analysis/results/e48_tuple_guard_predictions.jsonl"
E48_RESULTS = ROOT / "analysis/results/e48_tuple_guard_results.json"


def load_effect_rows(path: Path) -> list[EffectBindingRow]:
    return [EffectBindingRow.from_dict(row) for row in read_jsonl(path)]


def load_tuple_predictions(path: Path) -> list[TuplePrediction]:
    predictions = []
    for row in read_jsonl(path):
        allowed = {
            "case_id",
            "method",
            "source_scope",
            "split_group_id",
            "predicted_effect",
            "predicted_resource",
            "authorization_match",
            "provenance_risk",
            "decision",
            "confidence",
            "uncertainty",
            "abstain_reason",
            "accessed_fields",
            "decision_inputs_hash",
            "claim_scope",
            "metadata",
        }
        predictions.append(TuplePrediction.from_dict({key: row[key] for key in allowed if key in row}))
    return predictions


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows = load_effect_rows(E48_ROWS)
    pairs = read_jsonl(E48_PAIRS)
    qwen = load_local_qwen_predictions(E48_QWEN)
    artifact_status = verify_e48_artifacts(rows, qwen)
    feature_rows = build_feature_rows(rows, qwen)
    source_aware_feature_rows = build_feature_rows(rows, qwen, include_source_metadata=True)
    audit = leakage_audit(feature_rows)
    manifest = write_feature_artifacts(ROOT, feature_rows, audit)
    if not audit["leakage_free"]:
        raise RuntimeError(f"E49 feature leakage audit failed: {audit}")

    stress_manifest = write_stress_sets(ROOT, rows)
    e48_predictions = load_tuple_predictions(E48_PREDICTIONS)
    e48_by_method = defaultdict(list)
    for pred in e48_predictions:
        e48_by_method[pred.method].append(pred)

    original_by_case = {row.case_id: row for row in rows}
    feature_by_case = {row.case_id: row for row in feature_rows}
    source_feature_by_case = {row.case_id: row for row in source_aware_feature_rows}
    splits = build_e49_splits(feature_rows, seeds=[0, 1, 2, 3, 4])
    main_model_configs = [
        ("logistic_calibrator", "full", True),
    ]
    full_model_configs = [
        ("logistic_calibrator", "full", True),
        ("calibrated_linear_fusion", "full", True),
        ("small_gbdt_fusion", "full", True),
        ("text_only_classifier_baseline", "full", True),
        ("logistic_calibrator", "no_provenance", False),
        ("logistic_calibrator", "no_evidence", True),
        ("logistic_calibrator", "no_disagreement", True),
        ("logistic_calibrator", "no_local_qwen", True),
        ("logistic_calibrator", "decision_votes_only", True),
        ("logistic_calibrator", "tuple_fields_only", True),
        ("logistic_calibrator", "full", False),
    ]
    all_split_results = []
    all_predictions: list[dict[str, Any]] = []
    curve_payload: dict[str, Any] = {"schema_version": "e49_risk_coverage_curves_v1", "curves": []}
    heatmap_payload: dict[str, Any] = {"schema_version": "e49_threshold_sensitivity_v1", "heatmaps": []}
    fitted_seed0_main = None
    seed0_threshold = None

    for spec in splits:
        train = rows_for_groups(feature_rows, spec.train_groups)
        validation = rows_for_groups(feature_rows, spec.validation_groups)
        test = rows_for_groups(feature_rows, spec.test_groups)
        split_record: dict[str, Any] = {
            "split": spec.to_dict(),
            "split_summary": split_summary(feature_rows, spec),
            "model_results": [],
            "hard_baselines": hard_baseline_summary(rows, e48_by_method, test),
        }
        if not train or not validation or not test or len({row.label for row in train}) < 2:
            split_record["status"] = "diagnostic_too_small_for_training"
            all_split_results.append(split_record)
            continue
        split_record["status"] = "complete"
        model_configs = full_model_configs if spec.name == "source_balanced_seed0" else main_model_configs
        for method, feature_mode, overlay in model_configs:
            try:
                model = fit_calibrator(train, method=method, feature_mode=feature_mode, overlay=overlay)
            except Exception as exc:  # keep source-shift failures explicit
                split_record["model_results"].append(
                    {"method": method, "feature_mode": feature_mode, "overlay": overlay, "status": "fit_failed", "error": str(exc)}
                )
                continue
            if spec.name == "source_balanced_seed0" and method == "logistic_calibrator" and feature_mode == "full" and overlay:
                fitted_seed0_main = model
            alphas = (0.05, 0.10, 0.15) if (method, feature_mode, overlay) == ("logistic_calibrator", "full", True) else (0.10,)
            for alpha in alphas:
                result = evaluate_model_on_split(
                    model,
                    train,
                    validation,
                    test,
                    original_by_case,
                    alpha=alpha,
                    objective="safety_first",
                    bootstrap_iters=args.bootstrap_iters,
                )
                if alpha == 0.10 and (method, feature_mode, overlay) == ("logistic_calibrator", "full", True):
                    hard_pred_map = {
                        pred.case_id: pred
                        for pred in e48_by_method.get("effect_binding_guard_full", [])
                    }
                    learned_preds = [
                        TuplePrediction.from_dict({k: v for k, v in pred.items() if k in TuplePrediction.__dataclass_fields__})
                        for pred in result["predictions"]
                    ]
                    hard_preds = [hard_pred_map[row.case_id] for row in test if row.case_id in hard_pred_map]
                    hard_rows = [original_by_case[row.case_id] for row in test if row.case_id in hard_pred_map]
                    result["paired_delta_vs_hard_full_guard"] = paired_delta_summary(
                        hard_rows,
                        learned_preds,
                        hard_preds,
                        bootstrap_iters=args.bootstrap_iters,
                    )
                if spec.name == "source_balanced_seed0" and result["method"] == "logistic_calibrator" and alpha == 0.10:
                    seed0_threshold = result["calibration"]["selected"]
                split_record["model_results"].append({k: v for k, v in result.items() if k != "predictions"})
                all_predictions.extend(
                    {
                        **pred,
                        "split_name": spec.name,
                        "alpha": alpha,
                        "objective": "safety_first",
                    }
                    for pred in result["predictions"]
                )
            if spec.name == "source_balanced_seed0" and method in {"logistic_calibrator", "calibrated_linear_fusion"} and feature_mode == "full" and overlay:
                test_risk = predict_risk(model, test)
                curve_payload["curves"].append(
                    risk_curve(test, original_by_case, test_risk, method_name=f"{method}::source_balanced_seed0", overlay=overlay)
                )
                heatmap_payload["heatmaps"].append(
                    {
                        "method": f"{method}::source_balanced_seed0",
                        "grid": threshold_heatmap(test, original_by_case, test_risk, method_name=method, overlay=overlay),
                    }
                )
            if method == "logistic_calibrator" and feature_mode == "full":
                split_record.setdefault("top_coefficients", {})[f"{method}_overlay_{overlay}"] = coefficients(model)
        if spec.name == "source_balanced_seed0":
            diagnostic_train = [source_feature_by_case[row.case_id] for row in train]
            diagnostic_validation = [source_feature_by_case[row.case_id] for row in validation]
            diagnostic_test = [source_feature_by_case[row.case_id] for row in test]
            diagnostic_model = fit_calibrator(
                diagnostic_train,
                method="logistic_calibrator",
                feature_mode="full",
                overlay=True,
            )
            diagnostic_result = evaluate_model_on_split(
                diagnostic_model,
                diagnostic_train,
                diagnostic_validation,
                diagnostic_test,
                original_by_case,
                alpha=0.10,
                objective="safety_first",
                bootstrap_iters=args.bootstrap_iters,
            )
            diagnostic_result["method"] = "logistic_calibrator__source_aware_diagnostic"
            diagnostic_result["feature_mode"] = "full_plus_source_scope"
            diagnostic_result["claim_scope"] = "non_deployable_diagnostic"
            split_record["model_results"].append({k: v for k, v in diagnostic_result.items() if k != "predictions"})
        all_split_results.append(split_record)

    if fitted_seed0_main is None or seed0_threshold is None:
        raise RuntimeError("source_balanced_seed0 main logistic calibrator did not fit")

    stress_results = evaluate_stress_sets(fitted_seed0_main, seed0_threshold, qwen)
    same_core = same_core_comparisons(rows, e48_by_method, all_predictions)
    failure_examples = collect_failure_examples(rows, all_predictions, limit=40)
    claim_boundary = claim_boundary_text(all_split_results, stress_results)
    capability = write_capability_matrix(all_split_results, stress_results, same_core)

    payload = {
        "schema_version": "e49_learned_fusion_results_v1",
        "artifact_status": artifact_status,
        "feature_manifest": manifest,
        "leakage_audit": audit,
        "stress_manifest": stress_manifest,
        "splits": all_split_results,
        "strong_gate_summary": strong_gate_summary(all_split_results, stress_results),
        "claim_boundary": claim_boundary,
    }
    write_json(ROOT / "analysis/results/e49_learned_fusion_results.json", payload)
    write_markdown_summary(payload, ROOT / "analysis/results/e49_learned_fusion_results.md")
    write_jsonl(ROOT / "analysis/results/e49_learned_fusion_predictions.jsonl", all_predictions)
    write_json(ROOT / "analysis/results/e49_risk_coverage_curves.json", curve_payload)
    write_json(ROOT / "analysis/results/e49_threshold_sensitivity.json", heatmap_payload)
    write_json(ROOT / "analysis/results/e49_ablation_results.json", ablation_payload(all_split_results))
    write_ablation_md(ablation_payload(all_split_results), ROOT / "analysis/results/e49_ablation_results.md")
    write_json(ROOT / "analysis/results/e49_same_core_comparisons.json", same_core)
    write_same_core_md(same_core, ROOT / "analysis/results/e49_same_core_comparisons.md")
    write_json(ROOT / "analysis/results/e49_failure_examples.json", failure_examples)
    write_json(ROOT / "analysis/results/e49_claim_boundary.json", {"claim_boundary": claim_boundary})
    (ROOT / "analysis/results/e49_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    write_json(ROOT / "analysis/results/e49_tuple_guard_results.json", payload)
    write_json(ROOT / "analysis/results/e49_stress_results.json", stress_results)
    write_stress_md(stress_results)
    return payload


def verify_e48_artifacts(rows: list[EffectBindingRow], qwen: dict[str, TuplePrediction]) -> dict[str, Any]:
    parse_valid = sum(bool(pred.metadata.get("parse_valid")) for pred in qwen.values())
    return {
        "e48_rows": len(rows),
        "local_qwen_predictions": len(qwen),
        "local_qwen_parse_valid": parse_valid,
        "local_qwen_parse_valid_rate": parse_valid / max(len(qwen), 1),
        "expected_822_rows": len(rows) == 822,
        "expected_822_qwen_predictions": len(qwen) == 822,
        "parse_valid_gate": parse_valid / max(len(qwen), 1) >= 0.98,
    }


def hard_baseline_summary(
    all_rows: list[EffectBindingRow],
    e48_by_method: dict[str, list[TuplePrediction]],
    test_features: list[FeatureRow],
) -> dict[str, Any]:
    test_case_ids = {row.case_id for row in test_features}
    rows = [row for row in all_rows if row.case_id in test_case_ids]
    out = {}
    for method in (
        "rule_tuple_guard",
        "local_qwen_tuple_guard",
        "always_use_evidence",
        "never_use_evidence",
        "control_provenance_minimal_check",
        "effect_binding_guard_full",
    ):
        preds = [pred for pred in e48_by_method.get(method, []) if pred.case_id in test_case_ids]
        if preds:
            out[method] = summarize_method(rows, preds, [], bootstrap_iters=200, seed=0)["overall"]
    return out


def evaluate_stress_sets(
    model: Any,
    selected_threshold: dict[str, Any],
    qwen: dict[str, TuplePrediction],
) -> dict[str, Any]:
    del qwen
    out = {"schema_version": "e49_stress_results_v1"}
    for name, path in (
        ("resource_authorization", ROOT / "data/e49_resource_authorization_stress.jsonl"),
        ("control_provenance", ROOT / "data/e49_control_provenance_stress.jsonl"),
    ):
        stress_rows = load_effect_rows(path)
        stress_features = build_feature_rows(stress_rows, None)
        original_by_case = {row.case_id: row for row in stress_rows}
        risk = predict_risk(model, stress_features)
        learned = risk_predictions(
            stress_features,
            original_by_case,
            risk,
            selected_threshold["allow_threshold"],
            selected_threshold["deny_threshold"],
            method_name="logistic_calibrator__stress_eval",
            overlay=True,
        )
        hard = run_nonmodel_guards(stress_rows, qwen_predictions=None)
        hard_full = [pred for pred in hard if pred.method == "effect_binding_guard_full"]
        rule = [pred for pred in hard if pred.method == "rule_tuple_guard"]
        no_prov = [pred for pred in hard if pred.method == "control_provenance_minimal_check"]
        out[name] = {
            "n_rows": len(stress_rows),
            "n_groups": len({row.split_group_id for row in stress_rows}),
            "learned_calibrator": summarize_method(stress_rows, learned, [], bootstrap_iters=500, seed=0)["overall"],
            "hard_full_guard": summarize_method(stress_rows, hard_full, [], bootstrap_iters=500, seed=1)["overall"],
            "rule_tuple_guard": summarize_method(stress_rows, rule, [], bootstrap_iters=500, seed=2)["overall"],
            "control_provenance_minimal_check": summarize_method(stress_rows, no_prov, [], bootstrap_iters=500, seed=3)["overall"],
            "by_axis": subgroup_metrics(stress_rows, learned, "counterfactual_axis"),
            "by_pair_role": subgroup_metrics(stress_rows, learned, "pair_role"),
            "selected_threshold": selected_threshold,
            "predictions": [pred.to_dict() for pred in learned],
        }
        write_json(ROOT / f"analysis/results/e49_{name}_stress.json", out[name])
    return out


def subgroup_metrics(rows: list[EffectBindingRow], preds: list[TuplePrediction], field: str) -> dict[str, Any]:
    pred_map = {pred.case_id: pred for pred in preds}
    groups = defaultdict(list)
    for row in rows:
        groups[str(getattr(row, field))].append(row)
    return {key: row_metrics(items, pred_map) for key, items in sorted(groups.items())}


def same_core_comparisons(
    rows: list[EffectBindingRow],
    e48_by_method: dict[str, list[TuplePrediction]],
    learned_predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    learned = [
        TuplePrediction.from_dict({k: v for k, v in pred.items() if k in TuplePrediction.__dataclass_fields__})
        for pred in learned_predictions
        if pred.get("split_name") == "source_balanced_seed0"
        and pred.get("alpha") == 0.10
        and pred.get("method") == "logistic_calibrator"
    ]
    learned_by_case = {pred.case_id: pred for pred in learned}
    out: dict[str, Any] = {"schema_version": "e49_same_core_comparisons_v1", "cores": {}}
    for source in ("phase4", "ipiguard", "camel"):
        source_rows = [row for row in rows if row.source_scope == source and row.case_id in learned_by_case]
        methods = {"learned_calibrator": [learned_by_case[row.case_id] for row in source_rows]}
        for method in ("effect_binding_guard_full", "local_qwen_tuple_guard", "rule_tuple_guard"):
            pred_map = {pred.case_id: pred for pred in e48_by_method.get(method, [])}
            methods[method] = [pred_map[row.case_id] for row in source_rows if row.case_id in pred_map]
        out["cores"][source] = {
            method: summarize_method(source_rows, preds, [], bootstrap_iters=500, seed=0)["overall"]
            for method, preds in methods.items()
            if preds
        }
    out["claim_boundary"] = "Same-core comparisons use E48 rows only; E47 official-checkpoint results remain referenced by prior E47 artifacts and are not averaged with E49 learned rows."
    return out


def collect_failure_examples(
    rows: list[EffectBindingRow],
    prediction_dicts: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    row_by_id = {row.case_id: row for row in rows}
    examples = []
    for pred in prediction_dicts:
        if pred.get("split_name") != "source_balanced_seed0" or pred.get("alpha") != 0.10:
            continue
        row = row_by_id.get(pred["case_id"])
        if not row:
            continue
        expected = row.labels["expected_decision"]
        decision = pred["decision"]
        if decision == expected:
            continue
        if expected == "DENY" and decision == "ALLOW":
            failure = "unsafe_pre_allow"
        elif expected == "ALLOW" and decision == "DENY":
            failure = "safe_false_deny"
        else:
            failure = "abstain_or_selective_miss"
        examples.append(
            {
                "case_id": row.case_id,
                "source_scope": row.source_scope,
                "method": pred["method"],
                "failure_type": failure,
                "expected_decision": expected,
                "predicted_decision": decision,
                "risk_score": pred.get("metadata", {}).get("risk_score"),
                "predicted_tuple": {
                    "effect": pred.get("predicted_effect"),
                    "resource_type": "redacted_non_oracle_resource_type",
                    "authorization_match": pred.get("authorization_match"),
                    "provenance_risk": pred.get("provenance_risk"),
                },
                "gold_tuple_for_analysis_only": {
                    "effect": row.labels.get("gold_effect"),
                    "resource": row.labels.get("gold_resource"),
                    "authorization_match": row.labels.get("gold_authorization_match"),
                    "provenance_risk": row.labels.get("gold_provenance_risk"),
                },
                "interpretation": "E49 failure example; gold tuple is analysis-only and was not a feature.",
                "claim_scope": "method-feasibility custom stress",
            }
        )
        if len(examples) >= limit:
            break
    return examples


def ablation_payload(split_results: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for split in split_results:
        if split.get("protocol") == "unused":
            continue
        for result in split.get("model_results", []):
            if result.get("alpha") != 0.10:
                continue
            rows.append(
                {
                    "split": split["split"]["name"],
                    "method": result.get("method"),
                    "feature_mode": result.get("feature_mode"),
                    "overlay": result.get("overlay"),
                    "status": result.get("status", "complete"),
                    "overall": result.get("summary", {}).get("overall"),
                    "brier_score": result.get("brier_score"),
                    "ece": result.get("ece", {}).get("ece") if isinstance(result.get("ece"), dict) else None,
                }
            )
    return {"schema_version": "e49_ablation_results_v1", "rows": rows}


def strong_gate_summary(split_results: list[dict[str, Any]], stress_results: dict[str, Any]) -> dict[str, Any]:
    seed_rows = [
        result
        for split in split_results
        if split["split"]["name"].startswith("source_balanced_seed")
        for result in split.get("model_results", [])
        if result.get("method") == "logistic_calibrator" and result.get("alpha") == 0.10 and result.get("feature_mode") == "full" and result.get("overlay") is True
    ]
    hard_rows = [
        split.get("hard_baselines", {}).get("effect_binding_guard_full")
        for split in split_results
        if split["split"]["name"].startswith("source_balanced_seed")
    ]
    def avg_metric(items: list[dict[str, Any]], key: str) -> float | None:
        values = [item["summary"]["overall"][key]["rate"] for item in items if item and item.get("summary", {}).get("overall", {}).get(key, {}).get("rate") is not None]
        return sum(values) / len(values) if values else None
    learned_upa = avg_metric(seed_rows, "unsafe_pre_allow")
    learned_cov = avg_metric(seed_rows, "coverage")
    learned_fd = avg_metric(seed_rows, "safe_false_deny")
    hard_upa_values = [item["unsafe_pre_allow"]["rate"] for item in hard_rows if item]
    hard_cov_values = [item["coverage"]["rate"] for item in hard_rows if item]
    hard_fd_values = [item["safe_false_deny"]["rate"] for item in hard_rows if item]
    camel = next((row for row in seed_rows if row.get("summary", {}).get("by_source", {}).get("camel")), None)
    camel_upa = camel["summary"]["by_source"]["camel"]["unsafe_pre_allow"]["rate"] if camel else None
    return {
        "source_balanced_alpha_0_10": {
            "learned_mean_unsafe_pre_allow": learned_upa,
            "learned_mean_coverage": learned_cov,
            "learned_mean_safe_false_deny": learned_fd,
            "hard_mean_unsafe_pre_allow": sum(hard_upa_values) / len(hard_upa_values) if hard_upa_values else None,
            "hard_mean_coverage": sum(hard_cov_values) / len(hard_cov_values) if hard_cov_values else None,
            "hard_mean_safe_false_deny": sum(hard_fd_values) / len(hard_fd_values) if hard_fd_values else None,
            "camel_unsafe_pre_allow_seed0": camel_upa,
        },
        "stress_coverage": {
            key: value.get("learned_calibrator", {}).get("coverage", {}).get("rate")
            for key, value in stress_results.items()
            if isinstance(value, dict)
        },
        "gate_interpretation": "Pass/fail must be interpreted with paired CIs in the main tables; this summary is descriptive.",
    }


def write_capability_matrix(split_results: list[dict[str, Any]], stress_results: dict[str, Any], same_core: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / "analysis/results/e49_capability_matrix_with_calibrator.csv"
    rows = []
    for split in split_results:
        for result in split.get("model_results", []):
            if result.get("alpha") != 0.10:
                continue
            overall = result.get("summary", {}).get("overall", {})
            rows.append(
                {
                    "scope": "e49_source_balanced" if split["split"]["name"].startswith("source_balanced") else split["split"]["protocol"],
                    "split": split["split"]["name"],
                    "method": result.get("method"),
                    "feature_mode": result.get("feature_mode"),
                    "overlay": result.get("overlay"),
                    "unsafe_pre_allow": get_rate(overall, "unsafe_pre_allow"),
                    "safe_false_deny": get_rate(overall, "safe_false_deny"),
                    "coverage": get_rate(overall, "coverage"),
                    "abstain": get_rate(overall, "abstain_rate"),
                }
            )
    for stress_name, payload in stress_results.items():
        if not isinstance(payload, dict) or "learned_calibrator" not in payload:
            continue
        rows.append(
            {
                "scope": f"e49_{stress_name}_stress",
                "split": "evaluation_only",
                "method": "logistic_calibrator",
                "feature_mode": "full",
                "overlay": True,
                "unsafe_pre_allow": get_rate(payload["learned_calibrator"], "unsafe_pre_allow"),
                "safe_false_deny": get_rate(payload["learned_calibrator"], "safe_false_deny"),
                "coverage": get_rate(payload["learned_calibrator"], "coverage"),
                "abstain": get_rate(payload["learned_calibrator"], "abstain_rate"),
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["scope"])
        writer.writeheader()
        writer.writerows(rows)
    return {"path": str(path), "n_rows": len(rows)}


def get_rate(payload: dict[str, Any], key: str) -> float | None:
    metric = payload.get(key)
    return metric.get("rate") if isinstance(metric, dict) else None


def claim_boundary_text(split_results: list[dict[str, Any]], stress_results: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# E49 Claim Boundary",
            "",
            "- E49 evaluates lightweight learned calibration over E48 non-oracle tuple features on controlled custom stress artifacts.",
            "- The main model excludes construction metadata, source metadata, audit status, gold tuple fields, oracle outputs, and E48 globally calibrated policy decisions.",
            "- Provenance hard overlay is part of the main method and is reported separately from learned risk fusion.",
            "- Resource/auth and control-provenance stress sets are evaluation-only and are not used for training or threshold selection.",
            "- Results do not establish production safety, a complete permission system, original-paper benchmark reproduction, or real deployed-agent readiness.",
            "- If learned fusion does not improve over the E48 hard guard under source-balanced splits, the correct interpretation is calibration diagnostic evidence, not a solved guard.",
        ]
    )


def write_markdown_summary(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# E49 Learned Effect-Binding Calibrator",
        "",
        f"- E48 rows: `{payload['artifact_status']['e48_rows']}`",
        f"- Feature leakage free: `{payload['leakage_audit']['leakage_free']}`",
        f"- Local-Qwen parse-valid rate reused from E48: `{payload['artifact_status']['local_qwen_parse_valid_rate']:.3f}`",
        "",
        "## Source-Balanced Alpha=0.10",
        "",
        "| Split | Method | UPA | FDeny | Coverage | Abstain |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for split in payload["splits"]:
        if not split["split"]["name"].startswith("source_balanced"):
            continue
        for result in split.get("model_results", []):
            if result.get("alpha") != 0.10 or result.get("method") != "logistic_calibrator":
                continue
            overall = result.get("summary", {}).get("overall", {})
            lines.append(
                f"| `{split['split']['name']}` | `{result.get('method')}:{result.get('feature_mode')}:overlay={result.get('overlay')}` | "
                f"{fmt(get_rate(overall, 'unsafe_pre_allow'))} | {fmt(get_rate(overall, 'safe_false_deny'))} | "
                f"{fmt(get_rate(overall, 'coverage'))} | {fmt(get_rate(overall, 'abstain_rate'))} |"
            )
    lines.extend(["", payload["claim_boundary"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ablation_md(payload: dict[str, Any], path: Path) -> None:
    lines = ["# E49 Ablation Results", "", "| Split | Method | Feature mode | Overlay | UPA | FDeny | Coverage |", "|---|---|---|---:|---:|---:|---:|"]
    for row in payload["rows"]:
        overall = row.get("overall") or {}
        lines.append(
            f"| `{row['split']}` | `{row['method']}` | `{row['feature_mode']}` | `{row['overlay']}` | "
            f"{fmt(get_rate(overall, 'unsafe_pre_allow'))} | {fmt(get_rate(overall, 'safe_false_deny'))} | {fmt(get_rate(overall, 'coverage'))} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_same_core_md(payload: dict[str, Any], path: Path) -> None:
    lines = ["# E49 Same-Core Comparisons", ""]
    for core, methods in payload["cores"].items():
        lines.extend([f"## {core}", "", "| Method | UPA | FDeny | Coverage |", "|---|---:|---:|---:|"])
        for method, overall in methods.items():
            lines.append(
                f"| `{method}` | {fmt(get_rate(overall, 'unsafe_pre_allow'))} | {fmt(get_rate(overall, 'safe_false_deny'))} | {fmt(get_rate(overall, 'coverage'))} |"
            )
        lines.append("")
    lines.append(payload["claim_boundary"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_stress_md(payload: dict[str, Any]) -> None:
    for name in ("resource_authorization", "control_provenance"):
        item = payload.get(name, {})
        lines = [f"# E49 {name} Stress", "", "| Method | UPA | FDeny | Coverage | Abstain |", "|---|---:|---:|---:|---:|"]
        for method in ("learned_calibrator", "hard_full_guard", "rule_tuple_guard", "control_provenance_minimal_check"):
            overall = item.get(method, {})
            lines.append(
                f"| `{method}` | {fmt(get_rate(overall, 'unsafe_pre_allow'))} | {fmt(get_rate(overall, 'safe_false_deny'))} | {fmt(get_rate(overall, 'coverage'))} | {fmt(get_rate(overall, 'abstain_rate'))} |"
            )
        (ROOT / f"analysis/results/e49_{name}_stress.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt(value: float | None) -> str:
    return "NA" if value is None else f"{value:.3f}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E49 learned effect-binding calibration experiments.")
    parser.add_argument("--bootstrap-iters", type=int, default=500)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
