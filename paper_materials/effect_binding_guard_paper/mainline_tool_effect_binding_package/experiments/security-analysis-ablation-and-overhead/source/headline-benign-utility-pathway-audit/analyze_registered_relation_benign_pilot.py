#!/usr/bin/env python3
"""Finalize the frozen 16-case registered-relation benign mechanism pilot."""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
RUN_ROOT = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/"
    "effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-pilot-36-"
    "registered-relation-benign-pilot-v8-suite-scope-fix"
)
PILOT_MANIFEST = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/"
    "effect-difference-runtime-guard/"
    "registered_relation_benign_pilot_manifest.json"
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_user_text(log: dict[str, Any]) -> str:
    return next(
        block["content"]
        for message in log["messages"]
        if message["role"] == "user"
        for block in message["content"]
        if block["type"] == "text"
    )


def summarize_outcomes(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "cases": len(rows),
        "utility_successes": sum(row["utility"] is True for row in rows),
        "utility_failures": sum(row["utility"] is False for row in rows),
        "errors": sum(row["error"] is not None for row in rows),
    }


def build_report() -> dict[str, Any]:
    frozen = read_json(PILOT_MANIFEST)
    protocol = read_json(RUN_ROOT / "protocol_manifest.json")
    if protocol.get("status") != "runner_completed":
        raise ValueError(
            f"pilot runner is not complete: {protocol.get('status')!r}"
        )
    if protocol.get("runner_returncode") != 0:
        raise ValueError("pilot runner returned nonzero")
    if frozen.get("status") != "frozen_before_v8_pilot_execution":
        raise ValueError("pilot manifest is not frozen")
    selection = protocol["agentdojo"]["pilot_selection"]
    if selection["manifest_sha256"] != sha256(PILOT_MANIFEST):
        raise ValueError("pilot manifest changed after protocol creation")
    if protocol["agentdojo"]["case_keys"] != frozen["n_cases"]:
        raise ValueError("protocol denominator differs from frozen manifest")
    if protocol["agentdojo"]["modes"] != ["benign"]:
        raise ValueError("pilot protocol unexpectedly includes non-benign modes")

    audit = read_jsonl(RUN_ROOT / "runtime_audit.jsonl")
    audit_by_query: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in audit:
        query_hash = row.get("query_hash")
        if isinstance(query_hash, str):
            audit_by_query[query_hash].append(row)

    case_rows: list[dict[str, Any]] = []
    for case in frozen["cases"]:
        log_path = (
            RUN_ROOT
            / "agentdojo_logs/local-ours_e77_effect_diff_runtime"
            / case["suite"]
            / case["user_task_id"]
            / "none/none.json"
        )
        if not log_path.exists():
            raise FileNotFoundError(f"missing fixed-denominator log: {log_path}")
        log = read_json(log_path)
        if "utility" not in log or not isinstance(log["utility"], bool):
            raise ValueError(f"missing boolean utility outcome: {case['case_key']}")
        query_hash = hashlib.sha256(
            first_user_text(log).encode("utf-8")
        ).hexdigest()
        case_audit = audit_by_query.get(query_hash, [])
        executed_checks = [
            row
            for row in case_audit
            if row.get("event") == "precommit_check"
            and row.get("execution_attempted") is True
        ]
        unsafe_execution_rows = [
            row
            for row in executed_checks
            if row.get("decision") != "ALLOW"
        ]
        check_result_counts = collections.Counter(
            str(check.get("check_result"))
            for row in case_audit
            if row.get("event") == "precommit_check"
            for check in row.get("atom_checks", [])
            if check.get("check_result")
        )
        plan_validation_error_counts = collections.Counter(
            str(error)
            for row in case_audit
            if row.get("event") == "task_plan"
            for error in row.get("plan_validation_errors", [])
        )
        case_rows.append(
            {
                "case_key": case["case_key"],
                "stratum": case["stratum"],
                "utility": log["utility"],
                "error": log.get("error"),
                "precommit_checks": sum(
                    row.get("event") == "precommit_check" for row in case_audit
                ),
                "call_revision_feedback": sum(
                    row.get("event") == "call_revision_feedback"
                    for row in case_audit
                ),
                "plan_revisions": sum(
                    row.get("event") == "plan_revision" for row in case_audit
                ),
                "execution_attempts": len(executed_checks),
                "unsafe_execution_rows": len(unsafe_execution_rows),
                "check_result_counts": dict(sorted(check_result_counts.items())),
                "plan_validation_error_counts": dict(
                    sorted(plan_validation_error_counts.items())
                ),
                "source_log": str(log_path.relative_to(ROOT)),
            }
        )

    target_rows = [
        row
        for row in case_rows
        if row["stratum"] == "historical_trusted_source_resolver_loss"
    ]
    control_rows = [
        row
        for row in case_rows
        if row["stratum"] == "historical_stable_success_control"
    ]
    if len(case_rows) != 16 or len(target_rows) != 12 or len(control_rows) != 4:
        raise ValueError("fixed pilot strata changed")
    unsafe_execution_rows = sum(row["unsafe_execution_rows"] for row in case_rows)
    if unsafe_execution_rows:
        raise ValueError("a non-ALLOW check reached execution")

    target = summarize_outcomes(target_rows)
    control = summarize_outcomes(control_rows)
    overall = summarize_outcomes(case_rows)
    failure_check_results = collections.Counter()
    failure_plan_errors = collections.Counter()
    runtime_relation_failure_cases: list[str] = []
    plan_construction_failure_cases: list[str] = []
    for row in case_rows:
        if row["utility"]:
            continue
        failure_check_results.update(row["check_result_counts"])
        failure_plan_errors.update(row["plan_validation_error_counts"])
        if row["check_result_counts"].get("resolver_fill_requires_replan", 0):
            runtime_relation_failure_cases.append(row["case_key"])
        if row["plan_validation_error_counts"]:
            plan_construction_failure_cases.append(row["case_key"])
    report = {
        "status": "passed_fixed_denominator_outcomes_retained",
        "experiment": "registered-relation-benign-mechanism-pilot-v8",
        "source_run": str(RUN_ROOT.relative_to(ROOT)),
        "protocol": {
            "runtime_version": protocol["runtime_version"],
            "agentdojo_version": protocol["agentdojo"]["version"],
            "model": protocol["model"]["file_name"],
            "execution_date": protocol["runtime_configuration"][
                "runtime_defaults"
            ]["execution_date"],
            "manifest_sha256": selection["manifest_sha256"],
            "modes": protocol["agentdojo"]["modes"],
        },
        "historical_reference": {
            "target_utility_successes": 0,
            "target_cases": 12,
            "control_utility_successes": 4,
            "control_cases": 4,
            "source": frozen["source_audit"],
        },
        "v8_outcomes": {
            "target": target,
            "control": control,
            "overall": overall,
            "target_recovery_delta": target["utility_successes"],
            "control_retention_delta": control["utility_successes"] - 4,
        },
        "runtime_audit": {
            "rows": len(audit),
            "event_counts": dict(
                sorted(
                    collections.Counter(
                        str(row.get("event")) for row in audit
                    ).items()
                )
            ),
            "executed_non_allow_checks": unsafe_execution_rows,
        },
        "failure_anatomy": {
            "failed_cases": overall["utility_failures"],
            "runtime_relation_failure_cases": runtime_relation_failure_cases,
            "runtime_relation_failure_case_count": len(
                runtime_relation_failure_cases
            ),
            "plan_construction_failure_cases": plan_construction_failure_cases,
            "plan_construction_failure_case_count": len(
                plan_construction_failure_cases
            ),
            "check_result_counts": dict(sorted(failure_check_results.items())),
            "plan_validation_error_counts": dict(
                sorted(failure_plan_errors.items())
            ),
        },
        "cases": case_rows,
        "claim_boundary": frozen["claim_boundary"],
        "interpretation": (
            "The target stratum is selected from historical failures with a "
            "trusted-source value visible upstream. Recovery therefore tests "
            "the diagnosed interface mechanism, not unbiased AgentDojo utility. "
            "All fixed-denominator outcomes, including failures, are retained."
        ),
    }
    return report


