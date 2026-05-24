"""T51: compare Auth-SafeInv mitigation against strong baselines.

This script evaluates contrastive projection under the same Auth-SafeInv
held-out cells used by the T47 confirmatory baseline sweep.

Two projection settings are reported:

* ``contrastive_train_only``: projection pairs are built only from the split's
  training rows. This is the strict coverage-missing setting.
* ``contrastive_observed_pair_upper_bound``: projection pairs may use all rows.
  This is an observed-pair repair upper bound, not evidence of zero-shot safety.

Outputs:
  analysis/auth_mitigation_vs_baseline_<data_name>.json
  analysis/auth_mitigation_vs_baseline_<data_name>.md
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

import experiment_auth_baselines as base_exp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auth-SafeInv mitigation-vs-baseline comparison.")
    parser.add_argument("data_name", nargs="?", default="qwen3-8b_authorization_counterfactuals_v1")
    parser.add_argument("--evaluations", nargs="*", default=["loto", "family"])
    parser.add_argument("--random-seeds", nargs="*", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--projection-seeds", nargs="*", type=int, default=[0, 1, 2])
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--max-pairs-per-tool-pair", type=int, default=60)
    parser.add_argument("--min-pos-per-tool", type=int, default=5)
    parser.add_argument("--min-train-pairs", type=int, default=5)
    parser.add_argument("--min-unauth-test", type=int, default=3)
    parser.add_argument("--thresholds", nargs="*", type=float)
    parser.add_argument("--target-fpr", type=float, default=0.10)
    return parser.parse_args()


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


def add_metric_row(
    rows: list[dict[str, Any]],
    *,
    spec: dict[str, Any],
    effect: str,
    method: str,
    metric: dict[str, Any] | None,
    n_train: int,
    n_test: int,
    extra: dict[str, Any],
) -> None:
    if metric is None:
        return
    rows.append(
        {
            **split_metadata(spec),
            "effect": effect,
            "method": method,
            "n_train": int(n_train),
            "n_test": int(n_test),
            **metric,
            **extra,
        }
    )


def threshold_curve(
    *,
    items: list[dict[str, Any]],
    test_idx: np.ndarray,
    effect: str,
    method: str,
    spec: dict[str, Any],
    scores: np.ndarray,
    thresholds: list[float],
    extra: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        metric = metric_from_scores(
            items=items,
            test_idx=test_idx,
            effect=effect,
            scores=scores,
            threshold=float(threshold),
        )
        if metric is None:
            continue
        rows.append(
            {
                **split_metadata(spec),
                "effect": effect,
                "method": method,
                "threshold": round(float(threshold), 4),
                "unauthorized_fnr": metric["unauthorized_fnr"],
                "not_authorized_absent_fpr": metric["not_authorized_absent_fpr"],
                "n_unauth_test": metric["n_unauth_test"],
                "not_authorized_absent_n": metric["not_authorized_absent_n"],
                **extra,
            }
        )
    return rows


def build_pairs(
    *,
    y: np.ndarray,
    tools: list[str],
    pair_idx: np.ndarray,
    rng: np.random.Generator,
    min_pos_per_tool: int,
    max_pairs_per_tool_pair: int,
) -> tuple[list[tuple[int, int]], dict[str, Any]]:
    tool_pos: dict[str, list[int]] = defaultdict(list)
    for idx in pair_idx:
        i = int(idx)
        if int(y[i]) == 1:
            tool_pos[tools[i]].append(i)

    valid = {tool: idxs for tool, idxs in tool_pos.items() if len(idxs) >= min_pos_per_tool}
    pairs: list[tuple[int, int]] = []
    for a, b in itertools.combinations(sorted(valid), 2):
        n = min(max_pairs_per_tool_pair, len(valid[a]), len(valid[b]))
        if n <= 0:
            continue
        a_sample = rng.choice(valid[a], size=n, replace=False)
        b_sample = rng.choice(valid[b], size=n, replace=False)
        pairs.extend((int(ai), int(bi)) for ai, bi in zip(a_sample, b_sample))

    info = {
        "n_pair_source_rows": int(len(pair_idx)),
        "n_positive_pair_tools": int(len(valid)),
        "positive_pair_tool_counts": {tool: len(valid[tool]) for tool in sorted(valid)},
        "n_train_pairs": int(len(pairs)),
    }
    return pairs, info


def train_projection_scores(
    *,
    x_t: torch.Tensor,
    x_np: np.ndarray,
    y: np.ndarray,
    tools: list[str],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    pair_idx: np.ndarray,
    seed: int,
    dim: int,
    epochs: int,
    lr: float,
    max_pairs_per_tool_pair: int,
    min_pos_per_tool: int,
    min_train_pairs: int,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    pairs, info = build_pairs(
        y=y,
        tools=tools,
        pair_idx=pair_idx,
        rng=rng,
        min_pos_per_tool=min_pos_per_tool,
        max_pairs_per_tool_pair=max_pairs_per_tool_pair,
    )
    if info["n_positive_pair_tools"] < 2:
        info.update({"status": "not_evaluable", "reason": "fewer_than_two_positive_training_tools"})
        return None, info
    if len(pairs) < min_train_pairs:
        info.update({"status": "not_evaluable", "reason": "too_few_cross_tool_positive_pairs"})
        return None, info

    neg_pool = [int(i) for i in pair_idx if int(y[int(i)]) == 0]
    if not neg_pool:
        info.update({"status": "not_evaluable", "reason": "empty_negative_pool"})
        return None, info
    if len(np.unique(y[train_idx])) < 2:
        info.update({"status": "not_evaluable", "reason": "classifier_train_has_single_class"})
        return None, info

    torch.manual_seed(seed)
    device = x_t.device
    pairs_t = torch.tensor(pairs, dtype=torch.long, device=device)
    neg_t = torch.tensor(neg_pool, dtype=torch.long, device=device)
    projection = torch.nn.Parameter(torch.randn(x_np.shape[1], dim, device=device) * 0.01)
    optimizer = torch.optim.Adam([projection], lr=lr)
    batch_size = 64

    for _ in range(epochs):
        perm = torch.randperm(len(pairs), device=device)
        for start in range(0, len(pairs), batch_size):
            batch = perm[start : start + batch_size]
            h_a = x_t[pairs_t[batch, 0]] @ projection
            h_b = x_t[pairs_t[batch, 1]] @ projection
            h_a = torch.nn.functional.normalize(h_a, dim=1)
            h_b = torch.nn.functional.normalize(h_b, dim=1)
            pos_loss = torch.mean(torch.sum((h_a - h_b) ** 2, dim=1))

            neg_idx = neg_t[torch.randint(len(neg_pool), (len(batch),), device=device)]
            h_neg = torch.nn.functional.normalize(x_t[neg_idx] @ projection, dim=1)
            neg_a = torch.sum((h_a - h_neg) ** 2, dim=1)
            neg_b = torch.sum((h_b - h_neg) ** 2, dim=1)
            neg_loss = torch.mean(torch.clamp(1.0 - neg_a, min=0.0))
            neg_loss = neg_loss + torch.mean(torch.clamp(1.0 - neg_b, min=0.0))
            reg_loss = 0.01 * torch.sum(projection**2)
            loss = pos_loss + 0.5 * neg_loss + reg_loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    train_t = torch.tensor(train_idx, dtype=torch.long, device=device)
    test_t = torch.tensor(test_idx, dtype=torch.long, device=device)
    with torch.no_grad():
        z_train = (x_t[train_t] @ projection).detach().cpu().numpy()
        z_test = (x_t[test_t] @ projection).detach().cpu().numpy()
    z_train = z_train / (np.linalg.norm(z_train, axis=1, keepdims=True) + 1e-8)
    z_test = z_test / (np.linalg.norm(z_test, axis=1, keepdims=True) + 1e-8)

    clf = base_exp.fit_logistic(z_train, y[train_idx])
    if clf is None:
        info.update({"status": "not_evaluable", "reason": "classifier_fit_failed"})
        return None, info

    info.update({"status": "ok", "reason": None})
    return clf.predict_proba(z_test)[:, 1], info


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
                "unique_cells": len({cell_key(v) for v in vals}),
                "mean_unauthorized_fnr": round(float(fnr.mean()), 4),
                "std_unauthorized_fnr": round(float(fnr.std(ddof=0)), 4),
                "median_unauthorized_fnr": round(float(np.median(fnr)), 4),
                "max_unauthorized_fnr": round(float(fnr.max()), 4),
                "mean_absent_not_authorized_fpr": None if not fpr_vals else round(float(np.mean(fpr_vals)), 4),
            }
        )
    return out


def aggregate_curves(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
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
                "unique_cells": len({cell_key(v) for v in vals}),
                "mean_unauthorized_fnr": round(float(np.mean([v["unauthorized_fnr"] for v in vals])), 4),
                "mean_absent_not_authorized_fpr": None if not fpr_vals else round(float(np.mean(fpr_vals)), 4),
            }
        )
    return out


def best_tradeoffs(curve_rows: list[dict[str, Any]], target_fpr: float) -> list[dict[str, Any]]:
    aggregate = aggregate_curves(curve_rows)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in aggregate:
        groups[(row["split_type"], row["method"])].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, method), vals in sorted(groups.items()):
        candidates = [
            v
            for v in vals
            if v["mean_absent_not_authorized_fpr"] is not None
            and float(v["mean_absent_not_authorized_fpr"]) <= target_fpr
        ]
        if not candidates:
            out.append(
                {
                    "split_type": split_type,
                    "method": method,
                    "target_fpr": target_fpr,
                    "threshold": None,
                    "mean_unauthorized_fnr": None,
                    "mean_absent_not_authorized_fpr": None,
                    "unique_cells": 0,
                }
            )
            continue
        best = min(candidates, key=lambda v: (v["mean_unauthorized_fnr"], v["mean_absent_not_authorized_fpr"]))
        out.append({**best, "target_fpr": target_fpr})
    return out


def best_from_rows(rows: list[dict[str, Any]], target_fpr: float, excluded_methods: set[str] | None = None) -> list[dict[str, Any]]:
    excluded_methods = excluded_methods or set()
    eligible = [row for row in rows if row.get("method") not in excluded_methods]
    return best_tradeoffs(eligible, target_fpr)


def same_cell_baseline_comparison(
    *,
    base: Path,
    data_name: str,
    mitigation_curve_rows: list[dict[str, Any]],
    target_fpr: float,
) -> dict[str, Any]:
    baseline_path = base / "analysis" / f"auth_baseline_confirmatory_{data_name}.json"
    if not baseline_path.exists():
        return {"available": False, "reason": f"missing {baseline_path}"}
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_rows = baseline.get("threshold_curve_rows", [])
    baseline_cells_by_split = {
        split: {cell_key(row) for row in baseline_rows if row["split_type"] == split and row["method"] == "pooled_logistic"}
        for split in sorted({row["split_type"] for row in baseline_rows})
    }

    rows: list[dict[str, Any]] = []
    methods = sorted({row["method"] for row in mitigation_curve_rows})
    splits = sorted({row["split_type"] for row in mitigation_curve_rows})
    for split_type in splits:
        for method in methods:
            mit_rows = [
                row for row in mitigation_curve_rows if row["split_type"] == split_type and row["method"] == method
            ]
            if not mit_rows:
                continue
            cells = {cell_key(row) for row in mit_rows}
            baseline_subset = [
                row
                for row in baseline_rows
                if row["split_type"] == split_type
                and cell_key(row) in cells
                and row["method"] != "open_set_abstain"
            ]
            mit_best = best_tradeoffs(mit_rows, target_fpr)
            base_best = best_from_rows(baseline_subset, target_fpr, excluded_methods={"open_set_abstain"})
            mit_best_row = next((row for row in mit_best if row["split_type"] == split_type and row["method"] == method), None)
            viable_base = [
                row
                for row in base_best
                if row["split_type"] == split_type
                and row["mean_unauthorized_fnr"] is not None
            ]
            best_base = None
            if viable_base:
                best_base = min(viable_base, key=lambda v: (v["mean_unauthorized_fnr"], v["mean_absent_not_authorized_fpr"]))
            baseline_cell_count = len(baseline_cells_by_split.get(split_type, set()))
            rows.append(
                {
                    "split_type": split_type,
                    "mitigation_method": method,
                    "target_fpr": target_fpr,
                    "mitigation_cells": len(cells),
                    "baseline_cells_total": baseline_cell_count,
                    "cell_coverage": round(len(cells) / baseline_cell_count, 4) if baseline_cell_count else None,
                    "mitigation_threshold": None if mit_best_row is None else mit_best_row["threshold"],
                    "mitigation_mean_fnr": None if mit_best_row is None else mit_best_row["mean_unauthorized_fnr"],
                    "mitigation_mean_fpr": None if mit_best_row is None else mit_best_row["mean_absent_not_authorized_fpr"],
                    "best_baseline_method": None if best_base is None else best_base["method"],
                    "best_baseline_threshold": None if best_base is None else best_base["threshold"],
                    "best_baseline_mean_fnr": None if best_base is None else best_base["mean_unauthorized_fnr"],
                    "best_baseline_mean_fpr": None if best_base is None else best_base["mean_absent_not_authorized_fpr"],
                    "delta_fnr_vs_best_baseline": None
                    if best_base is None or mit_best_row is None or mit_best_row["mean_unauthorized_fnr"] is None
                    else round(best_base["mean_unauthorized_fnr"] - mit_best_row["mean_unauthorized_fnr"], 4),
                }
            )

    return {
        "available": True,
        "baseline_source": str(baseline_path.relative_to(base)),
        "excluded_baseline_methods": ["open_set_abstain"],
        "rows": rows,
    }


def run() -> dict[str, Any]:
    args = parse_args()
    torch.set_num_threads(4)
    thresholds = args.thresholds if args.thresholds else [round(float(v), 4) for v in np.linspace(0.0, 1.0, 21)]

    base = Path(__file__).resolve().parent.parent
    x, y_all, items, effect_names = base_exp.load(base, args.data_name)
    tools = [item["tool_name"] for item in items]
    specs = base_exp.build_split_specs(items, args.evaluations, args.random_seeds)
    all_idx = np.arange(len(items), dtype=int)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x_t = torch.tensor(x, dtype=torch.float32, device=device)

    fixed_rows: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []

    methods = {
        "contrastive_train_only": "strict split-training positive pairs only",
        "contrastive_observed_pair_upper_bound": "all observed positive pairs; upper-bound repair setting",
    }

    for spec_id, spec in enumerate(specs, start=1):
        print(f"[{spec_id}/{len(specs)}] {split_metadata(spec)}", flush=True)
        train_idx = spec["train_idx"]
        test_idx = spec["test_idx"]
        for effect_idx, effect in enumerate(effect_names):
            unauth_test = base_exp.unauthorized_labels(items, effect)[test_idx]
            if int(unauth_test.sum()) < args.min_unauth_test:
                continue
            y_effect = y_all[:, effect_idx]
            pair_sources = {
                "contrastive_train_only": train_idx,
                "contrastive_observed_pair_upper_bound": all_idx,
            }
            for method, pair_idx in pair_sources.items():
                for seed in args.projection_seeds:
                    scores, info = train_projection_scores(
                        x_t=x_t,
                        x_np=x,
                        y=y_effect,
                        tools=tools,
                        train_idx=train_idx,
                        test_idx=test_idx,
                        pair_idx=pair_idx,
                        seed=seed + effect_idx * 1000,
                        dim=args.dim,
                        epochs=args.epochs,
                        lr=args.lr,
                        max_pairs_per_tool_pair=args.max_pairs_per_tool_pair,
                        min_pos_per_tool=args.min_pos_per_tool,
                        min_train_pairs=args.min_train_pairs,
                    )
                    extra = {
                        "projection_seed": seed,
                        "dim": args.dim,
                        "epochs": args.epochs,
                        "lr": args.lr,
                        "pair_source": "train_split" if method == "contrastive_train_only" else "all_observed_rows",
                        "n_positive_pair_tools": info.get("n_positive_pair_tools"),
                        "n_train_pairs": info.get("n_train_pairs"),
                    }
                    if scores is None:
                        skipped_rows.append(
                            {
                                **split_metadata(spec),
                                "effect": effect,
                                "method": method,
                                "projection_seed": seed,
                                **info,
                            }
                        )
                        continue

                    metric = metric_from_scores(
                        items=items,
                        test_idx=test_idx,
                        effect=effect,
                        scores=scores,
                        threshold=0.5,
                    )
                    add_metric_row(
                        fixed_rows,
                        spec=spec,
                        effect=effect,
                        method=method,
                        metric=metric,
                        n_train=len(train_idx),
                        n_test=len(test_idx),
                        extra=extra,
                    )
                    curve_rows.extend(
                        threshold_curve(
                            items=items,
                            test_idx=test_idx,
                            effect=effect,
                            method=method,
                            spec=spec,
                            scores=scores,
                            thresholds=thresholds,
                            extra=extra,
                        )
                    )
            print(f"  {effect}: fixed rows {len(fixed_rows)}, skipped {len(skipped_rows)}", flush=True)

    payload = {
        "schema_version": "auth_mitigation_vs_baseline_v1",
        "generated_by": "experiment_auth_mitigation_comparison.py",
        "data_name": args.data_name,
        "n_samples": len(items),
        "effect_names": effect_names,
        "evaluations": args.evaluations,
        "projection_methods": methods,
        "projection_seeds": args.projection_seeds,
        "dim": args.dim,
        "epochs": args.epochs,
        "lr": args.lr,
        "thresholds": thresholds,
        "target_fpr": args.target_fpr,
        "fixed_threshold_rows": fixed_rows,
        "fixed_threshold_aggregate": aggregate_fixed(fixed_rows),
        "threshold_curve_rows": curve_rows,
        "threshold_curve_aggregate": aggregate_curves(curve_rows),
        "best_tradeoffs": best_tradeoffs(curve_rows, args.target_fpr),
        "skipped_rows": skipped_rows,
        "skip_summary": dict(sorted(Counter(row.get("reason", "unknown") for row in skipped_rows).items())),
        "same_cell_baseline_comparison": same_cell_baseline_comparison(
            base=base,
            data_name=args.data_name,
            mitigation_curve_rows=curve_rows,
            target_fpr=args.target_fpr,
        ),
        "caveats": [
            "`contrastive_train_only` is the strict split-matched setting and can be non-evaluable when the held-out split leaves fewer than two positive training tools.",
            "`contrastive_observed_pair_upper_bound` uses observed held-out-tool positive pairs for projection training; it is an upper bound on repair with coverage, not a zero-shot mitigation result.",
            "All classifiers train on realized effect labels; authorization enters through unauthorized-effect positives and absent-not-authorized negatives at evaluation time.",
            "Same-cell baseline comparisons exclude `open_set_abstain` because the T47 audit showed reject-all degeneracy can produce FNR=0 with unusable FPR.",
        ],
    }
    return payload


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Auth-SafeInv Mitigation vs Baseline",
        "",
        f"- Data: `{payload['data_name']}`",
        f"- Samples: {payload['n_samples']}",
        f"- Projection seeds: {payload['projection_seeds']}",
        f"- Projection dim / epochs: {payload['dim']} / {payload['epochs']}",
        f"- Target FPR: {payload['target_fpr']}",
        "",
        "## Fixed Threshold Aggregate",
        "",
        "| Split | Method | Rows | Cells | Mean FNR | Std FNR | Max FNR | Mean FPR |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["fixed_threshold_aggregate"]:
        lines.append(
            f"| `{row['split_type']}` | `{row['method']}` | {row['rows']} | {row['unique_cells']} | "
            f"{row['mean_unauthorized_fnr']} | {row['std_unauthorized_fnr']} | "
            f"{row['max_unauthorized_fnr']} | {row['mean_absent_not_authorized_fpr']} |"
        )

    lines.extend(
        [
            "",
            "## Best Mitigation Tradeoffs",
            "",
            "| Split | Method | Threshold | Rows | Cells | Mean FNR | Mean FPR |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in payload["best_tradeoffs"]:
        lines.append(
            f"| `{row['split_type']}` | `{row['method']}` | {row['threshold']} | {row['rows']} | "
            f"{row['unique_cells']} | {row['mean_unauthorized_fnr']} | {row['mean_absent_not_authorized_fpr']} |"
        )

    comparison = payload["same_cell_baseline_comparison"]
    lines.extend(["", "## Same-Cell Comparison vs T47 Baselines", ""])
    if not comparison.get("available"):
        lines.append(f"- Baseline comparison unavailable: {comparison.get('reason')}")
    else:
        lines.extend(
            [
                f"- Baseline source: `{comparison['baseline_source']}`",
                "- `open_set_abstain` is excluded from best-baseline selection.",
                "",
                "| Split | Mitigation | Cells | Coverage | Mit FNR | Mit FPR | Best baseline | Base FNR | Base FPR | Delta FNR |",
                "|---|---|---:|---:|---:|---:|---|---:|---:|---:|",
            ]
        )
        for row in comparison["rows"]:
            lines.append(
                f"| `{row['split_type']}` | `{row['mitigation_method']}` | {row['mitigation_cells']} | "
                f"{row['cell_coverage']} | {row['mitigation_mean_fnr']} | {row['mitigation_mean_fpr']} | "
                f"`{row['best_baseline_method']}` | {row['best_baseline_mean_fnr']} | "
                f"{row['best_baseline_mean_fpr']} | {row['delta_fnr_vs_best_baseline']} |"
            )

    lines.extend(["", "## Training-Signal Skips", ""])
    if payload["skip_summary"]:
        for reason, count in payload["skip_summary"].items():
            lines.append(f"- `{reason}`: {count}")
    else:
        lines.append("- No skipped projection runs.")

    lines.extend(["", "## Caveats", ""])
    for caveat in payload["caveats"]:
        lines.append(f"- {caveat}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = run()
    base = Path(__file__).resolve().parent.parent
    out_json = base / "analysis" / f"auth_mitigation_vs_baseline_{payload['data_name']}.json"
    out_md = base / "analysis" / f"auth_mitigation_vs_baseline_{payload['data_name']}.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Saved JSON: {out_json}")
    print(f"Saved MD:   {out_md}")
    print(f"Fixed rows: {len(payload['fixed_threshold_rows'])}")
    print(f"Curve rows: {len(payload['threshold_curve_rows'])}")
    print(f"Skipped rows: {len(payload['skipped_rows'])}")


if __name__ == "__main__":
    main()
