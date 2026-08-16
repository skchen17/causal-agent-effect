#!/usr/bin/env python3
"""Run and finalize the frozen bounded public-family AgentDojo search."""

from __future__ import annotations

import argparse
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

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75 import (
    official_live_method_config,
)
from src.experiments.effect_binding_guard.e88_agentdojo_attack_dataset.bounded_search import (
    EVALUATION_ROOT,
    FAMILIES,
    METHODS,
    MODEL,
    MODEL_SHA256,
    RESULT_ROOT,
    ROOT,
    RUN_ROOT,
    SUITES,
    sha256_file,
    summarize_predictions,
    validate_preregistration,
)


AGENTDOJO_PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("run", "finalize", "both"), default="both")
    parser.add_argument("--port", type=int, default=18087)
    parser.add_argument("--model-id", default="qwen3_32b_local")
    parser.add_argument("--wait-pid", type=int, action="append", default=[])
    parser.add_argument("--force-rerun", action="store_true")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def load_protocol() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    protocol = json.loads(
        (EVALUATION_ROOT / "preregistration.json").read_text(encoding="utf-8")
    )
    cases = read_jsonl(EVALUATION_ROOT / "locked-case-manifest.jsonl")
    validate_preregistration(protocol, cases)
    if not MODEL.exists() or sha256_file(MODEL) != MODEL_SHA256:
        raise ValueError("Qwen3-32B artifact is missing or changed")
    return protocol, cases


def server_healthy(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        pass
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/v1/models", timeout=3
        ) as response:
            return response.status == 200
    except Exception:
        return False


def start_server(port: int, model_id: str) -> tuple[subprocess.Popen[bytes] | None, Any]:
    if server_healthy(port):
        return None, None
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    handle = (RUN_ROOT / "qwen32-server.log").open("ab")
    command = [
        "/home/user/anaconda3/bin/python",
        "-m",
        "llama_cpp.server",
        "--model",
        str(MODEL),
        "--model_alias",
        model_id,
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
        "65536",
        "--n_batch",
        "1024",
        "--n_ubatch",
        "512",
        "--flash_attn",
        "true",
    ]
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"},
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    for _ in range(240):
        if process.poll() is not None:
            raise RuntimeError("bounded-search model server exited during startup")
        if server_healthy(port):
            return process, handle
        time.sleep(2)
    process.terminate()
    raise TimeoutError("bounded-search model server health timeout")


def wait_for_pids(pids: list[int]) -> None:
    pending = {pid for pid in pids if pid > 0}
    while pending:
        pending = {pid for pid in pending if Path(f"/proc/{pid}").exists()}
        if pending:
            write_json(
                RUN_ROOT / "queue-status.json",
                {"status": "waiting", "wait_pids": sorted(pending)},
            )
            time.sleep(60)


def grouped_cases(cases: list[dict[str, Any]]) -> dict[tuple[str, str], list[str]]:
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for case in cases:
        grouped[(case["suite"], case["injection_task_id"])].append(
            case["user_task_id"]
        )
    return {
        key: sorted(set(user_task_ids))
        for key, user_task_ids in grouped.items()
    }


def benchmark_command(
    *,
    method: str,
    family: str,
    suite: str,
    injection_task_id: str,
    user_task_ids: list[str],
    port: int,
    model_id: str,
    force_rerun: bool,
) -> tuple[list[str], dict[str, str], Path]:
    config = official_live_method_config(method)
    logdir = RUN_ROOT / "logs" / method / family
    logdir.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        **config.get("env", {}),
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": str(ROOT / "code"),
        "LOCAL_LLM_PORT": str(port),
        "E77_PLAN_CACHE": str(RUN_ROOT / "cache/e77-plan-cache.json"),
        "E77_AUDIT_JSONL": str(RUN_ROOT / "audit/e77-runtime-audit.jsonl"),
        "E77_RUNTIME_CATALOG": str(
            ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"
        ),
    }
    command = [
        str(AGENTDOJO_PYTHON),
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
        "--attack",
        family,
        "--injection-task",
        injection_task_id,
    ]
    for user_task_id in user_task_ids:
        command.extend(["--user-task", user_task_id])
    if config.get("defense"):
        command.extend(["--defense", config["defense"]])
    for module in config.get("modules_to_load", []):
        command.extend(["--module-to-load", module])
    if force_rerun:
        command.append("--force-rerun")
    return command, env, logdir


