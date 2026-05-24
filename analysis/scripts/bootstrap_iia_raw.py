#!/usr/bin/env python3
"""Bootstrap pIIA raw intervention outcomes by source examples.

The raw pIIA JSONL contains one row per intervention. This script estimates
source-cluster bootstrap intervals by resampling source examples within each
effect and recomputing direction-balanced pIIA-within, pIIA-cross, and drop.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
DEFAULT_RAW = ANALYSIS / "iia_true_raw_qwen3-8b_scenarios_merged.jsonl"
DEFAULT_OUT = ANALYSIS / "iia_true_bootstrap_qwen3-8b_scenarios_merged.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def direction_key(row: dict[str, Any]) -> tuple[str, str]:
    return row["direction_tool"], row["evaluation_tool"]


def direction_balanced_mean(rows: list[dict[str, Any]], source_weights: Counter[int] | None = None) -> float:
    by_direction: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_direction[direction_key(row)].append(row)

    rates = []
    for dir_rows in by_direction.values():
        if source_weights is None:
            vals = [float(row["success_score_increase"]) for row in dir_rows]
        else:
            vals = []
            for row in dir_rows:
                weight = source_weights.get(int(row["source_index"]), 0)
                vals.extend([float(row["success_score_increase"])] * weight)
        if vals:
            rates.append(float(np.mean(vals)))
    return float(np.mean(rates)) if rates else float("nan")


def percentile_interval(values: np.ndarray, alpha: float = 0.05) -> list[float]:
    lo, hi = np.quantile(values, [alpha / 2, 1 - alpha / 2])
    return [round(float(lo), 4), round(float(hi), 4)]


def bootstrap_effect(rows: list[dict[str, Any]], n_boot: int, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    source_ids = sorted({int(row["source_index"]) for row in rows})
    within_rows = [row for row in rows if row["mode"] == "within_tool"]
    cross_rows = [row for row in rows if row["mode"] == "cross_tool_direction"]

    within_point = direction_balanced_mean(within_rows)
    cross_point = direction_balanced_mean(cross_rows)
    drop_point = within_point - cross_point

    within_samples = np.zeros(n_boot, dtype=np.float64)
    cross_samples = np.zeros(n_boot, dtype=np.float64)
    drop_samples = np.zeros(n_boot, dtype=np.float64)
    for b in range(n_boot):
        sampled = rng.choice(source_ids, size=len(source_ids), replace=True)
        weights = Counter(int(x) for x in sampled)
        within = direction_balanced_mean(within_rows, weights)
        cross = direction_balanced_mean(cross_rows, weights)
        within_samples[b] = within
        cross_samples[b] = cross
        drop_samples[b] = within - cross

    return {
        "n_raw_outcomes": len(rows),
        "n_source_examples": len(source_ids),
        "n_direction_pairs": len({direction_key(row) for row in cross_rows}),
        "iia_within": round(float(within_point), 4),
        "iia_cross": round(float(cross_point), 4),
        "piia_drop": round(float(drop_point), 4),
        "iia_within_ci95": percentile_interval(within_samples),
        "iia_cross_ci95": percentile_interval(cross_samples),
        "piia_drop_ci95": percentile_interval(drop_samples),
        "bootstrap": {
            "unit": "source_index",
            "n_boot": n_boot,
            "seed": seed,
            "direction_balanced": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default=str(DEFAULT_RAW))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    raw_path = Path(args.raw)
    out_path = Path(args.out)
    rows = read_jsonl(raw_path)
    by_effect: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_effect[row["effect"]].append(row)

    result = {
        "raw_path": str(raw_path.relative_to(ROOT) if raw_path.is_relative_to(ROOT) else raw_path),
        "n_raw_outcomes": len(rows),
        "effects": {
            effect: bootstrap_effect(effect_rows, args.n_boot, args.seed)
            for effect, effect_rows in sorted(by_effect.items())
        },
    }
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path)


if __name__ == "__main__":
    main()
