#!/usr/bin/env python3
"""Validate and summarize the E77 official AgentDojo full run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"
METHOD = "agentdojo_live_ours_e77_effect_diff_runtime"
E75_PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
MODEL_FILE = "Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf"
MODEL_BYTES = 5_629_105_408
MODEL_SHA256 = "9be227448d319e6a7acca8056b71bf7d9a2c6b2811986e6658a9dedc208d0ada"
EXPECTED_SUITES = {"workspace": 280, "slack": 126, "travel": 160, "banking": 160}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def artifact_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return resolved.name


def official_prompt_hashes(agentdojo_version: str) -> set[str]:
    code = r'''
import hashlib
import json
from agentdojo.task_suite.load_suites import get_suite

version = __VERSION__
out = []
for suite_name in ["workspace", "slack", "travel", "banking"]:
    suite = get_suite(version, suite_name)
    for task in suite.user_tasks.values():
        out.append(hashlib.sha256(getattr(task, "PROMPT", "").encode()).hexdigest())
print(json.dumps(sorted(set(out))))
'''.replace("__VERSION__", json.dumps(agentdojo_version))
    completed = subprocess.run(
        [str(E75_PYTHON), "-c", code], check=False, capture_output=True, text=True, timeout=120
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Official prompt extraction failed: {completed.stderr[-1000:]}")
    return set(json.loads(completed.stdout))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--logdir", type=Path, required=True)
    parser.add_argument("--run-status", type=Path, default=RESULTS / "e75_agentdojo_official_live_run_status.json")
    parser.add_argument("--import-metrics", type=Path, default=RESULTS / "e75_agentdojo_official_live_import_metrics.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_status = read_json(args.run_status)
    imported = read_json(args.import_metrics)
    registration = read_json(RESULTS / "e77_descriptor_registration_report.json")
    targeted = read_json(RESULTS / "e77_targeted_attack_replay_status.json")
    audit = read_jsonl(args.audit)
    plans = [row for row in audit if row.get("event") == "task_plan"]
    checks = [row for row in audit if row.get("event") == "precommit_check"]
    prompt_hashes = official_prompt_hashes(imported.get("target_agentdojo_version", "v1.1.2"))
    official_plans = [row for row in plans if row.get("query_hash") in prompt_hashes]
    auxiliary_plans = [row for row in plans if row.get("query_hash") not in prompt_hashes]
    official_checks = [row for row in checks if row.get("query_hash") in prompt_hashes]
    auxiliary_checks = [row for row in checks if row.get("query_hash") not in prompt_hashes]
    official_plan_hashes = {row.get("query_hash") for row in official_plans}
    official_checks_without_plan = sum(row.get("query_hash") not in official_plan_hashes for row in official_checks)
    metrics = next((row for row in imported.get("metrics", []) if row.get("method_id") == METHOD), None)
    commands = run_status.get("commands", [])
    clean_commands = all(
        row.get("returncode") == 0 and not row.get("server_400_error") and not row.get("server_500_error")
        and not row.get("context_length_exceeded") for row in commands
    )
    metric_complete = bool(
        metrics
        and metrics.get("n_total") == 726
        and metrics.get("n_benign") == 97
        and metrics.get("n_attack") == 629
        and metrics.get("n_error") == 0
        and metrics.get("suite_counts") == EXPECTED_SUITES
    )
    import_complete = (
        imported.get("status") == "passed" and imported.get("n_rows") == 726
        and imported.get("official_case_keys") == 726
        and imported.get("method_key_counts", {}).get(METHOD) == 726 and metrics is not None
        and imported.get("malformed_logs") == 0 and imported.get("included_rows_with_missing_metrics") == 0
        and imported.get("post_tool_empty_assistant_rows") == 0
        and imported.get("duplicate_method_case_logs") == 0
        and imported.get("target_version_mismatch_rows") == 0
        and imported.get("method_suite_key_counts", {}).get(METHOD) == EXPECTED_SUITES
    )
    audit_complete = (
        official_checks_without_plan == 0
        and all(row.get("parse_valid") is True for row in official_plans)
        and all(row.get("runtime_called_llm") is False for row in official_checks)
    )
    complete = import_complete and metric_complete and audit_complete and clean_commands
    decisions = Counter(row.get("decision", "unknown") for row in official_checks)
    auxiliary_decisions = Counter(row.get("decision", "unknown") for row in auxiliary_checks)
    by_source: dict[str, Counter[str]] = defaultdict(Counter)
    for row in official_checks:
        by_source[row.get("descriptor_source", "unknown")][row.get("decision", "unknown")] += 1
    registration = dict(registration)
    registration["registered_descriptor_path"] = artifact_path(
        RESULTS / "e77_registered_effect_diff_descriptors.jsonl"
    )
    report = {
        "experiment": "E77 sandbox effect-diff descriptor runtime",
        "status": "passed" if complete else "failed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "method_id": METHOD,
        "agentdojo_version": imported.get("target_agentdojo_version"),
        "official_case_keys": imported.get("n_rows"),
        "logdir": artifact_path(args.logdir),
        "audit_path": artifact_path(args.audit),
        "model": {
            "display_name": "Qwen3.5-9B-DeepSeek-V4-Flash",
            "file_name": MODEL_FILE,
            "quantization": "Q4_K_M",
            "bytes": MODEL_BYTES,
            "sha256": MODEL_SHA256,
            "temperature": 0.0,
        },
        "agent_max_tokens": 4096,
        "context_window": 131072,
        "metrics": metrics,
        "registration": registration,
        "targeted_replay": {"status": targeted.get("status"), "n_cases": len(targeted.get("commands", []))},
        "runtime_audit": {
            "n_rows": len(audit),
            "official_task_plan_events": len(official_plans),
            "official_distinct_task_queries_planned": len(official_plan_hashes),
            "official_task_plan_parse_valid": sum(bool(row.get("parse_valid")) for row in official_plans),
            "official_task_plan_parse_invalid": sum(not row.get("parse_valid") for row in official_plans),
            "official_precommit_checks": len(official_checks),
            "official_checks_without_plan": official_checks_without_plan,
            "decision_counts": dict(decisions),
            "decisions_by_descriptor_source": {key: dict(value) for key, value in by_source.items()},
            "explicit_override_count": sum(row.get("decision") == "ALLOW_EXPLICIT_OVERRIDE" for row in official_checks),
            "guard_llm_calls_after_task_plan": sum(bool(row.get("runtime_called_llm")) for row in official_checks),
            "auxiliary_task_plan_events_excluded": len(auxiliary_plans),
            "auxiliary_precommit_checks_excluded": len(auxiliary_checks),
            "auxiliary_decision_counts_excluded": dict(auxiliary_decisions),
        },
        "verification_gates": {
            "official_import_complete": import_complete,
            "metric_denominators_complete": metric_complete,
            "runtime_audit_complete": audit_complete,
            "commands_clean": clean_commands,
        },
        "command_diagnostics": [
            {key: row.get(key) for key in ("suite", "mode", "returncode", "server_400_error", "server_500_error", "context_length_exceeded")}
            for row in commands
        ],
        "claim_boundary": (
            "E77 evaluates local-LLM effect inventories compiled with independent AgentDojo sandbox field "
            "state/output differences, fail-closed unresolved fields, mediated webpage destinations, sanitized "
            "resolver evidence, and no repeated-call override. It is a sandbox benchmark result, not a production guarantee."
        ),
    }
    json_path = RESULTS / "e77_agentdojo_official_full_run_report.json"
    md_path = RESULTS / "e77_agentdojo_official_full_run_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    metric = metrics or {}
    md_path.write_text(
        "# E77 Official AgentDojo Full-Run Report\n\n"
        f"- Status: `{report['status']}`\n"
        f"- Official keys: `{report['official_case_keys']}/726`\n"
        f"- Attack success: `{metric.get('attack_successes', 0)}/{metric.get('n_attack', 0)} = {metric.get('attack_success_rate', 0):.3f}`\n"
        f"- Benign utility: `{metric.get('benign_utility_successes', 0)}/{metric.get('n_benign', 0)} = {metric.get('benign_utility_rate', 0):.3f}`\n"
        f"- Attack-task utility: `{metric.get('attack_user_utility_successes', 0)}/{metric.get('n_attack', 0)} = {metric.get('attack_user_utility_rate', 0):.3f}`\n"
        f"- Official plan-event parse valid: `{report['runtime_audit']['official_task_plan_parse_valid']}/{report['runtime_audit']['official_task_plan_events']}`\n"
        f"- Official pre-commit checks: `{report['runtime_audit']['official_precommit_checks']}`\n"
        f"- Decisions: `{json.dumps(report['runtime_audit']['decision_counts'], sort_keys=True)}`\n"
        f"- Explicit overrides: `{report['runtime_audit']['explicit_override_count']}`\n"
        f"- Auxiliary plan/check events excluded: `{report['runtime_audit']['auxiliary_task_plan_events_excluded']}/{report['runtime_audit']['auxiliary_precommit_checks_excluded']}`\n"
        f"- Post-tool empty responses: `{imported.get('post_tool_empty_assistant_rows')}`\n\n"
        "## Claim Boundary\n\n" + report["claim_boundary"] + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "report_json": str(json_path), "report_md": str(md_path)}, indent=2))
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
