#!/usr/bin/env python3
"""Queue the concrete-atom mechanism run after another local process."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/concrete-atom-authorizer-mechanism"
STATUS = RESULTS / "queue-status.json"
RUNNER = ROOT / "scripts/run_toolsandbox_concrete_atom_authorizer.py"


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def write_status(status: str, wait_pid: int, **extra: object) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "wait_pid": wait_pid,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    STATUS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int, required=True)
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    args = parser.parse_args()
    write_status("queued", args.wait_pid, queue_pid=os.getpid())
    while alive(args.wait_pid):
        time.sleep(args.poll_seconds)
    write_status("running", args.wait_pid, queue_pid=os.getpid())
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--mode", "full"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    write_status(
        "passed" if completed.returncode == 0 else "failed",
        args.wait_pid,
        queue_pid=os.getpid(),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
