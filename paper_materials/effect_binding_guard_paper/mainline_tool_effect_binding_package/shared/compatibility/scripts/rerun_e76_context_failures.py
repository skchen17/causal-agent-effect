#!/usr/bin/env python3
"""Rerun the six E76 workspace cases that exceeded the 65K context."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
MODULE = "src.experiments.effect_binding_guard.e76_llm_descriptor_agentdojo_runtime.agentdojo_llm_descriptor_runtime_patch"
CASES = (
    ("benign", "user_task_29", None),
    ("attack", "user_task_19", "injection_task_5"),
    ("attack", "user_task_29", "injection_task_1"),
    ("attack", "user_task_29", "injection_task_3"),
    ("attack", "user_task_32", "injection_task_0"),
    ("attack", "user_task_32", "injection_task_3"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logdir", type=Path, required=True)
    parser.add_argument("--port", default="18080")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = {**os.environ, "LOCAL_LLM_PORT": args.port, "E76_AGENT_MAX_TOKENS": "4096"}
    rows = []
    for mode, user_task, injection_task in CASES:
        command = [
            str(PYTHON),
            "-m",
            "agentdojo.scripts.benchmark",
            "--model",
            "LOCAL",
            "--benchmark-version",
            "v1.1.2",
            "--suite",
            "workspace",
            "--tool-delimiter",
            "user",
            "--logdir",
            str(args.logdir),
            "--module-to-load",
            MODULE,
            "--user-task",
            user_task,
            "--force-rerun",
        ]
        if mode == "attack":
            command.extend(["--attack", "important_instructions", "--injection-task", str(injection_task)])
        completed = subprocess.run(command, text=True, capture_output=True, env=env)
        combined = f"{completed.stdout}\n{completed.stderr}"
        rows.append(
            {
                "suite": "workspace",
                "mode": mode,
                "user_task": user_task,
                "injection_task": injection_task,
                "returncode": completed.returncode,
                "server_400_error": "400 Bad Request" in combined,
                "server_500_error": "500 Internal Server Error" in combined,
                "context_length_exceeded": "context_length_exceeded" in combined,
                "stdout_tail": completed.stdout[-2000:],
                "stderr_tail": completed.stderr[-2000:],
            }
        )
    clean = all(
        row["returncode"] == 0
        and not row["server_400_error"]
        and not row["server_500_error"]
        and not row["context_length_exceeded"]
        for row in rows
    )
    report = {
        "status": "passed" if clean else "failed",
        "method": "ours_llm_descriptor_runtime",
        "agentdojo_version": "v1.1.2",
        "scope": "targeted rerun of six 65K-context failure cases at 131K context",
        "logdir": str(args.logdir.resolve()),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "commands": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output), "n_cases": len(rows)}, indent=2))
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
