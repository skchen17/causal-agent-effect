#!/usr/bin/env python3
"""Finalize four interleaved DeepSeek benign repetitions."""

from __future__ import annotations

import csv
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "paper").is_dir())
RUNS = ROOT / "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard"
OUT = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard"
STATUS = OUT / "deepseek_benign_interleaved_run_status.json"
CONDITIONS = ("no_guard", "spotlighting", "c1f")
REPS = tuple(f"matched-r{index}" for index in range(1, 5))
PIPELINE = {
    "no_guard": "local",
    "spotlighting": "local-spotlighting_with_delimiting",
    "c1f": "local-ours_e77_effect_diff_runtime",
}
SUITE_N = {"banking": 16, "slack": 21, "travel": 20, "workspace": 40}
MARGIN = -0.05


def read_logs(condition: str, rep: str) -> dict[str, dict[str, Any]]:
    root = RUNS / f"deepseek-confirmation-{condition}-benign-{rep}"
    rows: dict[str, dict[str, Any]] = {}
    for suite, expected in SUITE_N.items():
        paths = sorted((root / suite / "agentdojo_logs" / PIPELINE[condition] / suite).glob("user_task_*/none/none.json"))
        if len(paths) != expected:
            raise RuntimeError(f"{condition}/{rep}/{suite}: expected {expected}, observed {len(paths)}")
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            key = f'{suite}:{payload["user_task_id"]}'
            if key in rows:
                raise RuntimeError(f"duplicate benign key: {condition}/{rep}/{key}")
            if payload.get("error") is not None or not isinstance(payload.get("utility"), bool):
                raise RuntimeError(f"non-evaluable benign row: {condition}/{rep}/{key}")
            rows[key] = payload
    if len(rows) != 97:
        raise RuntimeError(f"{condition}/{rep}: expected 97 keys, observed {len(rows)}")
    return rows


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = int(probability * (len(ordered) - 1))
    return ordered[index]


def bootstrap_difference(
    no_guard: dict[str, list[int]], c1f: dict[str, list[int]], iterations: int = 20000
) -> dict[str, Any]:
    keys = sorted(no_guard)
    per_task = {key: sum(c1f[key]) / 4 - sum(no_guard[key]) / 4 for key in keys}
    observed = sum(per_task.values()) / len(keys)
    rng = random.Random(20260809)
    draws = []
    for _ in range(iterations):
        sample = [keys[rng.randrange(len(keys))] for _ in keys]
        draws.append(sum(per_task[key] for key in sample) / len(sample))
    lower = quantile(draws, 0.05)
    return {
        "unit": "AgentDojo user task with four repeated outcomes per condition",
        "iterations": iterations,
        "difference_c1f_minus_no_guard": observed,
        "one_sided_95_lower_bound": lower,
        "noninferiority_margin": MARGIN,
        "noninferior": lower > MARGIN,
    }


def main() -> int:
    if json.loads(STATUS.read_text(encoding="utf-8")).get("status") != "passed":
        raise RuntimeError("interleaved runner has not passed")
    all_rows: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    metric_rows = []
    task_outcomes: dict[str, dict[str, list[int]]] = {condition: {} for condition in CONDITIONS}
    for rep in REPS:
        for condition in CONDITIONS:
            logs = read_logs(condition, rep)
            all_rows[(condition, rep)] = logs
            successes = sum(row["utility"] for row in logs.values())
            metric_rows.append(
                {
                    "condition": condition,
                    "rep": rep,
                    "n": 97,
                    "utility_successes": successes,
                    "utility_rate": successes / 97,
                }
            )
            for key, row in logs.items():
                task_outcomes[condition].setdefault(key, []).append(int(row["utility"]))
    if any(len(values) != 4 for condition in task_outcomes.values() for values in condition.values()):
        raise RuntimeError("task repetition accounting is incomplete")

    aggregates = []
    for condition in CONDITIONS:
        rows = [row for row in metric_rows if row["condition"] == condition]
        aggregates.append(
            {
                "condition": condition,
                "runs": 4,
                "task_evaluations": 388,
                "utility_successes": sum(row["utility_successes"] for row in rows),
                "mean_utility_rate": sum(row["utility_rate"] for row in rows) / 4,
                "min_utility_rate": min(row["utility_rate"] for row in rows),
                "max_utility_rate": max(row["utility_rate"] for row in rows),
            }
        )

    churn = []
    for rep in REPS:
        no_guard = all_rows[("no_guard", rep)]
        c1f = all_rows[("c1f", rep)]
        counts = Counter(
            (
                "both" if no_guard[key]["utility"] and c1f[key]["utility"] else
                "no_guard_only" if no_guard[key]["utility"] else
                "c1f_only" if c1f[key]["utility"] else "neither"
            )
            for key in no_guard
        )
        churn.append({"rep": rep, **{key: counts[key] for key in ("both", "no_guard_only", "c1f_only", "neither")}})

    bootstrap = bootstrap_difference(task_outcomes["no_guard"], task_outcomes["c1f"])
    report = {
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "deepseek-v4-flash",
        "benchmark": "AgentDojo v1.1.2 benign tasks",
        "conditions": list(CONDITIONS),
        "interleaved": True,
        "per_run": metric_rows,
        "aggregates": aggregates,
        "paired_task_churn": churn,
        "task_cluster_bootstrap": bootstrap,
        "claim_eligibility": {
            "benign_noninferiority_at_five_percentage_points": bootstrap["noninferior"]
        },
        "claim_boundary": "Repeated same-model benign utility; no security result is inferred from these benign-only runs.",
    }
    (OUT / "deepseek_benign_interleaved_results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (OUT / "deepseek_benign_interleaved_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metric_rows[0]))
        writer.writeheader()
        writer.writerows(metric_rows)
    lines = [
        "# DeepSeek Interleaved Benign Utility",
        "",
        "| Condition | Repetitions | Successes | Mean utility | Range |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in aggregates:
        lines.append(
            f"| {row['condition']} | 4 | {row['utility_successes']}/388 | "
            f"{row['mean_utility_rate']:.3f} | {row['min_utility_rate']:.3f}--{row['max_utility_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            f"Task-clustered C1f minus no-guard difference: {bootstrap['difference_c1f_minus_no_guard']:.3f}; "
            f"one-sided 95% lower bound {bootstrap['one_sided_95_lower_bound']:.3f}; "
            f"noninferior at -0.05: {bootstrap['noninferior']}.",
            "",
        ]
    )
    (OUT / "deepseek_benign_interleaved_results.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "passed", "aggregates": aggregates, "bootstrap": bootstrap}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
