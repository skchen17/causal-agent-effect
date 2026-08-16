#!/usr/bin/env python3
"""Summarize the frozen smoke after call-revision routing was repaired."""

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
    "recovery-normalization-qwen32-smoke-call-routing-v5"
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


def task_text(log: dict[str, Any]) -> str:
    return next(
        block["content"]
        for message in log["messages"]
        if message["role"] == "user"
        for block in message["content"]
        if block["type"] == "text"
    )


def main() -> int:
    benign = read_json(
        RUN_ROOT
        / "agentdojo_logs/local-ours_e77_effect_diff_runtime/banking/"
        "user_task_0/none/none.json"
    )
    attack = read_json(
        RUN_ROOT
        / "agentdojo_logs/local-ours_e77_effect_diff_runtime/banking/"
        "user_task_0/important_instructions/injection_task_0.json"
    )
    audit = read_jsonl(RUN_ROOT / "runtime_audit.jsonl")
    command_status = read_json(RUN_ROOT / "command_status.json")
    if command_status.get("status") != "passed":
        raise ValueError("source smoke did not complete successfully")

    query_hash = hashlib.sha256(task_text(benign).encode()).hexdigest()
    plan_indices = [
        index
        for index, row in enumerate(audit)
        if row.get("event") == "task_plan"
    ]
    if len(plan_indices) != 3:
        raise ValueError(f"expected three benchmark task segments, observed {len(plan_indices)}")
    benign_audit = audit[plan_indices[0] : plan_indices[1]]
    benign_send_checks = [
        row
        for row in benign_audit
        if row.get("event") == "precommit_check"
        and row.get("query_hash") == query_hash
        and row.get("tool_name") == "send_money"
    ]
    benign_feedback = [
        row
        for row in benign_audit
        if row.get("event") == "call_revision_feedback"
        and row.get("query_hash") == query_hash
        and row.get("tool_name") == "send_money"
    ]
    benign_plan_revisions = [
        row
        for row in benign_audit
        if row.get("event") == "plan_revision"
        and row.get("query_hash") == query_hash
        and row.get("tool_name") == "send_money"
    ]
    if len(benign_send_checks) != 2 or len(benign_feedback) != 2:
        raise ValueError("expected two benign send-money retries and feedback rows")
    if benign_plan_revisions:
        raise ValueError("call-only mismatch unexpectedly invoked permission-plan revision")
    if any(row.get("runtime_called_llm") is not False for row in benign_feedback):
        raise ValueError("call-revision feedback unexpectedly called the policy-plane LLM")

    first_statuses = {
        str(row["resource_type"]): str(row["check_result"])
        for row in benign_send_checks[0].get("atom_checks", [])
    }
    expected_statuses = {
        "amount": "resolved_from_authorized_read",
        "recipient": "resolved_from_authorized_read",
        "date": "resolver_fill_requires_replan",
        "subject": "outside_exact_plan",
    }
    if first_statuses != expected_statuses:
        raise ValueError(
            f"smoke status changed: expected {expected_statuses!r}, "
            f"observed {first_statuses!r}"
        )

    event_counts = collections.Counter(str(row.get("event")) for row in audit)
    report = {
        "status": "passed",
        "experiment": "call-revision-routing-v5-smoke-audit",
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
        "routing_check": {
            "benign_send_money_attempts": len(benign_send_checks),
            "call_revision_feedback_rows": len(benign_feedback),
            "permission_plan_revision_rows_for_same_call": len(benign_plan_revisions),
            "runtime_llm_calls_for_call_only_mismatch": sum(
                row.get("runtime_called_llm") is True for row in benign_feedback
            ),
            "first_attempt_field_statuses": first_statuses,
            "send_money_execution_attempts": sum(
                row.get("execution_attempted") is True
                for row in benign_send_checks
            ),
        },
        "runtime_audit": {
            "rows": len(audit),
            "event_counts": dict(sorted(event_counts.items())),
        },
        "interpretation": (
            "The runtime now separates call repair from authority expansion: both "
            "benign send-money mismatches produce deterministic call-revision feedback "
            "without invoking the permission-plan revision model. Utility remains false "
            "because the accepted plan cannot express a bill-derived descriptive subject "
            "or a trusted runtime date default. This isolates a relation-interface gap "
            "rather than an atom-mediation rejection of the authorized amount or recipient."
        ),
        "claim_boundary": (
            "This is a two-row mechanism smoke, not a utility or attack-success estimate. "
            "It supports only the routing and failure-localization claims above."
        ),
    }
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = RESULT_ROOT / "call-revision-routing-v5-smoke.json"
    md_path = RESULT_ROOT / "call-revision-routing-v5-smoke.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md_path.write_text(
        "\n".join(
            [
                "# Call-Revision Routing v5 Smoke",
                "",
                f"- Benign utility: `{report['outcomes']['benign_utility']}`",
                f"- Attack goal achieved: `{report['outcomes']['attack_goal_achieved']}`",
                f"- Call-revision feedback rows: "
                f"`{report['routing_check']['call_revision_feedback_rows']}`",
                f"- Policy-plane LLM calls for those mismatches: "
                f"`{report['routing_check']['runtime_llm_calls_for_call_only_mismatch']}`",
                f"- Field statuses: `{json.dumps(first_statuses, sort_keys=True)}`",
                f"- Executed `send_money` calls: "
                f"`{report['routing_check']['send_money_execution_attempts']}`",
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
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
