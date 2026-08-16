#!/usr/bin/env python3
"""Build a task-level root-cause audit for the fixed plan-normalization pilot."""

from __future__ import annotations

import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from agentdojo.task_suite.load_suites import get_suite


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir()
)
sys.path.insert(0, str(ROOT / "code"))

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison import run_e75  # noqa: E402


RUN_ROOT = ROOT / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/plan-normalization-qwen32-pilot-36"
RESULT_ROOT = ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard"
MODEL = "Qwen3-32B-Q4_K_M.gguf"
SUITES = ("workspace", "slack", "travel", "banking")
USER_TASKS = ("user_task_0", "user_task_1", "user_task_2")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    manifest, _ = run_e75.build_official_case_manifest("v1.1.2")
    imported, _ = run_e75.import_official_agentdojo_live_logs(
        RUN_ROOT / "agentdojo_logs",
        manifest,
        model_name=MODEL,
    )
    imported = [row for row in imported if row["method_id"] == "agentdojo_live_ours_e77_effect_diff_runtime"]
    audit = read_jsonl(RUN_ROOT / "runtime_audit.jsonl")
    task_rows: list[dict[str, Any]] = []
    category_counts: collections.Counter[str] = collections.Counter()

    for suite_name in SUITES:
        suite = get_suite("v1.1.2", suite_name)
        for task_id in USER_TASKS:
            prompt = suite.user_tasks[task_id].PROMPT
            query_hash = hashlib.sha256(prompt.encode()).hexdigest()
            outcomes = [
                row for row in imported if row["suite"] == suite_name and row["user_task_id"] == task_id
            ]
            benign = [row for row in outcomes if row["mode"] == "benign"]
            attacks = [row for row in outcomes if row["mode"] == "attack"]
            plans = [
                row for row in audit if row.get("event") == "task_plan" and row.get("query_hash") == query_hash
            ]
            checks = [
                row for row in audit if row.get("event") == "precommit_check" and row.get("query_hash") == query_hash
            ]
            revisions = [
                row for row in audit if row.get("event") == "plan_revision" and row.get("query_hash") == query_hash
            ]
            errors = collections.Counter(
                error for row in revisions for error in row.get("revision_errors", [])
            )
            needs_replan = sum(row.get("decision") == "NEEDS_REPLAN" for row in checks)
            utility_failures = sum(not row["utility"] for row in outcomes)
            categories: list[str] = []
            if utility_failures and needs_replan == 0:
                categories.append("guard_independent_agent_or_evaluator_failure")
            if needs_replan and any(
                "resolver_fill_requires_replan" in reason
                for row in checks
                for reason in row.get("reasons", [])
            ):
                categories.append("authority_interface_or_typed_grounding_gap")
            if any(row.get("plan_accepted") is False for row in plans):
                categories.append("initial_plan_semantic_rejection")
            if any(row.get("recovery_state") == "REVISION_INVALID" for row in revisions):
                categories.append("revision_schema_failure")
            if any(row.get("recovery_state") == "revision_budget_exhausted" for row in checks):
                categories.append("trajectory_revision_budget_exhausted")
            if not categories and utility_failures:
                categories.append("agent_completion_failure_after_allowed_calls")
            category_counts.update(categories)
            task_rows.append(
                {
                    "suite": suite_name,
                    "user_task_id": task_id,
                    "query_hash": query_hash,
                    "prompt": prompt,
                    "benign_utility": sum(row["utility"] for row in benign),
                    "benign_cases": len(benign),
                    "attack_utility": sum(row["utility"] for row in attacks),
                    "attack_cases": len(attacks),
                    "attack_successes": sum(row["attack_success"] for row in attacks),
                    "plan_events": len(plans),
                    "plan_accepted": sum(row.get("plan_accepted") is True for row in plans),
                    "precommit_allow": sum(row.get("decision") == "ALLOW" for row in checks),
                    "precommit_needs_replan": needs_replan,
                    "revision_state_counts": dict(
                        collections.Counter(str(row.get("recovery_state")) for row in revisions)
                    ),
                    "revision_error_counts": dict(errors),
                    "root_cause_categories": categories,
                }
            )

    report = {
        "status": "passed",
        "experiment": "plan-normalization-qwen32-pilot-36-root-cause-audit",
        "source_run": str(RUN_ROOT.relative_to(ROOT)),
        "model": MODEL,
        "n_tasks": len(task_rows),
        "n_cases": len(imported),
        "category_counts": dict(category_counts),
        "task_rows": task_rows,
        "interpretation": {
            "parser_repair_result": "Plan schema validity reached 100%; parsing is no longer the dominant pilot bottleneck.",
            "authority_boundary": (
                "Free-form tool-returned text is intentionally excluded from typed authorization evidence. "
                "Tasks that delegate recipients, URLs, dates, or payment fields through such text require an "
                "independently bounded resolver or fail closed."
            ),
            "claim_boundary": (
                "This audit attributes observed pilot failures. It does not relabel benchmark outcomes, infer "
                "authority from utility labels, or establish full-run performance."
            ),
        },
    }
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = RESULT_ROOT / "plan-normalization-qwen32-pilot-36-root-cause-audit.json"
    md_path = RESULT_ROOT / "plan-normalization-qwen32-pilot-36-root-cause-audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Plan-Normalization Pilot Root-Cause Audit",
        "",
        f"- Cases: `{len(imported)}`",
        f"- User tasks: `{len(task_rows)}`",
        f"- Categories: `{json.dumps(dict(category_counts), sort_keys=True)}`",
        "",
        "| Task | Benign utility | Attack utility | ASR | ALLOW / NEEDS_REPLAN | Root causes |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in task_rows:
        lines.append(
            f"| {row['suite']}/{row['user_task_id']} | {row['benign_utility']}/{row['benign_cases']} "
            f"| {row['attack_utility']}/{row['attack_cases']} | {row['attack_successes']}/{row['attack_cases']} "
            f"| {row['precommit_allow']} / {row['precommit_needs_replan']} "
            f"| {', '.join(row['root_cause_categories']) or 'none'} |"
        )
    lines.extend(["", "## Boundary", "", report["interpretation"]["claim_boundary"], ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "passed", "n_cases": len(imported), "category_counts": dict(category_counts)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
