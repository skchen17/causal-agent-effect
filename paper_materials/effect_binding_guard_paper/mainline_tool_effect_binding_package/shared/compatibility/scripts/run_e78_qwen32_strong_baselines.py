#!/usr/bin/env python3
"""Run and validate the Qwen3-32B same-protocol AgentDojo comparison."""

from __future__ import annotations

import argparse
import csv
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


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"
RUNS = ROOT / "runs/e78_qwen32_strong_baselines"
MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
E75_MODULE = "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75"
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
PORT = 18082
EXPECTED_CASES = 726
EXPECTED_MODEL_BYTES = 19_762_149_024
EXPECTED_MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"

DIRECT_METHODS = (
    "no_guard",
    "transformers_pi_detector",
    "piguard",
    "spotlighting",
    "prompt_sandwiching",
    "promptarmor_local",
    "melon_local",
    "ours_e77_effect_diff_runtime",
)

METHOD_METADATA = {
    "no_guard": ("No defense", "AgentDojo built-in", "official_same_protocol"),
    "transformers_pi_detector": ("PI Detector", "released ProtectAI checkpoint", "official_same_protocol"),
    "piguard": ("PIGuard/InjecGuard", "released checkpoint adapter", "official_same_protocol"),
    "spotlighting": ("Spotlighting", "AgentDojo built-in prompting defense", "official_same_protocol"),
    "prompt_sandwiching": ("Prompt Sandwiching", "paper-defined adapter", "comparable_adapter"),
    "promptarmor_local": ("PromptArmor-style", "paper-defined local sanitizer", "comparable_adapter"),
    "melon_local": ("MELON-style", "masked re-execution with lexical similarity", "comparable_adapter"),
    "ours_e77_effect_diff_runtime": ("Effect-binding runtime guard", "E77", "proposed_method"),
    "attriguard": ("AttriGuard", "released Zenodo artifact", "released_artifact_adapter"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("full", "summarize"), default="full")
    parser.add_argument("--methods", default=",".join(DIRECT_METHODS))
    parser.add_argument("--skip-attriguard", action="store_true")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--context", type=int, default=65536)
    parser.add_argument("--timeout", type=int, default=0)
    parser.add_argument("--wait-pid-file", type=Path)
    parser.add_argument("--server-log", type=Path, default=RUNS / "llama_cpp_server.log")
    return parser.parse_args()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wait_for_pid_file(path: Path | None) -> None:
    if path is None or not path.exists():
        return
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        except PermissionError:
            return
        time.sleep(30)


def wait_for_model() -> None:
    while not MODEL.exists() or MODEL.stat().st_size != EXPECTED_MODEL_BYTES:
        time.sleep(30)
    observed = sha256(MODEL)
    if observed != EXPECTED_MODEL_SHA256:
        raise RuntimeError(f"Qwen3-32B checksum mismatch: expected {EXPECTED_MODEL_SHA256}, observed {observed}")


def server_healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def build_server_command(port: int, context: int) -> list[str]:
    return [
        "/home/user/anaconda3/bin/python", "-m", "llama_cpp.server",
        "--model", str(MODEL), "--model_alias", "qwen3_32b_local",
        "--host", "127.0.0.1", "--port", str(port),
        "--n_gpu_layers", "-1", "--split_mode", "1", "--tensor_split", "0.5", "0.5",
        "--n_ctx", str(context), "--n_batch", "1024", "--n_ubatch", "512", "--flash_attn", "true",
    ]


def start_server(port: int, context: int, log_path: Path) -> subprocess.Popen[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_server_command(port, context)
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"}
    handle = log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)
    for _ in range(240):
        if process.poll() is not None:
            raise RuntimeError(f"llama.cpp server exited with {process.returncode}; inspect {log_path}")
        if server_healthy(port):
            return process
        time.sleep(2)
    process.terminate()
    raise TimeoutError("Qwen3-32B llama.cpp server did not become healthy")


def run_command(command: list[str], *, env: dict[str, str], log_path: Path, timeout: int | None = None) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        completed = subprocess.run(
            command, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
            text=True, timeout=timeout or None,
        )
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}; inspect {log_path}")


def method_logdir(method: str) -> Path:
    return RUNS / "agentdojo_logs" / method


