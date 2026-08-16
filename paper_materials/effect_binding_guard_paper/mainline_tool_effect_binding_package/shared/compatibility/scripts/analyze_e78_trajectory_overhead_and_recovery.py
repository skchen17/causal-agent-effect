#!/usr/bin/env python3
"""Summarize paired trajectory duration and audited E77 recovery behavior."""

from __future__ import annotations

import importlib.util
import json
import math
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


NO_GUARD = "agentdojo_live_local_no_guard"
OURS = "agentdojo_live_ours_e77_effect_diff_runtime"


def find_root(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if all((candidate / name).exists() for name in ("paper", "experiments", "shared")):
            return candidate
    raise RuntimeError("could not locate the package root")


ROOT = find_root(Path(__file__).resolve())
FROZEN_ROWS = (
    ROOT
    / "experiments/unified-agent-security-baselines/results/strong-model-baseline-comparison/"
    "qwen32-frozen-case-rows.jsonl"
)
STRICT_REPORT = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-context-repaired-report.json"
)
LOG_ROOT = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-context-repaired/agentdojo_logs/"
    "local-ours_e77_effect_diff_runtime"
)
RESULTS = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "runtime-overhead-measurement"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        rows.append(value)
    return rows


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires nonempty values")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return ordered[index]


def distribution(values: list[float]) -> dict[str, float | int]:
    if not values or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("durations must be finite positive numbers")
    return {
        "n": len(values),
        "mean_seconds": statistics.fmean(values),
        "median_seconds": statistics.median(values),
        "p95_seconds": percentile(values, 0.95),
        "min_seconds": min(values),
        "max_seconds": max(values),
    }


