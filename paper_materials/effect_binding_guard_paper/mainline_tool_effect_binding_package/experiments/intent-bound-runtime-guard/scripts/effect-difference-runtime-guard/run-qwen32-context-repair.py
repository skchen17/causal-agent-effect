#!/usr/bin/env python3
"""Rerun only the Qwen32 rows affected by context-length failures."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
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
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
MODEL = Path(
    "/data/CSK/causal-agent-safety-research/models/"
    "Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"
)
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
PYTHON = (
    ROOT
    / "experiments/unified-agent-security-baselines/runs/"
    "unified-agent-security-comparison/agentdojo-env/bin/python"
)
EXPERIMENT = ROOT / "experiments/intent-bound-runtime-guard"
FULL_RUN = EXPERIMENT / "runs/effect-difference-runtime-guard/recovery-normalization-qwen32-full"
REPAIR_STAGE = os.environ.get("QWEN32_REPAIR_STAGE", "r1")
RUN_NAME = os.environ.get("QWEN32_REPAIR_RUN_NAME", "qwen32-context-repair")
RUN_ROOT = EXPERIMENT / "runs/effect-difference-runtime-guard" / RUN_NAME
RESULTS = EXPERIMENT / "results/effect-difference-runtime-guard"
DESCRIPTORS = RESULTS / "registered-effect-diff-descriptors.jsonl"
CATALOG = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
)
PATCH_MODULE = (
    "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard."
    "agentdojo_e77_runtime_patch"
)
PORT = 18088
CONTEXT = int(os.environ.get("QWEN32_REPAIR_CONTEXT", "73728"))
N_GPU_LAYERS = int(os.environ.get("QWEN32_REPAIR_GPU_LAYERS", "65"))
KV_CACHE_TYPE = os.environ.get("QWEN32_REPAIR_KV_TYPE", "f16")
KV_CACHE_TYPE_IDS = {"f16": "1", "q8_0": "8"}
if KV_CACHE_TYPE not in KV_CACHE_TYPE_IDS:
    raise ValueError(f"unsupported QWEN32_REPAIR_KV_TYPE: {KV_CACHE_TYPE}")
RUNTIME_VERSION = "effect_diff_runtime_recovery_normalization_v2"

# These are exactly the official rows flagged by the completed 726-key run's
# post-tool empty-assistant/context diagnostic.
REPAIR_GROUPS_R1 = [
    {"mode": "benign", "user_task_id": "user_task_35", "injection_task_ids": []},
    {
        "mode": "attack",
        "user_task_id": "user_task_34",
        "injection_task_ids": ["injection_task_1", "injection_task_3"],
    },
    {
        "mode": "attack",
        "user_task_id": "user_task_35",
        "injection_task_ids": [
            "injection_task_1",
            "injection_task_2",
            "injection_task_3",
            "injection_task_4",
            "injection_task_5",
        ],
    },
    {
        "mode": "attack",
        "user_task_id": "user_task_25",
        "injection_task_ids": ["injection_task_4"],
    },
    {
        "mode": "attack",
        "user_task_id": "user_task_38",
        "injection_task_ids": [
            "injection_task_0",
            "injection_task_1",
            "injection_task_2",
        ],
    },
]

# R2 contains only the two R1 rows that exceeded 73,728 tokens and the four
# rows that R1 did not reach after failing closed.
REPAIR_GROUPS_R2 = [
    {
        "mode": "attack",
        "user_task_id": "user_task_35",
        "injection_task_ids": ["injection_task_2", "injection_task_4"],
    },
    {
        "mode": "attack",
        "user_task_id": "user_task_25",
        "injection_task_ids": ["injection_task_4"],
    },
    {
        "mode": "attack",
        "user_task_id": "user_task_38",
        "injection_task_ids": [
            "injection_task_0",
            "injection_task_1",
            "injection_task_2",
        ],
    },
]
REPAIR_GROUPS_R3 = [
    {
        "mode": "attack",
        "user_task_id": "user_task_38",
        "injection_task_ids": ["injection_task_1", "injection_task_2"],
    },
]
REPAIR_GROUPS_BY_STAGE = {
    "r1": REPAIR_GROUPS_R1,
    "r2": REPAIR_GROUPS_R2,
    "r3": REPAIR_GROUPS_R3,
}
if REPAIR_STAGE not in REPAIR_GROUPS_BY_STAGE:
    raise ValueError(f"unsupported QWEN32_REPAIR_STAGE: {REPAIR_STAGE}")
REPAIR_GROUPS = REPAIR_GROUPS_BY_STAGE[REPAIR_STAGE]
EXPECTED_REPAIR_ROWS = sum(
    len(group["injection_task_ids"]) if group["mode"] == "attack" else 1
    for group in REPAIR_GROUPS
)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def healthy() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def start_server() -> tuple[subprocess.Popen[str], Any]:
    server_log = RUN_ROOT / "llama_cpp_server.log"
    handle = server_log.open("a", encoding="utf-8")
    command = [
        "/home/user/anaconda3/bin/python",
        "-m",
        "llama_cpp.server",
        "--model",
        str(MODEL),
        "--model_alias",
        "qwen3_32b_context_repair",
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT),
        "--n_gpu_layers",
        str(N_GPU_LAYERS),
        "--split_mode",
        "1",
        "--tensor_split",
        "0.5",
        "0.5",
        "--n_ctx",
        str(CONTEXT),
        "--n_batch",
        "1024",
        "--n_ubatch",
        "512",
        "--flash_attn",
        "true",
        "--type_k",
        KV_CACHE_TYPE_IDS[KV_CACHE_TYPE],
        "--type_v",
        KV_CACHE_TYPE_IDS[KV_CACHE_TYPE],
    ]
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"},
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    (RUN_ROOT / "server.pid").write_text(f"{process.pid}\n", encoding="utf-8")
    for _ in range(300):
        if process.poll() is not None:
            handle.close()
            raise RuntimeError(f"Qwen32 server exited with {process.returncode}")
        if healthy():
            return process, handle
        time.sleep(2)
    process.terminate()
    handle.close()
    raise TimeoutError("Qwen32 context-repair server did not become healthy")


def expected_path(group: dict[str, Any], injection_task_id: str | None) -> Path:
    attack = "important_instructions" if injection_task_id else "none"
    injection = injection_task_id or "none"
    return (
        RUN_ROOT
        / "agentdojo_logs/local-ours_e77_effect_diff_runtime/workspace"
        / group["user_task_id"]
        / attack
        / f"{injection}.json"
    )


def message_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(item.get("content", item.get("text", "")))
            if isinstance(item, dict)
            else str(item)
            for item in content
        )
    return str(content)


def has_post_tool_empty(messages: list[dict[str, Any]]) -> bool:
    for index, message in enumerate(messages[1:], 1):
        if message.get("role") == "assistant" and not message_text(message.get("content")).strip():
            if any(previous.get("role") == "tool" for previous in messages[:index]):
                return True
    return False


def benchmark_command(group: dict[str, Any]) -> list[str]:
    command = [
        str(PYTHON),
        "-m",
        "agentdojo.scripts.benchmark",
        "--model",
        "LOCAL",
        "--benchmark-version",
        "v1.1.2",
        "--suite",
        "workspace",
        "--tool-delimiter",
        "user",
        "--logdir",
        str(RUN_ROOT / "agentdojo_logs"),
        "--module-to-load",
        PATCH_MODULE,
        "--user-task",
        group["user_task_id"],
        "--force-rerun",
    ]
    if group["mode"] == "attack":
        command.extend(["--attack", "important_instructions"])
        for injection_task_id in group["injection_task_ids"]:
            command.extend(["--injection-task", injection_task_id])
    return command


def main() -> int:
    required = (MODEL, PYTHON, DESCRIPTORS, CATALOG, FULL_RUN / "plan_cache.json")
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"context-repair inputs missing: {missing}")
    if sha256(MODEL) != MODEL_SHA256:
        raise ValueError("Qwen32 checkpoint hash changed")

    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    repair_cache = RUN_ROOT / "plan_cache.json"
    if not repair_cache.exists():
        shutil.copy2(FULL_RUN / "plan_cache.json", repair_cache)
    protocol = {
        "experiment": f"Qwen3-32B targeted context repair {REPAIR_STAGE}",
        "repair_stage": REPAIR_STAGE,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_full_run": str(FULL_RUN.relative_to(ROOT)),
        "runtime_version": RUNTIME_VERSION,
        "agentdojo_version": "v1.1.2",
        "suite": "workspace",
        "repair_groups": REPAIR_GROUPS,
        "expected_official_repair_rows": EXPECTED_REPAIR_ROWS,
        "model": {
            "file_name": MODEL.name,
            "sha256": MODEL_SHA256,
            "temperature": 0.0,
            "agent_output_cap": 4096,
            "context_window": CONTEXT,
        },
        "gpu_configuration": {
            "visible_devices": [0, 1],
            "n_gpu_layers": N_GPU_LAYERS,
            "tensor_split": [0.5, 0.5],
            "flash_attention": True,
            "kv_cache_type": KV_CACHE_TYPE,
        },
        "claim_boundary": (
            "This run repairs only the 12 official rows whose original trajectories "
            "recorded context-length failures. It uses the same checkpoint, decoding "
            "temperature, output cap, descriptors, runtime, and validators; only the "
            "available context window is increased. Original full-run artifacts remain immutable."
        ),
    }
    write_json(RUN_ROOT / "protocol_manifest.json", protocol)
    env = {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": str(ROOT / "code"),
        "LOCAL_LLM_PORT": str(PORT),
        "E77_EFFECT_DIFF_RUNTIME": "1",
        "E77_PLAN_CACHE": str(repair_cache),
        "E77_AUDIT_JSONL": str(RUN_ROOT / "runtime_audit.jsonl"),
        "E77_RUNTIME_CATALOG": str(CATALOG),
        "E77_REGISTERED_DESCRIPTOR_JSONL": str(DESCRIPTORS),
        "E77_PLANNER_PORT": str(PORT),
        "E77_AGENT_MAX_TOKENS": "4096",
        "E77_MAX_PLAN_REVISIONS": "3",
        "E77_PLANNER_REPAIR_ATTEMPTS": "1",
        "E77_REVISION_MAX_TOKENS": "2048",
        "E75_LIVE_MODEL_NAME": MODEL.name,
    }

    server: subprocess.Popen[str] | None = None
    server_handle = None
    command_rows = []
    try:
        server, server_handle = start_server()
        for index, group in enumerate(REPAIR_GROUPS):
            command = benchmark_command(group)
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=None,
            )
            combined = f"{completed.stdout}\n{completed.stderr}"
            log_path = RUN_ROOT / f"runner_{index}_{group['mode']}_{group['user_task_id']}.log"
            log_path.write_text(combined, encoding="utf-8")
            row = {
                "group_index": index,
                "mode": group["mode"],
                "user_task_id": group["user_task_id"],
                "injection_task_ids": group["injection_task_ids"],
                "returncode": completed.returncode,
                "server_400_error": "400 Bad Request" in combined,
                "server_500_error": "500 Internal Server Error" in combined,
                "context_length_exceeded": "context_length_exceeded" in combined,
                "log_path": str(log_path.relative_to(ROOT)),
            }
            command_rows.append(row)
            write_json(RUN_ROOT / "command_status.json", {"commands": command_rows})
            if (
                completed.returncode != 0
                or row["server_400_error"]
                or row["server_500_error"]
                or row["context_length_exceeded"]
            ):
                raise RuntimeError(f"context repair command failed: {row}")
    finally:
        if server is not None and server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
        if server_handle is not None:
            server_handle.close()

    repaired_rows = []
    for group in REPAIR_GROUPS:
        ids = group["injection_task_ids"] if group["mode"] == "attack" else [None]
        for injection_task_id in ids:
            path = expected_path(group, injection_task_id)
            if not path.exists():
                raise FileNotFoundError(f"expected repaired row is missing: {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            repaired_rows.append(
                {
                    "suite": payload.get("suite_name"),
                    "user_task_id": payload.get("user_task_id"),
                    "injection_task_id": payload.get("injection_task_id"),
                    "utility": payload.get("utility"),
                    "security": payload.get("security"),
                    "error": payload.get("error"),
                    "post_tool_empty_assistant": has_post_tool_empty(payload.get("messages") or []),
                    "source_file": str(path.relative_to(ROOT)),
                }
            )
    clean = (
        len(repaired_rows) == EXPECTED_REPAIR_ROWS
        and all(row["error"] is None for row in repaired_rows)
        and all(row["utility"] is not None and row["security"] is not None for row in repaired_rows)
        and not any(row["post_tool_empty_assistant"] for row in repaired_rows)
    )
    server_text = (RUN_ROOT / "llama_cpp_server.log").read_text(encoding="utf-8")
    clean = clean and "400 Bad Request" not in server_text and "500 Internal Server Error" not in server_text
    report = {
        **protocol,
        "status": "passed" if clean else "failed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "commands": command_rows,
        "repaired_rows": repaired_rows,
        "n_repaired_rows": len(repaired_rows),
        "server_400_errors": server_text.count("400 Bad Request"),
        "server_500_errors": server_text.count("500 Internal Server Error"),
    }
    write_json(RUN_ROOT / "repair_report.json", report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "n_repaired_rows": report["n_repaired_rows"],
                "server_400_errors": report["server_400_errors"],
            },
            indent=2,
        )
    )
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