def run_direct_method(method: str, port: int, timeout: int) -> None:
    logdir = method_logdir(method)
    # The strict importer requires the method directory to exist even before
    # the first benchmark row is emitted.
    logdir.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        # The benchmark agent calls the dedicated llama.cpp server over HTTP.
        # Keep small detector checkpoints on CPU so they cannot contend for the
        # two GPUs holding Qwen3-32B and its long-context KV cache.
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": str(ROOT / "code"),
        "E77_PLAN_CACHE": str(RUNS / "cache/e77_plan_cache.json"),
        "E77_AUDIT_JSONL": str(RUNS / "audit/e77_runtime_audit.jsonl"),
        "E77_RUNTIME_CATALOG": str(ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"),
        "E75_PROMPTARMOR_CACHE_PATH": str(RUNS / "cache/promptarmor_qwen32.json"),
        "E75_MELON_LOCAL_CACHE_PATH": str(RUNS / "cache/melon_qwen32.json"),
    }
    command = [
        str(PYTHON), "-m", E75_MODULE, "--mode", "official-live-run",
        "--agentdojo-version", "v1.1.2", "--live-method", method,
        "--live-suites", "workspace,slack,travel,banking", "--live-modes", "benign,attack",
        "--live-logdir", str(logdir), "--local-llm-port", str(port),
        "--live-timeout-seconds", str(timeout),
    ]
    run_command(command, env=env, log_path=RUNS / f"runner_{method}.log")


def run_attriguard(port: int, context: int, timeout: int) -> None:
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": str(ROOT / "code")}
    command = [
        str(PYTHON), "-m", E75_MODULE, "--mode", "attriguard-sharded-run",
        "--agentdojo-version", "v1.1.2", "--attriguard-logdir", str(method_logdir("attriguard")),
        "--local-llm-port", str(port), "--live-suites", "workspace,slack,travel,banking",
        "--live-modes", "benign,attack", "--attriguard-max-workers", "1",
        "--attriguard-local-max-tokens", "4096", "--attriguard-local-context-window", str(context),
        "--attriguard-resume-all-missing", "--live-timeout-seconds", str(timeout),
    ]
    run_command(command, env=env, log_path=RUNS / "runner_attriguard.log")


def import_direct(methods: list[str]) -> dict[str, Any]:
    command = [
        str(PYTHON), "-m", E75_MODULE, "--mode", "official-live-import",
        "--agentdojo-version", "v1.1.2", "--live-logdir", str(method_logdir(methods[0])),
    ]
    for method in methods[1:]:
        command.extend(["--live-extra-logdir", str(method_logdir(method))])
    env = {**os.environ, "PYTHONPATH": str(ROOT / "code")}
    run_command(command, env=env, log_path=RUNS / "import_direct.log")
    source = RESULTS / "e75_agentdojo_official_live_import_metrics.json"
    return json.loads(source.read_text(encoding="utf-8"))


def expected_method_id(method: str) -> str:
    mapping = {
        "no_guard": "agentdojo_live_local_no_guard",
        "transformers_pi_detector": "agentdojo_live_transformers_pi_detector",
        "piguard": "agentdojo_live_piguard",
        "spotlighting": "agentdojo_live_spotlighting_with_delimiting",
        "prompt_sandwiching": "agentdojo_live_prompt_sandwiching",
        "promptarmor_local": "agentdojo_live_promptarmor_local",
        "melon_local": "agentdojo_live_melon_local",
        "ours_e77_effect_diff_runtime": "agentdojo_live_ours_e77_effect_diff_runtime",
    }
    return mapping[method]


def attriguard_protocol_gate(status: dict[str, Any]) -> tuple[bool, str]:
    """Require every official key to have a clean, uniform protocol attempt."""
    imported = status.get("import_report", {})
    count = imported.get("method_key_counts", {}).get("agentdojo_live_attriguard", 0)
    clean = status.get("protocol_clean_imported_official_keys", 0)
    failed = status.get("failed_case_keys", EXPECTED_CASES - clean)
    passed = status.get("status") == "passed" and count == EXPECTED_CASES and clean == EXPECTED_CASES and failed == 0
    detail = f"expected 726 clean keys, observed imported={count}, clean={clean}, protocol_failures={failed}"
    return passed, detail


