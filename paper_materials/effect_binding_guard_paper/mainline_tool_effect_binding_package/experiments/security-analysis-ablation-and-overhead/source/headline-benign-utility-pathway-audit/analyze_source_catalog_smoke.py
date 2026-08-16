#!/usr/bin/env python3
"""Summarize the frozen end-to-end smoke after the source-catalog repair."""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir()
)
RUN_ROOT = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-smoke-source-catalog-fix-v1"
)
RESULT_ROOT = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "headline-benign-utility-pathway-audit"
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    benign_path = (
        RUN_ROOT
        / "agentdojo_logs/local-ours_e77_effect_diff_runtime/banking/"
        "user_task_0/none/none.json"
    )
    attack_path = (
        RUN_ROOT
        / "agentdojo_logs/local-ours_e77_effect_diff_runtime/banking/"
        "user_task_0/important_instructions/injection_task_0.json"
    )
    benign = read_json(benign_path)
    attack = read_json(attack_path)
    audit = read_jsonl(RUN_ROOT / "runtime_audit.jsonl")
    task = next(
        block["content"]
        for message in benign["messages"]
        if message["role"] == "user"
        for block in message["content"]
        if block["type"] == "text"
    )
    query_hash = hashlib.sha256(task.encode()).hexdigest()
    plans = [
        row
        for row in audit
        if row.get("event") == "task_plan" and row.get("query_hash") == query_hash
    ]
    send_checks = [
        row
        for row in audit
        if row.get("event") == "precommit_check"
        and row.get("query_hash") == query_hash
        and row.get("tool_name") == "send_money"
    ]
    if not plans or not send_checks:
        raise ValueError("expected benign plan and send_money check are missing")
    first_check = send_checks[0]
    statuses = {
        str(row["resource_type"]): str(row["check_result"])
        for row in first_check.get("atom_checks", [])
    }
    expected_statuses = {
        "amount": "resolved_from_authorized_read",
        "recipient": "resolved_from_authorized_read",
        "date": "resolver_fill_requires_replan",
        "subject": "outside_exact_plan",
    }
    if statuses != expected_statuses:
        raise ValueError(
            f"smoke status changed: expected {expected_statuses!r}, observed {statuses!r}"
        )
    event_counts = collections.Counter(str(row.get("event")) for row in audit)
    report = {
        "status": "passed",
        "experiment": "source-catalog-fix-end-to-end-smoke-audit",
        "source_run": str(RUN_ROOT.relative_to(ROOT)),
        "scope": {
            "model": "Qwen3-32B-Q4_K_M.gguf",
            "agentdojo_version": "v1.1.2",
            "suite": "banking",
            "user_task": "user_task_0",
            "benign_cases": 1,
            "attack_cases": 1,
        },
        "outcomes": {
            "benign_utility": bool(benign["utility"]),
            "attack_utility": bool(attack["utility"]),
            "attack_goal_achieved": bool(attack["security"]),
            "errors": int(benign["error"] is not None)
            + int(attack["error"] is not None),
        },
        "planner": {
            "accepted": all(row.get("plan_accepted") is True for row in plans),
            "validation_errors": sorted(
                {
                    error
                    for row in plans
                    for error in row.get("plan_validation_errors", [])
                }
            ),
            "declared_bill_source_visible_in_raw_prefix": all(
                '"source_tools": ["read_file"]' in row.get("raw_output_prefix", "")
                for row in plans
            ),
        },
        "first_benign_send_money_check": {
            "initial_decision": first_check["initial_decision"],
            "final_decision": first_check["decision"],
            "recovery_state": first_check["recovery_state"],
            "field_statuses": statuses,
            "execution_attempted": first_check["execution_attempted"],
        },
        "runtime_audit": {
            "rows": len(audit),
            "event_counts": dict(sorted(event_counts.items())),
            "send_money_execution_attempts": sum(
                row.get("execution_attempted") is True for row in send_checks
            ),
        },
        "interpretation": (
            "The source-catalog repair reaches the end-to-end runtime and resolves the "
            "bill amount and recipient from read_file. Utility remains false because the "
            "agent proposes an ungrounded date and a subject outside the exact initial "
            "plan, after which bounded recovery denies the call. The next interface gap "
            "is relational authorization for derived metadata and trusted runtime "
            "defaults, not resolver source naming."
        ),
        "claim_boundary": (
            "This is a two-row smoke audit. It does not estimate utility recovery, ASR, "
            "or benchmark-wide safety and is not admitted as a main paper result."
        ),
    }
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = RESULT_ROOT / "source-catalog-fix-end-to-end-smoke.json"
    md_path = RESULT_ROOT / "source-catalog-fix-end-to-end-smoke.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md_path.write_text(
        "\n".join(
            [
                "# Source-Catalog Fix End-to-End Smoke",
                "",
                f"- Benign utility: `{report['outcomes']['benign_utility']}`",
                f"- Attack goal achieved: `{report['outcomes']['attack_goal_achieved']}`",
                f"- Planner accepted: `{report['planner']['accepted']}`",
                f"- Field statuses: `{json.dumps(statuses, sort_keys=True)}`",
                f"- Executed `send_money` calls: "
                f"`{report['runtime_audit']['send_money_execution_attempts']}`",
                "",
                "## Interpretation",
                "",
                report["interpretation"],
                "",
                "## Claim Boundary",
                "",
                report["claim_boundary"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "outcomes": report["outcomes"],
                "field_statuses": statuses,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
