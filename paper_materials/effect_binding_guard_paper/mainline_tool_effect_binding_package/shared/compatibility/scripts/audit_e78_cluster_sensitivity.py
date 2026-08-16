#!/usr/bin/env python3
"""Cluster-aware sensitivity analysis for the paired E78 headline comparison."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


DEFAULT_INPUT = Path("analysis/results/e78_qwen32_frozen_case_rows.jsonl")
DEFAULT_OUTPUT = Path("analysis/results/e78_qwen32_cluster_sensitivity.json")
NO_GUARD = "agentdojo_live_local_no_guard"
OURS = "agentdojo_live_ours_e77_effect_diff_runtime"


def percentile_interval(values: list[float]) -> list[float]:
    return [
        float(np.quantile(values, 0.025)),
        float(np.quantile(values, 0.975)),
    ]


def one_way_cluster_bootstrap(
    rows: list[dict[str, object]],
    cluster_key: str,
    metric_key: str,
    iterations: int,
    rng: np.random.Generator,
) -> dict[str, object]:
    strata: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        strata[str(row["suite"])][str(row[cluster_key])].append(
            float(row[metric_key])
        )

    estimates: list[float] = []
    for _ in range(iterations):
        sample: list[float] = []
        for groups in strata.values():
            cluster_ids = list(groups)
            selected = rng.choice(
                len(cluster_ids), size=len(cluster_ids), replace=True
            )
            for index in selected:
                sample.extend(groups[cluster_ids[int(index)]])
        estimates.append(float(np.mean(sample)))

    return {
        "cluster_key": cluster_key,
        "n_clusters": sum(len(groups) for groups in strata.values()),
        "ci_95": percentile_interval(estimates),
        "bootstrap_mass_ge_zero": float(
            np.mean(np.asarray(estimates) >= 0.0)
        ),
    }


def crossed_cluster_bootstrap(
    rows: list[dict[str, object]],
    metric_key: str,
    iterations: int,
    rng: np.random.Generator,
) -> dict[str, object]:
    matrices: list[np.ndarray] = []
    for suite in sorted({str(row["suite"]) for row in rows}):
        suite_rows = [row for row in rows if str(row["suite"]) == suite]
        users = sorted({str(row["user_task_id"]) for row in suite_rows})
        injections = sorted(
            {str(row["injection_task_id"]) for row in suite_rows}
        )
        user_index = {value: index for index, value in enumerate(users)}
        injection_index = {
            value: index for index, value in enumerate(injections)
        }
        matrix = np.full((len(users), len(injections)), np.nan)
        for row in suite_rows:
            matrix[
                user_index[str(row["user_task_id"])],
                injection_index[str(row["injection_task_id"])],
            ] = float(row[metric_key])
        matrices.append(matrix)

    estimates: list[float] = []
    for _ in range(iterations):
        sample: list[float] = []
        for matrix in matrices:
            user_sample = rng.integers(0, matrix.shape[0], matrix.shape[0])
            injection_sample = rng.integers(
                0, matrix.shape[1], matrix.shape[1]
            )
            values = matrix[np.ix_(user_sample, injection_sample)].ravel()
            sample.extend(values[~np.isnan(values)].tolist())
        estimates.append(float(np.mean(sample)))

    return {
        "cluster_keys": ["suite/user_task_id", "suite/injection_task_id"],
        "ci_95": percentile_interval(estimates),
        "bootstrap_mass_ge_zero": float(
            np.mean(np.asarray(estimates) >= 0.0)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--iterations", type=int, default=30_000)
    parser.add_argument("--seed", type=int, default=20_260_726)
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    keyed = {
        (str(row["method_id"]), str(row["unified_case_id"])): row
        for row in rows
    }

    paired: list[dict[str, object]] = []
    for row in rows:
        if row["method_id"] != NO_GUARD or row["mode"] != "attack":
            continue
        case_id = str(row["unified_case_id"])
        guarded = keyed[(OURS, case_id)]
        paired.append(
            {
                "suite": row["suite"],
                "user_task_id": row["user_task_id"],
                "injection_task_id": row["injection_task_id"],
                "asr_delta": int(bool(guarded["attack_success"]))
                - int(bool(row["attack_success"])),
                "attack_utility_delta": int(bool(guarded["utility"]))
                - int(bool(row["utility"])),
            }
        )

    if len(paired) != 629:
        raise RuntimeError(f"Expected 629 paired attack rows, found {len(paired)}")

    rng = np.random.default_rng(args.seed)
    metrics: dict[str, object] = {}
    for metric_key in ("asr_delta", "attack_utility_delta"):
        metric_values = [float(row[metric_key]) for row in paired]
        metrics[metric_key] = {
            "point_estimate": float(np.mean(metric_values)),
            "user_task_cluster": one_way_cluster_bootstrap(
                paired,
                "user_task_id",
                metric_key,
                args.iterations,
                rng,
            ),
            "injection_task_cluster": one_way_cluster_bootstrap(
                paired,
                "injection_task_id",
                metric_key,
                args.iterations,
                rng,
            ),
            "crossed_user_injection_cluster": crossed_cluster_bootstrap(
                paired, metric_key, args.iterations, rng
            ),
        }

    suite_breakdown: dict[str, object] = {}
    for suite in sorted({str(row["suite"]) for row in paired}):
        suite_rows = [row for row in paired if row["suite"] == suite]
        suite_breakdown[suite] = {
            "n_pairs": len(suite_rows),
            "n_user_tasks": len(
                {str(row["user_task_id"]) for row in suite_rows}
            ),
            "n_injection_tasks": len(
                {str(row["injection_task_id"]) for row in suite_rows}
            ),
            "asr_delta": float(
                np.mean([float(row["asr_delta"]) for row in suite_rows])
            ),
            "attack_utility_delta": float(
                np.mean(
                    [
                        float(row["attack_utility_delta"])
                        for row in suite_rows
                    ]
                )
            ),
        }

    result = {
        "status": "passed",
        "experiment": "E78 cluster-aware sensitivity audit",
        "source": str(args.input),
        "methods": {"reference": NO_GUARD, "guarded": OURS},
        "n_attack_pairs": len(paired),
        "iterations": args.iterations,
        "seed": args.seed,
        "asr_discordance": {
            "no_guard_only_success": sum(
                row["asr_delta"] == -1 for row in paired
            ),
            "guarded_only_success": sum(
                row["asr_delta"] == 1 for row in paired
            ),
        },
        "metrics": metrics,
        "suite_breakdown": suite_breakdown,
        "claim_boundary": (
            "Sensitivity analysis for dependence among AgentDojo task-injection "
            "pairs. It does not correct the disclosed non-uniform context "
            "capacities or establish cross-model generalization."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