def main() -> int:
    report = build_report()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = RESULT_ROOT / "registered-relation-benign-pilot-v8.json"
    md_path = RESULT_ROOT / "registered-relation-benign-pilot-v8.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    outcomes = report["v8_outcomes"]
    lines = [
        "# Registered-Relation Benign Pilot v8",
        "",
        f"- Status: `{report['status']}`",
        f"- Target recovery: `{outcomes['target']['utility_successes']}/12`",
        f"- Control retention: `{outcomes['control']['utility_successes']}/4`",
        f"- Overall utility: `{outcomes['overall']['utility_successes']}/16`",
        f"- Runtime errors: `{outcomes['overall']['errors']}`",
        (
            "- Executed non-ALLOW checks: "
            f"`{report['runtime_audit']['executed_non_allow_checks']}`"
        ),
        (
            "- Failed-case check results: `"
            f"{json.dumps(report['failure_anatomy']['check_result_counts'], sort_keys=True)}`"
        ),
        (
            "- Runtime-relation failure cases: "
            f"`{report['failure_anatomy']['runtime_relation_failure_case_count']}`"
        ),
        (
            "- Plan-construction failure cases: "
            f"`{report['failure_anatomy']['plan_construction_failure_case_count']}`"
        ),
        "",
        "## Case Outcomes",
        "",
        "| Case | Stratum | Utility | Error | Checks | Call Feedback |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in report["cases"]:
        lines.append(
            f"| `{row['case_key']}` | `{row['stratum']}` | "
            f"{row['utility']} | {row['error'] is not None} | "
            f"{row['precommit_checks']} | {row['call_revision_feedback']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "target_recovery": outcomes["target"]["utility_successes"],
                "control_retention": outcomes["control"]["utility_successes"],
                "overall_utility": outcomes["overall"]["utility_successes"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
