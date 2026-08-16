#!/usr/bin/env python3
"""Run the frozen attack-development manifest with no guard and DeepSeek."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "paper").is_dir() and (parent / "experiments").is_dir()
)
MANIFEST = (
    ROOT / "experiments/intent-bound-runtime-guard/evaluation/"
    "effect-difference-runtime-guard/benign97_threeway_attack_smoke_manifest_2026-08-08.json"
)
RUN_ROOT = (
    ROOT / "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard/"
    "deepseek-development-no-guard-20260808"
)
PYTHON = (
    ROOT / "experiments/unified-agent-security-baselines/runs/"
    "unified-agent-security-comparison/agentdojo-env/bin/python"
)
MODULE = "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75"
SHARED_STATUS = ROOT / "analysis/results/e75_agentdojo_official_live_run_status.json"


def main() -> int:
    if RUN_ROOT.exists():
        raise FileExistsError(f"refusing to overwrite {RUN_ROOT}")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    groups: dict[tuple[str, str], list[str]] = {}
    for row in data["cases"]:
        groups.setdefault((row["suite"], row["injection_task_id"]), []).append(
            row["user_task_id"]
        )
    RUN_ROOT.mkdir(parents=True)
    statuses = []
    for (suite, injection_id), task_ids in sorted(groups.items()):
        logdir = RUN_ROOT / f"{suite}-{injection_id}" / "agentdojo_logs"
        command = [
            str(PYTHON), "-m", MODULE,
            "--mode", "official-live-run",
            "--agentdojo-version", "v1.1.2",
            "--live-method", "no_guard",
            "--live-suites", suite,
            "--live-modes", "attack",
            "--live-logdir", str(logdir),
            "--live-injection-task", injection_id,
            "--local-llm-port", "18087",
        ]
        for task_id in sorted(task_ids):
            command.extend(["--live-user-task", task_id])
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env={**os.environ, "CUDA_VISIBLE_DEVICES": ""},
            text=True,
            capture_output=True,
        )
        status = json.loads(SHARED_STATUS.read_text(encoding="utf-8"))
        status["subprocess_returncode"] = completed.returncode
        status["shared_status_collision"] = status.get("logdir") != str(logdir)
        status_path = RUN_ROOT / f"command_status.{suite}-{injection_id}.json"
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
        (RUN_ROOT / f"stdout.{suite}-{injection_id}.log").write_text(completed.stdout)
        (RUN_ROOT / f"stderr.{suite}-{injection_id}.log").write_text(completed.stderr)
        statuses.append(status)
        if (
            completed.returncode != 0
            or status.get("status") != "passed"
            or status["shared_status_collision"]
        ):
            break
    passed = len(statuses) == len(groups) and all(
        row.get("status") == "passed"
        and row.get("subprocess_returncode") == 0
        and not row.get("shared_status_collision")
        for row in statuses
    )
    summary = {
        "status": "passed" if passed else "failed",
        "condition": "no_guard",
        "model": os.getenv("E77_LLM_MODEL", "unspecified"),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "n_manifest_cases": data["n_cases"],
        "n_groups_completed": len(statuses),
        "run_root": str(RUN_ROOT.relative_to(ROOT)),
    }
    (RUN_ROOT / "run_status.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
