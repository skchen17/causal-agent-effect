#!/usr/bin/env python3
"""Wait for ToolSandbox queue, then run paired AgentLAB saved-attack transfer rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
RUN = ROOT / "runs/e79_agentlab_saved_transfer"
MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
PYTHON = os.environ.get("EFFECT_BINDING_PYTHON", sys.executable)
CASES = ROOT / "evaluation/e79_long_horizon/agentlab_saved_attack_cases.jsonl"
SAVED_MANIFEST = ROOT / "evaluation/e79_long_horizon/agentlab_saved_attack_manifest.json"
PAIR_RESULT = ROOT / "analysis/results/e79_agentlab_saved_transfer_current_pair_results.json"


def write_status(value: dict) -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "queue_status.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def wait_for_process(pid: int) -> None:
    while Path(f"/proc/{pid}").exists():
        time.sleep(60)


def model_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def build_pair_report(run_root: Path) -> dict:
    reports = {}
    for method in ("no_guard", "c1f"):
        path = ROOT / f"analysis/results/e79_agentlab_saved_transfer_{method}_results.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "passed" or payload.get("expected_case_keys") != 303:
            raise RuntimeError(f"AgentLAB paired result is incomplete: {method}")
        reports[method] = payload
    c1f_status_path = ROOT / "analysis/results/e79_agentlab_saved_transfer_c1f_full_status.json"
    c1f_status = json.loads(c1f_status_path.read_text(encoding="utf-8"))
    source_hashes = c1f_status.get("c1f_source_hashes") or {}
    if len(source_hashes) < 2:
        raise RuntimeError("current C1f source hashes are missing from AgentLAB run status")
    c1f = reports["c1f"]
    payload = {
        "experiment": "agentlab_saved_transfer_current_c1f_pair",
        "status": "passed",
        "method": "c1f",
        "agentdojo_version": "v1.2.1",
        "expected_case_keys": 303,
        "metrics": c1f["metrics"],
        "precommit_mediation": c1f["precommit_mediation"],
        "comparison_metrics": [
            {"condition": method, **reports[method]["metrics"]}
            for method in ("no_guard", "c1f")
        ],
        "model": "Qwen3-32B-Q4_K_M",
        "model_sha256": SHA256,
        "case_manifest_sha256": model_sha256(CASES),
        "saved_attack_manifest_sha256": model_sha256(SAVED_MANIFEST),
        "c1f_source_hashes": source_hashes,
        "source_result_hashes": {
            method: model_sha256(
                ROOT / f"analysis/results/e79_agentlab_saved_transfer_{method}_results.json"
            )
            for method in ("no_guard", "c1f")
        },
        "run_root": str(run_root.relative_to(ROOT)),
        "official_validator": True,
        "real_external_side_effects": False,
        "claim_boundary": (
            "Matched no-guard/current-C1f replay of 303 frozen AgentLAB saved attacks "
            "under one local checkpoint and deterministic AgentDojo v1.2.1 validators; "
            "not regeneration of AgentLAB's adaptive optimization protocol."
        ),
    }
    PAIR_RESULT.parent.mkdir(parents=True, exist_ok=True)
    PAIR_RESULT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int, default=3837961)
    parser.add_argument("--port", type=int, default=18084)
    parser.add_argument("--run-root", type=Path, default=RUN / "protocol_fixed_v2")
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=("no_guard", "e77", "c1f"),
        default=("no_guard", "e77"),
    )
    args = parser.parse_args()
    run_root = args.run_root if args.run_root.is_absolute() else ROOT / args.run_root
    run_root.mkdir(parents=True, exist_ok=True)
    status = {
        "status": "waiting_for_gpu_owner",
        "queue_pid": os.getpid(),
        "wait_pid": args.wait_pid,
        "run_root": str(run_root.relative_to(ROOT)),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_status(status)
    wait_for_process(args.wait_pid)
    if model_sha256(MODEL) != SHA256:
        raise RuntimeError("Qwen3-32B checksum mismatch")
    server_log = (run_root / "qwen32_server.log").open("a", encoding="utf-8")
    command = [
        PYTHON, "-m", "llama_cpp.server", "--model", str(MODEL),
        "--model_alias", "qwen3_32b_local", "--host", "127.0.0.1", "--port", str(args.port),
        "--n_gpu_layers", "65", "--split_mode", "1", "--tensor_split", "0.35", "0.65",
        "--n_ctx", "65536", "--n_batch", "1024", "--n_ubatch", "512", "--flash_attn", "true",
    ]
    server = subprocess.Popen(command, cwd=ROOT, env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"}, stdout=server_log, stderr=subprocess.STDOUT)
    try:
        for _ in range(240):
            if server.poll() is not None:
                raise RuntimeError("AgentLAB Qwen server exited during startup")
            if healthy(args.port):
                break
            time.sleep(2)
        else:
            raise TimeoutError("AgentLAB Qwen server health timeout")
        status.update({"status": "running", "server_pid": server.pid, "started_at": datetime.now(timezone.utc).isoformat()})
        write_status(status)
        env = {**os.environ, "PYTHONPATH": str(ROOT / "code")}
        for method in args.methods:
            smoke_root = run_root / "smoke" / method
            status.update({"status": "running_smoke", "method": method})
            write_status(status)
            with (run_root / f"smoke_runner_{method}.log").open("a", encoding="utf-8") as handle:
                completed = subprocess.run(
                    [PYTHON, "scripts/run_e79_agentlab_saved_transfer.py",
                     "--method", method, "--mode", "smoke", "--port", str(args.port),
                     "--model-id", "qwen3_32b_local", "--logdir", str(smoke_root), "--force-rerun"],
                    cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
                )
            if completed.returncode != 0:
                raise RuntimeError(f"AgentLAB {method} smoke runner failed")
            with (run_root / f"smoke_finalizer_{method}.log").open("a", encoding="utf-8") as handle:
                finalized = subprocess.run(
                    [PYTHON, "scripts/finalize_e79_agentlab_saved_transfer.py",
                     "--method", method, "--mode", "smoke", "--logdir", str(smoke_root)],
                    cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
                )
            if finalized.returncode != 0:
                raise RuntimeError(f"AgentLAB {method} smoke protocol validation failed")

        for method in args.methods:
            full_root = run_root / "full" / method
            status.update({"status": "running_full", "method": method})
            write_status(status)
            with (run_root / f"runner_{method}.log").open("a", encoding="utf-8") as handle:
                completed = subprocess.run(
                    [PYTHON, "scripts/run_e79_agentlab_saved_transfer.py",
                     "--method", method, "--mode", "full", "--port", str(args.port),
                     "--model-id", "qwen3_32b_local", "--logdir", str(full_root),
                     "--force-rerun"],
                    cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
                )
            if completed.returncode != 0:
                raise RuntimeError(f"AgentLAB {method} runner failed")
            with (run_root / f"finalizer_{method}.log").open("a", encoding="utf-8") as handle:
                finalized = subprocess.run(
                    [PYTHON, "scripts/finalize_e79_agentlab_saved_transfer.py",
                     "--method", method, "--logdir", str(full_root)],
                    cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
                )
            if finalized.returncode != 0:
                raise RuntimeError(f"AgentLAB {method} finalizer failed")
        if {"no_guard", "c1f"}.issubset(args.methods):
            paired = build_pair_report(run_root)
            status["paired_result"] = str(PAIR_RESULT.relative_to(ROOT))
            status["paired_result_sha256"] = model_sha256(PAIR_RESULT)
            status["paired_attack_successes"] = {
                row["condition"]: row["attack_successes"]
                for row in paired["comparison_metrics"]
            }
        status.update({"status": "passed", "completed_at": datetime.now(timezone.utc).isoformat()})
        write_status(status)
        return 0
    except Exception as exc:
        status.update({"status": "failed", "error": repr(exc), "completed_at": datetime.now(timezone.utc).isoformat()})
        write_status(status)
        raise
    finally:
        if server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
        server_log.close()


if __name__ == "__main__":
    raise SystemExit(main())
