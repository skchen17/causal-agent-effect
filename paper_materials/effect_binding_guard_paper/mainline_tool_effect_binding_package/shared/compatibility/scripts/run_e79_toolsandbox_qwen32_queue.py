#!/usr/bin/env python3
"""Wait for E78, then run paired ToolSandbox rows on the same local Qwen3-32B."""

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


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/e79_toolsandbox_local"
PYTHON = ROOT / "runs/e79_toolsandbox_env/bin/python"
MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"


def write_status(value: dict) -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "queue_status.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def wait_for_e78(pid: int) -> None:
    while Path(f"/proc/{pid}").exists():
        try:
            command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            break
        if "run_e78_qwen32_strong_baselines.py" not in command:
            break
        time.sleep(60)


def healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def model_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int, default=3638426)
    parser.add_argument("--port", type=int, default=18083)
    args = parser.parse_args()
    status = {"status": "waiting_for_e78", "wait_pid": args.wait_pid, "created_at": datetime.now(timezone.utc).isoformat()}
    write_status(status)
    wait_for_e78(args.wait_pid)
    observed = model_sha256(MODEL)
    if observed != SHA256:
        raise RuntimeError("Qwen3-32B checksum mismatch")
    server_log = (RUN / "qwen32_server.log").open("a", encoding="utf-8")
    command = [
        "/home/user/anaconda3/bin/python", "-m", "llama_cpp.server", "--model", str(MODEL),
        "--model_alias", "qwen3_32b_local", "--host", "127.0.0.1", "--port", str(args.port),
        "--n_gpu_layers", "-1", "--split_mode", "1", "--tensor_split", "0.5", "0.5",
        "--n_ctx", "65536", "--n_batch", "1024", "--n_ubatch", "512", "--flash_attn", "true",
    ]
    server = subprocess.Popen(command, cwd=ROOT, env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"}, stdout=server_log, stderr=subprocess.STDOUT)
    try:
        for _ in range(240):
            if server.poll() is not None:
                raise RuntimeError("E79 Qwen server exited during startup")
            if healthy(args.port):
                break
            time.sleep(2)
        else:
            raise TimeoutError("E79 Qwen server health timeout")
        status.update({"status": "running", "started_at": datetime.now(timezone.utc).isoformat(), "server_pid": server.pid})
        write_status(status)
        env = {
            **os.environ,
            "PYTHONPATH": f"{ROOT}:{ROOT / 'code'}:{ROOT / 'runs/e79_external_benchmarks/ToolSandbox'}",
        }
        for method in ("no_guard", "effect_guard"):
            with (RUN / f"runner_{method}.log").open("a", encoding="utf-8") as handle:
                completed = subprocess.run(
                    [str(PYTHON), "scripts/run_e79_toolsandbox_local.py", "--mode", "full", "--method", method,
                     "--base-url", f"http://127.0.0.1:{args.port}/v1", "--model", "qwen3_32b_local"],
                    cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
                )
            if completed.returncode != 0:
                raise RuntimeError(f"E79 ToolSandbox {method} failed; inspect runner log")
        completed = subprocess.run(
            [str(PYTHON), "scripts/finalize_e79_toolsandbox_local.py"], cwd=ROOT, env=env,
            stdout=(RUN / "finalizer.log").open("a", encoding="utf-8"), stderr=subprocess.STDOUT,
        )
        if completed.returncode != 0:
            raise RuntimeError("E79 ToolSandbox finalizer failed")
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
