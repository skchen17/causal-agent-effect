from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .io_utils import write_json


DEFAULT_MODEL = "models/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf"
DEFAULT_STATE = "runs/tool_effect_fragmentation_phase5/local_server_state.json"
DEFAULT_LOG = "runs/tool_effect_fragmentation_phase5/local_server.log"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage the Phase 5 local OpenAI-compatible GGUF server.")
    parser.add_argument("action", choices=("start", "status", "stop", "health"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--state", default=DEFAULT_STATE)
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--model-alias", default="Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf")
    parser.add_argument("--n-gpu-layers", type=int, default=-1)
    parser.add_argument("--n-ctx", type=int, default=16384)
    parser.add_argument("--gpu", default="1")
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def health(base_url: str, timeout: float = 5.0) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/models"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {"ok": True, "url": url, "payload": payload}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return {"ok": False, "url": url, "error": f"{type(error).__name__}: {error}"}


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def start_server(
    root: Path,
    *,
    model: Path,
    state_path: Path,
    log_path: Path,
    host: str,
    port: int,
    model_alias: str,
    n_gpu_layers: int,
    n_ctx: int,
    gpu: str,
    timeout: int,
) -> dict[str, Any]:
    if not model.exists():
        raise FileNotFoundError(model)
    base_url = f"http://{host}:{port}/v1"
    existing = load_state(state_path)
    if existing and process_alive(int(existing.get("pid", -1))) and health(base_url)["ok"]:
        return existing

    state_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "llama_cpp.server",
        "--model",
        str(model),
        "--model_alias",
        model_alias,
        "--host",
        host,
        "--port",
        str(port),
        "--n_gpu_layers",
        str(n_gpu_layers),
        "--n_ctx",
        str(n_ctx),
    ]
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpu
    with log_path.open("ab") as log_handle:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    started = time.time()
    check = health(base_url)
    while not check["ok"] and time.time() - started < timeout and process.poll() is None:
        time.sleep(2)
        check = health(base_url)
    state = {
        "schema_version": "tool_effect_fragmentation_phase5_local_server_v1",
        "pid": process.pid,
        "command": command,
        "base_url": base_url,
        "model_path": str(model),
        "model_alias": model_alias,
        "model_sha256": sha256_file(model),
        "cuda_visible_devices": gpu,
        "n_gpu_layers": n_gpu_layers,
        "n_ctx": n_ctx,
        "log_path": str(log_path),
        "started_at_unix": started,
        "health": check,
    }
    write_json(state_path, state)
    if not check["ok"]:
        state["status"] = "failed"
        write_json(state_path, state)
        raise RuntimeError(f"Local server failed health gate: {check}")
    state["status"] = "running"
    write_json(state_path, state)
    return state


def stop_server(state_path: Path) -> dict[str, Any]:
    state = load_state(state_path) or {"status": "not_started"}
    pid = int(state.get("pid", -1))
    if pid > 0 and process_alive(pid):
        os.killpg(pid, signal.SIGTERM)
        state["status"] = "stopped"
        state["stopped_at_unix"] = time.time()
        write_json(state_path, state)
    return state


def load_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    state_path = root / args.state
    if args.action == "start":
        result = start_server(
            root,
            model=root / args.model,
            state_path=state_path,
            log_path=root / args.log,
            host=args.host,
            port=args.port,
            model_alias=args.model_alias,
            n_gpu_layers=args.n_gpu_layers,
            n_ctx=args.n_ctx,
            gpu=args.gpu,
            timeout=args.timeout,
        )
    elif args.action == "stop":
        result = stop_server(state_path)
    elif args.action == "health":
        result = health(f"http://{args.host}:{args.port}/v1")
    else:
        result = load_state(state_path) or {"status": "not_started"}
        if result.get("pid"):
            result["process_alive"] = process_alive(int(result["pid"]))
            result["health"] = health(result.get("base_url", f"http://{args.host}:{args.port}/v1"))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
