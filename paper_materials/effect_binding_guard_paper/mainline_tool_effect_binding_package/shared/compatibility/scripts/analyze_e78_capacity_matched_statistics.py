#!/usr/bin/env python3
"""Analyze paired E78 capacity-matched rows with explicit missingness."""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


DEFAULT_INPUT = Path("analysis/results/e78_capacity_matched_merged_rows.jsonl")
DEFAULT_OUTPUT = Path("analysis/results/e78_capacity_matched_statistics.json")
NO_GUARD = "agentdojo_live_local_no_guard"
OURS = "agentdojo_live_ours_e77_effect_diff_runtime"
METHODS = (
    "agentdojo_live_melon_local",
    "agentdojo_live_prompt_sandwiching",
    "agentdojo_live_promptarmor_local",
    "agentdojo_live_spotlighting_with_delimiting",
    OURS,
)
METRICS = {
    "attack_success": ("attack", "attack_success"),
    "attack_utility": ("attack", "utility"),
    "benign_utility": ("benign", "utility"),
}


def case_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["suite"]),
        str(row["mode"]),
        str(row["user_task_id"]),
        str(row.get("injection_task_id") or "none"),
    )


def exact_mcnemar(left: list[bool], right: list[bool]) -> dict[str, Any]:
    left_only = sum(a and not b for a, b in zip(left, right, strict=True))
    right_only = sum(not a and b for a, b in zip(left, right, strict=True))
    discordant = left_only + right_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant, k)
            for k in range(min(left_only, right_only) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {
        "no_guard_only_success": left_only,
        "method_only_success": right_only,
        "discordant": discordant,
        "p_value": p_value,
    }


def paired_bootstrap(
    left: list[bool],
    right: list[bool],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    n = len(left)
    estimates = []
    for _ in range(samples):
        indices = [rng.randrange(n) for _ in range(n)]
        estimates.append(
            sum(int(right[index]) - int(left[index]) for index in indices) / n
        )
    estimates.sort()
    return {
        "difference_method_minus_no_guard": sum(
            int(b) - int(a) for a, b in zip(left, right, strict=True)
        )
        / n,
        "ci95": [
            estimates[max(0, math.floor(0.025 * samples))],
            estimates[min(samples - 1, math.ceil(0.975 * samples) - 1)],
        ],
        "samples": samples,
        "seed": seed,
    }


def holm(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for index, (name, value) in enumerate(ordered):
        running = max(running, min(1.0, (total - index) * value))
        adjusted[name] = running
    return adjusted


def evaluable_pairs(
    index: dict[str, dict[tuple[str, str, str, str], dict[str, Any]]],
    method_id: str,
    metric_name: str,
) -> tuple[list[dict[str, Any]], list[bool], list[bool]]:
    mode, field = METRICS[metric_name]
    paired_rows = []
    left = []
    right = []
    for key in sorted(set(index[NO_GUARD]) & set(index[method_id])):
        if key[1] != mode:
            continue
        no_guard = index[NO_GUARD][key]
        method = index[method_id][key]
        left_value = no_guard.get(field)
        right_value = method.get(field)
        if (
            no_guard.get("error")
            or method.get("error")
            or not isinstance(left_value, bool)
            or not isinstance(right_value, bool)
        ):
            continue
        paired_rows.append(
            {
                "suite": key[0],
                "mode": key[1],
                "user_task_id": key[2],
                "injection_task_id": key[3],
                "delta": int(right_value) - int(left_value),
            }
        )
        left.append(left_value)
        right.append(right_value)
    if not paired_rows:
        raise ValueError(f"no evaluable pairs for {method_id}/{metric_name}")
    return paired_rows, left, right


def cluster_bootstrap(
    rows: list[dict[str, Any]],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    by_suite_user: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        by_suite_user[row["suite"]][row["user_task_id"]].append(row["delta"])

    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(samples):
        values = []
        for groups in by_suite_user.values():
            identifiers = list(groups)
            selected = rng.integers(0, len(identifiers), len(identifiers))
            for index in selected:
                values.extend(groups[identifiers[int(index)]])
        estimates.append(float(np.mean(values)))
    return {
        "cluster": "suite/user_task_id",
        "n_clusters": sum(len(groups) for groups in by_suite_user.values()),
        "difference_method_minus_no_guard": float(
            np.mean([row["delta"] for row in rows])
        ),
        "ci95": [
            float(np.quantile(estimates, 0.025)),
            float(np.quantile(estimates, 0.975)),
        ],
        "bootstrap_mass_ge_zero": float(
            np.mean(np.asarray(estimates) >= 0.0)
        ),
        "samples": samples,
        "seed": seed,
    }


def analyze(
    rows: list[dict[str, Any]],
    *,
    bootstrap_samples: int,
    cluster_samples: int,
    seed: int,
) -> dict[str, Any]:
    index: dict[
        str, dict[tuple[str, str, str, str], dict[str, Any]]
    ] = defaultdict(dict)
    for row in rows:
        method_id = str(row["method_id"])
        key = case_key(row)
        if key in index[method_id]:
            raise ValueError(f"duplicate row: {method_id}/{key}")
        index[method_id][key] = row

    comparisons: dict[str, Any] = {}
    raw_p = {}
    ours_attack_rows = None
    for method_index, method_id in enumerate(METHODS):
        comparisons[method_id] = {}
        for metric_index, metric_name in enumerate(METRICS):
            paired_rows, left, right = evaluable_pairs(
                index, method_id, metric_name
            )
            mcnemar = exact_mcnemar(left, right)
            comparison_key = f"{method_id}:{metric_name}"
            raw_p[comparison_key] = mcnemar["p_value"]
            comparisons[method_id][metric_name] = {
                "n_paired": len(left),
                "no_guard_successes": sum(left),
                "method_successes": sum(right),
                "no_guard_rate": sum(left) / len(left),
                "method_rate": sum(right) / len(right),
                "paired_bootstrap": paired_bootstrap(
                    left,
                    right,
                    samples=bootstrap_samples,
                    seed=seed + method_index * 10 + metric_index,
                ),
                "exact_mcnemar": mcnemar,
            }
            if method_id == OURS and metric_name == "attack_success":
                ours_attack_rows = paired_rows

    adjusted = holm(raw_p)
    for method_id in METHODS:
        for metric_name in METRICS:
            comparisons[method_id][metric_name]["holm_adjusted_p"] = adjusted[
                f"{method_id}:{metric_name}"
            ]
    if ours_attack_rows is None:
        raise AssertionError("missing guarded attack pairs")

    return {
        "status": "passed",
        "experiment": "E78 capacity-matched paired statistics",
        "source": str(DEFAULT_INPUT),
        "reference_method": NO_GUARD,
        "comparisons": comparisons,
        "ours_attack_user_cluster": cluster_bootstrap(
            ours_attack_rows,
            samples=cluster_samples,
            seed=seed + 1000,
        ),
        "multiple_testing": (
            "Holm correction over five method comparisons and three metrics"
        ),
        "claim_boundary": (
            "Pairwise estimates use only keys with complete native metrics for "
            "both methods. The companion E78 report retains all-key uncertainty "
            "bounds for non-evaluable trajectories. Cluster resampling is a "
            "dependence sensitivity analysis, not cross-model evidence."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bootstrap-samples", type=int, default=30_000)
    parser.add_argument("--cluster-samples", type=int, default=30_000)
    parser.add_argument("--seed", type=int, default=20_260_730)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = analyze(
        rows,
        bootstrap_samples=args.bootstrap_samples,
        cluster_samples=args.cluster_samples,
        seed=args.seed,
    )
    report["source"] = str(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
