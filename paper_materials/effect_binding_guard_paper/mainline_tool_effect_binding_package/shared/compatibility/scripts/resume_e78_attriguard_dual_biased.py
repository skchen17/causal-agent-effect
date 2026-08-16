#!/usr/bin/env python3
"""Resume E78 AttriGuard with a GPU1-biased two-GPU split."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/e78_qwen32_strong_baselines"
MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
PORT = 18082
GPU_LAYERS = 65
TENSOR_SPLIT = ("0.35", "0.65")


def write_status(value: dict) -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "dual_biased_resume_status.json").write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def healthy() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def main() -> int:
    status = {
        "experiment": "E78 AttriGuard GPU1-biased dual-GPU resume",
        "status": "starting",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "physical_gpus": [0, 1],
        "gpu_layers": GPU_LAYERS,
        "tensor_split": list(TENSOR_SPLIT),
        "context": 65536,
        "resume_existing_logs": True,
        "resource_boundary": (
            "All model layers are GPU-resident and biased toward physical GPU 1 to reduce "
            "contention with an unrelated process on physical GPU 0."
        ),
    }
    write_status(status)
    server_log = (RUN / "llama_cpp_server_dual_biased.log").open("a", encoding="utf-8")
    server = subprocess.Popen(
        [
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
            str(PORT),
            "--n_gpu_layers",
            str(GPU_LAYERS),
            "--split_mode",
            "1",
            "--tensor_split",
            *TENSOR_SPLIT,
            "--n_ctx",
            "65536",
            "--n_batch",
            "1024",
            "--n_ubatch",
            "512",
            "--n_threads",
            "48",
            "--n_threads_batch",
            "96",
            "--flash_attn",
            "true",
        ],
        cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"},
        stdout=server_log,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(300):
            if server.poll() is not None:
                raise RuntimeError("GPU1-biased llama.cpp server exited during startup")
            if healthy():
                break
            time.sleep(2)
        else:
            raise TimeoutError("GPU1-biased llama.cpp server health timeout")

        status.update(
            {
                "status": "running",
                "server_pid": server.pid,
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        write_status(status)
        with (RUN / "runner_attriguard_dual_biased.log").open("a", encoding="utf-8") as handle:
            completed = subprocess.run(
                [
                    str(PYTHON),
                    "-m",
                    "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75",
                    "--mode",
                    "attriguard-sharded-run",
                    "--agentdojo-version",
                    "v1.1.2",
                    "--attriguard-logdir",
                    str(RUN / "agentdojo_logs/attriguard"),
                    "--local-llm-port",
                    str(PORT),
                    "--live-suites",
                    "workspace,slack,travel,banking",
                    "--live-modes",
                    "benign,attack",
                    "--attriguard-max-workers",
                    "1",
                    "--attriguard-local-max-tokens",
                    "4096",
                    "--attriguard-local-context-window",
                    "65536",
                    "--attriguard-resume-all-missing",
                    "--live-timeout-seconds",
                    "0",
                ],
                cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT / "code"), "CUDA_VISIBLE_DEVICES": ""},
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
        if completed.returncode != 0:
            raise RuntimeError(f"AttriGuard dual-GPU resume failed with return code {completed.returncode}")
        status.update({"status": "passed", "completed_at": datetime.now(timezone.utc).isoformat()})
        write_status(status)
        return 0
    except Exception as exc:
        status.update(
            {
                "status": "failed",
                "error": repr(exc),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        write_status(status)
        raise
    finally:
        if server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
        server_log.close()


if __name__ == "__main__":
    raise SystemExit(main())
