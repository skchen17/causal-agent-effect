#!/usr/bin/env python3
"""Queue E88 smoke and gated full evaluation."""

from __future__ import annotations

import argparse
import json

from src.experiments.effect_binding_guard.e88_agentdojo_attack_dataset.staged_runner import execute_staged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int, default=0)
    parser.add_argument("--port", type=int, default=18086)
    args = parser.parse_args()
    status = execute_staged(args.port, args.wait_pid)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if status["status"] in {"passed", "stopped_after_smoke"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
