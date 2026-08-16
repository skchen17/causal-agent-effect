#!/usr/bin/env python3
"""Rerun the frozen 40-key bounded search with the current frozen C1f profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "paper/current-usenix").is_dir()
)
CODE_ROOT = PACKAGE_ROOT / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75 import (
    official_live_method_config,
)
from src.experiments.effect_binding_guard.e88_agentdojo_attack_dataset.bounded_search import (
    EVALUATION_ROOT,
    FAMILIES,
    MODEL,
    MODEL_SHA256,
    ROOT,
    SUITES,
    sha256_file,
    summarize_predictions,
    validate_preregistration,
)


PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
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
OLD_PREDICTIONS = (
    ROOT
    / "experiments/adaptive-injection-benchmark/results/"
    "bounded-public-family-search/predictions.jsonl"
)
OLD_REPORT = (
    ROOT
    / "experiments/adaptive-injection-benchmark/results/"
    "bounded-public-family-search/bounded-search-report.json"
)
RUN_ROOT = (
    ROOT
    / "experiments/adaptive-injection-benchmark/runs/"
    "bounded-public-family-search-current-c1f"
)
RESULT_ROOT = (
    ROOT
    / "experiments/adaptive-injection-benchmark/results/"
    "bounded-public-family-search-current-c1f"
)
METHOD = "ours_e77_effect_diff_runtime"
PIPELINE = "local-ours_e77_effect_diff_runtime"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int, action="append", default=[])
    parser.add_argument("--port", type=int, default=18090)
    parser.add_argument("--model-id", default="qwen3_32b_local")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def wait_for_pids(pids: list[int]) -> None:
    pending = {pid for pid in pids if pid > 0}
    while pending:
        pending = {pid for pid in pending if Path(f"/proc/{pid}").exists()}
        write_json(RUN_ROOT / "queue-status.json", {"status": "waiting", "wait_pids": sorted(pending)})
        if pending:
            time.sleep(60)


def server_healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def start_server(port: int, model_id: str) -> tuple[subprocess.Popen[bytes], Any]:
    if not MODEL.is_file() or sha256_file(MODEL) != MODEL_SHA256:
        raise RuntimeError("Qwen3-32B model is missing or changed")
    if server_healthy(port):
        raise RuntimeError(f"refusing to reuse unverified server on port {port}")
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    handle = (RUN_ROOT / "qwen32-server.log").open("ab")
    command = [
        os.environ.get("LLAMA_CPP_PYTHON", sys.executable), "-m", "llama_cpp.server",
        "--model", str(MODEL), "--model_alias", model_id,
        "--host", "127.0.0.1", "--port", str(port),
        "--n_gpu_layers", "65", "--split_mode", "1",
        "--tensor_split", "0.35", "0.65", "--n_ctx", "65536",
        "--n_batch", "1024", "--n_ubatch", "512", "--flash_attn", "true",
    ]
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"},
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    for _ in range(240):
        if process.poll() is not None:
            raise RuntimeError("bounded current-C1f model server exited during startup")
        if server_healthy(port):
            return process, handle
        time.sleep(2)
    process.terminate()
    raise TimeoutError("bounded current-C1f model server health timeout")


def verify_frozen_c1f() -> dict[str, str]:
    frozen = json.loads(FROZEN_C1F.read_text(encoding="utf-8"))
    if frozen.get("status") != "frozen_before_c1f_live_regression":
        raise RuntimeError("C1f freeze manifest has wrong status")
    hashes = {"freeze_manifest": sha256_file(FROZEN_C1F)}
    for name, artifact in frozen["source_artifacts"].items():
        path = ROOT / artifact["path"]
        observed = sha256_file(path)
        if observed != artifact["sha256"]:
            raise RuntimeError(f"frozen C1f artifact changed: {artifact['path']}")
        hashes[name] = observed
    return hashes


def grouped_cases(cases: list[dict[str, Any]]) -> dict[tuple[str, str], list[str]]:
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for case in cases:
        grouped[(case["suite"], case["injection_task_id"])].append(case["user_task_id"])
    return {key: sorted(set(values)) for key, values in grouped.items()}


def result_path(family: str, case: dict[str, Any]) -> Path:
    return (
        RUN_ROOT / "logs" / METHOD / family / PIPELINE / case["suite"]
        / case["user_task_id"] / family / f'{case["injection_task_id"]}.json'
    )


def evaluable(path: Path, family: str) -> bool:
    if not path.is_file():
        return False
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        row.get("attack_type") == family
        and row.get("error") is None
        and isinstance(row.get("utility"), bool)
        and isinstance(row.get("security"), bool)
    )


def environment(port: int) -> dict[str, str]:
    config = official_live_method_config(METHOD)
    return {
        **os.environ,
        **config.get("env", {}),
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": f"{SHADOW}:{ROOT / 'code'}",
        "LOCAL_LLM_PORT": str(port),
        "E77_POLICY_VARIANT": "atom_control_taint_envelope",
        "E77_REGISTERED_DESCRIPTOR_JSONL": str(DESCRIPTORS),
        "E77_RUNTIME_CATALOG": str(RUNTIME_CATALOG),
        "E77_RELATION_CATALOG": str(RELATION_CATALOG),
        "E77_AUDIT_JSONL": str(RUN_ROOT / "audit/runtime_audit.jsonl"),
        "E77_PLAN_CACHE": str(RUN_ROOT / "cache/unused_plan_cache.json"),
        "E77_EXECUTION_DATE": "2026-08-02",
        "E77_UNCERTAINTY_POLICY": "allow_with_trail",
    }


def execute(cases: list[dict[str, Any]], protocol: dict[str, Any], port: int, model_id: str) -> None:
    config = official_live_method_config(METHOD)
    groups = grouped_cases(cases)
    for family in protocol["development_selected_family_order"]:
        for (suite, injection_task_id), user_task_ids in sorted(groups.items()):
            expected = [
                case for case in cases
                if case["suite"] == suite
                and case["injection_task_id"] == injection_task_id
            ]
            if all(result_path(family, case).is_file() and evaluable(result_path(family, case), family) for case in expected):
                continue
            command = [
                str(PYTHON), "-m", "agentdojo.scripts.benchmark",
                "--model", "LOCAL", "--model-id", model_id,
                "--benchmark-version", "v1.1.2", "--suite", suite,
                "--tool-delimiter", "user", "--logdir", str(RUN_ROOT / "logs" / METHOD / family),
                "--attack", family, "--injection-task", injection_task_id,
            ]
            for user_task_id in user_task_ids:
                command.extend(["--user-task", user_task_id])
            if config.get("defense"):
                command.extend(["--defense", config["defense"]])
            for module in config.get("modules_to_load", []):
                command.extend(["--module-to-load", module])
            if any(result_path(family, case).exists() for case in expected):
                command.append("--force-rerun")
            write_json(
                RUN_ROOT / "queue-status.json",
                {
                    "status": "running", "family": family, "suite": suite,
                    "injection_task_id": injection_task_id, "n_user_tasks": len(user_task_ids),
                },
            )
            with (RUN_ROOT / "runner.log").open("a", encoding="utf-8") as handle:
                completed = subprocess.run(
                    command, cwd=ROOT, env=environment(port), stdout=handle,
                    stderr=subprocess.STDOUT, text=True,
                )
            if completed.returncode != 0:
                raise RuntimeError(f"benchmark failed: {family}/{suite}/{injection_task_id}")


def collect_current(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        for family in FAMILIES:
            path = result_path(family, case)
            if not evaluable(path, family):
                raise RuntimeError(f"missing or incomplete current-C1f row: {path.relative_to(ROOT)}")
            output = json.loads(path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "method": METHOD,
                    "case_id": case["case_id"],
                    "suite": case["suite"],
                    "user_task_id": case["user_task_id"],
                    "injection_task_id": case["injection_task_id"],
                    "attack_family": family,
                    "attack_success": output["security"],
                    "user_utility": output["utility"],
                    "error": False,
                    "result_sha256": sha256_file(path),
                    "result_source": str(path.relative_to(ROOT)),
                }
            )
    return rows


def load_no_guard(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected = {(case["case_id"], family) for case in cases for family in FAMILIES}
    rows = [row for row in read_jsonl(OLD_PREDICTIONS) if row["method"] == "no_guard"]
    observed = {(row["case_id"], row["attack_family"]) for row in rows}
    if len(rows) != 160 or observed != expected or any(row.get("error") for row in rows):
        raise RuntimeError("frozen no-guard bounded-search rows do not match the locked manifest")
    return rows


def verify_no_guard_source(
    protocol: dict[str, Any], cases: list[dict[str, Any]]
) -> dict[str, str]:
    rows = load_no_guard(cases)
    report = json.loads(OLD_REPORT.read_text(encoding="utf-8"))
    if (
        report.get("status") != "passed"
        or report.get("experiment") != "bounded_public_family_search"
        or report.get("protocol_version") != protocol["protocol_version"]
        or report.get("locked_cases") != 40
        or report.get("variant_rows") != 320
        or len(rows) != 160
    ):
        raise RuntimeError("frozen no-guard bounded-search source is incomplete")
    return {
        "preregistration": sha256_file(EVALUATION_ROOT / "preregistration.json"),
        "locked_manifest": sha256_file(EVALUATION_ROOT / "locked-case-manifest.jsonl"),
        "old_report": sha256_file(OLD_REPORT),
        "old_predictions": sha256_file(OLD_PREDICTIONS),
        "declared_model": protocol["model_sha256"],
    }


def main() -> int:
    args = parse_args()
    protocol = json.loads((EVALUATION_ROOT / "preregistration.json").read_text(encoding="utf-8"))
    cases = read_jsonl(EVALUATION_ROOT / "locked-case-manifest.jsonl")
    validate_preregistration(protocol, cases)
    wait_for_pids(args.wait_pid)
    frozen_hashes = verify_frozen_c1f()
    no_guard_hashes = verify_no_guard_source(protocol, cases)
    server = None
    handle = None
    try:
        server, handle = start_server(args.port, args.model_id)
        execute(cases, protocol, args.port, args.model_id)
        predictions = [*load_no_guard(cases), *collect_current(cases)]
        predictions.sort(key=lambda row: (row["method"], row["case_id"], row["attack_family"]))
        report = summarize_predictions(predictions, protocol, cases)
        report.update(
            {
                "status": "passed" if report.get("status") == "passed" else "failed",
                "experiment": "bounded_public_family_search_current_c1f",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model_sha256": MODEL_SHA256,
                "locked_manifest_sha256": sha256_file(EVALUATION_ROOT / "locked-case-manifest.jsonl"),
                "no_guard_predictions_sha256": sha256_file(OLD_PREDICTIONS),
                "no_guard_source_hashes": no_guard_hashes,
                "current_c1f_source_hashes": frozen_hashes,
                "claim_boundary": (
                    "Worst-of-four public AgentDojo generators on 40 frozen keys. The no-guard rows "
                    "are hash-reused from the same Qwen checkpoint and protocol; current C1f rows are "
                    "rerun after its August freeze. This is bounded sensitivity, not unrestricted adaptation."
                ),
            }
        )
        if report["status"] != "passed" or report.get("variant_rows") != 320:
            raise RuntimeError("current-C1f bounded-search finalizer failed")
        RESULT_ROOT.mkdir(parents=True, exist_ok=True)
        write_jsonl(RESULT_ROOT / "predictions.jsonl", predictions)
        write_json(RESULT_ROOT / "results.json", report)
        write_json(RUN_ROOT / "queue-status.json", {"status": "passed", "variant_rows": 320})
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        write_json(RUN_ROOT / "queue-status.json", {"status": "failed", "error": repr(exc)})
        raise
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
        if handle is not None:
            handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
