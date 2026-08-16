#!/usr/bin/env python3
"""Run E77 on the ten attacks that succeeded against E76."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
MODULE = "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.agentdojo_e77_runtime_patch"
CASES = (
    ("banking", "user_task_11", "injection_task_4"),
    ("slack", "user_task_16", "injection_task_3"),
    ("slack", "user_task_17", "injection_task_1"),
    ("slack", "user_task_17", "injection_task_3"),
    ("slack", "user_task_2", "injection_task_2"),
    ("slack", "user_task_20", "injection_task_3"),
    ("slack", "user_task_3", "injection_task_3"),
    ("travel", "user_task_19", "injection_task_4"),
    ("travel", "user_task_6", "injection_task_4"),
    ("workspace", "user_task_18", "injection_task_3"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logdir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", default="18080")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = {**os.environ, "LOCAL_LLM_PORT": args.port, "E77_AGENT_MAX_TOKENS": "4096"}
    commands = []
    for suite, user_task, injection_task in CASES:
        command = [
            str(PYTHON), "-m", "agentdojo.scripts.benchmark",
            "--model", "LOCAL", "--benchmark-version", "v1.1.2",
            "--suite", suite, "--tool-delimiter", "user",
            "--logdir", str(args.logdir), "--attack", "important_instructions",
            "--module-to-load", MODULE,
            "--user-task", user_task, "--injection-task", injection_task,
            "--force-rerun",
        ]
        completed = subprocess.run(command, text=True, capture_output=True, env=env)
        combined = completed.stdout + "\n" + completed.stderr
        commands.append(
            {
                "suite": suite,
                "user_task": user_task,
                "injection_task": injection_task,
                "returncode": completed.returncode,
                "server_400_error": "400 Bad Request" in combined,
                "server_500_error": "500 Internal Server Error" in combined,
                "context_length_exceeded": "context_length_exceeded" in combined,
                "stdout_tail": completed.stdout[-1600:],
                "stderr_tail": completed.stderr[-1600:],
            }
        )
    clean = all(
        row["returncode"] == 0 and not row["server_400_error"] and not row["server_500_error"]
        and not row["context_length_exceeded"] for row in commands
    )
    report = {
        "status": "passed" if clean else "failed",
        "scope": "E77 targeted replay of ten E76 successful attacks",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "logdir": str(args.logdir.resolve()),
        "commands": commands,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "n_cases": len(commands), "output": str(args.output)}, indent=2))
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
