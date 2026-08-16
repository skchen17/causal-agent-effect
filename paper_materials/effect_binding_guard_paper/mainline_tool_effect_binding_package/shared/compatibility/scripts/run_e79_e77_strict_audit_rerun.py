#!/usr/bin/env python3
"""Run targeted audit smokes and a fresh E79 E77 full evaluation."""

from __future__ import annotations

import argparse
import collections
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
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
sys.path.insert(0, str(ROOT / "code"))
MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
DEFAULT_RUN_ROOT = ROOT / "runs/e79_agentlab_saved_transfer/protocol_invalid_tool_audit_v3"
TARGET_CASES = (
    "banking:user_task_11:injection_task_5",
    "slack:user_task_10:injection_task_5",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def first_user_text(payload: dict[str, Any]) -> str | None:
    for message in payload.get("messages") or []:
        if message.get("role") != "user":
            continue
        texts = [
            block.get("content", "")
            for block in message.get("content") or []
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if texts:
            return "\n".join(texts)
    return None


def executed_signatures(payload: dict[str, Any]) -> collections.Counter[str]:
    from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import (
        call_signature,
    )

    signatures: collections.Counter[str] = collections.Counter()
    for message in payload.get("messages") or []:
        call = message.get("tool_call") if message.get("role") == "tool" else None
        if not isinstance(call, dict):
            continue
        if isinstance(call.get("function"), str) and isinstance(call.get("args"), dict):
            signatures[call_signature(call["function"], call["args"])] += 1
    return signatures


def write_status(path: Path, **values: Any) -> None:
    payload = {"experiment": "E79", "method": "e77", **values}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def run_command(command: list[str], log_path: Path, env: dict[str, str]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}")


def targeted_mediation(logdir: Path) -> dict[str, Any]:
    payloads = []
    for path in sorted(logdir.rglob("*.json")):
        if path.name == "e77_plan_cache.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("suite_name") and payload.get("messages"):
            payloads.append(payload)
    audit = read_jsonl(logdir / "e77_runtime_audit.jsonl")
    checked: collections.Counter[str] = collections.Counter()
    executed: collections.Counter[str] = collections.Counter()
    for payload in payloads:
        query = first_user_text(payload)
        if query is None:
            raise ValueError("targeted log has no user query")
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        checked.update(
            row["call_signature"]
            for row in audit
            if row.get("event") == "precommit_check" and row.get("query_hash") == query_hash
        )
        executed.update(executed_signatures(payload))
    return {
        "n_cases": len(payloads),
        "tool_result_calls": sum(executed.values()),
        "precommit_checks": sum(checked.values()),
        "signature_multiset_exact_match": executed == checked,
        "missing_check_occurrences": sum((executed - checked).values()),
        "extra_check_occurrences": sum((checked - executed).values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18084)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    status_path = run_root / "status.json"
    write_status(
        status_path,
        status="initializing",
        created_at=datetime.now(timezone.utc).isoformat(),
        run_root=str(run_root),
    )
    if model_sha256(MODEL) != MODEL_SHA256:
        raise RuntimeError("Qwen3-32B checksum mismatch")

    server_log = (run_root / "qwen32_server.log")
    server_log.parent.mkdir(parents=True, exist_ok=True)
    server_handle = server_log.open("a", encoding="utf-8")
    server_command = [
        "/home/user/anaconda3/bin/python",
        "-m",
        "llama_cpp.server",
        "--model",
        str(MODEL),
        "--model_alias",
        "qwen3_32b_local",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.port),
        "--n_gpu_layers",
        "65",
        "--split_mode",
        "1",
        "--tensor_split",
        "0.35",
        "0.65",
        "--n_ctx",
        "65536",
        "--n_batch",
        "1024",
        "--n_ubatch",
        "512",
        "--flash_attn",
        "true",
    ]
    server = subprocess.Popen(
        server_command,
        cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"},
        stdout=server_handle,
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
        write_status(
            status_path,
            status="targeted_smoke",
            server_pid=server.pid,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        env = {**os.environ, "PYTHONPATH": str(ROOT / "code")}
        smoke_root = run_root / "targeted_smoke" / "e77"
        for case_key in TARGET_CASES:
            run_command(
                [
                    "/home/user/anaconda3/bin/python",
                    "scripts/run_e79_agentlab_saved_transfer.py",
                    "--method",
                    "e77",
                    "--mode",
                    "targeted",
                    "--case-key",
                    case_key,
                    "--port",
                    str(args.port),
                    "--model-id",
                    "qwen3_32b_local",
                    "--logdir",
                    str(smoke_root),
                    "--force-rerun",
                ],
                run_root / f"targeted_{case_key.replace(':', '_')}.log",
                env,
            )
        smoke_mediation = targeted_mediation(smoke_root)
        if smoke_mediation["n_cases"] != 2 or not smoke_mediation["signature_multiset_exact_match"]:
            raise RuntimeError(f"targeted mediation gate failed: {smoke_mediation}")

        full_root = run_root / "full" / "e77"
        write_status(
            status_path,
            status="full_run",
            server_pid=server.pid,
            targeted_mediation=smoke_mediation,
        )
        run_command(
            [
                "/home/user/anaconda3/bin/python",
                "scripts/run_e79_agentlab_saved_transfer.py",
                "--method",
                "e77",
                "--mode",
                "full",
                "--port",
                str(args.port),
                "--model-id",
                "qwen3_32b_local",
                "--logdir",
                str(full_root),
                "--force-rerun",
            ],
            run_root / "full_runner_e77.log",
            env,
        )
        write_status(
            status_path,
            status="finalizing",
            server_pid=server.pid,
            targeted_mediation=smoke_mediation,
        )
        run_command(
            [
                "/home/user/anaconda3/bin/python",
                "scripts/finalize_e79_agentlab_saved_transfer.py",
                "--method",
                "e77",
                "--mode",
                "full",
                "--logdir",
                str(full_root),
            ],
            run_root / "full_finalizer_e77.log",
            env,
        )
        write_status(
            status_path,
            status="passed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            targeted_mediation=smoke_mediation,
        )
        return 0
    except Exception as exc:
        write_status(
            status_path,
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            error=repr(exc),
        )
        raise
    finally:
        if server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
        server_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
