#!/usr/bin/env python3
"""Run no-guard, Spotlighting, and frozen C1f on one local Qwen3-32B server."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "paper").is_dir() and (parent / "experiments").is_dir()
)
PYTHON = ROOT / "experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python"
MODULE = "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75"
MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
PORT = 18087
SHADOW = ROOT / "code/shadow_atom_envelope_c1f"
DESCRIPTORS = ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl"
RUNTIME_CATALOG = ROOT / "experiments/security-analysis-ablation-and-overhead/evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
RELATION_CATALOG = ROOT / "experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/registered_relation_catalog.json"
FREEZE = ROOT / "experiments/intent-bound-runtime-guard/evaluation/counterfactual-atom-envelope-guard/c1f_frozen_candidate_2026-08-08.json"
RUNS = ROOT / "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard"
OUT = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard"
EXPECTED = {
    "benign": {"banking": 16, "slack": 21, "travel": 20, "workspace": 40},
    "attack": {"banking": 144, "slack": 105, "travel": 140, "workspace": 240},
}
CONDITIONS = ("no_guard", "spotlighting", "c1f")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sources() -> dict[str, str]:
    if sha256(MODEL) != MODEL_SHA256:
        raise RuntimeError("Qwen3-32B model hash mismatch")
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    for artifact in frozen["source_artifacts"].values():
        path = ROOT / artifact["path"]
        if sha256(path) != artifact["sha256"]:
            raise RuntimeError(f"frozen C1f artifact changed: {artifact['path']}")
    return {
        "model": MODEL_SHA256,
        "c1f_freeze": sha256(FREEZE),
        "descriptors": sha256(DESCRIPTORS),
        "runtime_catalog": sha256(RUNTIME_CATALOG),
        "relation_catalog": sha256(RELATION_CATALOG),
    }


def healthy() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def start_server() -> subprocess.Popen[str] | None:
    if healthy():
        return None
    OUT.mkdir(parents=True, exist_ok=True)
    log = (OUT / "qwen32_matched_llama_cpp.log").open("a", encoding="utf-8")
    command = [
        "/home/user/anaconda3/bin/python", "-m", "llama_cpp.server",
        "--model", str(MODEL), "--model_alias", "qwen3_32b_local",
        "--host", "127.0.0.1", "--port", str(PORT),
        "--n_gpu_layers", "65", "--split_mode", "1",
        "--tensor_split", "0.35", "0.65", "--n_ctx", "65536",
        "--n_batch", "1024", "--n_ubatch", "512", "--flash_attn", "true",
    ]
    process = subprocess.Popen(
        command, cwd=ROOT, env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"},
        stdout=log, stderr=subprocess.STDOUT, text=True,
    )
    for _ in range(300):
        if process.poll() is not None:
            raise RuntimeError("llama.cpp server exited during startup")
        if healthy():
            return process
        time.sleep(2)
    process.terminate()
    raise TimeoutError("Qwen3-32B server did not become healthy")


def pipeline(condition: str) -> str:
    return {
        "no_guard": "local",
        "spotlighting": "local-spotlighting_with_delimiting",
        "c1f": "local-ours_e77_effect_diff_runtime",
    }[condition]


def log_paths(logdir: Path, suite: str, mode: str, condition: str) -> list[Path]:
    base = logdir / pipeline(condition) / suite
    pattern = "user_task_*/none/none.json" if mode == "benign" else "user_task_*/important_instructions/*.json"
    return sorted(base.glob(pattern))


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
        "attack_successes": sum(bool(row.get("security")) for row in rows) if mode == "attack" else None,
        "errors": sum(row.get("error") is not None for row in rows),
        "incomplete": incomplete,
    }


def run_suite(condition: str, mode: str, suite: str) -> dict[str, Any]:
    root = RUNS / f"qwen32-matched-{condition}-{mode}-r1" / suite
    logdir = root / "agentdojo_logs"
    existing = log_paths(logdir, suite, mode, condition)
    expected = EXPECTED[mode][suite]
    existing_metrics = summarize(existing, mode)
    if (
        len(existing) == expected
        and existing_metrics["errors"] == 0
        and existing_metrics["incomplete"] == 0
    ):
        return {"status": "resumed_complete", "metrics": existing_metrics}
    method = {
        "no_guard": "no_guard",
        "spotlighting": "spotlighting",
        "c1f": "ours_e77_effect_diff_runtime",
    }[condition]
    command = [
        str(PYTHON), "-m", MODULE, "--mode", "official-live-run",
        "--agentdojo-version", "v1.1.2", "--live-method", method,
        "--live-suites", suite, "--live-modes", mode,
        "--live-logdir", str(logdir), "--local-llm-port", str(PORT),
        "--live-timeout-seconds", "0",
    ]
    base_pythonpath = str(ROOT / "code")
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": base_pythonpath, "E75_LIVE_MODEL_NAME": "qwen3_32b_local"}
    if condition == "c1f":
        env.update({
            "PYTHONPATH": f"{SHADOW}:{ROOT / 'code'}",
            "E77_POLICY_VARIANT": "atom_control_taint_envelope",
            "E77_REGISTERED_DESCRIPTOR_JSONL": str(DESCRIPTORS),
            "E77_RUNTIME_CATALOG": str(RUNTIME_CATALOG),
            "E77_RELATION_CATALOG": str(RELATION_CATALOG),
            "E77_AUDIT_JSONL": str(root / "runtime_audit.jsonl"),
            "E77_PLAN_CACHE": str(root / "unused_plan_cache.json"),
            "E77_EXECUTION_DATE": "2026-08-02",
            "E77_UNCERTAINTY_POLICY": "allow_with_trail",
        })
    started = datetime.now(timezone.utc).isoformat()
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    root.mkdir(parents=True, exist_ok=True)
    (root / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    (root / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    paths = log_paths(logdir, suite, mode, condition)
    metrics = summarize(paths, mode)
    row = {
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
    }
    (root / "status.json").write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    return row


def main() -> int:
    hashes = verify_sources()
    OUT.mkdir(parents=True, exist_ok=True)
    protocol_path = OUT / "qwen32_matched_protocol.json"
    protocol = {
        "status": "frozen_before_execution",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "model": "Qwen3-32B-Q4_K_M",
        "hashes": hashes,
        "conditions": list(CONDITIONS),
        "agentdojo_version": "v1.1.2",
        "case_keys_per_condition": 726,
        "gpu": {"n_gpu_layers": 65, "tensor_split": [0.35, 0.65]},
        "retain_all_failures": True,
    }
    if protocol_path.exists():
        existing = json.loads(protocol_path.read_text(encoding="utf-8"))
        if existing.get("hashes") != hashes:
            raise RuntimeError("source hashes changed after Qwen protocol freeze")
    else:
        protocol_path.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    server = start_server()
    all_rows: list[dict[str, Any]] = []
    try:
        for condition in CONDITIONS:
            for mode in ("benign", "attack"):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    futures = {pool.submit(run_suite, condition, mode, suite): suite for suite in EXPECTED[mode]}
                    group = {}
                    for future in as_completed(futures):
                        suite = futures[future]
                        group[suite] = future.result()
                for suite in EXPECTED[mode]:
                    all_rows.append({"condition": condition, "mode": mode, "suite": suite, **group[suite]})
                status = "passed" if all(row["status"] in {"passed", "resumed_complete"} for row in group.values()) else "failed"
                (OUT / "qwen32_matched_run_status.json").write_text(
                    json.dumps({"status": "running" if status == "passed" else "failed", "rows": all_rows}, indent=2) + "\n",
                    encoding="utf-8",
                )
                if status == "failed":
                    return 2
        (OUT / "qwen32_matched_run_status.json").write_text(
            json.dumps({"status": "passed", "rows": all_rows}, indent=2) + "\n", encoding="utf-8"
        )
        return 0
    finally:
        if server is not None and server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=60)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
