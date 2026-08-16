#!/usr/bin/env python3
"""Run E77-v3 on the frozen Qwen3-32B AgentDojo v1.1.2 protocol."""

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
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir()
)
RESULTS = ROOT / "analysis/results"
MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
MODEL_BYTES = 19_762_149_024
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
E75_PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
E75_MODULE = "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75"
RUNTIME_VERSION = "e77_effect_diff_runtime_v3_bounded_recovery"
DEFAULT_PORT = 18083
DEFAULT_CONTEXT = 65536


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "full", "status"), default="status")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--context", type=int, default=DEFAULT_CONTEXT)
    parser.add_argument("--timeout", type=int, default=0)
    return parser.parse_args()


def run_root(mode: str) -> Path:
    return ROOT / ("runs/e77_v3_qwen32_smoke" if mode == "smoke" else "runs/e77_v3_qwen32_full")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hashes() -> dict[str, str]:
    paths = {
        "runtime_patch": ROOT / "code/src/experiments/effect_binding_guard/e77_effect_diff_runtime_guard/agentdojo_e77_runtime_patch.py",
        "runtime_core": ROOT / "code/src/experiments/effect_binding_guard/e77_effect_diff_runtime_guard/e77_runtime.py",
        "registered_descriptors": RESULTS / "e77_registered_effect_diff_descriptors.jsonl",
        "runtime_catalog": ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json",
    }
    return {name: sha256(path) for name, path in paths.items()}


def server_healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def server_command(port: int, context: int) -> list[str]:
    return [
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
        str(port),
        "--n_gpu_layers",
        "65",
        "--split_mode",
        "1",
        "--tensor_split",
        "0.35",
        "0.65",
        "--n_ctx",
        str(context),
        "--n_batch",
        "1024",
        "--n_ubatch",
        "512",
        "--flash_attn",
        "true",
    ]


def start_server(root: Path, port: int, context: int) -> subprocess.Popen[str]:
    log_path = root / "llama_cpp_server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        server_command(port, context),
        cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"},
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    (root / "server.pid").write_text(f"{process.pid}\n", encoding="utf-8")
    for _ in range(300):
        if process.poll() is not None:
            raise RuntimeError(f"llama.cpp server exited with {process.returncode}; inspect {log_path}")
        if server_healthy(port):
            return process
        time.sleep(2)
    process.terminate()
    raise TimeoutError("Qwen3-32B server did not become healthy")


def protocol_manifest(mode: str, port: int, context: int) -> dict[str, Any]:
    if not MODEL.exists() or MODEL.stat().st_size != MODEL_BYTES:
        raise FileNotFoundError(f"Expected Qwen3-32B model ({MODEL_BYTES} bytes) is unavailable")
    return {
        "experiment": "E77-v3 Qwen3-32B official AgentDojo full run",
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "runtime_version": RUNTIME_VERSION,
        "agentdojo": {
            "version": "v1.1.2",
            "case_keys": 2 if mode == "smoke" else 726,
            "suites": ["banking"] if mode == "smoke" else ["workspace", "slack", "travel", "banking"],
            "modes": ["benign", "attack"],
            "attack": "important_instructions",
            "tool_delimiter": "user",
        },
        "model": {
            "file_name": MODEL.name,
            "bytes": MODEL_BYTES,
            "sha256": MODEL_SHA256,
            "quantization": "Q4_K_M",
            "temperature": 0.0,
            "context_window": context,
            "agent_output_cap": 4096,
        },
        "gpu_configuration": {
            "visible_devices": [0, 1],
            "n_gpu_layers": 65,
            "tensor_split": [0.35, 0.65],
            "flash_attention": True,
        },
        "runtime_configuration": {
            "max_plan_revisions": 3,
            "planner_repair_attempts": 1,
            "revision_output_cap": 2048,
            "default_totalization": "evaluation/e81_ablation/agentdojo_runtime_catalog.json",
            "post_registration_llm_role": "bounded plan/revision proposal only; exact authorization remains deterministic",
        },
        "authority_scope": {
            "main_run": "model-proposed task plan with deterministic completeness, grounding, resolver-provenance, and exact-call checks",
            "e84_reviewed_manifests_used": False,
            "reason": "E84 is retained as an independent authority-interface coverage analysis and later ablation; it is not leaked into the main benchmark runtime.",
        },
        "source_sha256": source_hashes(),
        "port": port,
        "real_external_side_effects": False,
    }


