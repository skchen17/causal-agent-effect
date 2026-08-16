#!/usr/bin/env python3
"""Strict finalizer for the plan-normalization AgentDojo full run."""

from __future__ import annotations

import collections
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir()
)
EXPERIMENT_ROOT = ROOT / "experiments/intent-bound-runtime-guard"
RESULTS = EXPERIMENT_ROOT / "results/effect-difference-runtime-guard"
RUN_ROOT = EXPERIMENT_ROOT / "runs/effect-difference-runtime-guard/plan-normalization-qwen32-full"
LOGDIR = RUN_ROOT / "agentdojo_logs"
AUDIT = RUN_ROOT / "runtime_audit.jsonl"
PROTOCOL = RUN_ROOT / "protocol_manifest.json"
COMMAND_STATUS = RUN_ROOT / "command_status.json"
E75_PYTHON = (
    ROOT
    / "experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python"
)
EXPECTED_RUNTIME = "effect_diff_runtime_plan_normalization_v1"
METHOD = "agentdojo_live_ours_e77_effect_diff_runtime"
EXPECTED_SUITES = {"workspace": 280, "slack": 126, "travel": 160, "banking": 160}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def official_prompt_hashes() -> set[str]:
    code = r'''
import hashlib
import json
from agentdojo.task_suite.load_suites import get_suite

out = []
for suite_name in ["workspace", "slack", "travel", "banking"]:
    suite = get_suite("v1.1.2", suite_name)
    for task in suite.user_tasks.values():
        out.append(hashlib.sha256(getattr(task, "PROMPT", "").encode()).hexdigest())
print(json.dumps(sorted(set(out))))
'''
    completed = subprocess.run(
        [str(E75_PYTHON), "-c", code],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"AgentDojo prompt-hash extraction failed: {completed.stderr[-1000:]}")
    return set(json.loads(completed.stdout))


def rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def main() -> int:
    sys.path.insert(0, str(ROOT / "code"))
    from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison import run_e75

    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    command_status = json.loads(COMMAND_STATUS.read_text(encoding="utf-8"))
    manifest_rows, _ = run_e75.build_official_case_manifest("v1.1.2")
    imported_rows, import_report = run_e75.import_official_agentdojo_live_logs(
        LOGDIR,
        manifest_rows,
        model_name=str(protocol["model"]["file_name"]),
    )
    method_rows = [row for row in imported_rows if row["method_id"] == METHOD]
    metric = next((row for row in import_report["metrics"] if row["method_id"] == METHOD), None)

    audit = read_jsonl(AUDIT)
    prompt_hashes = official_prompt_hashes()
    official_audit = [row for row in audit if row.get("query_hash") in prompt_hashes]
    plans = [row for row in official_audit if row.get("event") == "task_plan"]
    checks = [row for row in official_audit if row.get("event") == "precommit_check"]
    revisions = [row for row in official_audit if row.get("event") == "plan_revision"]
    versions = collections.Counter(str(row.get("runtime_version")) for row in official_audit)

    diagnostic_fields = ("schema_parse_valid", "validation_passed", "plan_accepted")
    diagnostic_complete = bool(plans) and all(
        all(isinstance(row.get(field), bool) for field in diagnostic_fields) for row in plans
    )
    diagnostic_consistent = diagnostic_complete and all(
        row["plan_accepted"] == row["validation_passed"]
        and (not row["plan_accepted"] or row["schema_parse_valid"])
        and (row["schema_parse_valid"] or not row["validation_passed"])
        for row in plans
    )
    plan_counts = {
        field: sum(row.get(field) is True for row in plans)
        for field in diagnostic_fields
    }

    accepted_by_query: dict[str, bool] = {}
    for row in plans:
        query_hash = str(row.get("query_hash"))
        accepted_by_query[query_hash] = accepted_by_query.get(query_hash, False) or row.get("plan_accepted") is True
    rejected_queries = {query_hash for query_hash, accepted in accepted_by_query.items() if not accepted}
    rejected_side_effect_checks = [
        row
        for row in checks
        if row.get("query_hash") in rejected_queries
        and row.get("descriptor_source") != "read_only_schema_descriptor"
    ]
    rejected_plans_fail_closed = all(
        row.get("initial_decision") != "ALLOW" for row in rejected_side_effect_checks
    )

    command_rows = command_status.get("commands", [])
    command_clean = bool(command_rows) and all(
        row.get("returncode") == 0
        and not row.get("server_400_error")
        and not row.get("server_500_error")
        and not row.get("context_length_exceeded")
        for row in command_rows
    )
    gates = {
        "protocol_manifest_matches_runtime": protocol.get("runtime_version") == EXPECTED_RUNTIME,
        "runner_completed": protocol.get("status") == "runner_completed",
        "official_rows_726": len(method_rows) == 726 and len({row["unified_case_id"] for row in method_rows}) == 726,
        "suite_counts_exact": metric is not None and metric.get("suite_counts") == EXPECTED_SUITES,
        "metric_denominators_exact": metric is not None and metric.get("n_benign") == 97 and metric.get("n_attack") == 629,
        "no_import_errors": (
            metric is not None
            and metric.get("n_error") == 0
            and import_report.get("malformed_logs") == 0
            and import_report.get("duplicate_method_case_logs") == 0
            and import_report.get("target_version_mismatch_rows") == 0
        ),
        "command_protocol_clean": command_clean,
        "all_official_audit_rows_match_runtime": bool(official_audit) and set(versions) == {EXPECTED_RUNTIME},
        "plan_diagnostics_complete": diagnostic_complete,
        "plan_diagnostics_consistent": diagnostic_consistent,
        "rejected_initial_plans_fail_closed": rejected_plans_fail_closed,
        "authorization_checks_deterministic": bool(checks) and all(
            row.get("authorization_decision_deterministic") is True for row in checks
        ),
        "revision_llm_never_directly_authorizes": all(
            row.get("decision") in {"ALLOW", "NEEDS_REPLAN"}
            and row.get("authorization_decision_deterministic") is True
            for row in checks
            if row.get("runtime_called_llm") is True
        ),
    }
    complete = all(gates.values())
    report = {
        "experiment": "Plan-normalization Qwen3-32B official AgentDojo full run",
        "status": "passed" if complete else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_version": EXPECTED_RUNTIME,
        "protocol_manifest": str(PROTOCOL.relative_to(ROOT)),
        "metrics": metric,
        "import": {
            "official_rows": len(method_rows),
            "post_tool_empty_assistant_rows": import_report.get("post_tool_empty_assistant_rows"),
            "included_rows_with_missing_metrics": import_report.get("included_rows_with_missing_metrics"),
        },
        "plan_quality": {
            "events": len(plans),
            "unique_tasks": len(accepted_by_query),
            "schema_parse_valid": plan_counts["schema_parse_valid"],
            "schema_parse_valid_rate": rate(plan_counts["schema_parse_valid"], len(plans)),
            "validation_passed": plan_counts["validation_passed"],
            "validation_passed_rate": rate(plan_counts["validation_passed"], len(plans)),
            "plan_accepted": plan_counts["plan_accepted"],
            "plan_accepted_rate": rate(plan_counts["plan_accepted"], len(plans)),
            "rejected_unique_tasks": len(rejected_queries),
            "rejected_plan_side_effect_checks": len(rejected_side_effect_checks),
            "validation_error_counts": dict(
                collections.Counter(
                    error
                    for row in plans
                    for error in row.get("plan_validation_errors", [])
                )
            ),
        },
        "runtime_audit": {
            "official_rows": len(official_audit),
            "task_plans": len(plans),
            "precommit_checks": len(checks),
            "plan_revisions": len(revisions),
            "runtime_version_counts": dict(versions),
            "decision_counts": dict(collections.Counter(str(row.get("decision")) for row in checks)),
            "initial_decision_counts": dict(collections.Counter(str(row.get("initial_decision")) for row in checks)),
            "recovery_state_counts": dict(collections.Counter(str(row.get("recovery_state")) for row in checks)),
            "revision_llm_calls": sum(row.get("runtime_called_llm") is True for row in checks),
        },
        "verification_gates": gates,
        "claim_boundary": (
            "This run separates plan-schema parsing from semantic authority validation. A semantically rejected "
            "plan remains a measured model outcome and causes fail-closed handling for side-effectful calls; it is "
            "not treated as a harness failure. Exact authorization remains deterministic after bounded model-proposed "
            "revision. Results apply to AgentDojo v1.1.2 sandbox execution and do not imply production safety."
        ),
    }
    report_json = RESULTS / "plan-normalization-qwen32-full-report.json"
    report_md = RESULTS / "plan-normalization-qwen32-full-report.md"
    write_json(report_json, report)
    lines = [
        "# Plan-Normalization Qwen3-32B Full-Run Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Official rows: `{len(method_rows)}/726`",
    ]
    if metric:
        lines.extend(
            [
                f"- ASR: `{metric['attack_successes']}/629 = {metric['attack_success_rate']:.3f}`",
                f"- Benign utility: `{metric['benign_utility_successes']}/97 = {metric['benign_utility_rate']:.3f}`",
                f"- Attack utility: `{metric['attack_user_utility_successes']}/629 = {metric['attack_user_utility_rate']:.3f}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Plan Quality",
            "",
            f"- Schema valid: `{plan_counts['schema_parse_valid']}/{len(plans)}`",
            f"- Validation passed: `{plan_counts['validation_passed']}/{len(plans)}`",
            f"- Plan accepted: `{plan_counts['plan_accepted']}/{len(plans)}`",
            f"- Rejected unique tasks: `{len(rejected_queries)}`",
            "",
            "## Verification Gates",
            "",
        ]
    )
    lines.extend(f"- {key}: `{value}`" for key, value in gates.items())
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    report_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "official_rows": len(method_rows), "gates": gates}, indent=2))
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
