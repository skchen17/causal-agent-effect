#!/usr/bin/env python3
"""Build an evaluation-only authority sidecar from AgentDojo ground truth."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from enum import Enum
from pathlib import Path
from typing import Any

from agentdojo.task_suite.load_suites import get_suite


def find_root(path: Path) -> Path:
    for candidate in (Path.cwd().resolve(), *path.resolve().parents):
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return normalize(value.value)
    if isinstance(value, dict):
        return {str(key): normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def build(root: Path, output: Path) -> dict[str, Any]:
    manifests_path = (
        root
        / "experiments/human-authority-and-causal-validation/evaluation/"
        "authority-manifest-human-review/runtime_ready_trusted_manifests.jsonl"
    )
    reviewed_tasks = {
        (str(row["suite"]), str(row["user_task_id"]))
        for row in read_jsonl(manifests_path)
    }
    if len(reviewed_tasks) != 26:
        raise ValueError(f"expected 26 reviewed tasks, found {len(reviewed_tasks)}")

    rows = []
    for suite_name, user_task_id in sorted(reviewed_tasks):
        suite = get_suite("v1.1.2", suite_name)
        task = suite.user_tasks[user_task_id]
        environment = task.init_environment(
            suite.load_and_inject_default_environment({})
        )
        calls = [
            {
                "tool_name": call.function,
                "arguments": normalize(call.args),
            }
            for call in task.ground_truth(environment)
        ]
        source = inspect.getsource(task.ground_truth)
        rows.append(
            {
                "agentdojo_version": "v1.1.2",
                "suite": suite_name,
                "user_task_id": user_task_id,
                "original_task_sha256": hashlib.sha256(
                    task.PROMPT.encode()
                ).hexdigest(),
                "ground_truth_source_sha256": hashlib.sha256(
                    source.encode()
                ).hexdigest(),
                "ground_truth_calls": calls,
                "contains_attack_goal": False,
                "contains_attack_label": False,
                "contains_model_trace": False,
                "evaluation_only": True,
            }
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "status": "passed",
        "agentdojo_version": "v1.1.2",
        "task_count": len(rows),
        "call_count": sum(len(row["ground_truth_calls"]) for row in rows),
        "contains_attack_material": False,
        "contains_model_traces": False,
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "claim_boundary": (
            "The sidecar is an evaluation-only exact authority oracle derived "
            "from official AgentDojo user-task ground-truth calls. It is not "
            "deployable authority and may exclude valid alternative plans."
        ),
    }
    (output.parent / "official-ground-truth-authority-build.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = (args.root or find_root(Path(__file__))).resolve()
    output = args.output or (
        root
        / "experiments/security-analysis-ablation-and-overhead/results/"
        "joint-effect-authority-diagnostic/official-ground-truth-authority.jsonl"
    )
    print(json.dumps(build(root, output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
