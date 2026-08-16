#!/usr/bin/env python3
"""Audit the public AgentLAB Task-Injection artifact and run an offline smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "runs/e79_external_benchmarks/AgentLAB"
TASK_INJECTION = REPO / "Task-Injection/agentdojo"
SOURCE = TASK_INJECTION / "src"
RESULTS = ROOT / "analysis/results"
EXPECTED_REVISION = "36f58e60c36bbd6d5b8e61d50d7db7d9ea7258d7"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()


def checked_in_pair_inventory() -> dict[str, Any]:
    rows_by_model_suite: dict[str, dict[str, set[tuple[str, str]]]] = {}
    row_counts: Counter[tuple[str, str]] = Counter()
    files = sorted((TASK_INJECTION / "res/long_horizon").glob("*/*/v1.2.1/pipeline_results.jsonl"))
    malformed = 0
    for path in files:
        suite = path.parent.parent.name
        model = path.parent.parent.parent.name
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            row_counts[(model, suite)] += 1
            rows_by_model_suite.setdefault(model, {}).setdefault(suite, set()).add(
                (str(row.get("user_task_id", "")), str(row.get("injection_task_id", "")))
            )
    complete_comparisons = {}
    for model, suites in sorted(rows_by_model_suite.items()):
        if set(suites) != {"workspace", "travel", "banking", "slack"}:
            continue
        pair_counts = {suite: len(pairs) for suite, pairs in sorted(suites.items())}
        complete_comparisons[model] = {
            "pair_counts": pair_counts,
            "total_unique_pairs": sum(pair_counts.values()),
            "jsonl_rows": {
                suite: row_counts[(model, suite)] for suite in sorted(suites)
            },
        }
    return {
        "result_files": len(files),
        "complete_four_suite_comparison_roots": complete_comparisons,
        "malformed_jsonl_rows": malformed,
    }


def run_native_smoke() -> dict[str, Any]:
    sys.path.insert(0, str(SOURCE))
    from agentdojo.agent_pipeline.ground_truth_pipeline import GroundTruthPipeline  # noqa: PLC0415
    from agentdojo.task_suite.load_suites import get_suite  # noqa: PLC0415

    suites = {}
    for suite_name in ("workspace", "travel", "banking", "slack"):
        suite = get_suite("v1.2.1", suite_name)
        suites[suite_name] = {
            "user_tasks": len(suite.user_tasks),
            "injection_tasks": len(suite.injection_tasks),
            "full_pairs": len(suite.user_tasks) * len(suite.injection_tasks),
        }
    banking = get_suite("v1.2.1", "banking")
    task = banking.get_user_task_by_id("user_task_0")
    utility, security = banking.run_task_with_pipeline(GroundTruthPipeline(task), task, None, {})
    return {
        "suite_inventory": suites,
        "total_user_tasks": sum(row["user_tasks"] for row in suites.values()),
        "total_injection_tasks": sum(row["injection_tasks"] for row in suites.values()),
        "full_cartesian_pairs": sum(row["full_pairs"] for row in suites.values()),
        "offline_ground_truth_smoke": {
            "suite": "banking",
            "user_task": "user_task_0",
            "utility": bool(utility),
            "security_field_value": bool(security),
            "note": "With no injection task, this is an environment/evaluator smoke, not an attack result.",
        },
    }


def run() -> dict[str, Any]:
    revision = git("rev-parse", "HEAD")
    worktree = git("status", "--porcelain")
    native = run_native_smoke()
    pair_inventory = checked_in_pair_inventory()
    passed = (
        revision == EXPECTED_REVISION
        and not worktree
        and native["total_user_tasks"] == 97
        and native["total_injection_tasks"] == 35
        and native["full_cartesian_pairs"] == 949
        and native["offline_ground_truth_smoke"]["utility"]
        and native["offline_ground_truth_smoke"]["security_field_value"]
        and pair_inventory["malformed_jsonl_rows"] == 0
        and pair_inventory["complete_four_suite_comparison_roots"].get("gpt-4o-backip", {}).get("total_unique_pairs") == 303
    )
    return {
        "experiment": "E79",
        "audit_type": "agentlab_task_injection_source_and_offline_smoke",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed_with_protocol_blockers" if passed else "failed",
        "source": {
            "repository": "https://github.com/TanqiuJiang/AgentLAB",
            "revision": revision,
            "worktree_clean": not worktree,
            "task_injection_agentdojo_version": "0.1.34",
            "suite_version": "v1.2.1",
        },
        "native_inventory_and_smoke": native,
        "checked_in_long_horizon_results": pair_inventory,
        "evaluator_semantics": {
            "planner": "deterministic task ground_truth pipeline for Task-Injection evaluation",
            "judge": "deterministic environment/output/trace utility and injection-goal predicates",
            "security_true_semantics": "injection goal executed; this is attack success, not defense success",
        },
        "protocol_blockers": [
            "The README names gpt-5.1 for attack generation while code paths default or hard-code gpt-5-mini.",
            "The exact non-banking 303-pair selector and ordering command is not committed.",
            "Adaptive rounds reuse prior successful attacks and skip prior successes, so shell-loop rounds are not independent trials.",
            "The attacker requires OpenAI Responses structured parsing (and Batch/File APIs in batch mode); chat-completions-only local servers are insufficient.",
            "Some local victim setup probes port 8000 directly instead of uniformly honoring LOCAL_LLM_PORT.",
        ],
        "next_gate": (
            "Freeze an explicit pair manifest, attack-generator checkpoint, rewrite budget, ordering, memory-reset policy, "
            "seed, and error semantics; then run no-guard and guarded victims on identical saved attacks."
        ),
        "claim_boundary": (
            "The public Task-Injection source, deterministic task/evaluator path, and one offline ground-truth task ran locally. "
            "No attack was generated, no victim LLM was run, and no AgentLAB ASR or utility result is claimed."
        ),
    }


def main() -> int:
    report = run()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e79_agentlab_source_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    native = report["native_inventory_and_smoke"]
    lines = [
        "# E79 AgentLAB Task-Injection Source Audit",
        "",
        f"Status: `{report['status']}`.",
        "",
        f"- Revision: `{report['source']['revision']}`.",
        f"- Inventory: {native['total_user_tasks']} user tasks, {native['total_injection_tasks']} injection tasks, {native['full_cartesian_pairs']} full Cartesian pairs.",
        "- The offline banking ground-truth pipeline and deterministic evaluator completed successfully.",
        "- In this artifact, `security=True` means the injection goal executed and therefore counts as attack success.",
        "",
        "## Protocol Blockers",
        "",
        *[f"- {item}" for item in report["protocol_blockers"]],
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
    ]
    (RESULTS / "e79_agentlab_source_audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed_with_protocol_blockers" else 1


if __name__ == "__main__":
    raise SystemExit(main())
