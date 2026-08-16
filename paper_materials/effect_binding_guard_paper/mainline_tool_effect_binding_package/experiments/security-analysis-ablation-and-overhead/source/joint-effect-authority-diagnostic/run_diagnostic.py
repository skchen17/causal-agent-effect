#!/usr/bin/env python3
"""Run the fixed four-cell joint effect/authority diagnostic."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
COMPAT_CODE = ROOT / "shared/compatibility/code"
if str(COMPAT_CODE) not in sys.path:
    sys.path.insert(0, str(COMPAT_CODE))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagnostic import run  # noqa: E402


if __name__ == "__main__":
    builder = Path(__file__).resolve().parent / "build_official_ground_truth_authority.py"
    default_python = (
        ROOT
        / "experiments/unified-agent-security-baselines/runs/"
        "unified-agent-security-comparison/agentdojo-env/bin/python"
    )
    agentdojo_python = Path(os.getenv("AGENTDOJO_PYTHON", str(default_python)))
    if not agentdojo_python.exists():
        raise FileNotFoundError(
            "AgentDojo Python is unavailable; set AGENTDOJO_PYTHON to the "
            "benchmark environment interpreter"
        )
    subprocess.run(
        [
            str(agentdojo_python),
            str(builder),
            "--root",
            str(ROOT),
        ],
        check=True,
    )
    report = run(ROOT)
    print(
        json.dumps(
            {
                "status": report["status"],
                "common_support_case_count": report["common_support_case_count"],
                "factorial_deltas": report["factorial_deltas_on_common_support"],
            },
            indent=2,
            sort_keys=True,
        )
    )
