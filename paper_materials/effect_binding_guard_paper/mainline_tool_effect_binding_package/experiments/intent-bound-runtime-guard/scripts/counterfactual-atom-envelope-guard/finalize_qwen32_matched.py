#!/usr/bin/env python3
"""Strictly finalize the 3 x 726 Qwen3-32B matched comparison."""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "paper").is_dir())
RUNS = ROOT / "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard"
OUT = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard"
STATUS = OUT / "qwen32_matched_run_status.json"
PROTOCOL = OUT / "qwen32_matched_protocol.json"
CONDITIONS = ("no_guard", "spotlighting", "c1f")
PIPELINE = {
    "no_guard": "local",
    "spotlighting": "local-spotlighting_with_delimiting",
    "c1f": "local-ours_e77_effect_diff_runtime",
}
SUITE_N = {
    "benign": {"banking": 16, "slack": 21, "travel": 20, "workspace": 40},
    "attack": {"banking": 144, "slack": 105, "travel": 140, "workspace": 240},
}


def exact_mcnemar(reference_only: int, method_only: int) -> float:
    n = reference_only + method_only
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, index) for index in range(min(reference_only, method_only) + 1))
    return min(1.0, 2 * tail / (2**n))


def load(condition: str, mode: str) -> dict[str, dict[str, Any]]:
    rows = {}
    for suite, expected in SUITE_N[mode].items():
        root = RUNS / f"qwen32-matched-{condition}-{mode}-r1" / suite / "agentdojo_logs" / PIPELINE[condition] / suite
        pattern = "user_task_*/none/none.json" if mode == "benign" else "user_task_*/important_instructions/*.json"
        paths = sorted(root.glob(pattern))
        if len(paths) != expected:
            raise RuntimeError(f"{condition}/{mode}/{suite}: expected {expected}, observed {len(paths)}")
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            injection = payload.get("injection_task_id") or "none"
            key = f'{suite}:{payload["user_task_id"]}:{injection}'
            if key in rows:
                raise RuntimeError(f"duplicate Qwen key: {condition}/{mode}/{key}")
            if payload.get("error") is not None or not isinstance(payload.get("utility"), bool):
                raise RuntimeError(f"non-evaluable Qwen row: {condition}/{mode}/{key}")
            if mode == "attack" and not isinstance(payload.get("security"), bool):
                raise RuntimeError(f"missing security metric: {condition}/{key}")
            rows[key] = payload
    if len(rows) != sum(SUITE_N[mode].values()):
        raise RuntimeError(f"wrong Qwen denominator for {condition}/{mode}")
    return rows


def main() -> int:
    if json.loads(STATUS.read_text(encoding="utf-8")).get("status") != "passed":
        raise RuntimeError("Qwen matched runner has not passed")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    all_rows = {(condition, mode): load(condition, mode) for condition in CONDITIONS for mode in ("benign", "attack")}
    metrics = []
    for condition in CONDITIONS:
        benign = all_rows[(condition, "benign")]
        attack = all_rows[(condition, "attack")]
        metrics.append(
            {
                "condition": condition,
                "n_benign": 97,
                "benign_utility_successes": sum(row["utility"] for row in benign.values()),
                "benign_utility_rate": sum(row["utility"] for row in benign.values()) / 97,
                "n_attack": 629,
                "attack_utility_successes": sum(row["utility"] for row in attack.values()),
                "attack_utility_rate": sum(row["utility"] for row in attack.values()) / 629,
                "attack_successes": sum(row["security"] for row in attack.values()),
                "attack_success_rate": sum(row["security"] for row in attack.values()) / 629,
                "errors": 0,
            }
        )
    paired = {}
    reference = {**all_rows[("no_guard", "benign")], **all_rows[("no_guard", "attack")]}
    for condition in ("spotlighting", "c1f"):
        candidate = {**all_rows[(condition, "benign")], **all_rows[(condition, "attack")]}
        if set(candidate) != set(reference):
            raise RuntimeError(f"paired key mismatch for {condition}")
        comparisons = {}
        for metric, keys in (
            ("utility", sorted(reference)),
            ("attack_success", sorted(all_rows[("no_guard", "attack")]))
        ):
            ref_value = lambda key: bool(reference[key]["utility" if metric == "utility" else "security"])
            cand_value = lambda key: bool(candidate[key]["utility" if metric == "utility" else "security"])
            counts = Counter(
                "both" if ref_value(key) and cand_value(key) else
                "reference_only" if ref_value(key) else
                "method_only" if cand_value(key) else "neither"
                for key in keys
            )
            comparisons[metric] = {
                **{name: counts[name] for name in ("both", "reference_only", "method_only", "neither")},
                "exact_mcnemar_two_sided_p": exact_mcnemar(counts["reference_only"], counts["method_only"]),
            }
        paired[condition] = comparisons
    report = {
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": protocol,
        "model": "Qwen3-32B-Q4_K_M",
        "benchmark": "AgentDojo v1.1.2",
        "case_keys_per_condition": 726,
        "metrics": metrics,
        "paired_against_no_guard": paired,
        "claim_boundary": "Same checkpoint, context, benchmark keys, and official validators; no production or unrestricted-adaptive claim.",
    }
    (OUT / "qwen32_matched_results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Qwen3-32B Matched Comparison",
        "",
        "| Condition | BU | Attack utility | Attack success |",
        "|---|---:|---:|---:|",
    ]
    for row in metrics:
        lines.append(
            f"| {row['condition']} | {row['benign_utility_successes']}/97 | "
            f"{row['attack_utility_successes']}/629 | {row['attack_successes']}/629 |"
        )
    lines.append("")
    (OUT / "qwen32_matched_results.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "passed", "metrics": metrics}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
