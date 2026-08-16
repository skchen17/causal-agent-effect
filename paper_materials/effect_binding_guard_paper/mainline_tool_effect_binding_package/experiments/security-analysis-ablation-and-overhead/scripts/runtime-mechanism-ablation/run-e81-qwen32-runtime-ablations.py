#!/usr/bin/env python3
"""Run the E81 single-switch ablations on the reviewed AgentDojo subset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
MODEL = Path(
    "/data/CSK/causal-agent-safety-research/models/"
    "Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"
)
MODEL_ALIAS = "e81_qwen32_local"
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
MANIFESTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "authority-manifest-human-review/runtime_ready_trusted_manifests.jsonl"
)
CATALOG = ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"
PROJECTIONS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "causal-effect-projection-validation-2/trusted_security_effect_projections.jsonl"
)
RAW_REGISTRY = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "runtime-mechanism-ablation/a9_raw_descriptor_registry.jsonl"
)
BASE_RUNS = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/runs/"
    "runtime-mechanism-ablation"
)
PATCH_MODULE = (
    "src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime."
    "agentdojo_ablation_runtime_patch"
)
ABLATION_RUNTIME_SOURCE = (
    ROOT
    / "code/src/experiments/effect_binding_guard/"
    "e81_agentdojo_hardened_runtime/ablation_runtime.py"
)
PATCH_SOURCE = ABLATION_RUNTIME_SOURCE.with_name(
    "agentdojo_ablation_runtime_patch.py"
)
HARDENED_RUNTIME_SOURCE = (
    ROOT
    / "code/src/experiments/effect_binding_guard/"
    "e80_contract_obligation_hardening/runtime.py"
)
RUNNER_SOURCE = Path(__file__).resolve()
ROWS = ("A0", "A1", "A2", "A7", "A9", "A11", "A12", "A13", "A15")
ROW_LABELS = {
    "A0": "no_guard",
    "A1": "full_reviewed_effect_contract_guard",
    "A2": "tool_call_level_only",
    "A7": "no_provenance_control_binding",
    "A9": "schema_description_only_registration",
    "A11": "no_task_authority_envelope",
    "A12": "no_authorized_read_grounding",
    "A13": "omitted_fields_permissive",
    "A15": "no_replan_recovery",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--rows", default=",".join(ROWS))
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--context", type=int, default=65536)
    parser.add_argument("--attack-selection", choices=("first", "all"), default="first")
    parser.add_argument("--force-rerun", action="store_true")
    parser.add_argument("--run-tag", default="")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def server_model_id(port: int) -> str | None:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/v1/models", timeout=3
        ) as response:
            payload = json.loads(response.read().decode())
        return payload["data"][0]["id"]
    except Exception:
        return None


def start_server(
    port: int, context: int, log_path: Path
) -> subprocess.Popen[str] | None:
    existing = server_model_id(port)
    if existing is not None:
        if existing != MODEL_ALIAS:
            raise RuntimeError(
                f"port {port} serves {existing!r}, expected {MODEL_ALIAS!r}"
            )
        return None
    command = [
        "/home/user/anaconda3/bin/python",
        "-m",
        "llama_cpp.server",
        "--model",
        str(MODEL),
        "--model_alias",
        MODEL_ALIAS,
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
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"},
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for _ in range(180):
        if process.poll() is not None:
            raise RuntimeError(
                f"llama.cpp server exited with {process.returncode}; inspect {log_path}"
            )
        if server_model_id(port) == MODEL_ALIAS:
            return process
        time.sleep(2)
    process.terminate()
    raise TimeoutError(f"{MODEL_ALIAS} server did not become healthy")


def selected_tasks(scope: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in read_jsonl(MANIFESTS):
        grouped[row["suite"]].append(row["user_task_id"])
    tasks = {
        suite: sorted(set(task_ids))
        for suite, task_ids in sorted(grouped.items())
    }
    if scope == "smoke":
        targeted = {
            "banking": ["user_task_14"],
            "slack": ["user_task_0"],
            "travel": ["user_task_10"],
            "workspace": ["user_task_8"],
        }
        for suite, task_ids in targeted.items():
            if any(task_id not in tasks[suite] for task_id in task_ids):
                raise RuntimeError(f"targeted E81 smoke task missing for {suite}")
        return targeted
    return tasks


def official_injection_tasks() -> dict[str, list[str]]:
    code = (
        "from agentdojo.task_suite.load_suites import get_suite; import json; "
        "print(json.dumps({s: sorted(get_suite('v1.1.2', s).injection_tasks) "
        "for s in ['banking','slack','travel','workspace']}))"
    )
    completed = subprocess.run(
        [str(PYTHON), "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return json.loads(completed.stdout)


def benchmark_command(
    *,
    suite: str,
    mode: str,
    task_ids: list[str],
    injection_task_id: str | None,
    row_id: str,
    logdir: Path,
    force_rerun: bool,
) -> list[str]:
    command = [
        str(PYTHON),
        "-m",
        "agentdojo.scripts.benchmark",
        "--model",
        "LOCAL",
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
    if row_id != "A0":
        command.extend(["--module-to-load", PATCH_MODULE])
    if force_rerun:
        command.append("--force-rerun")
    return command


def run_command(
    command: list[str], env: dict[str, str], log_path: Path
) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if completed.returncode != 0:
        raise RuntimeError(
            f"benchmark command failed with {completed.returncode}; inspect {log_path}"
        )


def main() -> int:
    args = parse_args()
    rows = [item.strip().upper() for item in args.rows.split(",") if item.strip()]
    unknown = sorted(set(rows) - set(ROWS))
    if unknown or len(rows) != len(set(rows)):
        raise ValueError(f"invalid or duplicate E81 rows: {unknown or rows}")
    required = (
        PYTHON,
        MODEL,
        MANIFESTS,
        CATALOG,
        PROJECTIONS,
        RAW_REGISTRY,
        ABLATION_RUNTIME_SOURCE,
        PATCH_SOURCE,
        HARDENED_RUNTIME_SOURCE,
        RUNNER_SOURCE,
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"E81 inputs missing: {missing}")
    observed_sha = file_sha256(MODEL)
    if observed_sha != MODEL_SHA256:
        raise RuntimeError(
            f"Qwen32 checkpoint hash mismatch: {observed_sha}"
        )

    tasks = selected_tasks(args.scope)
    injections = official_injection_tasks()
    suffix = f"-{args.run_tag}" if args.run_tag else ""
    run_root = BASE_RUNS / f"e81-qwen32-{args.scope}{suffix}"
    run_root.mkdir(parents=True, exist_ok=True)
    selected_injections: dict[str, Any] = {
        suite: (
            values[0] if args.attack_selection == "first" else list(values)
        )
        for suite, values in injections.items()
    }
    n_benign = sum(len(value) for value in tasks.values())
    n_attack = (
        n_benign
        if args.attack_selection == "first"
        else sum(len(tasks[suite]) * len(injections[suite]) for suite in tasks)
    )
    protocol = {
        "experiment": "E81-Qwen32-runtime-mechanism-ablation",
        "scope": args.scope,
        "agentdojo_version": "v1.1.2",
        "model_artifact": MODEL.name,
        "model_sha256": observed_sha,
        "model_alias": MODEL_ALIAS,
        "context_window": args.context,
        "gpu_configuration": {
            "visible_devices": "0,1",
            "n_gpu_layers": 65,
            "tensor_split": [0.35, 0.65],
        },
        "rows": rows,
        "row_labels": {row_id: ROW_LABELS[row_id] for row_id in rows},
        "tasks": tasks,
        "attack_selection": (
            "first_sorted_official_injection_task_per_suite"
            if args.attack_selection == "first"
            else "all_official_injection_tasks_per_suite"
        ),
        "selected_injection_tasks": selected_injections,
        "expected_benign_cases_per_row": n_benign,
        "expected_attack_cases_per_row": n_attack,
        "expected_cases_per_row": n_benign + n_attack,
        "source_hashes": {
            "authority_manifests": file_sha256(MANIFESTS),
            "runtime_catalog": file_sha256(CATALOG),
            "trusted_effect_projections": file_sha256(PROJECTIONS),
            "round0_descriptor_registry": file_sha256(RAW_REGISTRY),
            "ablation_runtime": file_sha256(ABLATION_RUNTIME_SOURCE),
            "agentdojo_ablation_patch": file_sha256(PATCH_SOURCE),
            "hardened_runtime": file_sha256(HARDENED_RUNTIME_SOURCE),
            "runner": file_sha256(RUNNER_SOURCE),
        },
        "single_variable_gate": {
            row_id: ROW_LABELS[row_id] for row_id in rows if row_id != "A0"
        },
        "claim_boundary": (
            "E81 uses Qwen3-32B on the reviewed 26-task AgentDojo v1.1.2 "
            "subset. Full scope crosses those tasks with all 169 official "
            "injection pairs. It is not the full 726-case benchmark."
        ),
    }
    (run_root / "protocol_manifest.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    server = start_server(
        args.port, args.context, run_root / "llama_cpp_server.log"
    )
    try:
        for row_id in rows:
            logdir = run_root / "agentdojo_logs" / row_id.lower()
            logdir.mkdir(parents=True, exist_ok=True)
            audit_path = run_root / f"{row_id.lower()}_runtime_audit.jsonl"
            if audit_path.exists() and args.force_rerun:
                audit_path.unlink()
            env = {
                **os.environ,
                "CUDA_VISIBLE_DEVICES": "",
                "PYTHONPATH": str(ROOT / "code"),
                "LOCAL_LLM_PORT": str(args.port),
            }
            if row_id != "A0":
                env.update(
                    {
                        "E81_RUNTIME_ABLATION": "1",
                        "E81_ABLATION_ROW": row_id,
                        "E81_RUNTIME_MANIFESTS": str(MANIFESTS),
                        "E81_RUNTIME_CATALOG": str(CATALOG),
                        "E81_TRUSTED_EFFECT_PROJECTIONS": str(PROJECTIONS),
                        "E81_RAW_DESCRIPTOR_REGISTRY": str(RAW_REGISTRY),
                        "E81_RUNTIME_AUDIT_JSONL": str(audit_path),
                    }
                )
            for suite, task_ids in sorted(tasks.items()):
                for mode in ("benign", "attack"):
                    run_command(
                        benchmark_command(
                            suite=suite,
                            mode=mode,
                            task_ids=task_ids,
                            injection_task_id=(
                                injections[suite][0]
                                if args.attack_selection == "first"
                                else None
                            ),
                            row_id=row_id,
                            logdir=logdir,
                            force_rerun=args.force_rerun,
                        ),
                        env,
                        run_root / f"runner_{row_id.lower()}.log",
                    )
    finally:
        if server is not None and server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()

    (run_root / "run_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "scope": args.scope,
                "rows": rows,
                "expected_cases_per_row": n_benign + n_attack,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "run_root": str(run_root.relative_to(ROOT)),
                "rows": rows,
                "expected_cases_per_row": n_benign + n_attack,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
