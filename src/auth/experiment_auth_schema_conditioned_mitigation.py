"""T55: effect-schema conditioned Auth-SafeInv monitor.

This experiment evaluates a pair-free, safety-supervised monitor over
candidate-effect queries. Each row asks whether a named candidate effect is
both realized by the tool call and outside the task authorization envelope.

Important interpretation:
  This is not the same training setting as the T47/T54 realized-effect probes.
  It trains directly on unauthorized-effect labels after adding a candidate
  effect schema to the input. Treat comparisons to T54 baselines as
  setting-shifted diagnostics, not as a like-for-like method win.

Outputs:
  analysis/auth_schema_conditioned_mitigation_<data_name>.json
  analysis/auth_schema_conditioned_mitigation_<data_name>.md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import experiment_auth_baselines as base_exp


DEFAULT_METHODS = ["schema_sgd_logistic", "schema_per_effect_sgd"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Effect-schema conditioned Auth-SafeInv monitor.")
    parser.add_argument("data_name", nargs="?", default="qwen3-8b_auth_effect_schema_conditioned_v2")
    parser.add_argument("--baseline-data-name", default="qwen3-8b_authorization_counterfactuals_v2")
    parser.add_argument("--evaluations", nargs="*", default=["loto", "family"])
    parser.add_argument("--conditions", nargs="*", default=["full_tool_chain", "auth_only_control", "tool_only_control"])
    parser.add_argument("--methods", nargs="*", default=DEFAULT_METHODS)
    parser.add_argument("--random-seeds", nargs="*", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--torch-seeds", nargs="*", type=int, default=[0])
    parser.add_argument("--hidden-dims", nargs="*", type=int, default=[64])
    parser.add_argument("--lrs", nargs="*", type=float, default=[1e-3])
    parser.add_argument("--torch-epochs", type=int, default=15)
    parser.add_argument("--thresholds", nargs="*", type=float)
    parser.add_argument("--target-fpr", type=float, default=0.10)
    parser.add_argument("--min-unauth-test", type=int, default=3)
    return parser.parse_args()


def load(base: Path, data_name: str) -> tuple[np.ndarray, list[dict[str, Any]]]:
    x = np.load(base / "embeddings" / f"embeddings_{data_name}.npy").astype(np.float32)
    data_file = data_name.replace("qwen3-8b_", "")
    items = [
        json.loads(line)
        for line in (base / "data" / f"{data_file}.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if len(items) != len(x):
        raise ValueError(f"Length mismatch: items={len(items)} X={len(x)}")
    return x, items


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
    items: list[dict[str, Any]],
    condition_idx: np.ndarray,
    evaluations: list[str],
    random_seeds: list[int],
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    condition_set = set(int(i) for i in condition_idx)
    if "random" in evaluations:
        groups = np.array(sorted({items[int(i)]["split_group"] for i in condition_idx}))
        for seed in random_seeds:
            rng = np.random.default_rng(seed)
            shuffled = groups.copy()
            rng.shuffle(shuffled)
            train_groups = set(shuffled[: int(len(shuffled) * 0.8)])
            train = np.array(
                [i for i in condition_idx if items[int(i)]["split_group"] in train_groups],
                dtype=int,
            )
            test = np.array(
                [i for i in condition_idx if items[int(i)]["split_group"] not in train_groups],
                dtype=int,
            )
            specs.append({"split_type": "random_group", "seed": seed, "train_idx": train, "test_idx": test})
    if "loto" in evaluations:
        for tool in sorted({items[int(i)]["tool_name"] for i in condition_idx}):
            train = np.array(
                [i for i in condition_idx if items[int(i)]["tool_name"] != tool],
                dtype=int,
            )
            test = np.array(
                [i for i in condition_idx if items[int(i)]["tool_name"] == tool],
                dtype=int,
            )
            specs.append({"split_type": "leave_one_tool_out", "heldout_tool": tool, "train_idx": train, "test_idx": test})
    if "family" in evaluations:
        for family in sorted({items[int(i)]["counterfactual_family"] for i in condition_idx}):
            train = np.array(
                [i for i in condition_idx if items[int(i)]["counterfactual_family"] != family],
                dtype=int,
            )
            test = np.array(
                [i for i in condition_idx if items[int(i)]["counterfactual_family"] == family],
                dtype=int,
            )
            specs.append({"split_type": "leave_one_family_out", "heldout_family": family, "train_idx": train, "test_idx": test})
    return [
        spec
        for spec in specs
        if len(spec["train_idx"]) > 0
        and len(spec["test_idx"]) > 0
        and len(set(spec["train_idx"]).intersection(condition_set)) == len(spec["train_idx"])
    ]


def labels(items: list[dict[str, Any]]) -> np.ndarray:
    return np.array([int(item["label_unauthorized_effect"]) for item in items], dtype=int)


def domain_ids(items: list[dict[str, Any]], idx: np.ndarray) -> np.ndarray:
    vocab = {tool: i for i, tool in enumerate(sorted({item["tool_name"] for item in items}))}
    return np.array([vocab[items[int(i)]["tool_name"]] for i in idx], dtype=int)


def evaluate_candidate_predictions(
    *,
    items: list[dict[str, Any]],
    test_idx: np.ndarray,
    effect: str,
    scores: np.ndarray,
    threshold: float,
) -> dict[str, Any] | None:
    local = [pos for pos, idx in enumerate(test_idx) if items[int(idx)]["candidate_effect"] == effect]
    if not local:
        return None
    y = np.array([int(items[int(test_idx[pos])]["label_unauthorized_effect"]) for pos in local], dtype=int)
    absent = np.array([bool(items[int(test_idx[pos])]["label_absent_not_authorized"]) for pos in local], dtype=bool)
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


def add_fixed_and_curve_rows(
    *,
    fixed_rows: list[dict[str, Any]],
    curve_rows: list[dict[str, Any]],
    items: list[dict[str, Any]],
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
    candidate_effects = effect_filter or sorted({items[int(i)]["candidate_effect"] for i in test_idx})
    for effect in candidate_effects:
        metric = evaluate_candidate_predictions(
            items=items,
            test_idx=test_idx,
            effect=effect,
            scores=scores,
            threshold=0.5,
        )
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
            curve_metric = evaluate_candidate_predictions(
                items=items,
                test_idx=test_idx,
                effect=effect,
                scores=scores,
                threshold=threshold,
            )
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


def fit_sgd_scores(
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


def add_per_effect_sgd_rows(
    *,
    fixed_rows: list[dict[str, Any]],
    curve_rows: list[dict[str, Any]],
    x: np.ndarray,
    y: np.ndarray,
    items: list[dict[str, Any]],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    spec: dict[str, Any],
    condition: str,
    thresholds: list[float],
    min_unauth_test: int,
) -> int:
    added = 0
    for effect in sorted({items[int(i)]["candidate_effect"] for i in test_idx}):
        train_effect_idx = np.array(
            [int(i) for i in train_idx if items[int(i)]["candidate_effect"] == effect],
            dtype=int,
        )
        local_positions = [pos for pos, idx in enumerate(test_idx) if items[int(idx)]["candidate_effect"] == effect]
        if not local_positions:
            continue
        test_effect_idx = np.array([int(test_idx[pos]) for pos in local_positions], dtype=int)
        if int(y[test_effect_idx].sum()) < min_unauth_test:
            continue
        effect_seed = 1000 + sum((pos + 1) * ord(ch) for pos, ch in enumerate(effect))
        scores_local = fit_sgd_scores(
            x_train=x[train_effect_idx],
            y_train=y[train_effect_idx],
            x_test=x[test_effect_idx],
            random_state=effect_seed,
        )
        if scores_local is None:
            continue
        scores = np.zeros(len(test_idx), dtype=float)
        scores[local_positions] = scores_local
        before = len(curve_rows)
        add_fixed_and_curve_rows(
            fixed_rows=fixed_rows,
            curve_rows=curve_rows,
            items=items,
            test_idx=test_idx,
            scores=scores,
            spec=spec,
            condition=condition,
            method="schema_per_effect_sgd",
            thresholds=thresholds,
            min_unauth_test=min_unauth_test,
            extra={"optimizer": "per_effect_sgd_log_loss", "trained_effect": effect},
            effect_filter=[effect],
        )
        added += len(curve_rows) - before
    return added


def aggregate_fixed(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["split_type"], row["schema_condition"], row["method"])].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, condition, method), vals in sorted(groups.items()):
        fnr = np.array([row["unauthorized_fnr"] for row in vals], dtype=float)
        fpr_vals = [row["not_authorized_absent_fpr"] for row in vals if row["not_authorized_absent_fpr"] is not None]
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
                "mean_absent_not_authorized_fpr": None if not fpr_vals else round(float(np.mean(fpr_vals)), 4),
            }
        )
    return out


def aggregate_curves(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["split_type"], row["schema_condition"], row["method"], float(row["threshold"]))].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, condition, method, threshold), vals in sorted(groups.items()):
        fpr_vals = [row["not_authorized_absent_fpr"] for row in vals if row["not_authorized_absent_fpr"] is not None]
        out.append(
            {
                "split_type": split_type,
                "schema_condition": condition,
                "method": method,
                "threshold": round(float(threshold), 4),
                "rows": len(vals),
                "unique_cells": len({cell_key(v) for v in vals}),
                "mean_unauthorized_fnr": round(float(np.mean([v["unauthorized_fnr"] for v in vals])), 4),
                "mean_absent_not_authorized_fpr": None if not fpr_vals else round(float(np.mean(fpr_vals)), 4),
            }
        )
    return out


def best_tradeoffs(rows: list[dict[str, Any]], target_fpr: float) -> list[dict[str, Any]]:
    aggregate = aggregate_curves(rows)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in aggregate:
        groups[(row["split_type"], row["schema_condition"], row["method"])].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, condition, method), vals in sorted(groups.items()):
        candidates = [
            row
            for row in vals
            if row["mean_absent_not_authorized_fpr"] is not None
            and float(row["mean_absent_not_authorized_fpr"]) <= target_fpr
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
    aggregates: list[dict[str, Any]] = []
    for (split_type, method, threshold), vals in sorted(groups.items()):
        fprs = [row["not_authorized_absent_fpr"] for row in vals if row["not_authorized_absent_fpr"] is not None]
        aggregates.append(
            {
                "split_type": split_type,
                "method": method,
                "threshold": threshold,
                "mean_unauthorized_fnr": round(float(np.mean([row["unauthorized_fnr"] for row in vals])), 4),
                "mean_absent_not_authorized_fpr": None if not fprs else round(float(np.mean(fprs)), 4),
            }
        )
    by_split_method: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in aggregates:
        by_split_method[(row["split_type"], row["method"])].append(row)
    out = []
    for (split_type, method), vals in sorted(by_split_method.items()):
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
    schema_curve_rows: list[dict[str, Any]],
    target_fpr: float,
) -> dict[str, Any]:
    baseline_path = base / "analysis" / f"auth_baseline_confirmatory_{baseline_data_name}.json"
    if not baseline_path.exists():
        return {"available": False, "reason": f"missing {baseline_path}"}
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_rows = baseline.get("threshold_curve_rows", [])
    rows: list[dict[str, Any]] = []
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in schema_curve_rows:
        groups[(row["split_type"], row["schema_condition"], row["method"])].append(row)

    for (split_type, condition, method), vals in sorted(groups.items()):
        cells = {cell_key(row) for row in vals}
        schema_best = best_tradeoffs(vals, target_fpr)
        schema_row = next(
            (
                row
                for row in schema_best
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
        rows.append(
            {
                "split_type": split_type,
                "schema_condition": condition,
                "schema_method": method,
                "target_fpr": target_fpr,
                "schema_cells": len(cells),
                "baseline_cells_matched": len({cell_key(row) for row in baseline_subset}),
                "schema_threshold": None if schema_row is None else schema_row["threshold"],
                "schema_mean_fnr": None if schema_row is None else schema_row["mean_unauthorized_fnr"],
                "schema_mean_fpr": None if schema_row is None else schema_row["mean_absent_not_authorized_fpr"],
                "best_baseline_method": None if best_base is None else best_base["method"],
                "best_baseline_threshold": None if best_base is None else best_base["threshold"],
                "best_baseline_mean_fnr": None if best_base is None else best_base["mean_unauthorized_fnr"],
                "best_baseline_mean_fpr": None if best_base is None else best_base["mean_absent_not_authorized_fpr"],
                "delta_fnr_vs_best_baseline": None
                if best_base is None or schema_row is None or schema_row["mean_unauthorized_fnr"] is None
                else round(best_base["mean_unauthorized_fnr"] - schema_row["mean_unauthorized_fnr"], 4),
            }
        )
    return {
        "available": True,
        "baseline_source": str(baseline_path.relative_to(base)),
        "excluded_baseline_methods": ["open_set_abstain"],
        "interpretation": "Setting-shifted comparison: schema monitor trains on candidate unauthorized labels; baselines train on realized effects.",
        "rows": rows,
    }


def run_method_scores(
    *,
    method: str,
    x: np.ndarray,
    y: np.ndarray,
    items: list[dict[str, Any]],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    args: argparse.Namespace,
) -> list[tuple[np.ndarray, dict[str, Any]]]:
    x_train = x[train_idx]
    x_test = x[test_idx]
    y_train = y[train_idx]
    if method == "schema_sgd_logistic":
        scores = fit_sgd_scores(x_train=x_train, y_train=y_train, x_test=x_test, random_state=17)
        if scores is None:
            return []
        return [(scores, {"optimizer": "sgd_log_loss"})]
    if method == "schema_pooled_logistic":
        clf = base_exp.fit_logistic(x_train, y_train)
        if clf is None:
            return []
        return [(clf.predict_proba(x_test)[:, 1], {})]

    domain_train = domain_ids(items, train_idx)
    outputs: list[tuple[np.ndarray, dict[str, Any]]] = []
    if method == "schema_irm_linear":
        for torch_seed in args.torch_seeds:
            for lr in args.lrs:
                scores = base_exp.train_irm_linear(
                    x_train,
                    y_train,
                    x_test,
                    domain_train,
                    epochs=args.torch_epochs,
                    lr=lr,
                    seed=torch_seed,
                )
                if scores is not None:
                    outputs.append((scores, {"torch_seed": torch_seed, "lr": lr, "epochs": args.torch_epochs}))
        return outputs
    if method in {"schema_domain_adversarial", "schema_supervised_contrastive"}:
        for torch_seed in args.torch_seeds:
            for hidden_dim in args.hidden_dims:
                for lr in args.lrs:
                    extra = {"torch_seed": torch_seed, "hidden_dim": hidden_dim, "lr": lr, "epochs": args.torch_epochs}
                    if method == "schema_domain_adversarial":
                        scores = base_exp.train_domain_adversarial(
                            x_train,
                            y_train,
                            x_test,
                            domain_train,
                            epochs=args.torch_epochs,
                            hidden_dim=hidden_dim,
                            lr=lr,
                            seed=torch_seed,
                        )
                    else:
                        scores = base_exp.train_supervised_contrastive(
                            x_train,
                            y_train,
                            x_test,
                            epochs=args.torch_epochs,
                            hidden_dim=hidden_dim,
                            lr=lr,
                            seed=torch_seed,
                        )
                    if scores is not None:
                        outputs.append((scores, extra))
        return outputs
    raise ValueError(f"Unknown method: {method}")


def run() -> dict[str, Any]:
    args = parse_args()
    torch.set_num_threads(4)
    thresholds = args.thresholds if args.thresholds else [round(float(v), 4) for v in np.linspace(0.0, 1.0, 21)]
    base = Path(__file__).resolve().parent.parent
    x, items = load(base, args.data_name)
    y = labels(items)

    available_conditions = sorted({item["schema_condition"] for item in items})
    conditions = [condition for condition in args.conditions if condition in available_conditions]
    if not conditions:
        raise ValueError(f"No requested conditions found. Available: {available_conditions}")

    fixed_rows: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []
    for condition in conditions:
        condition_idx = np.array([i for i, item in enumerate(items) if item["schema_condition"] == condition], dtype=int)
        specs = build_split_specs(items, condition_idx, args.evaluations, args.random_seeds)
        for spec_id, spec in enumerate(specs, start=1):
            print(f"[{condition} {spec_id}/{len(specs)}] {split_metadata(spec)}", flush=True)
            train_idx = spec["train_idx"]
            test_idx = spec["test_idx"]
            for method in args.methods:
                if method == "schema_per_effect_sgd":
                    added = add_per_effect_sgd_rows(
                        fixed_rows=fixed_rows,
                        curve_rows=curve_rows,
                        x=x,
                        y=y,
                        items=items,
                        train_idx=train_idx,
                        test_idx=test_idx,
                        spec=spec,
                        condition=condition,
                        thresholds=thresholds,
                        min_unauth_test=args.min_unauth_test,
                    )
                    if added == 0:
                        skipped_rows.append(
                            {
                                **split_metadata(spec),
                                "schema_condition": condition,
                                "method": method,
                                "reason": "per_effect_training_not_evaluable",
                            }
                        )
                    continue
                score_sets = run_method_scores(
                    method=method,
                    x=x,
                    y=y,
                    items=items,
                    train_idx=train_idx,
                    test_idx=test_idx,
                    args=args,
                )
                if not score_sets:
                    skipped_rows.append(
                        {
                            **split_metadata(spec),
                            "schema_condition": condition,
                            "method": method,
                            "reason": "training_not_evaluable",
                        }
                    )
                    continue
                for scores, extra in score_sets:
                    add_fixed_and_curve_rows(
                        fixed_rows=fixed_rows,
                        curve_rows=curve_rows,
                        items=items,
                        test_idx=test_idx,
                        scores=scores,
                        spec=spec,
                        condition=condition,
                        method=method,
                        thresholds=thresholds,
                        min_unauth_test=args.min_unauth_test,
                        extra=extra,
                    )
            print(f"  fixed rows {len(fixed_rows)}, curve rows {len(curve_rows)}", flush=True)

    payload = {
        "schema_version": "auth_schema_conditioned_mitigation_v1",
        "generated_by": "experiment_auth_schema_conditioned_mitigation.py",
        "data_name": args.data_name,
        "baseline_data_name": args.baseline_data_name,
        "n_samples": len(items),
        "conditions": conditions,
        "methods": args.methods,
        "evaluations": args.evaluations,
        "thresholds": thresholds,
        "target_fpr": args.target_fpr,
        "fixed_threshold_rows": fixed_rows,
        "fixed_threshold_aggregate": aggregate_fixed(fixed_rows),
        "threshold_curve_rows": curve_rows,
        "threshold_curve_aggregate": aggregate_curves(curve_rows),
        "best_tradeoffs": best_tradeoffs(curve_rows, args.target_fpr),
        "same_cell_baseline_comparison": same_cell_baseline_comparison(
            base=base,
            baseline_data_name=args.baseline_data_name,
            schema_curve_rows=curve_rows,
            target_fpr=args.target_fpr,
        ),
        "skipped_rows": skipped_rows,
        "caveats": [
            "This is a pair-free schema-conditioned monitor; it does not train on cross-tool positive pairs.",
            "It trains directly on unauthorized-effect labels after candidate-effect query expansion, so comparisons to T54 realized-effect probes are setting-shifted.",
            "Threshold-curve tradeoffs are ex-post diagnostics, not deployment-calibrated thresholds.",
            "The auth_only_control and tool_only_control conditions test whether gains come from both authorization context and tool causal information.",
        ],
    }
    return payload


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Auth Effect-Schema Conditioned Mitigation",
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
                "| Split | Condition | Method | Schema cells | Baseline cells | Schema FNR | Schema FPR | Best baseline | Base FNR | Base FPR | Delta FNR |",
                "|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|",
            ]
        )
        for row in comparison["rows"]:
            lines.append(
                f"| `{row['split_type']}` | `{row['schema_condition']}` | `{row['schema_method']}` | "
                f"{row['schema_cells']} | {row['baseline_cells_matched']} | "
                f"{row['schema_mean_fnr']} | {row['schema_mean_fpr']} | "
                f"`{row['best_baseline_method']}` | {row['best_baseline_mean_fnr']} | "
                f"{row['best_baseline_mean_fpr']} | {row['delta_fnr_vs_best_baseline']} |"
            )

    lines.extend(["", "## Skips", ""])
    if payload["skipped_rows"]:
        lines.append(f"- Skipped training rows: {len(payload['skipped_rows'])}")
    else:
        lines.append("- No skipped training runs.")

    lines.extend(["", "## Caveats", ""])
    for caveat in payload["caveats"]:
        lines.append(f"- {caveat}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = run()
    base = Path(__file__).resolve().parent.parent
    out_json = base / "analysis" / f"auth_schema_conditioned_mitigation_{payload['data_name']}.json"
    out_md = base / "analysis" / f"auth_schema_conditioned_mitigation_{payload['data_name']}.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Saved JSON: {out_json}")
    print(f"Saved MD:   {out_md}")
    print(f"Fixed rows: {len(payload['fixed_threshold_rows'])}")
    print(f"Curve rows: {len(payload['threshold_curve_rows'])}")
    print(f"Skipped rows: {len(payload['skipped_rows'])}")


if __name__ == "__main__":
    main()
