#!/usr/bin/env python3
"""Compatibility entrypoint for the Qwen3-32B E84 strong-baseline subset."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("run-e84-qwen9b-agentdojo-pilot.py")


if __name__ == "__main__":
    if "--model" not in sys.argv:
        sys.argv.extend(["--model", "qwen32"])
    if "--methods" not in sys.argv:
        sys.argv.extend(
            [
                "--methods",
                "no_guard,prompt_sandwiching,promptarmor_local,e84_reviewed_authority",
            ]
        )
    runpy.run_path(str(SCRIPT), run_name="__main__")
