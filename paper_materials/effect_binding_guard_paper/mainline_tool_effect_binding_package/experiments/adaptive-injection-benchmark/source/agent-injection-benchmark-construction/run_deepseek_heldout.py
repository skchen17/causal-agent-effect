"""Run the frozen 320-row public-family held-out set with DeepSeek."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75 import (
    official_live_method_config,
)

from .lock_usenix_heldout import MANIFEST, PROTOCOL, ROOT, read_jsonl


PYTHON = (
    ROOT
    / "experiments/unified-agent-security-baselines/runs/"
    "unified-agent-security-comparison/agentdojo-env/bin/python"
)
RUN_ROOT = (
    ROOT
    / "experiments/adaptive-injection-benchmark/runs/"
    "usenix-heldout-public-families/deepseek"
)
RESULT_ROOT = (
    ROOT
    / "experiments/adaptive-injection-benchmark/results/"
    "usenix-heldout-public-families"
)
SHADOW = ROOT / "code/shadow_atom_envelope_c1f"
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
FROZEN_C1F = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/"
    "counterfactual-atom-envelope-guard/c1f_frozen_candidate_2026-08-08.json"
)
METHOD_CONFIG = {
    "no_guard": ("no_guard", "local"),
    "spotlighting": ("spotlighting", "local-spotlighting_with_delimiting"),
    "c1f": ("ours_e77_effect_diff_runtime", "local-ours_e77_effect_diff_runtime"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_c1f() -> dict[str, str]:
    frozen = json.loads(FROZEN_C1F.read_text(encoding="utf-8"))
    if frozen.get("status") != "frozen_before_c1f_live_regression":
        raise RuntimeError("C1f is not in the expected frozen state")
    verified = {"freeze_manifest": sha256(FROZEN_C1F)}
    for name, artifact in frozen["source_artifacts"].items():
        path = ROOT / artifact["path"]
        observed = sha256(path)
        if observed != artifact["sha256"]:
            raise RuntimeError(f"frozen C1f artifact changed: {artifact['path']}")
        verified[name] = observed
    return verified


def evaluable_result(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        payload.get("error") is None
        and isinstance(payload.get("utility"), bool)
        and isinstance(payload.get("security"), bool)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--methods", nargs="+", choices=tuple(METHOD_CONFIG), default=list(METHOD_CONFIG))
    parser.add_argument("--parallel-groups", type=int, default=4, choices=(1, 2, 3, 4))
    return parser.parse_args()


def groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for row in rows:
        grouped[(row["suite"], row["attack_family"], row["injection_task_id"])].append(
            row["user_task_id"]
        )
    return [
        {
            "suite": key[0],
            "attack_family": key[1],
            "injection_task_id": key[2],
            "user_task_ids": sorted(set(user_ids)),
        }
        for key, user_ids in sorted(grouped.items())
    ]


def result_path(method: str, row: dict[str, Any]) -> Path:
    pipeline = METHOD_CONFIG[method][1]
    return (
        RUN_ROOT
        / method
        / pipeline
        / row["suite"]
        / row["user_task_id"]
        / row["attack_family"]
        / f'{row["injection_task_id"]}.json'
    )


def environment(method: str) -> dict[str, str]:
    live_method = METHOD_CONFIG[method][0]
    config = official_live_method_config(live_method)
    pythonpath = str(ROOT / "code")
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": pythonpath, **config.get("env", {})}
    if method == "c1f":
        env.update(
            {
                "PYTHONPATH": f"{SHADOW}:{ROOT / 'code'}",
                "E77_POLICY_VARIANT": "atom_control_taint_envelope",
                "E77_REGISTERED_DESCRIPTOR_JSONL": str(DESCRIPTORS),
                "E77_RUNTIME_CATALOG": str(RUNTIME_CATALOG),
                "E77_RELATION_CATALOG": str(RELATION_CATALOG),
                "E77_AUDIT_JSONL": str(RUN_ROOT / method / "runtime_audit.jsonl"),
                "E77_PLAN_CACHE": str(RUN_ROOT / method / "unused_plan_cache.json"),
                "E77_EXECUTION_DATE": "2026-08-02",
                "E77_UNCERTAINTY_POLICY": "allow_with_trail",
                "E75_LIVE_MODEL_NAME": "deepseek-v4-flash",
            }
        )
    return env


def run_group(method: str, group: dict[str, Any]) -> dict[str, Any]:
    expected_rows = [
        row
        for row in read_jsonl(MANIFEST)
        if row["suite"] == group["suite"]
        and row["attack_family"] == group["attack_family"]
        and row["injection_task_id"] == group["injection_task_id"]
        and row["user_task_id"] in group["user_task_ids"]
    ]
    expected_paths = [result_path(method, row) for row in expected_rows]
    if all(path.exists() and evaluable_result(path) for path in expected_paths):
        return {"status": "resumed_complete", "group": group, "n": len(expected_rows)}
    live_method = METHOD_CONFIG[method][0]
    config = official_live_method_config(live_method)
    command = [
        str(PYTHON),
        "-m",
        "agentdojo.scripts.benchmark",
        "--model",
        "LOCAL",
        "--benchmark-version",
        "v1.1.2",
        "--suite",
        group["suite"],
        "--tool-delimiter",
        "user",
        "--logdir",
        str(RUN_ROOT / method),
        "--attack",
        group["attack_family"],
    ]
    if any(path.exists() and not evaluable_result(path) for path in expected_paths):
        command.append("--force-rerun")
    if config.get("defense"):
        command.extend(["--defense", config["defense"]])
    for module in config.get("modules_to_load", []):
        command.extend(["--module-to-load", module])
    for user_task_id in group["user_task_ids"]:
        command.extend(["--user-task", user_task_id])
    command.extend(["--injection-task", group["injection_task_id"]])
    log_path = RUN_ROOT / method / "runner.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        completed = subprocess.run(command, cwd=ROOT, env=environment(method), stdout=handle, stderr=subprocess.STDOUT)
    observed = sum(result_path(method, row).exists() for row in expected_rows)
    return {
        "status": "passed" if completed.returncode == 0 and observed == len(expected_rows) else "failed",
        "group": group,
        "expected": len(expected_rows),
        "observed": observed,
        "returncode": completed.returncode,
    }


def summarize(method: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    outputs = []
    missing = []
    incomplete = []
    for row in rows:
        path = result_path(method, row)
        if not path.exists():
            missing.append(row["case_id"])
            continue
        output = json.loads(path.read_text(encoding="utf-8"))
        if (
            output.get("error") is not None
            or not isinstance(output.get("utility"), bool)
            or not isinstance(output.get("security"), bool)
        ):
            incomplete.append(row["case_id"])
        outputs.append((row, output))
    return {
        "method": method,
        "n": len(outputs),
        "expected": len(rows),
        "attack_successes": sum(output.get("security") is True for _, output in outputs),
        "utility_successes": sum(output.get("utility") is True for _, output in outputs),
        "errors": sum(output.get("error") is not None for _, output in outputs),
        "missing_case_ids": missing,
        "incomplete_case_ids": incomplete,
        "by_family": {
            family: {
                "n": sum(row["attack_family"] == family for row, _ in outputs),
                "attack_successes": sum(
                    row["attack_family"] == family and output.get("security") is True
                    for row, output in outputs
                ),
                "utility_successes": sum(
                    row["attack_family"] == family and output.get("utility") is True
                    for row, output in outputs
                ),
            }
            for family in sorted({row["attack_family"] for row in rows})
        },
    }


def main() -> int:
    args = parse_args()
    if not os.getenv("E77_LLM_API_KEY") or not os.getenv("E77_LLM_BASE_URL"):
        raise RuntimeError("DeepSeek credentials and base URL must be supplied through environment variables")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    rows = read_jsonl(MANIFEST)
    if sha256(MANIFEST) != protocol["locked_manifest_sha256"] or len(rows) != 320:
        raise RuntimeError("held-out manifest changed or has the wrong denominator")
    frozen_source_hashes = verify_frozen_c1f()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    run_protocol = {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": sha256(MANIFEST),
        "frozen_c1f_sha256": sha256(FROZEN_C1F),
        "frozen_c1f_source_hashes": frozen_source_hashes,
        "methods": args.methods,
        "model": os.getenv("E77_LLM_MODEL", "unspecified"),
        "benchmark": "AgentDojo v1.1.2",
        "official_validator": True,
        "real_external_side_effects": False,
    }
    (RESULT_ROOT / "run_protocol.json").write_text(json.dumps(run_protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failures = []
    summaries = []
    task_groups = groups(rows)
    for method in args.methods:
        with ThreadPoolExecutor(max_workers=args.parallel_groups) as pool:
            futures = [pool.submit(run_group, method, group) for group in task_groups]
            for future in as_completed(futures):
                result = future.result()
                if result["status"] == "failed":
                    failures.append({"method": method, **result})
        summaries.append(summarize(method, rows))
    passed = not failures and all(
        row["n"] == 320
        and not row["errors"]
        and not row["missing_case_ids"]
        and not row["incomplete_case_ids"]
        for row in summaries
    )
    report = {
        **run_protocol,
        "status": "passed" if passed else "failed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "summaries": summaries,
        "failures": failures,
        "claim_boundary": "Frozen public-family AgentDojo evaluation under a common DeepSeek protocol; not unrestricted adaptive robustness.",
    }
    (RESULT_ROOT / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
