"""T56: decomposed Auth-SafeInv verifier.

This experiment follows the Auth-SafeInv definition more directly than T55.
Instead of training a single unauthorized-effect label, it trains two monitors:

  P(candidate effect is realized)
  P(candidate effect is authorized by the task)

The unauthorized score is then:

  P(realized) * (1 - P(authorized))

This is still a frozen-embedding diagnostic over schema-conditioned inputs. It
does not use cross-tool positive pairs or held-out-tool observed pairs.

Outputs:
  analysis/auth_decomposed_verifier_mitigation_<data_name>.json
  analysis/auth_decomposed_verifier_mitigation_<data_name>.md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import experiment_auth_baselines as base_exp


DEFAULT_METHODS = [
    "decomposed_sgd_product",
    "decomposed_sgd_mean",
    "decomposed_per_effect_sgd_product",
    "decomposed_per_effect_sgd_mean",
    "verifier_present_sgd_auth",
    "verifier_present_per_effect_sgd_auth",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T56 decomposed Auth-SafeInv verifier.")
    parser.add_argument("data_name", nargs="?", default="qwen3-8b_auth_effect_schema_conditioned_v2")
    parser.add_argument("--baseline-data-name", default="qwen3-8b_authorization_counterfactuals_v2")
    parser.add_argument("--evaluations", nargs="*", default=["loto", "family"])
    parser.add_argument("--conditions", nargs="*", default=["full_tool_chain", "auth_only_control", "tool_only_control"])
    parser.add_argument("--methods", nargs="*", default=DEFAULT_METHODS)
    parser.add_argument("--random-seeds", nargs="*", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--thresholds", nargs="*", type=float)
    parser.add_argument("--target-fpr", type=float, default=0.10)
    parser.add_argument("--min-unauth-test", type=int, default=3)
    parser.add_argument(
        "--output-suffix",
        default="",
        help="Optional suffix inserted before the output extension, e.g. _verifier_present_full.",
    )
    return parser.parse_args()


def load(base: Path, data_name: str) -> tuple[np.ndarray, list[dict[str, Any]]]:
    x = np.load(base / "embeddings" / f"embeddings_{data_name}.npy").astype(np.float32)
    data_file = data_name.replace("qwen3-8b_", "")
    rows = [
        json.loads(line)
        for line in (base / "data" / f"{data_file}.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if len(rows) != len(x):
        raise ValueError(f"Length mismatch: rows={len(rows)} embeddings={len(x)}")
    return x, rows


def split_metadata(spec: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in spec.items() if k not in {"train_idx", "test_idx"}}


def cell_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("split_type"),
        row.get("effect"),
        row.get("heldout_tool"),
        row.get("heldout_family"),
        row.get("seed"),
    )


def build_split_specs(
    rows: list[dict[str, Any]],
    condition_idx: np.ndarray,
    evaluations: list[str],
    random_seeds: list[int],
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    if "random" in evaluations:
        groups = np.array(sorted({rows[int(i)]["split_group"] for i in condition_idx}))
        for seed in random_seeds:
            rng = np.random.default_rng(seed)
            shuffled = groups.copy()
            rng.shuffle(shuffled)
            train_groups = set(shuffled[: int(len(shuffled) * 0.8)])
            train = np.array([i for i in condition_idx if rows[int(i)]["split_group"] in train_groups], dtype=int)
            test = np.array([i for i in condition_idx if rows[int(i)]["split_group"] not in train_groups], dtype=int)
            specs.append({"split_type": "random_group", "seed": seed, "train_idx": train, "test_idx": test})
    if "loto" in evaluations:
        for tool in sorted({rows[int(i)]["tool_name"] for i in condition_idx}):
            train = np.array([i for i in condition_idx if rows[int(i)]["tool_name"] != tool], dtype=int)
            test = np.array([i for i in condition_idx if rows[int(i)]["tool_name"] == tool], dtype=int)
            specs.append({"split_type": "leave_one_tool_out", "heldout_tool": tool, "train_idx": train, "test_idx": test})
    if "family" in evaluations:
        for family in sorted({rows[int(i)]["counterfactual_family"] for i in condition_idx}):
            train = np.array([i for i in condition_idx if rows[int(i)]["counterfactual_family"] != family], dtype=int)
            test = np.array([i for i in condition_idx if rows[int(i)]["counterfactual_family"] == family], dtype=int)
            specs.append({"split_type": "leave_one_family_out", "heldout_family": family, "train_idx": train, "test_idx": test})
    return [spec for spec in specs if len(spec["train_idx"]) > 0 and len(spec["test_idx"]) > 0]


def binary_label(rows: list[dict[str, Any]], key: str) -> np.ndarray:
    return np.array([int(bool(row[key])) for row in rows], dtype=int)


def fit_sgd(
    *,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    random_state: int,
) -> np.ndarray | None:
    if len(np.unique(y_train)) < 2:
        return None
    clf = make_pipeline(
        StandardScaler(),
        SGDClassifier(
            loss="log_loss",
            penalty="l2",
            alpha=1e-4,
            max_iter=1000,
            tol=1e-3,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=4,
        ),
    )
    clf.fit(x_train, y_train)
    return clf.predict_proba(x_test)[:, 1]


def evaluate_effect(
    *,
    rows: list[dict[str, Any]],
    test_idx: np.ndarray,
    effect: str,
    scores: np.ndarray,
    threshold: float,
) -> dict[str, Any] | None:
    local = [pos for pos, idx in enumerate(test_idx) if rows[int(idx)]["candidate_effect"] == effect]
    if not local:
        return None
    y = np.array([int(rows[int(test_idx[pos])]["label_unauthorized_effect"]) for pos in local], dtype=int)
    absent = np.array([bool(rows[int(test_idx[pos])]["label_absent_not_authorized"]) for pos in local], dtype=bool)
    n_pos = int(y.sum())
    if n_pos == 0:
        return None
    pred = (scores[local] >= threshold).astype(int)
    false_neg = int(((pred == 0) & (y == 1)).sum())
    absent_n = int(absent.sum())
    absent_fp = int(((pred == 1) & absent).sum())
    return {
        "n_unauth_test": n_pos,
        "false_negatives": false_neg,
        "unauthorized_fnr": round(false_neg / n_pos, 4),
        "unauthorized_fnr_wilson95": base_exp.wilson_interval(false_neg, n_pos),
        "not_authorized_absent_n": absent_n,
        "not_authorized_absent_fpr": None if absent_n == 0 else round(absent_fp / absent_n, 4),
        "threshold": round(float(threshold), 4),
    }


def add_rows(
    *,
    fixed_rows: list[dict[str, Any]],
    curve_rows: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    test_idx: np.ndarray,
    scores: np.ndarray,
    spec: dict[str, Any],
    condition: str,
    method: str,
    thresholds: list[float],
    min_unauth_test: int,
    extra: dict[str, Any],
    effect_filter: list[str] | None = None,
) -> None:
    effects = effect_filter or sorted({rows[int(i)]["candidate_effect"] for i in test_idx})
    for effect in effects:
        metric = evaluate_effect(rows=rows, test_idx=test_idx, effect=effect, scores=scores, threshold=0.5)
        if metric is not None and metric["n_unauth_test"] >= min_unauth_test:
            fixed_rows.append(
                {
                    **split_metadata(spec),
                    "schema_condition": condition,
                    "effect": effect,
                    "method": method,
                    "n_test": int(len(test_idx)),
                    **metric,
                    **extra,
                }
            )
        for threshold in thresholds:
            curve_metric = evaluate_effect(rows=rows, test_idx=test_idx, effect=effect, scores=scores, threshold=threshold)
            if curve_metric is None or curve_metric["n_unauth_test"] < min_unauth_test:
                continue
            curve_rows.append(
                {
                    **split_metadata(spec),
                    "schema_condition": condition,
                    "effect": effect,
                    "method": method,
                    "n_test": int(len(test_idx)),
                    "threshold": round(float(threshold), 4),
                    "unauthorized_fnr": curve_metric["unauthorized_fnr"],
                    "not_authorized_absent_fpr": curve_metric["not_authorized_absent_fpr"],
                    "n_unauth_test": curve_metric["n_unauth_test"],
                    "not_authorized_absent_n": curve_metric["not_authorized_absent_n"],
                    **extra,
                }
            )


def run_decomposed_global(
    *,
    x: np.ndarray,
    rows: list[dict[str, Any]],
    present_y: np.ndarray,
    auth_y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    present_scores = fit_sgd(
        x_train=x[train_idx],
        y_train=present_y[train_idx],
        x_test=x[test_idx],
        random_state=101,
    )
    auth_scores = fit_sgd(
        x_train=x[train_idx],
        y_train=auth_y[train_idx],
        x_test=x[test_idx],
        random_state=102,
    )
    if present_scores is None or auth_scores is None:
        return None, {"reason": "single_class_present_or_authorized_train"}
    return present_scores * (1.0 - auth_scores), {
        "score_formula": "P(candidate_effect_present) * (1 - P(candidate_effect_authorized))",
        "present_model": "sgd_log_loss",
        "authorized_model": "sgd_log_loss",
    }


def run_decomposed_global_components(
    *,
    x: np.ndarray,
    present_y: np.ndarray,
    auth_y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
) -> tuple[np.ndarray | None, np.ndarray | None, dict[str, Any]]:
    present_scores = fit_sgd(
        x_train=x[train_idx],
        y_train=present_y[train_idx],
        x_test=x[test_idx],
        random_state=101,
    )
    auth_scores = fit_sgd(
        x_train=x[train_idx],
        y_train=auth_y[train_idx],
        x_test=x[test_idx],
        random_state=102,
    )
    if present_scores is None or auth_scores is None:
        return None, None, {"reason": "single_class_present_or_authorized_train"}
    return present_scores, auth_scores, {
        "present_model": "sgd_log_loss",
        "authorized_model": "sgd_log_loss",
    }


def run_auth_global_component(
    *,
    x: np.ndarray,
    auth_y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    auth_scores = fit_sgd(
        x_train=x[train_idx],
        y_train=auth_y[train_idx],
        x_test=x[test_idx],
        random_state=102,
    )
    if auth_scores is None:
        return None, {"reason": "single_class_authorized_train"}
    return auth_scores, {
        "authorized_model": "sgd_log_loss",
    }


def run_decomposed_per_effect(
    *,
    x: np.ndarray,
    rows: list[dict[str, Any]],
    present_y: np.ndarray,
    auth_y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    effect: str,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    train_effect_idx = np.array([int(i) for i in train_idx if rows[int(i)]["candidate_effect"] == effect], dtype=int)
    test_positions = [pos for pos, idx in enumerate(test_idx) if rows[int(idx)]["candidate_effect"] == effect]
    if len(train_effect_idx) == 0 or not test_positions:
        return None, {"reason": "empty_effect_train_or_test"}
    test_effect_idx = np.array([int(test_idx[pos]) for pos in test_positions], dtype=int)
    seed = 2000 + sum((pos + 1) * ord(ch) for pos, ch in enumerate(effect))
    present_scores = fit_sgd(
        x_train=x[train_effect_idx],
        y_train=present_y[train_effect_idx],
        x_test=x[test_effect_idx],
        random_state=seed,
    )
    auth_scores = fit_sgd(
        x_train=x[train_effect_idx],
        y_train=auth_y[train_effect_idx],
        x_test=x[test_effect_idx],
        random_state=seed + 1,
    )
    if present_scores is None or auth_scores is None:
        return None, {"reason": "single_class_effect_present_or_authorized_train"}
    scores = np.zeros(len(test_idx), dtype=float)
    scores[test_positions] = present_scores * (1.0 - auth_scores)
    return scores, {
        "score_formula": "per-effect P(candidate_effect_present) * (1 - P(candidate_effect_authorized))",
        "present_model": "per_effect_sgd_log_loss",
        "authorized_model": "per_effect_sgd_log_loss",
        "trained_effect": effect,
    }


def run_decomposed_per_effect_components(
    *,
    x: np.ndarray,
    rows: list[dict[str, Any]],
    present_y: np.ndarray,
    auth_y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    effect: str,
) -> tuple[np.ndarray | None, np.ndarray | None, list[int], dict[str, Any]]:
    train_effect_idx = np.array([int(i) for i in train_idx if rows[int(i)]["candidate_effect"] == effect], dtype=int)
    test_positions = [pos for pos, idx in enumerate(test_idx) if rows[int(idx)]["candidate_effect"] == effect]
    if len(train_effect_idx) == 0 or not test_positions:
        return None, None, test_positions, {"reason": "empty_effect_train_or_test"}
    test_effect_idx = np.array([int(test_idx[pos]) for pos in test_positions], dtype=int)
    seed = 2000 + sum((pos + 1) * ord(ch) for pos, ch in enumerate(effect))
    present_scores = fit_sgd(
        x_train=x[train_effect_idx],
        y_train=present_y[train_effect_idx],
        x_test=x[test_effect_idx],
        random_state=seed,
    )
    auth_scores = fit_sgd(
        x_train=x[train_effect_idx],
        y_train=auth_y[train_effect_idx],
        x_test=x[test_effect_idx],
        random_state=seed + 1,
    )
    if present_scores is None or auth_scores is None:
        return None, None, test_positions, {"reason": "single_class_effect_present_or_authorized_train"}
    return present_scores, auth_scores, test_positions, {
        "present_model": "per_effect_sgd_log_loss",
        "authorized_model": "per_effect_sgd_log_loss",
        "trained_effect": effect,
    }


def run_auth_per_effect_component(
    *,
    x: np.ndarray,
    rows: list[dict[str, Any]],
    auth_y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    effect: str,
) -> tuple[np.ndarray | None, list[int], dict[str, Any]]:
    train_effect_idx = np.array([int(i) for i in train_idx if rows[int(i)]["candidate_effect"] == effect], dtype=int)
    test_positions = [pos for pos, idx in enumerate(test_idx) if rows[int(idx)]["candidate_effect"] == effect]
    if len(train_effect_idx) == 0 or not test_positions:
        return None, test_positions, {"reason": "empty_effect_train_or_test"}
    test_effect_idx = np.array([int(test_idx[pos]) for pos in test_positions], dtype=int)
    seed = 2000 + sum((pos + 1) * ord(ch) for pos, ch in enumerate(effect))
    auth_scores = fit_sgd(
        x_train=x[train_effect_idx],
        y_train=auth_y[train_effect_idx],
        x_test=x[test_effect_idx],
        random_state=seed + 1,
    )
    if auth_scores is None:
        return None, test_positions, {"reason": "single_class_effect_authorized_train"}
    return auth_scores, test_positions, {
        "authorized_model": "per_effect_sgd_log_loss",
        "trained_effect": effect,
    }


def compose_scores(present_scores: np.ndarray, auth_scores: np.ndarray, formula: str) -> np.ndarray:
    not_authorized = 1.0 - auth_scores
    if formula == "product":
        return present_scores * not_authorized
    if formula == "mean":
        return 0.5 * (present_scores + not_authorized)
    if formula == "min":
        return np.minimum(present_scores, not_authorized)
    raise ValueError(f"Unknown decomposed score formula: {formula}")


def formula_for_method(method: str) -> str:
    if method.endswith("_product"):
        return "product"
    if method.endswith("_mean"):
        return "mean"
    if method.endswith("_min"):
        return "min"
    raise ValueError(f"Cannot infer formula from method: {method}")


def uses_global_auth_model(method: str) -> bool:
    return method.startswith("decomposed_sgd_") or method == "verifier_present_sgd_auth"


def uses_per_effect_auth_model(method: str) -> bool:
    return method.startswith("decomposed_per_effect_sgd_") or method == "verifier_present_per_effect_sgd_auth"


def aggregate_curves(curve_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in curve_rows:
        groups[(row["split_type"], row["schema_condition"], row["method"], float(row["threshold"]))].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, condition, method, threshold), vals in sorted(groups.items()):
        fprs = [row["not_authorized_absent_fpr"] for row in vals if row["not_authorized_absent_fpr"] is not None]
        out.append(
            {
                "split_type": split_type,
                "schema_condition": condition,
                "method": method,
                "threshold": round(float(threshold), 4),
                "rows": len(vals),
                "unique_cells": len({cell_key(v) for v in vals}),
                "mean_unauthorized_fnr": round(float(np.mean([v["unauthorized_fnr"] for v in vals])), 4),
                "mean_absent_not_authorized_fpr": None if not fprs else round(float(np.mean(fprs)), 4),
            }
        )
    return out


def aggregate_fixed(fixed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in fixed_rows:
        groups[(row["split_type"], row["schema_condition"], row["method"])].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, condition, method), vals in sorted(groups.items()):
        fprs = [row["not_authorized_absent_fpr"] for row in vals if row["not_authorized_absent_fpr"] is not None]
        fnr = np.array([row["unauthorized_fnr"] for row in vals], dtype=float)
        out.append(
            {
                "split_type": split_type,
                "schema_condition": condition,
                "method": method,
                "rows": len(vals),
                "unique_cells": len({cell_key(v) for v in vals}),
                "mean_unauthorized_fnr": round(float(fnr.mean()), 4),
                "std_unauthorized_fnr": round(float(fnr.std(ddof=0)), 4),
                "max_unauthorized_fnr": round(float(fnr.max()), 4),
                "mean_absent_not_authorized_fpr": None if not fprs else round(float(np.mean(fprs)), 4),
            }
        )
    return out


def best_tradeoffs(curve_rows: list[dict[str, Any]], target_fpr: float) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in aggregate_curves(curve_rows):
        groups[(row["split_type"], row["schema_condition"], row["method"])].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, condition, method), vals in sorted(groups.items()):
        candidates = [
            row
            for row in vals
            if row["mean_absent_not_authorized_fpr"] is not None
            and row["mean_absent_not_authorized_fpr"] <= target_fpr
        ]
        if not candidates:
            out.append(
                {
                    "split_type": split_type,
                    "schema_condition": condition,
                    "method": method,
                    "target_fpr": target_fpr,
                    "threshold": None,
                    "mean_unauthorized_fnr": None,
                    "mean_absent_not_authorized_fpr": None,
                    "unique_cells": 0,
                }
            )
            continue
        best = min(candidates, key=lambda row: (row["mean_unauthorized_fnr"], row["mean_absent_not_authorized_fpr"]))
        out.append({**best, "target_fpr": target_fpr})
    return out


def best_baseline_rows(rows: list[dict[str, Any]], target_fpr: float) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("method") == "open_set_abstain":
            continue
        groups[(row["split_type"], row["method"], float(row["threshold"]))].append(row)
    aggregate: list[dict[str, Any]] = []
    for (split_type, method, threshold), vals in sorted(groups.items()):
        fprs = [row["not_authorized_absent_fpr"] for row in vals if row["not_authorized_absent_fpr"] is not None]
        aggregate.append(
            {
                "split_type": split_type,
                "method": method,
                "threshold": round(float(threshold), 4),
                "mean_unauthorized_fnr": round(float(np.mean([row["unauthorized_fnr"] for row in vals])), 4),
                "mean_absent_not_authorized_fpr": None if not fprs else round(float(np.mean(fprs)), 4),
            }
        )
    by_method: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in aggregate:
        by_method[(row["split_type"], row["method"])].append(row)
    out = []
    for (_, _), vals in sorted(by_method.items()):
        candidates = [
            row
            for row in vals
            if row["mean_absent_not_authorized_fpr"] is not None
            and row["mean_absent_not_authorized_fpr"] <= target_fpr
        ]
        if candidates:
            out.append(min(candidates, key=lambda row: (row["mean_unauthorized_fnr"], row["mean_absent_not_authorized_fpr"])))
    return out


def same_cell_baseline_comparison(
    *,
    base: Path,
    baseline_data_name: str,
    curve_rows: list[dict[str, Any]],
    target_fpr: float,
) -> dict[str, Any]:
    baseline_path = base / "analysis" / f"auth_baseline_confirmatory_{baseline_data_name}.json"
    if not baseline_path.exists():
        return {"available": False, "reason": f"missing {baseline_path}"}
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_rows = baseline.get("threshold_curve_rows", [])
    out = []
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in curve_rows:
        groups[(row["split_type"], row["schema_condition"], row["method"])].append(row)
    for (split_type, condition, method), vals in sorted(groups.items()):
        cells = {cell_key(row) for row in vals}
        dec_best = best_tradeoffs(vals, target_fpr)
        dec_row = next(
            (
                row
                for row in dec_best
                if row["split_type"] == split_type
                and row["schema_condition"] == condition
                and row["method"] == method
            ),
            None,
        )
        baseline_subset = [
            row
            for row in baseline_rows
            if row["split_type"] == split_type
            and row.get("method") != "open_set_abstain"
            and cell_key(row) in cells
        ]
        base_best = best_baseline_rows(baseline_subset, target_fpr)
        best_base = min(base_best, key=lambda row: (row["mean_unauthorized_fnr"], row["mean_absent_not_authorized_fpr"])) if base_best else None
        out.append(
            {
                "split_type": split_type,
                "schema_condition": condition,
                "decomposed_method": method,
                "target_fpr": target_fpr,
                "decomposed_cells": len(cells),
                "baseline_cells_matched": len({cell_key(row) for row in baseline_subset}),
                "decomposed_threshold": None if dec_row is None else dec_row["threshold"],
                "decomposed_mean_fnr": None if dec_row is None else dec_row["mean_unauthorized_fnr"],
                "decomposed_mean_fpr": None if dec_row is None else dec_row["mean_absent_not_authorized_fpr"],
                "best_baseline_method": None if best_base is None else best_base["method"],
                "best_baseline_threshold": None if best_base is None else best_base["threshold"],
                "best_baseline_mean_fnr": None if best_base is None else best_base["mean_unauthorized_fnr"],
                "best_baseline_mean_fpr": None if best_base is None else best_base["mean_absent_not_authorized_fpr"],
                "delta_fnr_vs_best_baseline": None
                if dec_row is None or best_base is None or dec_row["mean_unauthorized_fnr"] is None
                else round(best_base["mean_unauthorized_fnr"] - dec_row["mean_unauthorized_fnr"], 4),
            }
        )
    return {
        "available": True,
        "baseline_source": str(baseline_path.relative_to(base)),
        "excluded_baseline_methods": ["open_set_abstain"],
        "interpretation": "Setting-shifted comparison: decomposed verifier uses candidate present/authorized supervision over schema-conditioned inputs; T54 baselines train realized-effect probes.",
        "rows": out,
    }


def run() -> dict[str, Any]:
    args = parse_args()
    thresholds = args.thresholds if args.thresholds else [round(float(v), 4) for v in np.linspace(0.0, 1.0, 21)]
    base = Path(__file__).resolve().parent.parent
    x, rows = load(base, args.data_name)
    present_y = binary_label(rows, "candidate_effect_present")
    auth_y = binary_label(rows, "candidate_effect_authorized")
    available_conditions = sorted({row["schema_condition"] for row in rows})
    conditions = [condition for condition in args.conditions if condition in available_conditions]
    if not conditions:
        raise ValueError(f"No requested conditions found. Available: {available_conditions}")

    fixed_rows: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []
    for condition in conditions:
        condition_idx = np.array([i for i, row in enumerate(rows) if row["schema_condition"] == condition], dtype=int)
        specs = build_split_specs(rows, condition_idx, args.evaluations, args.random_seeds)
        for spec_id, spec in enumerate(specs, start=1):
            print(f"[{condition} {spec_id}/{len(specs)}] {split_metadata(spec)}", flush=True)
            train_idx = spec["train_idx"]
            test_idx = spec["test_idx"]
            global_methods = [method for method in args.methods if uses_global_auth_model(method)]
            if global_methods:
                verifier_only_global = all(method == "verifier_present_sgd_auth" for method in global_methods)
                if verifier_only_global:
                    auth_scores, info = run_auth_global_component(
                        x=x,
                        auth_y=auth_y,
                        train_idx=train_idx,
                        test_idx=test_idx,
                    )
                    if auth_scores is None:
                        for method in global_methods:
                            skipped_rows.append({**split_metadata(spec), "schema_condition": condition, "method": method, **info})
                    else:
                        for method in global_methods:
                            scores = present_y[test_idx].astype(float) * (1.0 - auth_scores)
                            extra_info = {
                                **info,
                                "score_formula": "oracle_present_times_predicted_not_authorized",
                                "score_definition": "I(candidate_effect_present from verifier) * (1 - P(candidate_effect_authorized))",
                                "runtime_assumption": "requires an external or execution-level candidate-effect verifier",
                            }
                            add_rows(
                                fixed_rows=fixed_rows,
                                curve_rows=curve_rows,
                                rows=rows,
                                test_idx=test_idx,
                                scores=scores,
                                spec=spec,
                                condition=condition,
                                method=method,
                                thresholds=thresholds,
                                min_unauth_test=args.min_unauth_test,
                                extra=extra_info,
                            )
                else:
                    present_scores, auth_scores, info = run_decomposed_global_components(
                        x=x,
                        present_y=present_y,
                        auth_y=auth_y,
                        train_idx=train_idx,
                        test_idx=test_idx,
                    )
                    if present_scores is None or auth_scores is None:
                        for method in global_methods:
                            skipped_rows.append({**split_metadata(spec), "schema_condition": condition, "method": method, **info})
                    else:
                        for method in global_methods:
                            if method == "verifier_present_sgd_auth":
                                scores = present_y[test_idx].astype(float) * (1.0 - auth_scores)
                                extra_info = {
                                    **info,
                                    "score_formula": "oracle_present_times_predicted_not_authorized",
                                    "score_definition": "I(candidate_effect_present from verifier) * (1 - P(candidate_effect_authorized))",
                                    "runtime_assumption": "requires an external or execution-level candidate-effect verifier",
                                }
                            else:
                                formula = formula_for_method(method)
                                scores = compose_scores(present_scores, auth_scores, formula)
                                extra_info = {
                                    **info,
                                    "score_formula": formula,
                                    "score_definition": "compose(P(candidate_effect_present), 1 - P(candidate_effect_authorized))",
                                }
                            add_rows(
                                fixed_rows=fixed_rows,
                                curve_rows=curve_rows,
                                rows=rows,
                                test_idx=test_idx,
                                scores=scores,
                                spec=spec,
                                condition=condition,
                                method=method,
                                thresholds=thresholds,
                                min_unauth_test=args.min_unauth_test,
                                extra=extra_info,
                            )
            per_effect_methods = [method for method in args.methods if uses_per_effect_auth_model(method)]
            if per_effect_methods:
                for effect in sorted({rows[int(i)]["candidate_effect"] for i in test_idx}):
                    verifier_only_per_effect = all(
                        method == "verifier_present_per_effect_sgd_auth" for method in per_effect_methods
                    )
                    if verifier_only_per_effect:
                        auth_scores, test_positions, info = run_auth_per_effect_component(
                            x=x,
                            rows=rows,
                            auth_y=auth_y,
                            train_idx=train_idx,
                            test_idx=test_idx,
                            effect=effect,
                        )
                        present_scores = None
                    else:
                        present_scores, auth_scores, test_positions, info = run_decomposed_per_effect_components(
                            x=x,
                            rows=rows,
                            present_y=present_y,
                            auth_y=auth_y,
                            train_idx=train_idx,
                            test_idx=test_idx,
                            effect=effect,
                        )
                    if auth_scores is None or (present_scores is None and not verifier_only_per_effect):
                        for method in per_effect_methods:
                            skipped_rows.append(
                                {
                                    **split_metadata(spec),
                                    "schema_condition": condition,
                                    "method": method,
                                    "effect": effect,
                                    **info,
                                }
                            )
                        continue
                    for method in per_effect_methods:
                        scores = np.zeros(len(test_idx), dtype=float)
                        if method == "verifier_present_per_effect_sgd_auth":
                            effect_test_idx = np.array([int(test_idx[pos]) for pos in test_positions], dtype=int)
                            scores[test_positions] = present_y[effect_test_idx].astype(float) * (1.0 - auth_scores)
                            extra_info = {
                                **info,
                                "score_formula": "per-effect oracle_present_times_predicted_not_authorized",
                                "score_definition": "I(candidate_effect_present from verifier) * (1 - P(candidate_effect_authorized))",
                                "runtime_assumption": "requires an external or execution-level candidate-effect verifier",
                            }
                        else:
                            formula = formula_for_method(method)
                            scores[test_positions] = compose_scores(present_scores, auth_scores, formula)
                            extra_info = {
                                **info,
                                "score_formula": formula,
                                "score_definition": "per-effect compose(P(candidate_effect_present), 1 - P(candidate_effect_authorized))",
                            }
                        add_rows(
                            fixed_rows=fixed_rows,
                            curve_rows=curve_rows,
                            rows=rows,
                            test_idx=test_idx,
                            scores=scores,
                            spec=spec,
                            condition=condition,
                            method=method,
                            thresholds=thresholds,
                            min_unauth_test=args.min_unauth_test,
                            extra=extra_info,
                            effect_filter=[effect],
                        )
            print(f"  fixed rows {len(fixed_rows)}, curve rows {len(curve_rows)}, skipped {len(skipped_rows)}", flush=True)

    payload = {
        "schema_version": "auth_decomposed_verifier_mitigation_v1",
        "generated_by": "experiment_auth_decomposed_verifier_mitigation.py",
        "data_name": args.data_name,
        "baseline_data_name": args.baseline_data_name,
        "n_samples": len(rows),
        "conditions": conditions,
        "methods": args.methods,
        "evaluations": args.evaluations,
        "thresholds": thresholds,
        "target_fpr": args.target_fpr,
        "output_suffix": args.output_suffix,
        "fixed_threshold_rows": fixed_rows,
        "fixed_threshold_aggregate": aggregate_fixed(fixed_rows),
        "threshold_curve_rows": curve_rows,
        "threshold_curve_aggregate": aggregate_curves(curve_rows),
        "best_tradeoffs": best_tradeoffs(curve_rows, args.target_fpr),
        "same_cell_baseline_comparison": same_cell_baseline_comparison(
            base=base,
            baseline_data_name=args.baseline_data_name,
            curve_rows=curve_rows,
            target_fpr=args.target_fpr,
        ),
        "skipped_rows": skipped_rows,
        "caveats": [
            "This is a pair-free decomposed verifier over frozen schema-conditioned embeddings.",
            "The method trains on candidate-effect presence and authorization labels, then composes the unauthorized score as realized times not-authorized.",
            "`verifier_present_*` methods use the candidate-effect-present label at evaluation as a verifier-assisted upper-bound setting; they are not pure LLM representation probes.",
            "Comparisons to T54 baselines are setting-shifted because the verifier receives candidate-effect schema text and auxiliary supervision.",
            "Threshold tradeoffs are ex-post diagnostics, not deployment-calibrated thresholds.",
        ],
    }
    return payload


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Auth Decomposed Verifier Mitigation",
        "",
        f"- Data: `{payload['data_name']}`",
        f"- Samples: {payload['n_samples']}",
        f"- Conditions: `{payload['conditions']}`",
        f"- Methods: `{payload['methods']}`",
        f"- Target FPR: {payload['target_fpr']}",
        "",
        "## Fixed Threshold Aggregate",
        "",
        "| Split | Condition | Method | Rows | Cells | Mean FNR | Std FNR | Max FNR | Mean FPR |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["fixed_threshold_aggregate"]:
        lines.append(
            f"| `{row['split_type']}` | `{row['schema_condition']}` | `{row['method']}` | "
            f"{row['rows']} | {row['unique_cells']} | {row['mean_unauthorized_fnr']} | "
            f"{row['std_unauthorized_fnr']} | {row['max_unauthorized_fnr']} | "
            f"{row['mean_absent_not_authorized_fpr']} |"
        )

    lines.extend(
        [
            "",
            "## Best Ex-Post Tradeoffs",
            "",
            "| Split | Condition | Method | Threshold | Cells | Mean FNR | Mean FPR |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in payload["best_tradeoffs"]:
        lines.append(
            f"| `{row['split_type']}` | `{row['schema_condition']}` | `{row['method']}` | "
            f"{row['threshold']} | {row['unique_cells']} | {row['mean_unauthorized_fnr']} | "
            f"{row['mean_absent_not_authorized_fpr']} |"
        )

    comparison = payload["same_cell_baseline_comparison"]
    lines.extend(["", "## Same-Cell Comparison vs T54 Baselines", ""])
    if not comparison.get("available"):
        lines.append(f"- Baseline comparison unavailable: {comparison.get('reason')}")
    else:
        lines.extend(
            [
                f"- Baseline source: `{comparison['baseline_source']}`",
                f"- Interpretation: {comparison['interpretation']}",
                "",
                "| Split | Condition | Method | Cells | Baseline cells | Dec FNR | Dec FPR | Best baseline | Base FNR | Base FPR | Delta FNR |",
                "|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|",
            ]
        )
        for row in comparison["rows"]:
            lines.append(
                f"| `{row['split_type']}` | `{row['schema_condition']}` | `{row['decomposed_method']}` | "
                f"{row['decomposed_cells']} | {row['baseline_cells_matched']} | "
                f"{row['decomposed_mean_fnr']} | {row['decomposed_mean_fpr']} | "
                f"`{row['best_baseline_method']}` | {row['best_baseline_mean_fnr']} | "
                f"{row['best_baseline_mean_fpr']} | {row['delta_fnr_vs_best_baseline']} |"
            )

    lines.extend(["", "## Skips", ""])
    if payload["skipped_rows"]:
        lines.append(f"- Skipped rows: {len(payload['skipped_rows'])}")
    else:
        lines.append("- No skipped training runs.")
    lines.extend(["", "## Caveats", ""])
    for caveat in payload["caveats"]:
        lines.append(f"- {caveat}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = run()
    base = Path(__file__).resolve().parent.parent
    suffix = payload.get("output_suffix", "")
    out_json = base / "analysis" / f"auth_decomposed_verifier_mitigation_{payload['data_name']}{suffix}.json"
    out_md = base / "analysis" / f"auth_decomposed_verifier_mitigation_{payload['data_name']}{suffix}.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Saved JSON: {out_json}")
    print(f"Saved MD:   {out_md}")
    print(f"Fixed rows: {len(payload['fixed_threshold_rows'])}")
    print(f"Curve rows: {len(payload['threshold_curve_rows'])}")
    print(f"Skipped rows: {len(payload['skipped_rows'])}")


if __name__ == "__main__":
    main()
