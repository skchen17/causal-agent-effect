#!/usr/bin/env python3
"""Build a payload-free mechanistic taxonomy of E77 AgentDojo outcomes."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def find_root(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if all((candidate / name).exists() for name in ("paper", "experiments", "shared")):
            return candidate
    raise RuntimeError("could not locate the package root")


ROOT = find_root(Path(__file__).resolve())
LOG_ROOT = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-context-repaired/agentdojo_logs/"
    "local-ours_e77_effect_diff_runtime"
)
STRICT_REPORT = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-context-repaired-report.json"
)
DESCRIPTORS = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)
if not DESCRIPTORS.exists():
    DESCRIPTORS = ROOT / "analysis/results/e77_registered_effect_diff_descriptors.jsonl"
RESULTS = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard"
)
LEGACY_RESULTS = ROOT / "analysis/results"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def has_replan_marker(content: Any) -> bool:
    rendered = content if isinstance(content, str) else json.dumps(content, sort_keys=True, default=str)
    return "NEEDS_REPLAN" in rendered


def official_paths(root: Path) -> list[Path]:
    paths = []
    for path in root.rglob("*.json"):
        parts = path.relative_to(root).parts
        if len(parts) == 4 and parts[1].startswith("user_task_"):
            paths.append(path)
    return sorted(paths)


def classify(payload: dict[str, Any], effectful_tools: set[str]) -> dict[str, Any]:
    messages = payload.get("messages") or []
    emitted = []
    executed = []
    feedback = []
    for message in messages:
        if message.get("role") == "assistant":
            emitted.extend(message.get("tool_calls") or [])
        elif message.get("role") == "tool" and isinstance(message.get("tool_call"), dict):
            call = message["tool_call"]
            executed.append(call)
            if has_replan_marker(message.get("content")):
                feedback.append(call)
    effectful_emitted = [call for call in emitted if call.get("function") in effectful_tools]
    effectful_feedback = [call for call in feedback if call.get("function") in effectful_tools]
    effectful_commits = [
        call for call in executed
        if call.get("function") in effectful_tools and call not in effectful_feedback
    ]
    terminal_unexecuted = max(0, len(emitted) - len(executed))
    if payload.get("error"):
        stratum = "runtime_or_model_error"
    elif not emitted:
        stratum = "no_structured_tool_call"
    elif terminal_unexecuted:
        stratum = "terminal_unexecuted_call"
    elif effectful_commits and effectful_feedback:
        stratum = "effectful_commit_and_replan_feedback"
    elif effectful_commits:
        stratum = "effectful_commit_without_replan_feedback"
    elif effectful_feedback:
        stratum = "effectful_calls_intercepted_no_effectful_commit"
    else:
        stratum = "read_only_or_unregistered_tool_trajectory"
    return {
        "stratum": stratum,
        "emitted_calls": len(emitted),
        "executed_tool_results": len(executed),
        "effectful_calls_emitted": len(effectful_emitted),
        "effectful_commits": len(effectful_commits),
        "replan_feedback_events": len(feedback),
        "effectful_replan_events": len(effectful_feedback),
        "terminal_unexecuted_calls": terminal_unexecuted,
    }


def build(
    log_root: Path = LOG_ROOT,
    *,
    strict_report_path: Path | None = STRICT_REPORT,
) -> dict[str, Any]:
    effectful_tools = {row["tool_name"] for row in read_jsonl(DESCRIPTORS) if row.get("registered")}
    paths = official_paths(log_root)
    if len(paths) != 726:
        raise RuntimeError(f"expected 726 official user-task paths, found {len(paths)}")
    rows = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        parts = path.relative_to(log_root).parts
        mode = "benign" if parts[-1] == "none.json" else "attack"
        trajectory = classify(payload, effectful_tools)
        key = "/".join(parts)
        rows.append({
            "case_hash": hashlib.sha256(key.encode()).hexdigest(),
            "suite": payload["suite_name"],
            "mode": mode,
            "utility": payload.get("utility") is True,
            "attack_success": payload.get("security") is True if mode == "attack" else None,
            **trajectory,
        })

    def group(source: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(source)
        successes = sum(row["utility"] for row in source)
        feedback_cases = [row for row in source if row["replan_feedback_events"]]
        return {
            "n": n,
            "utility_successes": successes,
            "utility_rate": successes / n if n else None,
            "cases_with_replan_feedback": len(feedback_cases),
            "utility_successes_with_replan_feedback": sum(row["utility"] for row in feedback_cases),
            "effectful_commits": sum(row["effectful_commits"] for row in source),
            "replan_feedback_events": sum(row["replan_feedback_events"] for row in source),
            "terminal_unexecuted_calls": sum(row["terminal_unexecuted_calls"] for row in source),
            "strata": dict(sorted(Counter(row["stratum"] for row in source).items())),
            "utility_failure_strata": dict(sorted(Counter(row["stratum"] for row in source if not row["utility"]).items())),
        }

    modes = {mode: group([row for row in rows if row["mode"] == mode]) for mode in ("benign", "attack")}
    suites = {
        suite: group([row for row in rows if row["suite"] == suite])
        for suite in sorted({row["suite"] for row in rows})
    }
    feedback = [row for row in rows if row["replan_feedback_events"]]
    no_feedback = [row for row in rows if not row["replan_feedback_events"]]
    attack_rows = [row for row in rows if row["mode"] == "attack"]
    strict_reconciliation = None
    if strict_report_path is not None:
        strict = json.loads(strict_report_path.read_text(encoding="utf-8"))
        metrics = strict.get("metrics") or {}
        expected = {
            "status": strict.get("status"),
            "official_cases": metrics.get("n_total"),
            "benign_cases": metrics.get("n_benign"),
            "benign_utility_successes": metrics.get("benign_utility_successes"),
            "attack_cases": metrics.get("n_attack"),
            "attack_utility_successes": metrics.get("attack_user_utility_successes"),
            "attack_successes": metrics.get("attack_successes"),
        }
        observed = {
            "status": "passed",
            "official_cases": len(rows),
            "benign_cases": modes["benign"]["n"],
            "benign_utility_successes": modes["benign"]["utility_successes"],
            "attack_cases": modes["attack"]["n"],
            "attack_utility_successes": modes["attack"]["utility_successes"],
            "attack_successes": sum(row["attack_success"] for row in attack_rows),
        }
        if expected != observed:
            raise RuntimeError(
                "failure-taxonomy rows do not reconcile with the strict finalizer: "
                f"expected={expected!r}, observed={observed!r}"
            )
        strict_reconciliation = {
            "passed": True,
            "strict_report": str(strict_report_path.relative_to(ROOT)),
            "metrics": observed,
        }
    report = {
        "experiment": "E77",
        "analysis_type": "payload_free_mechanistic_failure_taxonomy",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "official_cases": len(rows),
        "registered_effectful_tools": len(effectful_tools),
        "modes": modes,
        "suites": suites,
        "feedback_association": {
            "cases_with_feedback": len(feedback),
            "utility_successes_with_feedback": sum(row["utility"] for row in feedback),
            "utility_rate_with_feedback": sum(row["utility"] for row in feedback) / len(feedback) if feedback else None,
            "cases_without_feedback": len(no_feedback),
            "utility_successes_without_feedback": sum(row["utility"] for row in no_feedback),
            "utility_rate_without_feedback": sum(row["utility"] for row in no_feedback) / len(no_feedback) if no_feedback else None,
        },
        "security_check": {
            "attack_cases": len(attack_rows),
            "benchmark_attack_successes": sum(row["attack_success"] for row in attack_rows),
        },
        "strict_finalizer_reconciliation": strict_reconciliation,
        "row_schema": sorted(rows[0]),
        "row_artifact": (
            "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
            "failure-taxonomy-rows.jsonl"
        ),
        "contains_prompts_or_model_outputs": False,
        "claim_boundary": (
            "Strata describe observed trajectory mechanics and association with utility; they do not identify a unique causal root cause. "
            "No prompt, injection payload, task text, model response, or tool-result body is copied into this artifact."
        ),
    }
    rendered_rows = "".join(
        json.dumps(row, sort_keys=True) + "\n" for row in rows
    )
    RESULTS.mkdir(parents=True, exist_ok=True)
    LEGACY_RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "failure-taxonomy-rows.jsonl").write_text(
        rendered_rows, encoding="utf-8"
    )
    (LEGACY_RESULTS / "e77_failure_taxonomy_rows.jsonl").write_text(
        rendered_rows, encoding="utf-8"
    )
    return report


def write(report: dict[str, Any]) -> None:
    rendered_json = json.dumps(report, indent=2, sort_keys=True) + "\n"
    (RESULTS / "failure-taxonomy.json").write_text(rendered_json, encoding="utf-8")
    (LEGACY_RESULTS / "e77_failure_taxonomy.json").write_text(
        rendered_json, encoding="utf-8"
    )
    lines = [
        "# E77 Payload-Free Failure Taxonomy", "", f"Status: `{report['status']}`.", "",
        "| Mode | Cases | Utility | Cases with replan feedback | Replan events | Terminal unexecuted calls |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for mode, item in report["modes"].items():
        lines.append(
            f"| {mode} | {item['n']} | {item['utility_successes']}/{item['n']} ({item['utility_rate']:.3f}) | "
            f"{item['cases_with_replan_feedback']} | {item['replan_feedback_events']} | {item['terminal_unexecuted_calls']} |"
        )
    lines.extend(["", "## Utility-Failure Strata", ""])
    for mode, item in report["modes"].items():
        lines.append(f"- {mode}: `{json.dumps(item['utility_failure_strata'], sort_keys=True)}`")
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    rendered_md = "\n".join(lines)
    (RESULTS / "failure-taxonomy.md").write_text(rendered_md, encoding="utf-8")
    (LEGACY_RESULTS / "e77_failure_taxonomy.md").write_text(
        rendered_md, encoding="utf-8"
    )


def main() -> int:
    report = build()
    write(report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
