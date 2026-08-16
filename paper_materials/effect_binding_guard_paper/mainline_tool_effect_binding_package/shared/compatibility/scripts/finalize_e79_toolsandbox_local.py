#!/usr/bin/env python3
"""Strictly finalize paired 30-scenario local ToolSandbox rows."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "runs/e79_toolsandbox_local"
MANIFEST = ROOT / "evaluation/e79_long_horizon/toolsandbox_feasibility_manifest.json"
RESULTS = ROOT / "analysis/results"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_rows(method: str, expected: set[str]) -> list[dict[str, Any]]:
    directory = RUN_ROOT / method / "rows"
    rows = []
    for name in sorted(expected):
        path = directory / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"missing {method} row: {name}")
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    observed = {path.stem for path in directory.glob("*.json")}
    if observed != expected:
        raise RuntimeError(f"{method} scenario keys differ: missing={sorted(expected-observed)} extra={sorted(observed-expected)}")
    return rows


def aggregate(method: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    usage = read_jsonl(RUN_ROOT / method / "usage.jsonl")
    return {
        "method": method,
        "n": len(rows),
        "completed_rows": sum(row["status"] == "passed" for row in rows),
        "error_rows": sum(row["status"] != "passed" for row in rows),
        "mean_similarity": sum(row["similarity"] for row in rows) / len(rows),
        "mean_milestone_similarity": sum(row["milestone_similarity"] for row in rows) / len(rows),
        "mean_minefield_similarity": sum(row["minefield_similarity"] for row in rows) / len(rows),
        "mean_turn_count": sum(row["turn_count"] for row in rows) / len(rows),
        "total_duration_seconds": sum(row["duration_seconds"] for row in rows),
        "model_calls": len(usage),
        "prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in usage),
        "completion_tokens": sum(row.get("completion_tokens") or 0 for row in usage),
        "precommit_checks": sum(row.get("precommit_checks") or 0 for row in rows) if method == "effect_guard" else None,
        "effectful_executions": sum(row.get("effectful_executions") or 0 for row in rows) if method == "effect_guard" else None,
    }


def audit_guard(expected: set[str]) -> dict[str, Any]:
    allowed = Counter()
    executed = Counter()
    plans = 0
    parse_failures = 0
    for name in sorted(expected):
        path = RUN_ROOT / "effect_guard" / "guard_audit" / f"{name}.jsonl"
        for event in read_jsonl(path):
            if event.get("event") == "permission_plan":
                plans += 1
                parse_failures += event.get("parse_valid") is not True
            elif event.get("event") == "precommit_check" and event.get("decision") == "ALLOW":
                allowed[event["call_signature"]] += 1
            elif event.get("event") == "effect_executed":
                executed[event["call_signature"]] += 1
    missing_precommit = executed - allowed
    return {
        "permission_plan_events": plans,
        "permission_plan_parse_failures": parse_failures,
        "allowed_precommit_occurrences": sum(allowed.values()),
        "effect_execution_occurrences": sum(executed.values()),
        "executions_without_allowed_precommit": sum(missing_precommit.values()),
        "every_effect_execution_precommitted": not missing_precommit,
    }


def build() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {row["scenario_name"] for row in manifest["scenarios"]}
    if len(expected) != 30:
        raise RuntimeError("frozen ToolSandbox key set is not 30")
    methods = {}
    for method in ("no_guard", "effect_guard"):
        methods[method] = aggregate(method, load_rows(method, expected))
    mediation = audit_guard(expected)
    status = "passed" if mediation["every_effect_execution_precommitted"] else "failed"
    return {
        "experiment": "E79 ToolSandbox local paired comparison",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "selection_hash": manifest["selection_hash"],
        "n_scenarios": len(expected),
        "methods": methods,
        "guard_mediation_audit": mediation,
        "claim_boundary": (
            "These 30 native ToolSandbox scenarios measure local stateful utility and mediation under a candidate LLM envelope. "
            "They contain no injected attack layer and do not establish independent authority soundness or 20-plus-call confinement."
        ),
    }


def main() -> int:
    report = build()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e79_toolsandbox_local_comparison_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E79 ToolSandbox Local Paired Comparison", "", f"Status: `{report['status']}`.", "",
        "| Method | N | Similarity | Milestone | Minefield | Errors | Model calls |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for method, row in report["methods"].items():
        lines.append(
            f"| {method} | {row['n']} | {row['mean_similarity']:.3f} | {row['mean_milestone_similarity']:.3f} | "
            f"{row['mean_minefield_similarity']:.3f} | {row['error_rows']} | {row['model_calls']} |"
        )
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    (RESULTS / "e79_toolsandbox_local_comparison_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
