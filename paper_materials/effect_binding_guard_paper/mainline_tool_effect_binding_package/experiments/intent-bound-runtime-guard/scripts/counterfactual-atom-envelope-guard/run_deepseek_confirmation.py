#!/usr/bin/env python3
"""Run resumable same-model AgentDojo confirmation conditions with DeepSeek."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "paper").is_dir() and (parent / "experiments").is_dir()
)
PYTHON = (
    ROOT
    / "experiments/unified-agent-security-baselines/runs/"
    "unified-agent-security-comparison/agentdojo-env/bin/python"
)
MODULE = "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75"
FREEZE_C1B = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/"
    "counterfactual-atom-envelope-guard/c1b_frozen_candidate_2026-08-08.json"
)
FREEZE_C1D = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/"
    "counterfactual-atom-envelope-guard/c1d_frozen_candidate_2026-08-08.json"
)
FREEZE_C1E = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/"
    "counterfactual-atom-envelope-guard/c1e_frozen_candidate_2026-08-08.json"
)
FREEZE_C1F = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/"
    "counterfactual-atom-envelope-guard/c1f_frozen_candidate_2026-08-08.json"
)
SHADOWS = {
    "c1b": ROOT / "code/shadow_atom_envelope_c1b",
    "c1d": ROOT / "code/shadow_atom_envelope_c1d",
    "c1e": ROOT / "code/shadow_atom_envelope_c1e",
    "c1f": ROOT / "code/shadow_atom_envelope_c1f",
}
BASELINE_METHODS = {
    "no_guard": ("no_guard", "local"),
    "repeat_user_prompt": ("repeat_user_prompt", "local-repeat_user_prompt"),
    "spotlighting": ("spotlighting", "local-spotlighting_with_delimiting"),
}
DESCRIPTORS = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)
RUNTIME_CATALOG = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
)
RELATION_CATALOG = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/"
    "registered_relation_catalog.json"
)
EXPECTED = {
    "benign": {"banking": 16, "slack": 21, "travel": 20, "workspace": 40},
    "attack": {"banking": 144, "slack": 105, "travel": 140, "workspace": 240},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--condition",
        choices=(
            "no_guard",
            "repeat_user_prompt",
            "spotlighting",
            "c1b",
            "c1d",
            "c1e",
            "c1f",
        ),
        required=True,
    )
    parser.add_argument("--mode", choices=("benign", "attack"), required=True)
    parser.add_argument("--rep", default="r1")
    parser.add_argument("--timeout-seconds", type=int, default=0)
    parser.add_argument("--parallel-suites", type=int, choices=(1, 2, 3, 4), default=1)
    parser.add_argument("--force-rerun", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_path(condition: str) -> Path:
    if condition == "c1b":
        return FREEZE_C1B
    if condition == "c1d":
        return FREEZE_C1D
    if condition == "c1e":
        return FREEZE_C1E
    if condition == "c1f":
        return FREEZE_C1F
    raise ValueError(f"condition has no frozen candidate: {condition}")


def verify_frozen_candidate(condition: str) -> dict[str, Any]:
    path = freeze_path(condition)
    data = json.loads(path.read_text(encoding="utf-8"))
    expected_status = {
        "c1b": "frozen_before_deepseek_confirmation",
        "c1d": "frozen_before_c1d_live_confirmation",
        "c1e": "frozen_before_c1e_live_regression",
        "c1f": "frozen_before_c1f_live_regression",
    }[condition]
    if data.get("status") != expected_status:
        raise RuntimeError(f"{condition} candidate is not frozen for confirmation")
    for item in data["source_artifacts"].values():
        path = ROOT / item["path"]
        if sha256(path) != item["sha256"]:
            raise RuntimeError(f"frozen artifact changed: {item['path']}")
    return data


def log_paths(logdir: Path, suite: str, mode: str, condition: str) -> list[Path]:
    if condition in SHADOWS:
        pipeline = "local-ours_e77_effect_diff_runtime"
    else:
        pipeline = BASELINE_METHODS[condition][1]
    root = logdir / pipeline
    if mode == "benign":
        return sorted((root / suite).glob("user_task_*/none/none.json"))
    return sorted((root / suite).glob("user_task_*/important_instructions/*.json"))


def summarize(paths: list[Path], mode: str) -> dict[str, Any]:
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    incomplete = sum(
        not isinstance(row.get("utility"), bool)
        or (mode == "attack" and not isinstance(row.get("security"), bool))
        for row in rows
    )
    return {
        "n": len(rows),
        "utility_successes": sum(bool(row.get("utility")) for row in rows),
        "attack_successes": (
            sum(bool(row.get("security")) for row in rows) if mode == "attack" else None
        ),
        "errors": sum(row.get("error") is not None for row in rows),
        "incomplete": incomplete,
    }


def run_suite(args: argparse.Namespace, run_root: Path, suite: str) -> tuple[str, dict[str, Any]]:
    suite_root = run_root / suite
    logdir = suite_root / "agentdojo_logs"
    existing = log_paths(logdir, suite, args.mode, args.condition)
    expected = EXPECTED[args.mode][suite]
    existing_metrics = summarize(existing, args.mode)
    if (
        len(existing) == expected
        and existing_metrics["errors"] == 0
        and existing_metrics["incomplete"] == 0
        and not args.force_rerun
    ):
        return suite, {
            "status": "resumed_complete",
            "expected": expected,
            "metrics": existing_metrics,
        }

    command = [
        str(PYTHON),
        "-m",
        MODULE,
        "--mode",
        "official-live-run",
        "--agentdojo-version",
        "v1.1.2",
        "--live-method",
        (
            "ours_e77_effect_diff_runtime"
            if args.condition in SHADOWS
            else BASELINE_METHODS[args.condition][0]
        ),
        "--live-suites",
        suite,
        "--live-modes",
        args.mode,
        "--live-logdir",
        str(logdir),
        "--local-llm-port",
        "18087",
        "--live-timeout-seconds",
        str(args.timeout_seconds),
    ]
    if args.force_rerun:
        command.append("--live-force-rerun")
    inherited_pythonpath = os.environ.get("PYTHONPATH", "")
    base_pythonpath = str(ROOT / "code")
    if inherited_pythonpath:
        base_pythonpath = f"{base_pythonpath}:{inherited_pythonpath}"
    env = {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": base_pythonpath,
    }
    if args.condition in SHADOWS:
        env.update(
            {
                "PYTHONPATH": f"{SHADOWS[args.condition]}:{ROOT / 'code'}",
                "E77_POLICY_VARIANT": "atom_control_taint_envelope",
                "E77_REGISTERED_DESCRIPTOR_JSONL": str(DESCRIPTORS),
                "E77_RUNTIME_CATALOG": str(RUNTIME_CATALOG),
                "E77_RELATION_CATALOG": str(RELATION_CATALOG),
                "E77_AUDIT_JSONL": str(suite_root / "runtime_audit.jsonl"),
                "E77_PLAN_CACHE": str(suite_root / "unused_plan_cache.json"),
                "E77_EXECUTION_DATE": "2026-08-02",
                "E77_UNCERTAINTY_POLICY": "allow_with_trail",
                "E75_LIVE_MODEL_NAME": "deepseek-v4-flash",
            }
        )
    started = datetime.now(timezone.utc).isoformat()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=args.timeout_seconds or None,
    )
    suite_root.mkdir(parents=True, exist_ok=True)
    (suite_root / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    (suite_root / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    paths = log_paths(logdir, suite, args.mode, args.condition)
    metrics = summarize(paths, args.mode)
    status = {
        "status": (
            "passed"
            if completed.returncode == 0
            and len(paths) == expected
            and metrics["errors"] == 0
            and metrics["incomplete"] == 0
            else "failed"
        ),
        "started_at": started,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "returncode": completed.returncode,
        "expected": expected,
        "metrics": metrics,
        "logdir": str(logdir.relative_to(ROOT)),
    }
    (suite_root / "status.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return suite, status


def main() -> int:
    args = parse_args()
    if not os.getenv("E77_LLM_API_KEY"):
        raise RuntimeError("E77_LLM_API_KEY must be supplied through the environment")
    frozen = verify_frozen_candidate(args.condition) if args.condition in SHADOWS else None
    run_root = (
        ROOT
        / "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard/"
        f"deepseek-confirmation-{args.condition}-{args.mode}-{args.rep}"
    )
    run_root.mkdir(parents=True, exist_ok=True)
    statuses: dict[str, Any] = {}

    suites = ("banking", "slack", "travel", "workspace")
    if args.parallel_suites == 1:
        for suite in suites:
            name, status = run_suite(args, run_root, suite)
            statuses[name] = status
            if status["status"] == "failed":
                break
    else:
        with ThreadPoolExecutor(max_workers=args.parallel_suites) as pool:
            futures = {
                pool.submit(run_suite, args, run_root, suite): suite for suite in suites
            }
            for future in as_completed(futures):
                name, status = future.result()
                statuses[name] = status
        statuses = {suite: statuses[suite] for suite in suites if suite in statuses}

    all_passed = len(statuses) == 4 and all(
        row["status"] in {"passed", "resumed_complete"} for row in statuses.values()
    )
    totals = {
        "n": sum(row["metrics"]["n"] for row in statuses.values()),
        "utility_successes": sum(
            row["metrics"]["utility_successes"] for row in statuses.values()
        ),
        "attack_successes": (
            sum(row["metrics"]["attack_successes"] for row in statuses.values())
            if args.mode == "attack"
            else None
        ),
        "errors": sum(row["metrics"]["errors"] for row in statuses.values()),
    }
    report = {
        "status": "passed" if all_passed else "failed",
        "condition": args.condition,
        "mode": args.mode,
        "rep": args.rep,
        "model": os.getenv("E77_LLM_MODEL", "unspecified"),
        "base_url": os.getenv("E77_LLM_BASE_URL", "unspecified"),
        "expected_total": sum(EXPECTED[args.mode].values()),
        "metrics": totals,
        "suite_statuses": statuses,
        "frozen_candidate": (
            str(freeze_path(args.condition).relative_to(ROOT)) if frozen is not None else None
        ),
        "claim_boundary": (
            "Official AgentDojo v1.1.2 same-model confirmation logs. Security is "
            "the official injection-task success indicator, so attack_successes "
            "counts rows with security=true."
        ),
    }
    (run_root / "confirmation_status.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
