#!/usr/bin/env python3
"""Measure the fixed guard's upper-bound coverage over all AgentDojo tasks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from agentdojo.task_suite.load_suites import get_suite


def find_root(path: Path) -> Path:
    for candidate in (Path.cwd().resolve(), *path.resolve().parents):
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
CATALOG = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
)
PROJECTIONS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "causal-effect-projection-validation-2/trusted_security_effect_projections.jsonl"
)
MANIFESTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "authority-manifest-human-review/semantic-interface-v3/trusted_manifests.jsonl"
)
OUTPUT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "full-benign-authority-coverage"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    projections = {
        (row["suite"], row["tool_name"]): row
        for row in read_jsonl(PROJECTIONS)
    }
    manifests = {
        (row["suite"], row["user_task_id"]): row
        for row in read_jsonl(MANIFESTS)
    }
    counts = Counter()
    rows = []
    for suite_name in ("banking", "slack", "travel", "workspace"):
        suite = get_suite("v1.1.2", suite_name)
        for task_id, task in suite.user_tasks.items():
            environment = task.init_environment(
                suite.load_and_inject_default_environment({})
            )
            effectful_tools = []
            for call in task.ground_truth(environment):
                tool = catalog["suites"][suite_name].get(call.function, {})
                effect_rows = projections.get(
                    (suite_name, call.function),
                    {},
                ).get("security_effect_projections", [])
                observation_only = bool(effect_rows) and all(
                    row.get("operation") == "read" for row in effect_rows
                )
                if tool.get("effectful_or_external") and not observation_only:
                    effectful_tools.append(call.function)
            manifest = manifests.get((suite_name, task_id))
            authority_tools = set((manifest or {}).get("authority_tools", {}))
            required_tools = set(effectful_tools)
            covered = not required_tools or required_tools <= authority_tools
            category = (
                "pure_observation"
                if not required_tools
                else "effectful_manifest_covered"
                if covered
                else "effectful_uncovered"
            )
            counts["n_tasks"] += 1
            counts[category] += 1
            counts["ground_truth_chain_covered"] += int(covered)
            rows.append(
                {
                    "suite": suite_name,
                    "user_task_id": task_id,
                    "category": category,
                    "effectful_tools": sorted(required_tools),
                    "manifest_available": manifest is not None,
                    "manifest_authority_tools": sorted(authority_tools),
                    "ground_truth_chain_covered": covered,
                }
            )
    report = {
        "experiment": "full_benign_authority_coverage_audit",
        "status": "passed",
        "agentdojo_version": "v1.1.2",
        "n_tasks": counts["n_tasks"],
        "pure_observation_tasks": counts["pure_observation"],
        "effectful_manifest_covered_tasks": counts[
            "effectful_manifest_covered"
        ],
        "effectful_uncovered_tasks": counts["effectful_uncovered"],
        "ground_truth_chain_covered_tasks": counts[
            "ground_truth_chain_covered"
        ],
        "coverage_upper_bound": (
            counts["ground_truth_chain_covered"] / counts["n_tasks"]
        ),
        "authority_manifest_count": len(manifests),
        "uses_official_ground_truth_only_for_post_hoc_scoring": True,
        "runtime_uses_official_ground_truth": False,
        "claim_boundary": (
            "This is a post-hoc interface coverage upper bound over official "
            "call chains, not observed model utility. Official call chains are "
            "not exposed to the runtime or authority manifests."
        ),
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "task-coverage.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (OUTPUT / "coverage-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "coverage-report.md").write_text(
        "\n".join(
            [
                "# Full Benign Authority Coverage Audit",
                "",
                f"- Official tasks: `{report['n_tasks']}`",
                f"- Pure observation: `{report['pure_observation_tasks']}`",
                (
                    "- Effectful and manifest-covered: "
                    f"`{report['effectful_manifest_covered_tasks']}`"
                ),
                f"- Effectful and uncovered: `{report['effectful_uncovered_tasks']}`",
                (
                    "- Covered official call chains: "
                    f"`{report['ground_truth_chain_covered_tasks']}/{report['n_tasks']}`"
                ),
                "",
                report["claim_boundary"],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
