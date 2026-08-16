#!/usr/bin/env python3
"""Compute paired binary statistics for frozen USENIX evaluation rows."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any


def read_rows(path: Path, key_field: str, metric: str) -> dict[str, bool]:
    rows: dict[str, bool] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        key = row.get(key_field)
        value = row.get(metric)
        if not isinstance(key, str) or not isinstance(value, bool):
            raise ValueError(f"{path}:{line_number}: missing string {key_field} or bool {metric}")
        if key in rows:
            raise ValueError(f"{path}:{line_number}: duplicate case key {key}")
        rows[key] = value
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def wilson(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("Wilson interval requires n > 0")
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def exact_mcnemar(a: list[bool], b: list[bool]) -> dict[str, Any]:
    b_only = sum((not left) and right for left, right in zip(a, b, strict=True))
    a_only = sum(left and (not right) for left, right in zip(a, b, strict=True))
    discordant = a_only + b_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, k) for k in range(0, min(a_only, b_only) + 1)) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {"a_only_success": a_only, "b_only_success": b_only, "discordant": discordant, "p_value": p_value}


def paired_bootstrap_difference(
    a: list[bool],
    b: list[bool],
    *,
    samples: int = 10000,
    seed: int = 20260712,
) -> dict[str, float]:
    if len(a) != len(b) or not a:
        raise ValueError("paired bootstrap requires equal nonempty vectors")
    rng = random.Random(seed)
    n = len(a)
    differences = []
    for _ in range(samples):
        indices = [rng.randrange(n) for _ in range(n)]
        differences.append(sum(int(b[i]) - int(a[i]) for i in indices) / n)
    differences.sort()
    low = differences[max(0, math.floor(0.025 * samples))]
    high = differences[min(samples - 1, math.ceil(0.975 * samples) - 1)]
    return {
        "difference_b_minus_a": sum(int(y) - int(x) for x, y in zip(a, b, strict=True)) / n,
        "ci95_low": low,
        "ci95_high": high,
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


def compare(
    a_rows: dict[str, bool],
    b_rows: dict[str, bool],
    *,
    bootstrap_samples: int = 10000,
    seed: int = 20260712,
) -> dict[str, Any]:
    if set(a_rows) != set(b_rows):
        missing_a = sorted(set(b_rows) - set(a_rows))
        missing_b = sorted(set(a_rows) - set(b_rows))
        raise ValueError(f"paired key mismatch: missing_a={missing_a[:10]}, missing_b={missing_b[:10]}")
    keys = sorted(a_rows)
    a = [a_rows[key] for key in keys]
    b = [b_rows[key] for key in keys]
    a_success = sum(a)
    b_success = sum(b)
    return {
        "n_paired": len(keys),
        "a": {"successes": a_success, "rate": a_success / len(keys), "wilson95": wilson(a_success, len(keys))},
        "b": {"successes": b_success, "rate": b_success / len(keys), "wilson95": wilson(b_success, len(keys))},
        "paired_bootstrap": paired_bootstrap_difference(a, b, samples=bootstrap_samples, seed=seed),
        "exact_mcnemar": exact_mcnemar(a, b),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", type=Path, required=True)
    parser.add_argument("--b", type=Path, required=True)
    parser.add_argument("--metric", required=True)
    parser.add_argument("--key-field", default="case_id")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260712)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = compare(
        read_rows(args.a, args.key_field, args.metric),
        read_rows(args.b, args.key_field, args.metric),
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    report.update({
        "metric": args.metric,
        "key_field": args.key_field,
        "method_a_source": str(args.a),
        "method_b_source": str(args.b),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
