#!/usr/bin/env python3
"""Run four interleaved benign repetitions for matched DeepSeek conditions."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "paper").is_dir() and (parent / "experiments").is_dir()
)
RUNNER = Path(__file__).resolve().parent / "run_deepseek_confirmation.py"
OUT = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard"
ORDERS = (
    ("no_guard", "spotlighting", "c1f"),
    ("spotlighting", "c1f", "no_guard"),
    ("c1f", "no_guard", "spotlighting"),
    ("no_guard", "c1f", "spotlighting"),
)


def main() -> int:
    if not os.getenv("E77_LLM_API_KEY"):
        raise RuntimeError("E77_LLM_API_KEY is required")
    rows = []
    for index, order in enumerate(ORDERS, start=1):
        rep = f"matched-r{index}"
        for condition in order:
            command = [
                sys.executable,
                str(RUNNER),
                "--condition",
                condition,
                "--mode",
                "benign",
                "--rep",
                rep,
                "--parallel-suites",
                "4",
            ]
            completed = subprocess.run(command, cwd=ROOT, check=False)
            rows.append(
                {
                    "rep": rep,
                    "condition": condition,
                    "returncode": completed.returncode,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / "deepseek_benign_interleaved_run_status.json").write_text(
                json.dumps({"status": "running", "rows": rows}, indent=2) + "\n",
                encoding="utf-8",
            )
            if completed.returncode != 0:
                return completed.returncode
    (OUT / "deepseek_benign_interleaved_run_status.json").write_text(
        json.dumps({"status": "passed", "rows": rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
