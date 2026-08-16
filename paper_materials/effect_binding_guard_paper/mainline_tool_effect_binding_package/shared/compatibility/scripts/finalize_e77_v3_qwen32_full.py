#!/usr/bin/env python3
"""Strict finalizer for the E77-v3 Qwen3-32B AgentDojo full run."""

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
RESULTS = ROOT / "analysis/results"
RUN_ROOT = ROOT / "runs/e77_v3_qwen32_full"
LOGDIR = RUN_ROOT / "agentdojo_logs"
AUDIT = RUN_ROOT / "runtime_audit.jsonl"
PROTOCOL = RUN_ROOT / "protocol_manifest.json"
COMMAND_STATUS = RUN_ROOT / "command_status.json"
E75_PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
EXPECTED_RUNTIME = "e77_effect_diff_runtime_v3_bounded_recovery"
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


def main() -> int:
    sys.path.insert(0, str(ROOT / "code"))
    from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison import run_e75

    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    command_status = json.loads(COMMAND_STATUS.read_text(encoding="utf-8"))
    manifest_rows, _ = run_e75.build_official_case_manifest("v1.1.2")
    imported_rows, import_report = run_e75.import_official_agentdojo_live_logs(LOGDIR, manifest_rows)
    method_rows = [row for row in imported_rows if row["method_id"] == METHOD]
    metric = next((row for row in import_report["metrics"] if row["method_id"] == METHOD), None)
    audit = read_jsonl(AUDIT)
    prompt_hashes = official_prompt_hashes()
    official_audit = [row for row in audit if row.get("query_hash") in prompt_hashes]
    plans = [row for row in official_audit if row.get("event") == "task_plan"]
    checks = [row for row in official_audit if row.get("event") == "precommit_check"]
    revisions = [row for row in official_audit if row.get("event") == "plan_revision"]
    versions = collections.Counter(str(row.get("runtime_version")) for row in official_audit)
    command_rows = command_status.get("commands", [])
    command_clean = bool(command_rows) and all(
        row.get("returncode") == 0
        and not row.get("server_400_error")
        and not row.get("server_500_error")
        and not row.get("context_length_exceeded")
        for row in command_rows
    )
    gates = {
        "protocol_manifest_is_v3": protocol.get("runtime_version") == EXPECTED_RUNTIME,
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
        "all_official_audit_rows_are_v3": bool(official_audit) and set(versions) == {EXPECTED_RUNTIME},
        "all_plans_parse_valid": bool(plans) and all(row.get("parse_valid") is True for row in plans),
        "authorization_checks_deterministic": bool(checks) and all(
            row.get("authorization_decision_deterministic") is True for row in checks
        ),
        "revision_llm_never_directly_authorizes": all(
            row.get("decision") in {"ALLOW", "NEEDS_REPLAN"} and row.get("authorization_decision_deterministic") is True
            for row in checks
            if row.get("runtime_called_llm") is True
        ),
    }
    complete = all(gates.values())
    report = {
        "experiment": "E77-v3 Qwen3-32B official AgentDojo full run",
        "status": "passed" if complete else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_version": EXPECTED_RUNTIME,
        "protocol_manifest": "runs/e77_v3_qwen32_full/protocol_manifest.json",
        "metrics": metric,
        "import": {
            "official_rows": len(method_rows),
            "post_tool_empty_assistant_rows": import_report.get("post_tool_empty_assistant_rows"),
            "included_rows_with_missing_metrics": import_report.get("included_rows_with_missing_metrics"),
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
            "E77-v3 uses a local model to propose a task-level authority plan and bounded revisions. "
            "Every exact call is totalized and deterministically checked after any revision. E84 reviewed manifests "
            "are not used in this main run. Results apply to AgentDojo v1.1.2 sandbox execution and do not imply production safety."
        ),
    }
    write_json(RESULTS / "e77_v3_qwen32_full_run_report.json", report)
    lines = [
        "# E77-v3 Qwen3-32B Full-Run Report",
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
    lines.extend(["", "## Verification Gates", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in gates.items())
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    (RESULTS / "e77_v3_qwen32_full_run_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "official_rows": len(method_rows), "gates": gates}, indent=2))
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