def live_command(mode: str, root: Path, port: int, timeout: int) -> list[str]:
    suites = "banking" if mode == "smoke" else "workspace,slack,travel,banking"
    command = [
        str(E75_PYTHON),
        "-m",
        E75_MODULE,
        "--mode",
        "official-live-run",
        "--agentdojo-version",
        "v1.1.2",
        "--live-method",
        "ours_e77_effect_diff_runtime",
        "--live-suites",
        suites,
        "--live-modes",
        "benign,attack",
        "--live-logdir",
        str(root / "agentdojo_logs"),
        "--local-llm-port",
        str(port),
        "--live-timeout-seconds",
        str(timeout),
    ]
    if mode == "smoke":
        command.extend(["--live-user-task", "user_task_0", "--live-injection-task", "injection_task_0"])
    return command


def status(root: Path) -> dict[str, Any]:
    manifest_path = root / "protocol_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    log_files = list((root / "agentdojo_logs").glob("**/*.json")) if (root / "agentdojo_logs").exists() else []
    audit_path = root / "runtime_audit.jsonl"
    audit_rows = sum(1 for line in audit_path.open(encoding="utf-8") if line.strip()) if audit_path.exists() else 0
    pid_path = root / "runner.pid"
    running = False
    pid = None
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            running = True
        except (OSError, ValueError):
            running = False
    return {
        "status": manifest.get("status", "not_started"),
        "running": running,
        "pid": pid,
        "raw_json_logs": len(log_files),
        "audit_rows": audit_rows,
        "run_root": str(root.relative_to(ROOT)),
    }


def main() -> int:
    args = parse_args()
    root = run_root(args.mode if args.mode != "status" else "full")
    if args.mode == "status":
        print(json.dumps(status(root), indent=2, sort_keys=True))
        return 0
    root.mkdir(parents=True, exist_ok=True)
    (root / "runner.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
    manifest = protocol_manifest(args.mode, args.port, args.context)
    write_json(root / "protocol_manifest.json", manifest)
    server: subprocess.Popen[str] | None = None
    try:
        server = start_server(root, args.port, args.context)
        env = {
            **os.environ,
            "CUDA_VISIBLE_DEVICES": "",
            "PYTHONPATH": str(ROOT / "code"),
            "E77_PLAN_CACHE": str(root / "plan_cache.json"),
            "E77_AUDIT_JSONL": str(root / "runtime_audit.jsonl"),
            "E77_RUNTIME_CATALOG": str(ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"),
            "E77_REGISTERED_DESCRIPTOR_JSONL": str(RESULTS / "e77_registered_effect_diff_descriptors.jsonl"),
            "E77_PLANNER_PORT": str(args.port),
            "E77_AGENT_MAX_TOKENS": "4096",
            "E77_MAX_PLAN_REVISIONS": "3",
            "E77_PLANNER_REPAIR_ATTEMPTS": "1",
            "E77_REVISION_MAX_TOKENS": "2048",
        }
        completed = subprocess.run(
            live_command(args.mode, root, args.port, args.timeout),
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=args.timeout or None,
        )
        (root / "runner_stdout.log").write_text(completed.stdout, encoding="utf-8")
        (root / "runner_stderr.log").write_text(completed.stderr, encoding="utf-8")
        shared_status = RESULTS / "e75_agentdojo_official_live_run_status.json"
        command_status = json.loads(shared_status.read_text(encoding="utf-8")) if shared_status.exists() else {}
        write_json(root / "command_status.json", command_status)
        manifest.update(
            {
                "status": "runner_completed" if completed.returncode == 0 else "runner_failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "runner_returncode": completed.returncode,
                "command_status": str((root / "command_status.json").relative_to(ROOT)),
            }
        )
        write_json(root / "protocol_manifest.json", manifest)
        print(json.dumps(status(root), indent=2, sort_keys=True))
        return completed.returncode
    except BaseException as exc:
        manifest.update(
            {
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error": repr(exc),
            }
        )
        write_json(root / "protocol_manifest.json", manifest)
        raise
    finally:
        if server is not None and server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