def summarize(methods: list[str], include_attriguard: bool, context: int) -> dict[str, Any]:
    imported = import_direct(methods)
    metric_by_id = {row["method_id"]: row for row in imported.get("metrics", [])}
    key_counts = imported.get("method_key_counts", {})
    rows = []
    failures = []
    for method in methods:
        method_id = expected_method_id(method)
        metric = metric_by_id.get(method_id)
        count = key_counts.get(method_id, 0)
        if count != EXPECTED_CASES or metric is None:
            failures.append(f"{method}: expected 726 keys, observed {count}")
            continue
        display, implementation, evidence = METHOD_METADATA[method]
        rows.append({"method": method, "display_name": display, "implementation": implementation,
                     "evidence_class": evidence, **metric})

    if include_attriguard:
        status_path = RESULTS / "e75_attriguard_sharded_run_status.json"
        if not status_path.exists():
            failures.append("attriguard: missing status artifact")
        else:
            status = json.loads(status_path.read_text(encoding="utf-8"))
            report = status.get("import_report", {})
            metric = next((m for m in report.get("metrics", []) if m.get("method_id") == "agentdojo_live_attriguard"), None)
            count = report.get("method_key_counts", {}).get("agentdojo_live_attriguard", 0)
            protocol_passed, protocol_detail = attriguard_protocol_gate(status)
            if count != EXPECTED_CASES or metric is None or not protocol_passed:
                failures.append(f"attriguard: {protocol_detail}")
            else:
                display, implementation, evidence = METHOD_METADATA["attriguard"]
                rows.append({"method": "attriguard", "display_name": display, "implementation": implementation,
                             "evidence_class": evidence, **metric})

    protocol = {
        "model_repo": "Qwen/Qwen3-32B-GGUF",
        "model_file": str(MODEL),
        "model_sha256": sha256(MODEL),
        "model_bytes": MODEL.stat().st_size,
        "quantization": "Q4_K_M",
        "agentdojo_version": "v1.1.2",
        "attack": "important_instructions",
        "official_case_keys": EXPECTED_CASES,
        "n_benign": 97,
        "n_attack": 629,
        "temperature": 0.0,
        "tool_delimiter": "user",
        "context_window": context,
        "real_external_side_effects": False,
    }
    report = {
        "experiment": "E78 Qwen3-32B strong same-protocol AgentDojo comparison",
        "status": "passed" if not failures else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": protocol,
        "methods": rows,
        "failures": failures,
        "claim_boundary": (
            "All main rows require 726 official AgentDojo v1.1.2 keys under one Qwen3-32B checkpoint. "
            "PromptArmor-style and MELON-style rows are comparable local adapters, not original-paper reproductions. "
            "The benchmark executes sandbox state transitions and no real external side effects."
        ),
    }
    write_json(RESULTS / "e78_qwen32_strong_baseline_report.json", report)
    with (RESULTS / "e78_qwen32_strong_baseline_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["method", "display_name", "evidence_class", "n_total", "benign_utility_rate",
                  "attack_user_utility_rate", "attack_success_rate", "error_rate"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    md = [
        "# E78 Qwen3-32B Strong Baseline Comparison", "", f"- Status: `{report['status']}`",
        f"- Model SHA-256: `{protocol['model_sha256']}`", f"- Official keys: `{EXPECTED_CASES}`", "",
        "| Method | Evidence | N | BU | UA | ASR | Errors |", "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        md.append(
            f"| {row['display_name']} | {row['evidence_class']} | {row['n_total']} | "
            f"{row['benign_utility_rate']:.3f} | {row['attack_user_utility_rate']:.3f} | "
            f"{row['attack_success_rate']:.3f} | {row['error_rate']:.3f} |"
        )
    if failures:
        md.extend(["", "## Blocking Failures", "", *[f"- {item}" for item in failures]])
    md.extend(["", "## Claim Boundary", "", report["claim_boundary"]])
    (RESULTS / "e78_qwen32_strong_baseline_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    write_json(RESULTS / "e78_qwen32_reproduction_status.json", {
        "status": report["status"], "required_methods": [*methods, *( ["attriguard"] if include_attriguard else [])],
        "failures": failures, "report": str(RESULTS / "e78_qwen32_strong_baseline_report.json"),
    })
    return report


def main() -> int:
    args = parse_args()
    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    unknown = sorted(set(methods) - set(DIRECT_METHODS))
    if unknown:
        raise ValueError(f"Unsupported E78 direct methods: {unknown}")
    RUNS.mkdir(parents=True, exist_ok=True)
    if args.mode == "summarize":
        report = summarize(methods, not args.skip_attriguard, args.context)
        print(json.dumps({"status": report["status"], "failures": report["failures"]}, indent=2))
        return 0 if report["status"] == "passed" else 1

    wait_for_pid_file(args.wait_pid_file)
    wait_for_model()
    manifest = {
        "status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
        "methods": methods, "include_attriguard": not args.skip_attriguard,
        "model": str(MODEL), "port": args.port, "context": args.context,
    }
    write_json(RUNS / "run_manifest.json", manifest)
    server: subprocess.Popen[str] | None = None
    try:
        server = start_server(args.port, args.context, args.server_log)
        (RUNS / "server.pid").write_text(str(server.pid) + "\n", encoding="utf-8")
        for method in methods:
            run_direct_method(method, args.port, args.timeout)
        if not args.skip_attriguard:
            run_attriguard(args.port, args.context, args.timeout)
        report = summarize(methods, not args.skip_attriguard, args.context)
        manifest.update({"status": report["status"], "completed_at": datetime.now(timezone.utc).isoformat(),
                         "failures": report["failures"]})
        write_json(RUNS / "run_manifest.json", manifest)
        return 0 if report["status"] == "passed" else 1
    except Exception as exc:
        manifest.update({"status": "failed", "completed_at": datetime.now(timezone.utc).isoformat(),
                         "error": repr(exc)})
        write_json(RUNS / "run_manifest.json", manifest)
        raise
    finally:
        if server is not None and server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
