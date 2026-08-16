#!/usr/bin/env python3
"""Run a fixed same-model AgentDojo subset for reviewed E84 authority manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import time
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir()
)
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
MODELS = {
    "qwen9b": {
        "path": Path(
            "/data/CSK/causal-agent-safety-research/models/"
            "Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf"
        ),
        "alias": "e84_qwen9b_local",
        "gpu_visible": "1",
        "default_context": 32768,
        "dual_gpu": False,
    },
    "qwen32": {
        "path": Path(
            "/data/CSK/causal-agent-safety-research/models/"
            "Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"
        ),
        "alias": "e84_qwen32_local",
        "gpu_visible": "0,1",
        "default_context": 65536,
        "dual_gpu": True,
    },
}
MANIFESTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/authority-manifest-human-review/"
    "runtime_ready_trusted_manifests.jsonl"
)
CATALOG = ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"
BASE_RUNS = ROOT / "experiments/security-analysis-ablation-and-overhead/runs/runtime-mechanism-ablation"
RESULTS = ROOT / "experiments/security-analysis-ablation-and-overhead/results/runtime-mechanism-ablation"
PATCH_MODULE = (
    "src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime."
    "agentdojo_reviewed_runtime_patch"
)
METHOD_MODULES = {
    "no_guard": None,
    "e84_reviewed_authority": PATCH_MODULE,
    "prompt_sandwiching": (
        "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison."
        "agentdojo_prompt_sandwiching_patch"
    ),
    "promptarmor_local": (
        "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison."
        "agentdojo_promptarmor_local_patch"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("smoke", "pilot"), default="smoke")
    parser.add_argument("--model", choices=tuple(MODELS), default="qwen9b")
    parser.add_argument("--port", type=int, default=18084)
    parser.add_argument("--context", type=int, default=0)
    parser.add_argument(
        "--server-model-id",
        default="",
        help="OpenAI-compatible model id; defaults to the runner's model alias.",
    )
    parser.add_argument("--methods", default="no_guard,e84_reviewed_authority")
    parser.add_argument(
        "--modes",
        choices=("benign", "attack", "both"),
        default="both",
    )
    parser.add_argument("--attack-selection", choices=("first", "all"), default="first")
    parser.add_argument(
        "--task-selection",
        choices=("manifest", "all"),
        default="manifest",
    )
    parser.add_argument("--manifests", type=Path, default=MANIFESTS)
    parser.add_argument("--force-rerun", action="store_true")
    parser.add_argument("--run-tag", default="")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def server_healthy(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        pass
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def build_server_command(
    model: dict[str, Any],
    port: int,
    context: int,
) -> list[str]:
    command = [
        "/home/user/anaconda3/bin/python",
        "-m",
        "llama_cpp.server",
        "--model",
        str(model["path"]),
        "--model_alias",
        str(model["alias"]),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--n_gpu_layers",
        "-1",
    ]
    if model["dual_gpu"]:
        command.extend(["--split_mode", "1", "--tensor_split", "0.5", "0.5"])
    command.extend(
        [
            "--n_ctx",
            str(context),
            "--n_batch",
            "1024",
            "--n_ubatch",
            "512",
            "--flash_attn",
            "true",
        ]
    )
    return command


def start_server(
    model: dict[str, Any],
    port: int,
    context: int,
    log_path: Path,
) -> subprocess.Popen[str] | None:
    if server_healthy(port):
        return None
    command = build_server_command(model, port, context)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": str(model["gpu_visible"])},
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for _ in range(180):
        if process.poll() is not None:
            raise RuntimeError(f"llama.cpp server exited with {process.returncode}; inspect {log_path}")
        if server_healthy(port):
            return process
        time.sleep(2)
    process.terminate()
    raise TimeoutError(f"{model['alias']} server did not become healthy")


def selected_tasks(
    scope: str,
    task_selection: str,
    manifests: Path,
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    if task_selection == "manifest":
        for row in read_jsonl(manifests):
            grouped[row["suite"]].append(row["user_task_id"])
    else:
        code = (
            "from agentdojo.task_suite.load_suites import get_suite; "
            "import json; "
            "print(json.dumps({s: sorted(get_suite('v1.1.2', s).user_tasks) "
            "for s in ['banking','slack','travel','workspace']}))"
        )
        completed = subprocess.run(
            [str(PYTHON), "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        grouped.update(json.loads(completed.stdout))
    out = {suite: sorted(set(task_ids)) for suite, task_ids in grouped.items()}
    if scope == "smoke":
        return {suite: task_ids[:1] for suite, task_ids in out.items()}
    return out


def benchmark_command(
    *, suite: str, mode: str, task_ids: list[str], injection_task_id: str | None,
    method: str, logdir: Path, force_rerun: bool, model_id: str
) -> list[str]:
    command = [
        str(PYTHON),
        "-m",
        "agentdojo.scripts.benchmark",
        "--model",
        "LOCAL",
        "--model-id",
        model_id,
        "--benchmark-version",
        "v1.1.2",
        "--suite",
        suite,
        "--tool-delimiter",
        "user",
        "--logdir",
        str(logdir),
    ]
    for task_id in task_ids:
        command.extend(["--user-task", task_id])
    if mode == "attack":
        command.extend(["--attack", "important_instructions"])
        if injection_task_id is not None:
            command.extend(["--injection-task", injection_task_id])
    module = METHOD_MODULES[method]
    if module:
        command.extend(["--module-to-load", module])
    if force_rerun:
        command.append("--force-rerun")
    return command


def run_command(command: list[str], env: dict[str, str], log_path: Path) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        completed = subprocess.run(command, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"benchmark command failed with {completed.returncode}; inspect {log_path}")


def main() -> int:
    args = parse_args()
    model = MODELS[args.model]
    model_path = Path(model["path"])
    if not model_path.exists():
        raise FileNotFoundError(f"model is missing: {model_path}")
    context = args.context or int(model["default_context"])
    server_model_id = args.server_model_id or str(model["alias"])
    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    if any(method not in METHOD_MODULES for method in methods):
        raise ValueError("unsupported method")
    manifests = args.manifests.resolve()
    if not manifests.exists():
        raise FileNotFoundError(f"authority manifests are missing: {manifests}")
    tasks = selected_tasks(args.scope, args.task_selection, manifests)
    injection_tasks: dict[str, list[str]] = {}
    code = (
        "from agentdojo.task_suite.load_suites import get_suite; "
        "import json; "
        "print(json.dumps({s: sorted(get_suite('v1.1.2', s).injection_tasks) "
        "for s in ['banking','slack','travel','workspace']}))"
    )
    completed = subprocess.run(
        [str(PYTHON), "-c", code], cwd=ROOT, text=True, capture_output=True, check=True
    )
    injection_tasks = json.loads(completed.stdout)
    suffix = f"-{args.run_tag}" if args.run_tag else ""
    run_root = BASE_RUNS / f"e84-{args.model}-{args.scope}{suffix}"
    run_root.mkdir(parents=True, exist_ok=True)
    n_benign = sum(len(value) for value in tasks.values())
    n_attack = (
        n_benign
        if args.attack_selection == "first"
        else sum(len(tasks[suite]) * len(injection_tasks[suite]) for suite in tasks)
    )
    selected_injection_tasks: dict[str, Any] = {
        suite: values[0] if args.attack_selection == "first" else values
        for suite, values in injection_tasks.items()
    }
    protocol = {
        "experiment": f"E84-{args.model}-reviewed-authority-AgentDojo-subset",
        "scope": args.scope,
        "agentdojo_version": "v1.1.2",
        "model_artifact": model_path.name,
        "model_sha256": file_sha256(model_path),
        "model_alias": model["alias"],
        "server_model_id": server_model_id,
        "context_window": context,
        "gpu_visible_to_model_server": model["gpu_visible"],
        "methods": methods,
        "tasks": tasks,
        "attack_selection": (
            "first_sorted_official_injection_task_per_suite"
            if args.attack_selection == "first"
            else "all_official_injection_tasks_per_suite"
        ),
        "selected_injection_tasks": selected_injection_tasks,
        "modes": args.modes,
        "expected_benign_cases_per_method": (
            n_benign if args.modes in {"benign", "both"} else 0
        ),
        "expected_attack_cases_per_method": (
            n_attack if args.modes in {"attack", "both"} else 0
        ),
        "expected_cases_per_method": (
            (n_benign if args.modes in {"benign", "both"} else 0)
            + (n_attack if args.modes in {"attack", "both"} else 0)
        ),
        "authority_manifest_count": len(read_jsonl(manifests)),
        "authority_manifest_path": str(manifests.relative_to(ROOT)),
        "task_selection": args.task_selection,
        "claim_boundary": (
            (
                "This uses the fixed 97-task AgentDojo v1.1.2 benign task set. "
                if args.task_selection == "all"
                else "This uses the authority-manifest task subset. "
            )
            + (
                "It uses one official injection goal per user task. "
                if args.attack_selection == "first"
                else "It uses all 169 official task-injection pairs available for these reviewed tasks. "
            )
            + "It is not the full 726-case benchmark and not evidence of production safety."
        ),
    }
    (run_root / "protocol_manifest.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    server = start_server(model, args.port, context, run_root / "llama_cpp_server.log")
    try:
        for method in methods:
            logdir = run_root / "agentdojo_logs" / method
            logdir.mkdir(parents=True, exist_ok=True)
            env = {
                **os.environ,
                "CUDA_VISIBLE_DEVICES": "",
                "PYTHONPATH": str(ROOT / "code"),
                "LOCAL_LLM_PORT": str(args.port),
            }
            if method == "prompt_sandwiching":
                env["E75_PROMPT_SANDWICHING"] = "1"
            if method == "promptarmor_local":
                env.update(
                    {
                        "E75_PROMPTARMOR_LOCAL": "1",
                        "E75_PROMPTARMOR_FAIL_CLOSED": "1",
                        "E75_PROMPTARMOR_CACHE_PATH": str(
                            run_root / "promptarmor_cache.json"
                        ),
                    }
                )
            if method == "e84_reviewed_authority":
                env.update(
                    {
                        "E84_REVIEWED_AUTHORITY_RUNTIME": "1",
                        "E84_RUNTIME_MANIFESTS": str(manifests),
                        "E84_RUNTIME_CATALOG": str(CATALOG),
                        "E84_TRUSTED_EFFECT_PROJECTIONS": str(
                            ROOT
                            / "experiments/human-authority-and-causal-validation/evaluation/"
                            "causal-effect-projection-validation-2/trusted_security_effect_projections.jsonl"
                        ),
                        "E84_RUNTIME_AUDIT_JSONL": str(run_root / "e84_runtime_audit.jsonl"),
                    }
                )
            for suite, task_ids in sorted(tasks.items()):
                modes = (
                    ("benign", "attack")
                    if args.modes == "both"
                    else (args.modes,)
                )
                for mode in modes:
                    run_command(
                        benchmark_command(
                            suite=suite,
                            mode=mode,
                            task_ids=task_ids,
                            injection_task_id=(
                                injection_tasks[suite][0]
                                if args.attack_selection == "first"
                                else None
                            ),
                            method=method,
                            logdir=logdir,
                            force_rerun=args.force_rerun,
                            model_id=server_model_id,
                        ),
                        env,
                        run_root / f"runner_{method}.log",
                    )
    finally:
        if server is not None and server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
    (run_root / "run_status.json").write_text(
        json.dumps({"status": "completed", "scope": args.scope, "methods": methods}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "completed", **protocol}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
