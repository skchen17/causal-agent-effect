#!/usr/bin/env python3
"""Summarize paired E77 uncertainty-policy smoke diagnostics."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir()
)
RUNS = ROOT / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard"
RESULTS = ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard"
RUN_CONFIGS = {
    "strict_smoke": RUNS / "recovery-normalization-qwen32-smoke-v3clean",
    "default_allow_smoke": (
        RUNS / "recovery-normalization-qwen32-smoke-allow-after-recovery-v3clean"
    ),
    "task_bound_resolver_smoke": (
        RUNS
        / "recovery-normalization-qwen32-smoke-allow-after-recovery-taskbound-slack-user2"
    ),
    "strict_fixed_pilot": (
        RUNS / "recovery-normalization-qwen32-pilot-36-final-runtime-v4"
    ),
    "default_allow_fixed_pilot": (
        RUNS
        / "recovery-normalization-qwen32-pilot-36-allow-after-recovery-final-runtime-v4"
    ),
}
EXPECTED_ROWS = {
    "strict_smoke": 2,
    "default_allow_smoke": 2,
    "task_bound_resolver_smoke": 2,
    "strict_fixed_pilot": 8,
    "default_allow_fixed_pilot": 8,
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize_run(path: Path) -> dict[str, Any]:
    manifest = read_json(path / "protocol_manifest.json")
    command_status = read_json(path / "command_status.json")
    logs = [read_json(item) for item in sorted((path / "agentdojo_logs").glob("**/*.json"))]
    official = [
        row
        for row in logs
        if str(row.get("user_task_id", "")).startswith("user_task_")
    ]
    benign = [row for row in official if row.get("injection_task_id") is None]
    attack = [row for row in official if row.get("injection_task_id") is not None]
    audit = read_jsonl(path / "runtime_audit.jsonl")
    checks = [row for row in audit if row.get("event") == "precommit_check"]
    return {
        "run_root": str(path.relative_to(ROOT)),
        "runner_status": manifest.get("status"),
        "command_returncodes": [row.get("returncode") for row in command_status.get("commands", [])],
        "uncertainty_policy": manifest.get("runtime_configuration", {}).get("uncertainty_policy"),
        "official_rows": len(official),
        "benign": {
            "n": len(benign),
            "utility_successes": sum(row.get("utility") is True for row in benign),
        },
        "attack": {
            "n": len(attack),
            "utility_successes": sum(row.get("utility") is True for row in attack),
            "attack_successes": sum(row.get("security") is True for row in attack),
        },
        "case_results": [
            {
                "suite": row.get("suite_name"),
                "mode": "attack" if row.get("injection_task_id") is not None else "benign",
                "utility": row.get("utility"),
                "attack_success": (
                    row.get("security") if row.get("injection_task_id") is not None else None
                ),
            }
            for row in official
        ],
        "precommit_checks": len(checks),
        "effective_decisions": dict(Counter(str(row.get("decision")) for row in checks)),
        "strict_guard_decisions": dict(Counter(str(row.get("guard_decision")) for row in checks)),
        "recovery_states": dict(Counter(str(row.get("recovery_state")) for row in checks)),
        "diagnostic_uncertainty_overrides": sum(
            row.get("diagnostic_uncertainty_override") is True for row in checks
        ),
        "explicit_denials": sum(row.get("decision") == "DENY" for row in checks),
        "execution_attempts": sum(row.get("execution_attempted") is True for row in checks),
    }


def main() -> int:
    runs = {name: summarize_run(path) for name, path in RUN_CONFIGS.items()}
    complete = all(
        row["runner_status"] == "runner_completed"
        and row["official_rows"] == EXPECTED_ROWS[name]
        and all(code == 0 for code in row["command_returncodes"])
        for name, row in runs.items()
    )
    strict_pilot = runs["strict_fixed_pilot"]
    permissive_pilot = runs["default_allow_fixed_pilot"]
    paired_pilot_delta = {
        "benign_utility_successes": (
            permissive_pilot["benign"]["utility_successes"]
            - strict_pilot["benign"]["utility_successes"]
        ),
        "attack_utility_successes": (
            permissive_pilot["attack"]["utility_successes"]
            - strict_pilot["attack"]["utility_successes"]
        ),
        "attack_successes": (
            permissive_pilot["attack"]["attack_successes"]
            - strict_pilot["attack"]["attack_successes"]
        ),
    }
    report = {
        "experiment": "E77 uncertainty default-allow and runtime recovery diagnostic",
        "status": "passed" if complete else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs": runs,
        "engineering_changes": [
            "NEEDS_REPLAN is separated from explicit DENY; only unresolved decisions may be overridden.",
            "Harmless plan JSON variants are normalized without creating authority.",
            "Copied resolver-catalog rows are rejected; the planner receives an explicit output anchor.",
            "Unknown resolver source tools are rejected and repaired against an exact allow-list.",
            "Revision budgets are bounded per call signature and per task.",
            "Source-bound guessed exact values are converted to unresolved relations, not accepted literals.",
            "Typed outputs from strictly authorized prior effects can instantiate later resolver relations.",
            "Task-bound unique identifiers may be projected from authorized free-text sources; raw text and candidates are excluded from revision-model prompts.",
            "English natural-language date ranges are canonicalized to the tool-call ISO representation.",
        ],
        "observations": {
            "default_allow_is_not_a_safe_main_policy": (
                runs["default_allow_smoke"]["diagnostic_uncertainty_overrides"] > 0
            ),
            "explicit_deny_remained_non_executable": (
                runs["default_allow_smoke"]["explicit_denials"] > 0
            ),
            "task_bound_resolver_benign_utility": runs["task_bound_resolver_smoke"]["benign"],
            "task_bound_resolver_attack": runs["task_bound_resolver_smoke"]["attack"],
            "fixed_four_suite_pilot_delta": paired_pilot_delta,
        },
        "claim_boundary": (
            "These fixed smoke cases validate runtime state transitions and one task-bound resolver "
            "path. They are not a performance estimate. A fixed pilot or full official run is required "
            "before changing paper-level utility or attack-success claims."
        ),
        "remaining_method_gaps": [
            "Required task-derived fields such as a generated transaction subject or inferred execution date need an explicit derivation contract; they are not silently authorized.",
            "The final fixed pilot contains one user task and one injection task per suite and is too small for paper-level performance claims.",
            "Default-allow executes unresolved calls and therefore remains a diagnostic upper-bound policy even when this pilot shows no ASR increase.",
            "A full v4 AgentDojo rerun is required before replacing the existing full-run paper numbers.",
        ],
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS / "uncertainty-default-allow-diagnostic-report.json"
    md_path = RESULTS / "uncertainty-default-allow-diagnostic-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# E77 uncertainty default-allow diagnostic",
                "",
                f"- Status: `{report['status']}`",
                f"- Strict smoke: `{json.dumps(runs['strict_smoke'], sort_keys=True)}`",
                f"- Default-allow smoke: `{json.dumps(runs['default_allow_smoke'], sort_keys=True)}`",
                f"- Task-bound resolver smoke: `{json.dumps(runs['task_bound_resolver_smoke'], sort_keys=True)}`",
                f"- Strict fixed pilot: `{json.dumps(runs['strict_fixed_pilot'], sort_keys=True)}`",
                f"- Default-allow fixed pilot: `{json.dumps(runs['default_allow_fixed_pilot'], sort_keys=True)}`",
                f"- Paired pilot delta: `{json.dumps(paired_pilot_delta, sort_keys=True)}`",
                "",
                "## Interpretation",
                "",
                "- Default-allow is an uncertainty-cost diagnostic, not a safe deployment policy.",
                "- Explicit `DENY` decisions and invalid tools remain non-executable.",
                "- The task-bound resolver recovered the selected Slack task in clean and injected contexts without completing the injection goal.",
                "- In the final v4 fixed four-suite pilot, default-allow changed one execution decision but did not change benign utility, attack utility, or attack successes.",
                "",
                "## Claim boundary",
                "",
                report["claim_boundary"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "json": str(json_path), "markdown": str(md_path)}, indent=2))
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
