"""T47 confirmatory sweep for Auth-SafeInv baselines.

This extends the T44 pilot with reviewer-facing checks:

* torch seed variance for IRM-linear, domain-adversarial, and supervised
  contrastive baselines;
* small hyperparameter sweep for hidden dimension / learning rate;
* threshold curves for FNR-FPR tradeoffs;
* explicit accounting for open-set abstention degenerating into reject-all on
  held-out tools.

The script keeps outputs separate from `experiment_auth_baselines.py`.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

import experiment_auth_baselines as base_exp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Confirmatory Auth-SafeInv baseline sweep.")
    parser.add_argument("data_name", nargs="?", default="qwen3-8b_authorization_counterfactuals_v1")
    parser.add_argument("--evaluations", nargs="*", default=["loto", "family"])
    parser.add_argument("--random-seeds", nargs="*", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--torch-seeds", nargs="*", type=int, default=[0, 1, 2])
    parser.add_argument("--hidden-dims", nargs="*", type=int, default=[64, 128])
    parser.add_argument("--lrs", nargs="*", type=float, default=[1e-3])
    parser.add_argument("--torch-epochs", type=int, default=15)
    parser.add_argument("--thresholds", nargs="*", type=float)
    parser.add_argument("--min-unauth-test", type=int, default=3)
    parser.add_argument("--calibration-fpr", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def metric_from_scores(
    *,
    items: list[dict[str, Any]],
    test_idx: np.ndarray,
    effect: str,
    scores: np.ndarray,
    threshold: float,
) -> dict[str, Any] | None:
    return base_exp.evaluate_predictions(
        items=items,
        test_idx=test_idx,
        effect_name=effect,
        scores=scores,
        threshold=threshold,
    )


def threshold_curve(
    *,
    items: list[dict[str, Any]],
    test_idx: np.ndarray,
    effect: str,
    scores: np.ndarray,
    thresholds: list[float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        metric = metric_from_scores(
            items=items,
            test_idx=test_idx,
            effect=effect,
            scores=scores,
            threshold=threshold,
        )
        if metric is None:
            continue
        rows.append(
            {
                "threshold": round(float(threshold), 4),
                "unauthorized_fnr": metric["unauthorized_fnr"],
                "not_authorized_absent_fpr": metric["not_authorized_absent_fpr"],
                "n_unauth_test": metric["n_unauth_test"],
                "not_authorized_absent_n": metric["not_authorized_absent_n"],
            }
        )
    return rows


def open_set_diagnostic(
    *,
    x_train: np.ndarray,
    x_test: np.ndarray,
    y_train: np.ndarray,
    items: list[dict[str, Any]],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    clf: Any,
    percentile: float = 95.0,
) -> tuple[np.ndarray, dict[str, Any]]:
    vocab = sorted({items[int(i)]["tool_name"] for i in train_idx})
    centroids: dict[str, np.ndarray] = {}
    train_distances: list[float] = []
    for tool in vocab:
        local = np.array([pos for pos, idx in enumerate(train_idx) if items[int(idx)]["tool_name"] == tool], dtype=int)
        if len(local) == 0:
            continue
        centroid = x_train[local].mean(axis=0)
        centroids[tool] = centroid
        train_distances.extend(np.linalg.norm(x_train[local] - centroid, axis=1).tolist())
    cutoff = float(np.percentile(train_distances, percentile)) if train_distances else float("inf")

    proba = clf.predict_proba(x_test)[:, 1]
    pred = proba >= 0.5
    abstained = np.zeros(len(test_idx), dtype=bool)
    unknown_tool = np.zeros(len(test_idx), dtype=bool)
    distance_abstain = np.zeros(len(test_idx), dtype=bool)
    for pos, idx in enumerate(test_idx):
        tool = items[int(idx)]["tool_name"]
        if tool not in centroids:
            pred[pos] = True
            abstained[pos] = True
            unknown_tool[pos] = True
            continue
        dist = float(np.linalg.norm(x_test[pos] - centroids[tool]))
        if dist > cutoff:
            pred[pos] = True
            abstained[pos] = True
            distance_abstain[pos] = True
    diagnostics = {
        "distance_cutoff_percentile": percentile,
        "distance_cutoff": round(cutoff, 4),
        "abstain_rate": round(float(abstained.mean()), 4),
        "unknown_tool_abstain_rate": round(float(unknown_tool.mean()), 4),
        "distance_abstain_rate": round(float(distance_abstain.mean()), 4),
        "reject_all_degenerate": bool(float(abstained.mean()) >= 0.95),
        "train_positive_rate": round(float(y_train.mean()), 4),
    }
    return pred.astype(int), diagnostics


def split_metadata(spec: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in spec.items() if k not in {"train_idx", "test_idx"}}


def add_metric_row(
    rows: list[dict[str, Any]],
    *,
    spec: dict[str, Any],
    effect: str,
    method: str,
    metric: dict[str, Any] | None,
    n_train: int,
    n_test: int,
    extra: dict[str, Any] | None = None,
) -> None:
    if metric is None:
        return
    row = {
        **split_metadata(spec),
        "effect": effect,
        "method": method,
        "n_train": int(n_train),
        "n_test": int(n_test),
        **metric,
    }
    if extra:
        row.update(extra)
    rows.append(row)


def add_curve_rows(
    rows: list[dict[str, Any]],
    *,
    spec: dict[str, Any],
    effect: str,
    method: str,
    curve: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> None:
    for item in curve:
        row = {**split_metadata(spec), "effect": effect, "method": method, **item}
        if extra:
            row.update(extra)
        rows.append(row)


def aggregate_fixed(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["split_type"], row["method"])].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, method), vals in sorted(groups.items()):
        fnr = np.array([v["unauthorized_fnr"] for v in vals], dtype=float)
        fpr_vals = [v["not_authorized_absent_fpr"] for v in vals if v["not_authorized_absent_fpr"] is not None]
        out.append(
            {
                "split_type": split_type,
                "method": method,
                "rows": len(vals),
                "mean_unauthorized_fnr": round(float(fnr.mean()), 4),
                "std_unauthorized_fnr": round(float(fnr.std(ddof=0)), 4),
                "median_unauthorized_fnr": round(float(np.median(fnr)), 4),
                "max_unauthorized_fnr": round(float(fnr.max()), 4),
                "mean_absent_not_authorized_fpr": None if not fpr_vals else round(float(np.mean(fpr_vals)), 4),
                "std_absent_not_authorized_fpr": None if not fpr_vals else round(float(np.std(fpr_vals, ddof=0)), 4),
            }
        )
    return out


def seed_variance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    per_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if "torch_seed" not in row:
            continue
        per_seed[(row["split_type"], row["method"], int(row["torch_seed"]))].append(row)

    by_method: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for (split_type, method, seed), vals in sorted(per_seed.items()):
        fnr = float(np.mean([v["unauthorized_fnr"] for v in vals]))
        fprs = [v["not_authorized_absent_fpr"] for v in vals if v["not_authorized_absent_fpr"] is not None]
        by_method[(split_type, method)].append(
            {
                "torch_seed": seed,
                "mean_unauthorized_fnr": fnr,
                "mean_absent_not_authorized_fpr": None if not fprs else float(np.mean(fprs)),
            }
        )

    out: list[dict[str, Any]] = []
    for (split_type, method), vals in sorted(by_method.items()):
        fnr = np.array([v["mean_unauthorized_fnr"] for v in vals], dtype=float)
        fpr_vals = [v["mean_absent_not_authorized_fpr"] for v in vals if v["mean_absent_not_authorized_fpr"] is not None]
        out.append(
            {
                "split_type": split_type,
                "method": method,
                "seeds": [v["torch_seed"] for v in vals],
                "seed_mean_fnr": round(float(fnr.mean()), 4),
                "seed_std_fnr": round(float(fnr.std(ddof=0)), 4),
                "seed_min_fnr": round(float(fnr.min()), 4),
                "seed_max_fnr": round(float(fnr.max()), 4),
                "seed_mean_fpr": None if not fpr_vals else round(float(np.mean(fpr_vals)), 4),
                "seed_std_fpr": None if not fpr_vals else round(float(np.std(fpr_vals, ddof=0)), 4),
            }
        )
    return out


def aggregate_curves(curve_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in curve_rows:
        groups[(row["split_type"], row["method"], float(row["threshold"]))].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, method, threshold), vals in sorted(groups.items()):
        fpr_vals = [v["not_authorized_absent_fpr"] for v in vals if v["not_authorized_absent_fpr"] is not None]
        out.append(
            {
                "split_type": split_type,
                "method": method,
                "threshold": round(float(threshold), 4),
                "rows": len(vals),
                "mean_unauthorized_fnr": round(float(np.mean([v["unauthorized_fnr"] for v in vals])), 4),
                "mean_absent_not_authorized_fpr": None if not fpr_vals else round(float(np.mean(fpr_vals)), 4),
            }
        )
    return out


def best_tradeoffs(curve_aggregate: list[dict[str, Any]], fpr_targets: list[float]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in curve_aggregate:
        groups[(row["split_type"], row["method"])].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, method), vals in sorted(groups.items()):
        for target in fpr_targets:
            candidates = [
                v
                for v in vals
                if v["mean_absent_not_authorized_fpr"] is not None
                and float(v["mean_absent_not_authorized_fpr"]) <= target
            ]
            if not candidates:
                out.append(
                    {
                        "split_type": split_type,
                        "method": method,
                        "target_fpr": target,
                        "threshold": None,
                        "mean_unauthorized_fnr": None,
                        "mean_absent_not_authorized_fpr": None,
                    }
                )
                continue
            best = min(candidates, key=lambda v: (v["mean_unauthorized_fnr"], v["mean_absent_not_authorized_fpr"]))
            out.append(
                {
                    "split_type": split_type,
                    "method": method,
                    "target_fpr": target,
                    "threshold": best["threshold"],
                    "mean_unauthorized_fnr": best["mean_unauthorized_fnr"],
                    "mean_absent_not_authorized_fpr": best["mean_absent_not_authorized_fpr"],
                }
            )
    return out


def run() -> dict[str, Any]:
    args = parse_args()
    torch.set_num_threads(4)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    base = Path(__file__).resolve().parent.parent
    thresholds = args.thresholds if args.thresholds else [round(float(v), 4) for v in np.linspace(0.0, 1.0, 21)]

    x, y_all, items, effect_names = base_exp.load(base, args.data_name)
    specs = base_exp.build_split_specs(items, args.evaluations, args.random_seeds)
    fixed_rows: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    open_set_rows: list[dict[str, Any]] = []

    domain_vocab = {tool: i for i, tool in enumerate(sorted({item["tool_name"] for item in items}))}
    for spec_id, spec in enumerate(specs, start=1):
        print(f"[{spec_id}/{len(specs)}] {split_metadata(spec)}", flush=True)
        train_idx = spec["train_idx"]
        test_idx = spec["test_idx"]
        x_train = x[train_idx]
        x_test = x[test_idx]
        domain_train = np.array([domain_vocab[items[int(i)]["tool_name"]] for i in train_idx], dtype=int)

        for effect_idx, effect in enumerate(effect_names):
            unauth_test = base_exp.unauthorized_labels(items, effect)[test_idx]
            if int(unauth_test.sum()) < args.min_unauth_test:
                continue
            y_effect = y_all[:, effect_idx]
            y_train = y_effect[train_idx]

            pooled = base_exp.fit_logistic(x_train, y_train)
            if pooled is not None:
                pooled_scores = pooled.predict_proba(x_test)[:, 1]
                metric = metric_from_scores(
                    items=items,
                    test_idx=test_idx,
                    effect=effect,
                    scores=pooled_scores,
                    threshold=0.5,
                )
                add_metric_row(
                    fixed_rows,
                    spec=spec,
                    effect=effect,
                    method="pooled_logistic",
                    metric=metric,
                    n_train=len(train_idx),
                    n_test=len(test_idx),
                )
                add_curve_rows(
                    curve_rows,
                    spec=spec,
                    effect=effect,
                    method="pooled_logistic",
                    curve=threshold_curve(
                        items=items,
                        test_idx=test_idx,
                        effect=effect,
                        scores=pooled_scores,
                        thresholds=thresholds,
                    ),
                )

                pred_open, open_diag = open_set_diagnostic(
                    x_train=x_train,
                    x_test=x_test,
                    y_train=y_train,
                    items=items,
                    train_idx=train_idx,
                    test_idx=test_idx,
                    clf=pooled,
                )
                open_metric = base_exp.evaluate_predictions(
                    items=items,
                    test_idx=test_idx,
                    effect_name=effect,
                    pred=pred_open,
                )
                add_metric_row(
                    fixed_rows,
                    spec=spec,
                    effect=effect,
                    method="open_set_abstain",
                    metric=open_metric,
                    n_train=len(train_idx),
                    n_test=len(test_idx),
                    extra=open_diag,
                )
                if open_metric is not None:
                    open_set_rows.append({**split_metadata(spec), "effect": effect, **open_metric, **open_diag})

            core_idx, val_idx = base_exp.validation_split(train_idx, items, args.seed)
            cal = base_exp.fit_logistic(x[core_idx], y_effect[core_idx])
            if cal is not None and len(val_idx) > 0:
                val_scores = cal.predict_proba(x[val_idx])[:, 1]
                threshold = base_exp.choose_calibrated_threshold(
                    val_scores,
                    y_effect[val_idx],
                    base_exp.unauthorized_labels(items, effect)[val_idx],
                    base_exp.absent_not_authorized_labels(items, effect)[val_idx],
                    args.calibration_fpr,
                )
                cal_scores = cal.predict_proba(x_test)[:, 1]
                add_metric_row(
                    fixed_rows,
                    spec=spec,
                    effect=effect,
                    method="calibrated_abstention",
                    metric=metric_from_scores(
                        items=items,
                        test_idx=test_idx,
                        effect=effect,
                        scores=cal_scores,
                        threshold=threshold,
                    ),
                    n_train=len(core_idx),
                    n_test=len(test_idx),
                    extra={"target_validation_fpr": args.calibration_fpr},
                )

            for torch_seed in args.torch_seeds:
                for lr in args.lrs:
                    irm_scores = base_exp.train_irm_linear(
                        x_train,
                        y_train,
                        x_test,
                        domain_train,
                        epochs=args.torch_epochs,
                        lr=lr,
                        seed=torch_seed + effect_idx * 1000,
                    )
                    if irm_scores is not None:
                        extra = {"torch_seed": torch_seed, "lr": lr, "epochs": args.torch_epochs, "config_id": f"seed{torch_seed}_lr{lr}"}
                        add_metric_row(
                            fixed_rows,
                            spec=spec,
                            effect=effect,
                            method="irm_linear",
                            metric=metric_from_scores(
                                items=items,
                                test_idx=test_idx,
                                effect=effect,
                                scores=irm_scores,
                                threshold=0.5,
                            ),
                            n_train=len(train_idx),
                            n_test=len(test_idx),
                            extra=extra,
                        )
                        add_curve_rows(
                            curve_rows,
                            spec=spec,
                            effect=effect,
                            method="irm_linear",
                            curve=threshold_curve(
                                items=items,
                                test_idx=test_idx,
                                effect=effect,
                                scores=irm_scores,
                                thresholds=thresholds,
                            ),
                            extra=extra,
                        )

                    for hidden_dim in args.hidden_dims:
                        config = {
                            "torch_seed": torch_seed,
                            "hidden_dim": hidden_dim,
                            "lr": lr,
                            "epochs": args.torch_epochs,
                            "config_id": f"seed{torch_seed}_h{hidden_dim}_lr{lr}",
                        }
                        dann_scores = base_exp.train_domain_adversarial(
                            x_train,
                            y_train,
                            x_test,
                            domain_train,
                            epochs=args.torch_epochs,
                            hidden_dim=hidden_dim,
                            lr=lr,
                            seed=torch_seed + effect_idx * 1000,
                        )
                        if dann_scores is not None:
                            add_metric_row(
                                fixed_rows,
                                spec=spec,
                                effect=effect,
                                method="domain_adversarial",
                                metric=metric_from_scores(
                                    items=items,
                                    test_idx=test_idx,
                                    effect=effect,
                                    scores=dann_scores,
                                    threshold=0.5,
                                ),
                                n_train=len(train_idx),
                                n_test=len(test_idx),
                                extra=config,
                            )
                            add_curve_rows(
                                curve_rows,
                                spec=spec,
                                effect=effect,
                                method="domain_adversarial",
                                curve=threshold_curve(
                                    items=items,
                                    test_idx=test_idx,
                                    effect=effect,
                                    scores=dann_scores,
                                    thresholds=thresholds,
                                ),
                                extra=config,
                            )

                        supcon_scores = base_exp.train_supervised_contrastive(
                            x_train,
                            y_train,
                            x_test,
                            epochs=args.torch_epochs,
                            hidden_dim=hidden_dim,
                            lr=lr,
                            seed=torch_seed + effect_idx * 1000,
                        )
                        if supcon_scores is not None:
                            add_metric_row(
                                fixed_rows,
                                spec=spec,
                                effect=effect,
                                method="supervised_contrastive",
                                metric=metric_from_scores(
                                    items=items,
                                    test_idx=test_idx,
                                    effect=effect,
                                    scores=supcon_scores,
                                    threshold=0.5,
                                ),
                                n_train=len(train_idx),
                                n_test=len(test_idx),
                                extra=config,
                            )
                            add_curve_rows(
                                curve_rows,
                                spec=spec,
                                effect=effect,
                                method="supervised_contrastive",
                                curve=threshold_curve(
                                    items=items,
                                    test_idx=test_idx,
                                    effect=effect,
                                    scores=supcon_scores,
                                    thresholds=thresholds,
                                ),
                                extra=config,
                            )
            print(f"  {effect}: fixed rows now {len(fixed_rows)}", flush=True)

    curve_aggregate = aggregate_curves(curve_rows)
    payload = {
        "data_name": args.data_name,
        "n_samples": len(items),
        "evaluations": args.evaluations,
        "torch_seeds": args.torch_seeds,
        "hidden_dims": args.hidden_dims,
        "lrs": args.lrs,
        "torch_epochs": args.torch_epochs,
        "thresholds": thresholds,
        "fixed_threshold_rows": fixed_rows,
        "fixed_threshold_aggregate": aggregate_fixed(fixed_rows),
        "torch_seed_variance": seed_variance(fixed_rows),
        "threshold_curve_rows": curve_rows,
        "threshold_curve_aggregate": curve_aggregate,
        "best_tradeoffs": best_tradeoffs(curve_aggregate, [0.05, 0.10, 0.20]),
        "open_set_diagnostics": {
            "rows": open_set_rows,
            "reject_all_rows": sum(1 for row in open_set_rows if row.get("reject_all_degenerate")),
            "total_rows": len(open_set_rows),
        },
        "caveats": [
            "This is still a compact confirmatory sweep; it improves over the T44 pilot but is not a final hyperparameter search.",
            "Threshold curves are diagnostic FNR-FPR tradeoffs over unauthorized positives and absent-not-authorized negatives.",
            "Open-set abstention is isolated because it can reduce FNR by rejecting every held-out-tool example, yielding unusable FPR.",
            "All torch models train on realized effect labels; authorization is evaluated through unauthorized-effect positives.",
        ],
    }
    return payload


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Auth-SafeInv Baseline Confirmatory Sweep",
        "",
        f"- Data: `{payload['data_name']}`",
        f"- Samples: {payload['n_samples']}",
        f"- Evaluations: {payload['evaluations']}",
        f"- Torch seeds: {payload['torch_seeds']}",
        f"- Hidden dims: {payload['hidden_dims']}",
        f"- Learning rates: {payload['lrs']}",
        f"- Torch epochs: {payload['torch_epochs']}",
        "",
        "## Fixed Threshold Aggregate",
        "",
        "| Split | Method | Rows | Mean FNR | Std FNR | Max FNR | Mean FPR | Std FPR |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["fixed_threshold_aggregate"]:
        lines.append(
            f"| `{row['split_type']}` | `{row['method']}` | {row['rows']} | "
            f"{row['mean_unauthorized_fnr']} | {row['std_unauthorized_fnr']} | "
            f"{row['max_unauthorized_fnr']} | {row['mean_absent_not_authorized_fpr']} | "
            f"{row['std_absent_not_authorized_fpr']} |"
        )

    lines.extend(["", "## Torch Seed Variance", "", "| Split | Method | Seeds | Mean FNR | Std FNR | Min FNR | Max FNR | Mean FPR |", "|---|---|---|---:|---:|---:|---:|---:|"])
    for row in payload["torch_seed_variance"]:
        lines.append(
            f"| `{row['split_type']}` | `{row['method']}` | `{row['seeds']}` | "
            f"{row['seed_mean_fnr']} | {row['seed_std_fnr']} | {row['seed_min_fnr']} | "
            f"{row['seed_max_fnr']} | {row['seed_mean_fpr']} |"
        )

    lines.extend(["", "## Best Threshold Tradeoffs", "", "| Split | Method | Target FPR | Threshold | Mean FNR | Mean FPR |", "|---|---|---:|---:|---:|---:|"])
    for row in payload["best_tradeoffs"]:
        lines.append(
            f"| `{row['split_type']}` | `{row['method']}` | {row['target_fpr']} | "
            f"{row['threshold']} | {row['mean_unauthorized_fnr']} | {row['mean_absent_not_authorized_fpr']} |"
        )

    open_diag = payload["open_set_diagnostics"]
    lines.extend(
        [
            "",
            "## Open-Set Degeneracy",
            "",
            f"- Reject-all degenerate rows: {open_diag['reject_all_rows']} / {open_diag['total_rows']}",
            "",
            "## Caveats",
            "",
        ]
    )
    for caveat in payload["caveats"]:
        lines.append(f"- {caveat}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = run()
    base = Path(__file__).resolve().parent.parent
    out_json = base / "analysis" / f"auth_baseline_confirmatory_{payload['data_name']}.json"
    out_md = base / "analysis" / f"auth_baseline_confirmatory_{payload['data_name']}.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Saved JSON: {out_json}")
    print(f"Saved MD:   {out_md}")
    print(f"Fixed rows: {len(payload['fixed_threshold_rows'])}")
    print(f"Curve rows: {len(payload['threshold_curve_rows'])}")


if __name__ == "__main__":
    main()
