#!/usr/bin/env python3
"""Run the strict paper and artifact finalization pipeline after frozen runs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
REPORT = PAPER / "reproduction/finalization_report.json"
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
PAPERSPINE = CODEX_HOME / "skills/paper-spine/scripts"


COMMANDS = [
    [str(PYTHON), "scripts/run_toolsandbox_concrete_atom_authorizer.py", "--mode", "full"],
    [str(PYTHON), "paper/current-usenix/reproduction/extract_sanitized_fixed_support.py"],
    [str(PYTHON), "paper/current-usenix/reproduction/export_final_case_outcomes.py"],
    [str(PYTHON), "paper/current-usenix/reproduction/generate_final_result_section.py"],
    [str(PYTHON), "scripts/reproduce_usenix_main.py"],
    [str(PYTHON), "paper/current-usenix/reproduction/generate_final_readiness_and_review.py"],
    ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-cd", "paper/current-usenix/main.tex"],
    [str(PYTHON), "paper/current-usenix/reproduction/check_page_budget.py"],
    [str(PYTHON), "paper/current-usenix/reproduction/audit_references.py"],
    [str(PYTHON), "paper/current-usenix/reproduction/audit_submission_sources.py"],
    [
        str(PYTHON),
        str(PAPERSPINE / "latex_guard.py"),
        "paper/current-usenix/main.tex",
        "--markdown",
    ],
    [
        str(PYTHON),
        str(PAPERSPINE / "artifact_check.py"),
        "paper/writing-workspace",
        "--markdown",
        "--write",
    ],
    [
        str(PYTHON),
        "-m",
        "pytest",
        "shared/compatibility/tests/tests/test_usenix_main_reproduction.py",
        "shared/compatibility/tests/tests/test_usenix27_artifact_manifest.py",
        "shared/compatibility/tests/tests/test_render_usenix_final_tables.py",
        "shared/compatibility/tests/tests/test_generate_final_readiness_and_review.py",
        "shared/compatibility/tests/tests/test_usenix_heldout_runner.py",
        "shared/compatibility/tests/tests/test_usenix_long_run_finalizers.py",
        "shared/compatibility/tests/tests/test_e79_agentlab_saved_transfer_runner.py",
        "shared/compatibility/tests/tests/test_c1f_closed_loop_four_view_extension.py",
        "shared/compatibility/tests/tests/test_c1f_raw_field_attribution.py",
        "shared/compatibility/tests/tests/test_current_c1f_bounded_adaptive.py",
        "shared/compatibility/tests/tests/test_toolsandbox_concrete_atom_authorizer.py",
        "-q",
    ],
    [str(PYTHON), "paper/current-usenix/artifact/build_manifest.py"],
    [str(PYTHON), "paper/current-usenix/artifact/build_anonymous_package.py"],
]


def write_report(status: str, rows: list[dict], error: str | None = None) -> None:
    payload = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "commands": rows,
        "error": error,
    }
    REPORT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int)
    args = parser.parse_args()
    while args.wait_pid and Path(f"/proc/{args.wait_pid}").exists():
        time.sleep(60)
    rows = []
    write_report("running", rows)
    for command in COMMANDS:
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        row = {
            "command": command,
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-8000:],
            "stderr_tail": completed.stderr[-8000:],
        }
        rows.append(row)
        if completed.returncode != 0:
            write_report("failed", rows, f"command failed: {command}")
            return completed.returncode or 1
        write_report("running", rows)
    write_report("passed", rows)
    print(json.dumps({"status": "passed", "commands": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
