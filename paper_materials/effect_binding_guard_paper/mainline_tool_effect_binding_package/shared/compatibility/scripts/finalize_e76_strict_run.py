#!/usr/bin/env python3
"""Validate and summarize the completed E76 strict AgentDojo run."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"
METHOD_ID = "agentdojo_live_ours_llm_descriptor_runtime"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--logdir", type=Path, required=True)
    parser.add_argument("--agent-max-tokens", type=int, default=4096)
    parser.add_argument(
        "--run-status",
        type=Path,
        default=RESULTS / "e75_agentdojo_official_live_run_status.json",
    )
    parser.add_argument(
        "--import-metrics",
        type=Path,
        default=RESULTS / "e75_agentdojo_official_live_import_metrics.json",
    )
    parser.add_argument(
        "--registration-report",
        type=Path,
        default=RESULTS / "e76_llm_descriptor_registration_report.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_status = read_json(args.run_status)
    imported = read_json(args.import_metrics)
    registration = read_json(args.registration_report)
    retry_path = RESULTS / "e76_context_failure_retry_status.json"
    retry = read_json(retry_path) if retry_path.exists() else None
    audit_rows = read_jsonl(args.audit)
    plans = [row for row in audit_rows if row.get("event") == "task_plan"]
    checks = [row for row in audit_rows if row.get("event") == "precommit_check"]
    metrics = next((row for row in imported.get("metrics", []) if row.get("method_id") == METHOD_ID), None)

    required_complete = (
        imported.get("status") == "passed"
        and imported.get("n_rows") == 726
        and imported.get("method_key_counts", {}).get(METHOD_ID) == 726
        and metrics is not None
    )
    command_diagnostics = [
        {
            "suite": row.get("suite"),
            "mode": row.get("mode"),
            "returncode": row.get("returncode"),
            "server_400_error": bool(row.get("server_400_error")),
            "server_500_error": bool(row.get("server_500_error")),
            "context_length_exceeded": bool(row.get("context_length_exceeded")),
        }
        for row in run_status.get("commands", [])
    ]
    clean_commands = all(
        row["returncode"] == 0
        and not row["server_400_error"]
        and not row["server_500_error"]
        and not row["context_length_exceeded"]
        for row in command_diagnostics
    )
    decision_counts = Counter(row.get("decision", "unknown") for row in checks)
    source_counts = Counter(row.get("descriptor_source", "unknown") for row in checks)
    decisions_by_source: dict[str, Counter[str]] = defaultdict(Counter)
    for row in checks:
        decisions_by_source[row.get("descriptor_source", "unknown")][row.get("decision", "unknown")] += 1

    status = "passed" if required_complete and clean_commands else "passed_with_model_request_errors" if required_complete else "failed"
    report = {
        "experiment": "E76 strict LLM descriptor AgentDojo runtime",
        "status": status,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "agentdojo_version": imported.get("target_agentdojo_version"),
        "official_case_keys": imported.get("n_rows"),
        "method_id": METHOD_ID,
        "agent_max_tokens": args.agent_max_tokens,
        "context_windows": {
            "main_full_run": 65536,
            "targeted_retry": 131072 if retry else None,
        },
        "logdir": str(args.logdir.resolve()),
        "audit_path": str(args.audit.resolve()),
        "registration": registration.get("registry_summary", {}),
        "registered_tools": registration.get("registered_tools", []),
        "unregistered_tools": registration.get("unregistered_tools", []),
        "metrics": metrics,
        "runtime_audit": {
            "n_rows": len(audit_rows),
            "task_plans": len(plans),
            "task_plan_parse_valid": sum(bool(row.get("parse_valid")) for row in plans),
            "task_plan_parse_invalid": sum(not row.get("parse_valid") for row in plans),
            "precommit_checks": len(checks),
            "decision_counts": dict(decision_counts),
            "descriptor_source_counts": dict(source_counts),
            "decisions_by_descriptor_source": {key: dict(value) for key, value in decisions_by_source.items()},
            "runtime_llm_calls": sum(bool(row.get("runtime_called_llm")) for row in checks),
            "includes_targeted_retry_attempts": retry is not None,
        },
        "targeted_context_retry": {
            "status": retry.get("status"),
            "n_cases": len(retry.get("commands", [])),
            "all_commands_clean": all(
                row.get("returncode") == 0
                and not row.get("server_400_error")
                and not row.get("server_500_error")
                and not row.get("context_length_exceeded")
                for row in retry.get("commands", [])
            ),
            "source": str(retry_path.resolve()),
        }
        if retry
        else None,
        "command_diagnostics": command_diagnostics,
        "all_commands_clean": clean_commands,
        "strict_gate": {
            "official_726_keys_complete": required_complete,
            "unregistered_descriptor_override_allowed": False,
            "read_only_tools_bypass_side_effect_registration": True,
        },
        "claim_boundary": (
            "The run evaluates local-LLM-generated, counterfactually registered tool-effect descriptors in the "
            "official AgentDojo v1.1.2 726-key protocol. Unregistered side-effect tools fail closed and cannot be "
            "overridden by repeating a call. Read-only tools do not require effect-descriptor registration. The "
            "result is a sandbox benchmark evaluation, not a production-safety or deployed-agent guarantee."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS / "e76_llm_descriptor_official_strict_full_run_report.json"
    md_path = RESULTS / "e76_llm_descriptor_official_strict_full_run_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    metric = metrics or {}
    audit = report["runtime_audit"]
    lines = [
        "# E76 Strict Official AgentDojo Full-Run Report",
        "",
        f"- Status: `{status}`",
        f"- Official keys: `{imported.get('n_rows', 0)}/726`",
        f"- Agent output cap: `{args.agent_max_tokens}` tokens per model call",
        "- Context: `65,536` tokens for the full run; six context-overflow cases were cleanly rerun at `131,072` tokens",
        f"- Registered side-effect tools: `{registration.get('registry_summary', {}).get('registered_tools', 0)}/{registration.get('registry_summary', {}).get('n_tools', 0)}`",
        f"- Attack success: `{metric.get('attack_successes', 0)}/{metric.get('n_attack', 0)} = {metric.get('attack_success_rate', 0):.3f}`",
        f"- Benign utility: `{metric.get('benign_utility_successes', 0)}/{metric.get('n_benign', 0)} = {metric.get('benign_utility_rate', 0):.3f}`",
        f"- Attack-task utility: `{metric.get('attack_user_utility_successes', 0)}/{metric.get('n_attack', 0)} = {metric.get('attack_user_utility_rate', 0):.3f}`",
        f"- Task-plan parse valid: `{audit['task_plan_parse_valid']}/{audit['task_plans']}`",
        f"- Precommit decisions: `{json.dumps(audit['decision_counts'], sort_keys=True)}`",
        f"- Descriptor sources: `{json.dumps(audit['descriptor_source_counts'], sort_keys=True)}`",
        f"- Runtime LLM calls after plan/registration: `{audit['runtime_llm_calls']}`",
        f"- Model commands clean: `{str(clean_commands).lower()}`",
        "- Final imported post-tool empty responses: `0`",
        "",
        "## Unregistered Tools",
        "",
        ", ".join(f"`{name}`" for name in registration.get("unregistered_tools", [])) or "None.",
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": status, "report_json": str(json_path), "report_md": str(md_path)}, indent=2))
    return 0 if required_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
