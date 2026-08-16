#!/usr/bin/env python3
"""Queue the provenance-normalized C1f AgentLAB full rerun on Qwen3-32B."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
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
MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
SERVER_PYTHON = Path("/home/user/anaconda3/bin/python")
CASES = ROOT / "evaluation/e79_long_horizon/agentlab_saved_attack_cases.jsonl"
SAVED_MANIFEST = ROOT / "evaluation/e79_long_horizon/agentlab_saved_attack_manifest.json"
PAIR_RESULT = ROOT / "analysis/results/e79_agentlab_saved_transfer_current_pair_results.json"
DEFAULT_RUN_ROOT = (
    ROOT
    / "experiments/long-horizon-transfer/runs/long-horizon-cross-environment-transfer/"
    "agentlab-c1f-provenance-normalized-qwen32"
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def wait_for_process(pid: int) -> None:
    while Path(f"/proc/{pid}").exists():
        time.sleep(60)


def healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def write_status(path: Path, status: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_logged(command: list[str], log: Path, env: dict[str, str]) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as handle:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}")


def build_pair_report(run_root: Path, c1f_pn: dict) -> dict:
    no_guard_path = ROOT / "analysis/results/e79_agentlab_saved_transfer_no_guard_results.json"
    no_guard = json.loads(no_guard_path.read_text(encoding="utf-8"))
    for name, payload in (("no_guard", no_guard), ("c1f_pn", c1f_pn)):
        if payload.get("status") != "passed" or payload.get("expected_case_keys") != 303:
            raise RuntimeError(f"AgentLAB paired result is incomplete: {name}")
    status_path = ROOT / "analysis/results/e79_agentlab_saved_transfer_c1f_pn_full_status.json"
    run_status = json.loads(status_path.read_text(encoding="utf-8"))
    source_hashes = run_status.get("c1f_source_hashes") or {}
    if len(source_hashes) < 2:
        raise RuntimeError("current C1f source hashes are missing from AgentLAB-PN status")
    payload = {
        "experiment": "agentlab_saved_transfer_current_c1f_pair",
        "status": "passed",
        "method": "c1f",
        "runtime_profile": "c1f_provenance_normalized_v1",
        "agentdojo_version": "v1.2.1",
        "expected_case_keys": 303,
        "metrics": c1f_pn["metrics"],
        "precommit_mediation": c1f_pn["precommit_mediation"],
        "comparison_metrics": [
            {"condition": "no_guard", **no_guard["metrics"]},
            {"condition": "c1f", **c1f_pn["metrics"]},
        ],
        "model": "Qwen3-32B-Q4_K_M",
        "model_sha256": MODEL_SHA256,
        "case_manifest_sha256": digest(CASES),
        "saved_attack_manifest_sha256": digest(SAVED_MANIFEST),
        "c1f_source_hashes": source_hashes,
        "source_result_hashes": {
            "no_guard": digest(no_guard_path),
            "c1f_pn": digest(
                ROOT / "analysis/results/e79_agentlab_saved_transfer_c1f_pn_results.json"
            ),
        },
        "run_root": str(run_root.relative_to(ROOT)),
        "official_validator": True,
        "real_external_side_effects": False,
        "claim_boundary": (
            "Matched no-guard/provenance-normalized C1f replay of 303 frozen AgentLAB "
            "saved attacks under one local checkpoint and deterministic AgentDojo v1.2.1 "
            "validators; not regeneration of AgentLAB's adaptive optimization protocol."
        ),
    }
    PAIR_RESULT.parent.mkdir(parents=True, exist_ok=True)
    PAIR_RESULT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int, default=2757694)
    parser.add_argument("--port", type=int, default=18092)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    args = parser.parse_args()
    run_root = args.run_root if args.run_root.is_absolute() else ROOT / args.run_root
    status_path = run_root / "queue_status.json"
    status = {
        "status": "waiting_for_prior_gpu_queue",
        "queue_pid": os.getpid(),
        "wait_pid": args.wait_pid,
        "model": "Qwen3-32B-Q4_K_M",
        "model_sha256": MODEL_SHA256,
        "method": "c1f_pn",
        "expected_case_keys": 303,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_status(status_path, status)
    wait_for_process(args.wait_pid)
    if digest(MODEL) != MODEL_SHA256:
        raise RuntimeError("Qwen3-32B checksum mismatch")

    run_root.mkdir(parents=True, exist_ok=True)
    server_log = (run_root / "qwen32_server.log").open("a", encoding="utf-8")
    server = subprocess.Popen(
        [
            str(SERVER_PYTHON), "-m", "llama_cpp.server", "--model", str(MODEL),
            "--model_alias", "qwen3_32b_local", "--host", "127.0.0.1", "--port", str(args.port),
            "--n_gpu_layers", "65", "--split_mode", "1", "--tensor_split", "0.35", "0.65",
            "--n_ctx", "65536", "--n_batch", "1024", "--n_ubatch", "512", "--flash_attn", "true",
        ],
        cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"},
        stdout=server_log,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(240):
            if server.poll() is not None:
                raise RuntimeError("Qwen server exited during startup")
            if healthy(args.port):
                break
            time.sleep(2)
        else:
            raise TimeoutError("Qwen server health timeout")

        env = {**os.environ, "PYTHONPATH": str(ROOT / "code")}
        status.update({"status": "running_smoke", "server_pid": server.pid})
        write_status(status_path, status)
        smoke = run_root / "smoke"
        run_logged(
            [
                str(PYTHON), "scripts/run_e79_agentlab_saved_transfer.py", "--method", "c1f_pn",
                "--mode", "smoke", "--port", str(args.port), "--model-id", "qwen3_32b_local",
                "--logdir", str(smoke), "--force-rerun",
            ],
            run_root / "smoke_runner.log",
            env,
        )
        run_logged(
            [
                str(PYTHON), "scripts/finalize_e79_agentlab_saved_transfer.py", "--method", "c1f_pn",
                "--mode", "smoke", "--logdir", str(smoke),
            ],
            run_root / "smoke_finalizer.log",
            env,
        )

        status.update({"status": "running_full", "full_started_at": datetime.now(timezone.utc).isoformat()})
        write_status(status_path, status)
        full = run_root / "full"
        run_logged(
            [
                str(PYTHON), "scripts/run_e79_agentlab_saved_transfer.py", "--method", "c1f_pn",
                "--mode", "full", "--port", str(args.port), "--model-id", "qwen3_32b_local",
                "--logdir", str(full), "--force-rerun",
            ],
            run_root / "full_runner.log",
            env,
        )
        run_logged(
            [
                str(PYTHON), "scripts/finalize_e79_agentlab_saved_transfer.py", "--method", "c1f_pn",
                "--logdir", str(full), "--audit", str(full / "e77_runtime_audit.jsonl"),
            ],
            run_root / "full_finalizer.log",
            env,
        )
        result = ROOT / "analysis/results/e79_agentlab_saved_transfer_c1f_pn_results.json"
        payload = json.loads(result.read_text(encoding="utf-8"))
        if payload.get("status") != "passed" or payload.get("expected_case_keys") != 303:
            raise RuntimeError("provenance-normalized full result failed strict finalization")
        paired = build_pair_report(run_root, payload)
        status.update(
            {
                "status": "passed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "result": str(result.relative_to(ROOT)),
                "result_sha256": digest(result),
                "paired_result": str(PAIR_RESULT.relative_to(ROOT)),
                "paired_result_sha256": digest(PAIR_RESULT),
                "paired_attack_successes": {
                    row["condition"]: row["attack_successes"]
                    for row in paired["comparison_metrics"]
                },
                "metrics": payload["metrics"],
            }
        )
        write_status(status_path, status)
        return 0
    except Exception as exc:
        status.update({"status": "failed", "error": repr(exc), "completed_at": datetime.now(timezone.utc).isoformat()})
        write_status(status_path, status)
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