def execute(
    protocol: dict[str, Any],
    cases: list[dict[str, Any]],
    *,
    port: int,
    model_id: str,
    force_rerun: bool,
) -> None:
    groups = grouped_cases(cases)
    for method in METHODS:
        for family in protocol["development_selected_family_order"]:
            for (suite, injection_task_id), user_task_ids in sorted(groups.items()):
                write_json(
                    RUN_ROOT / "queue-status.json",
                    {
                        "status": "running",
                        "method": method,
                        "attack_family": family,
                        "suite": suite,
                        "injection_task_id": injection_task_id,
                        "n_user_tasks": len(user_task_ids),
                    },
                )
                command, env, _ = benchmark_command(
                    method=method,
                    family=family,
                    suite=suite,
                    injection_task_id=injection_task_id,
                    user_task_ids=user_task_ids,
                    port=port,
                    model_id=model_id,
                    force_rerun=force_rerun,
                )
                with (RUN_ROOT / "runner.log").open("a", encoding="utf-8") as handle:
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
                        f"benchmark failed: {method}/{family}/{suite}/"
                        f"{injection_task_id}"
                    )


def collect_predictions(
    protocol: dict[str, Any], cases: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    case_index = {
        (row["suite"], row["user_task_id"], row["injection_task_id"]): row
        for row in cases
    }
    predictions: list[dict[str, Any]] = []
    for method in METHODS:
        for family in FAMILIES:
            root = RUN_ROOT / "logs" / method / family
            for path in sorted(root.rglob("*.json")):
                try:
                    row = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if row.get("attack_type") != family:
                    continue
                relative = path.relative_to(root).parts
                suite = next((part for part in relative if part in SUITES), None)
                user_task_id = row.get("user_task_id")
                injection_task_id = row.get("injection_task_id") or path.stem
                case = case_index.get((suite, user_task_id, injection_task_id))
                if case is None:
                    continue
                predictions.append(
                    {
                        "method": method,
                        "case_id": case["case_id"],
                        "suite": suite,
                        "user_task_id": user_task_id,
                        "injection_task_id": injection_task_id,
                        "attack_family": family,
                        "attack_success": row.get("security") is True,
                        "user_utility": row.get("utility") is True,
                        "error": row.get("error") is not None,
                        "result_sha256": sha256_file(path),
                        "result_source": str(path.relative_to(ROOT)),
                    }
                )
    predictions.sort(
        key=lambda row: (row["method"], row["case_id"], row["attack_family"])
    )
    return predictions


def finalize(
    protocol: dict[str, Any], cases: list[dict[str, Any]]
) -> dict[str, Any]:
    predictions = collect_predictions(protocol, cases)
    report = summarize_predictions(predictions, protocol, cases)
    write_jsonl(RESULT_ROOT / "predictions.jsonl", predictions)
    write_json(RESULT_ROOT / "bounded-search-report.json", report)
    lines = [
        "# Bounded Public-Family Search",
        "",
        f"Status: `{report['status']}`.",
        "",
        f"- Locked AgentDojo keys: `{report['locked_cases']}`.",
        f"- Executed variant rows: `{report['variant_rows']}`.",
        f"- Frozen family order: `{', '.join(protocol['development_selected_family_order'])}`.",
        "",
        "| Method | N | Worst-of-4 attacks | ASR | Terminal utility | Rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["search_metrics"]:
        lines.append(
            f"| {row['method']} | {row['n']} | {row['attack_successes']} | "
            f"{row['attack_success_rate']:.3f} | "
            f"{row['terminal_user_utility_successes']} | "
            f"{row['terminal_user_utility_rate']:.3f} |"
        )
    lines.extend(["", "## Paired Exact Tests", ""])
    for metric, stats in report["paired_statistics"].items():
        lines.append(
            f"- `{metric}`: reference-only `{stats['reference_only']}`, "
            f"guard-only `{stats['method_only']}`, exact two-sided McNemar "
            f"`p={stats['exact_mcnemar_two_sided_p']:.6f}`."
        )
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    (RESULT_ROOT / "bounded-search-report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    write_json(
        RUN_ROOT / "queue-status.json",
        {"status": "passed", "variant_rows": report["variant_rows"]},
    )
    return report


def main() -> int:
    args = parse_args()
    protocol, cases = load_protocol()
    wait_for_pids(args.wait_pid)
    server: subprocess.Popen[bytes] | None = None
    server_log = None
    try:
        if args.mode in {"run", "both"}:
            server, server_log = start_server(args.port, args.model_id)
            execute(
                protocol,
                cases,
                port=args.port,
                model_id=args.model_id,
                force_rerun=args.force_rerun,
            )
        if args.mode in {"finalize", "both"}:
            report = finalize(protocol, cases)
            print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        if server is not None and server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
        if server_log is not None:
            server_log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
