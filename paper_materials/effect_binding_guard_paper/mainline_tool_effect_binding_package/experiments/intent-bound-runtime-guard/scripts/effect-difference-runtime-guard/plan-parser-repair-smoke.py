#!/usr/bin/env python3
"""Replay previously invalid E77 task plans without executing any tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from agentdojo.task_suite.load_suites import get_suite

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import (
    build_tool_descriptor,
)
from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.agentdojo_e77_runtime_patch import (
    _model_plan,
)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--port", default="18084")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    invalid_hashes = {
        str(row.get("query_hash"))
        for row in read_jsonl(args.audit)
        if row.get("event") == "task_plan" and row.get("parse_valid") is not True
    }
    candidates: list[tuple[str, str, str, str, dict[str, dict[str, object]]]] = []
    for suite_name in ("workspace", "slack", "travel", "banking"):
        suite = get_suite("v1.1.2", suite_name)
        registry = {tool.name: build_tool_descriptor(tool) for tool in suite.tools}
        for task_id, task in suite.user_tasks.items():
            prompt = str(getattr(task, "PROMPT", ""))
            query_hash = hashlib.sha256(prompt.encode()).hexdigest()
            if query_hash in invalid_hashes:
                candidates.append((query_hash, suite_name, str(task_id), prompt, registry))

    candidates.sort(key=lambda row: row[0])
    os.environ["E77_PLANNER_PORT"] = str(args.port)
    os.environ["E77_PLAN_CACHE"] = str(args.cache)
    os.environ["E77_PLANNER_REPAIR_ATTEMPTS"] = "1"
    os.environ["E77_PLANNER_MAX_TOKENS"] = "4096"
    rows = []
    for query_hash, suite_name, task_id, prompt, registry in candidates[: args.limit]:
        plan, diagnostic = _model_plan(prompt, registry)
        rows.append(
            {
                "query_hash": query_hash,
                "suite": suite_name,
                "task_id": task_id,
                "schema_parse_valid": bool(diagnostic.get("schema_parse_valid", diagnostic.get("parse_valid"))),
                "validation_passed": bool(diagnostic.get("validation_passed", plan is not None)),
                "plan_accepted": plan is not None,
                "diagnostic": diagnostic,
                "planned_tools": sorted(plan.get("tools", {})) if plan else [],
            }
        )

    backend_errors = sum("error" in row["diagnostic"] for row in rows)
    report = {
        "status": "passed" if len(rows) == min(args.limit, len(candidates)) and backend_errors == 0 else "failed",
        "scope": "planner_only_no_tool_execution",
        "model_port": str(args.port),
        "previously_invalid_unique_tasks": len(candidates),
        "evaluated": len(rows),
        "schema_parse_valid": sum(bool(row["schema_parse_valid"]) for row in rows),
        "validation_passed": sum(bool(row["validation_passed"]) for row in rows),
        "plan_accepted": sum(bool(row["plan_accepted"]) for row in rows),
        "backend_errors": backend_errors,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: report[key] for key in ("status", "evaluated", "schema_parse_valid", "validation_passed", "plan_accepted")},
            indent=2,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