def load_taxonomy() -> dict[str, Any]:
    script = ROOT / "scripts/analyze_e77_failure_taxonomy.py"
    spec = importlib.util.spec_from_file_location("e77_failure_taxonomy_current", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build(LOG_ROOT, strict_report_path=STRICT_REPORT)


def build(
    frozen_rows_path: Path = FROZEN_ROWS,
    strict_report_path: Path = STRICT_REPORT,
) -> dict[str, Any]:
    rows = read_jsonl(frozen_rows_path)
    selected = [row for row in rows if row.get("method_id") in {NO_GUARD, OURS}]
    by_method = {
        method: {str(row["unified_case_id"]): row for row in selected if row.get("method_id") == method}
        for method in (NO_GUARD, OURS)
    }
    for method, method_rows in by_method.items():
        if len(method_rows) != 726:
            raise ValueError(f"{method}: expected 726 unique rows, observed {len(method_rows)}")
    if set(by_method[NO_GUARD]) != set(by_method[OURS]):
        raise ValueError("no-guard and E77 case keys differ")

    strict = json.loads(strict_report_path.read_text(encoding="utf-8"))
    if strict.get("status") != "passed" or (strict.get("metrics") or {}).get("n_total") != 726:
        raise ValueError("E77 strict finalizer is not a passed 726-row result")
    repair = strict.get("repair_metadata") or {}
    if repair.get("original_official_rows_retained") != 714 or repair.get("repaired_official_rows") != 12:
        raise ValueError("E77 714+12 repair boundary is missing")

    strata: dict[str, Any] = {}
    for mode in ("all", "benign", "attack"):
        keys = sorted(
            key
            for key, row in by_method[NO_GUARD].items()
            if mode == "all" or row.get("mode") == mode
        )
        no_guard = [float(by_method[NO_GUARD][key]["duration"]) for key in keys]
        ours = [float(by_method[OURS][key]["duration"]) for key in keys]
        deltas = [right - left for left, right in zip(no_guard, ours, strict=True)]
        ratios = [right / left for left, right in zip(no_guard, ours, strict=True)]
        strata[mode] = {
            "no_guard": distribution(no_guard),
            "ours": distribution(ours),
            "paired": {
                "n": len(keys),
                "mean_delta_seconds": statistics.fmean(deltas),
                "median_delta_seconds": statistics.median(deltas),
                "median_ratio": statistics.median(ratios),
                "ours_faster_cases": sum(delta < 0 for delta in deltas),
                "equal_duration_cases": sum(delta == 0 for delta in deltas),
                "ours_slower_cases": sum(delta > 0 for delta in deltas),
            },
        }

    runtime = strict.get("runtime_audit") or {}
    initial = Counter(runtime.get("initial_decision_counts") or {})
    final = Counter(runtime.get("decision_counts") or {})
    states = Counter(runtime.get("recovery_state_counts") or {})
    if sum(initial.values()) != runtime.get("precommit_checks") or sum(states.values()) != runtime.get("precommit_checks"):
        raise ValueError("runtime recovery counts do not reconcile with precommit checks")
    if final["ALLOW"] - initial["ALLOW"] != states["PLAN_REVISED"]:
        raise ValueError("recovered allow count does not reconcile with PLAN_REVISED")

    taxonomy = load_taxonomy()
    report = {
        "experiment": "E78 post-hoc paired trajectory duration and E77 recovery analysis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed_with_observational_timing_caveat",
        "protocol": {
            "paired_case_keys": 726,
            "model": "Qwen3-32B-Q4_K_M",
            "benchmark": "AgentDojo v1.1.2",
            "duration_field": "native AgentDojo per-trajectory wall-clock duration",
            "e77_context_boundary": {
                "original_rows": repair["original_official_rows_retained"],
                "repaired_rows": repair["repaired_official_rows"],
                "uniform_context_window": repair.get("uniform_context_window"),
            },
        },
        "duration": strata,
        "recovery": {
            "precommit_checks": runtime.get("precommit_checks"),
            "initial_decisions": dict(initial),
            "final_decisions": dict(final),
            "recovery_states": dict(states),
            "revision_llm_calls": runtime.get("revision_llm_calls"),
            "plan_revisions": runtime.get("plan_revisions"),
            "checks_transitioned_to_allow": states["PLAN_REVISED"],
            "trajectory_feedback_association": taxonomy["feedback_association"],
            "benign": taxonomy["modes"]["benign"],
            "attack": taxonomy["modes"]["attack"],
        },
        "verification": {
            "same_726_case_keys": True,
            "strict_e77_report_passed": True,
            "failure_taxonomy_reconciles": taxonomy["strict_finalizer_reconciliation"]["passed"],
            "positive_finite_duration": True,
        },
        "claim_boundary": (
            "Duration is a post-hoc paired observation from historical sequential runs. It includes model inference, "
            "sandbox work, and any recovery calls, but server load and execution order were not randomized. Twelve "
            "E77 rows also use disclosed larger-context repairs. The duration difference therefore describes observed "
            "trajectory cost and must not be interpreted as the causal latency added by the guard. Recovery counts "
            "are mechanistic audit totals; feedback/utility rates are associations, not causal effects."
        ),
    }
    return report


def write(report: dict[str, Any]) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "observed-trajectory-overhead-and-recovery.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    all_rows = report["duration"]["all"]
    recovery = report["recovery"]
    feedback = recovery["trajectory_feedback_association"]
    lines = [
        "# Observed Trajectory Cost and Recovery",
        "",
        f"- Status: `{report['status']}`",
        f"- Paired official keys: `{report['protocol']['paired_case_keys']}`",
        (
            f"- No guard duration: median `{all_rows['no_guard']['median_seconds']:.2f}s`, "
            f"p95 `{all_rows['no_guard']['p95_seconds']:.2f}s`."
        ),
        (
            f"- E77 duration: median `{all_rows['ours']['median_seconds']:.2f}s`, "
            f"p95 `{all_rows['ours']['p95_seconds']:.2f}s`."
        ),
        (
            f"- Paired median ratio: `{all_rows['paired']['median_ratio']:.3f}`; "
            f"paired median delta: `{all_rows['paired']['median_delta_seconds']:.2f}s`."
        ),
        f"- Pre-commit checks: `{recovery['precommit_checks']}`.",
        f"- Revision-model calls: `{recovery['revision_llm_calls']}`.",
        f"- Checks transitioned from replan to allow: `{recovery['checks_transitioned_to_allow']}`.",
        (
            f"- Trajectories with feedback: `{feedback['cases_with_feedback']}/726`; utility "
            f"`{feedback['utility_successes_with_feedback']}/{feedback['cases_with_feedback']}`."
        ),
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
    ]
    (RESULTS / "observed-trajectory-overhead-and-recovery.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> int:
    report = build()
    write(report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "paired_case_keys": report["protocol"]["paired_case_keys"],
                "median_ratio": report["duration"]["all"]["paired"]["median_ratio"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
