#!/usr/bin/env python3
"""Wait for the active paper finalizer, then run atom-vs-field attribution."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "paper/current-usenix").is_dir())
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
RESULT_DIR = ROOT / "experiments/security-analysis-ablation-and-overhead/results/atom-vs-field-semantic-attribution"
STATUS = RESULT_DIR / "queue-status.json"
TEST = ROOT / "shared/compatibility/tests/tests/test_atom_vs_field_semantic_attribution.py"
RUNNER = ROOT / "shared/compatibility/scripts/run_atom_vs_field_semantic_attribution.py"


def write(status: str, **extra) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat(), **extra}
    STATUS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int, required=True)
    args = parser.parse_args()
    write("queued", wait_pid=args.wait_pid)
    while Path(f"/proc/{args.wait_pid}").exists():
        time.sleep(60)
    commands = [
        [str(PYTHON), "-m", "pytest", str(TEST), "-q"],
        [str(PYTHON), str(RUNNER), "--mode", "full"],
    ]
    rows = []
    write("running", wait_pid=args.wait_pid, commands=rows)
    for command in commands:
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        rows.append({"command": command, "returncode": completed.returncode, "stdout_tail": completed.stdout[-6000:], "stderr_tail": completed.stderr[-6000:]})
        if completed.returncode:
            write("failed", wait_pid=args.wait_pid, commands=rows)
            return completed.returncode
        write("running", wait_pid=args.wait_pid, commands=rows)
    write("passed", wait_pid=args.wait_pid, commands=rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
