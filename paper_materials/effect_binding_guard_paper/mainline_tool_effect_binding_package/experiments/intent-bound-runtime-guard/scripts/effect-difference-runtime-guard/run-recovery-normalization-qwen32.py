#!/usr/bin/env python3
"""Run the recovery-normalization runtime on AgentDojo v1.1.2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
EXPERIMENT_ROOT = ROOT / "experiments/intent-bound-runtime-guard"
RESULTS = EXPERIMENT_ROOT / "results/effect-difference-runtime-guard"
COMPAT_RESULTS = ROOT / "analysis/results"
MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
MODEL_BYTES = 19_762_149_024
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
E75_PYTHON = ROOT / "experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python"
E75_MODULE = "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75"
RUNTIME_VERSION = "effect_diff_runtime_relation_onboarding_v17"
DEFAULT_PORT = 18087
DEFAULT_CONTEXT = 65536
RELATION_CATALOG = (
    EXPERIMENT_ROOT
    / "evaluation/effect-difference-runtime-guard/registered_relation_catalog.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "pilot", "full", "status"), default="status")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--context", type=int, default=DEFAULT_CONTEXT)
    parser.add_argument("--timeout", type=int, default=0)
    parser.add_argument(
        "--uncertainty-policy",
        choices=("fail_closed", "allow_after_recovery", "allow_with_trail"),
        default="fail_closed",
    )
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--suite", choices=("workspace", "slack", "travel", "banking"))
    parser.add_argument("--user-task")
    parser.add_argument("--injection-task")
    parser.add_argument(
        "--case-manifest",
        help="Frozen JSON manifest of suite/user-task benign pilot cases.",
    )
    parser.add_argument(
        "--execution-date",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="Runtime-controlled date exposed only through a registered default relation.",
    )
    return parser.parse_args()


def run_root(mode: str, uncertainty_policy: str = "fail_closed", run_tag: str = "") -> Path:
    names = {
        "smoke": "recovery-normalization-qwen32-smoke",
        "pilot": "recovery-normalization-qwen32-pilot-36",
        "full": "recovery-normalization-qwen32-full",
    }
    name = names[mode]
    if uncertainty_policy != "fail_closed":
        name = f"{name}-{uncertainty_policy.replace('_', '-')}"
    if run_tag:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", run_tag):
            raise ValueError("run tag must contain only letters, digits, dot, underscore, or dash")
        name = f"{name}-{run_tag}"
    return EXPERIMENT_ROOT / "runs/effect-difference-runtime-guard" / name


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
        "registered_descriptors": RESULTS / "registered-effect-diff-descriptors.jsonl",
        "runtime_catalog": (
            ROOT
            / "experiments/security-analysis-ablation-and-overhead/evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
        ),
        "relation_catalog": RELATION_CATALOG,
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


def protocol_manifest(
    mode: str,
    port: int,
    context: int,
    uncertainty_policy: str,
    execution_date: str,
) -> dict[str, Any]:
    if not MODEL.exists() or MODEL.stat().st_size != MODEL_BYTES:
        raise FileNotFoundError(f"Expected Qwen3-32B model ({MODEL_BYTES} bytes) is unavailable")
    return {
        "experiment": "Recovery-normalization Qwen3-32B AgentDojo run",
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "runtime_version": RUNTIME_VERSION,
        "agentdojo": {
            "version": "v1.1.2",
            "case_keys": 2 if mode == "smoke" else (36 if mode == "pilot" else 726),
            "suites": ["banking"] if mode == "smoke" else ["workspace", "slack", "travel", "banking"],
            "modes": ["benign", "attack"],
            "attack": "important_instructions",
            "tool_delimiter": "user",
            "pilot_selection": (
                {
                    "selection_policy": "fixed_task_id_prefix_not_selected_by_outcome",
                    "user_tasks": ["user_task_0", "user_task_1", "user_task_2"],
                    "injection_tasks": ["injection_task_1", "injection_task_2"],
                    "expected_per_suite": {"benign": 3, "attack": 6},
                }
                if mode == "pilot"
                else None
            ),
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
            "max_total_plan_revisions": 12,
            "uncertainty_policy": uncertainty_policy,
            "planner_repair_attempts": 2,
            "revision_output_cap": 2048,
            "default_totalization": (
                "experiments/security-analysis-ablation-and-overhead/evaluation/"
                "runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
            ),
            "registered_authority_relations": str(
                RELATION_CATALOG.relative_to(ROOT)
            ),
            "runtime_defaults": {"execution_date": execution_date},
            "post_registration_llm_role": "bounded plan/revision proposal only; exact authorization remains deterministic",
            "plan_diagnostics": ["schema_parse_valid", "validation_passed", "plan_accepted"],
            "semantic_rejection_policy": (
                "fail_closed_and_reported_as_model_outcome"
                if uncertainty_policy == "fail_closed"
                else "diagnostic_allow_after_bounded_recovery_with_strict_decision_preserved_in_audit"
            ),
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


def live_command(
    mode: str,
    root: Path,
    port: int,
    timeout: int,
    *,
    suite: str | None = None,
    user_task: str | None = None,
    user_tasks: list[str] | None = None,
    injection_task: str | None = None,
    live_modes: str = "benign,attack",
) -> list[str]:
    suites = suite or ("banking" if mode == "smoke" else "workspace,slack,travel,banking")
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
        live_modes,
        "--live-logdir",
        str(root / "agentdojo_logs"),
        "--local-llm-port",
        str(port),
        "--live-timeout-seconds",
        str(timeout),
    ]
    if user_tasks:
        for task_id in user_tasks:
            command.extend(["--live-user-task", task_id])
    elif user_task:
        command.extend(["--live-user-task", user_task])
    elif mode == "smoke":
        command.extend(["--live-user-task", "user_task_0", "--live-injection-task", "injection_task_0"])
    if injection_task:
        command.extend(["--live-injection-task", injection_task])
    if mode == "pilot" and not user_tasks and not user_task and not injection_task:
        for task_id in ("user_task_0", "user_task_1", "user_task_2"):
            command.extend(["--live-user-task", task_id])
        for task_id in ("injection_task_1", "injection_task_2"):
            command.extend(["--live-injection-task", task_id])
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
    if args.case_manifest and (args.user_task or args.injection_task or args.suite):
        raise ValueError(
            "--case-manifest cannot be combined with --suite, --user-task, "
            "or --injection-task"
        )
    if args.mode == "status" and args.run_tag:
        candidates = [
            run_root(mode, args.uncertainty_policy, args.run_tag)
            for mode in ("smoke", "pilot", "full")
        ]
        existing = [candidate for candidate in candidates if candidate.exists()]
        if len(existing) > 1:
            raise ValueError(
                "run tag exists under multiple modes; inspect the run roots directly"
            )
        root = existing[0] if existing else candidates[-1]
    else:
        root = run_root(
            args.mode if args.mode != "status" else "full",
            args.uncertainty_policy,
            args.run_tag,
        )
    if args.mode == "status":
        print(json.dumps(status(root), indent=2, sort_keys=True))
        return 0
    root.mkdir(parents=True, exist_ok=True)
    (root / "runner.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
    try:
        datetime.fromisoformat(args.execution_date)
    except ValueError as exc:
        raise ValueError("--execution-date must use ISO date format") from exc
    manifest = protocol_manifest(
        args.mode,
        args.port,
        args.context,
        args.uncertainty_policy,
        args.execution_date,
    )
    case_manifest: dict[str, Any] | None = None
    case_groups: dict[str, list[str]] = {}
    if args.case_manifest:
        case_manifest_path = Path(args.case_manifest).resolve()
        case_manifest = json.loads(case_manifest_path.read_text(encoding="utf-8"))
        if case_manifest.get("status") not in {
            "frozen_before_v8_pilot_execution",
            "frozen_before_expanded_recovery_pilot_execution",
        }:
            raise ValueError("case manifest is not frozen for pilot execution")
        if case_manifest.get("runtime_version") != RUNTIME_VERSION:
            raise ValueError("case manifest runtime version does not match runner")
        if case_manifest.get("modes") != ["benign"]:
            raise ValueError("case manifest must contain benign mode only")
        cases = case_manifest.get("cases")
        if not isinstance(cases, list) or len(cases) != case_manifest.get("n_cases"):
            raise ValueError("case manifest count does not match its case rows")
        for case in cases:
            suite = case.get("suite")
            task_id = case.get("user_task_id")
            if suite not in {"workspace", "slack", "travel", "banking"}:
                raise ValueError(f"unsupported suite in case manifest: {suite!r}")
            if not isinstance(task_id, str) or not re.fullmatch(
                r"user_task_[0-9]+", task_id
            ):
                raise ValueError(f"invalid task id in case manifest: {task_id!r}")
            case_groups.setdefault(suite, []).append(task_id)
        observed_keys = {
            f"{suite}/{task_id}"
            for suite, task_ids in case_groups.items()
            for task_id in task_ids
        }
        expected_keys = {case["case_key"] for case in cases}
        if observed_keys != expected_keys:
            raise ValueError("case manifest keys do not match suite/task fields")
        manifest["agentdojo"].update(
            {
                "case_keys": len(cases),
                "suites": sorted(case_groups),
                "modes": ["benign"],
                "pilot_selection": {
                    "manifest": str(case_manifest_path.relative_to(ROOT)),
                    "manifest_sha256": sha256(case_manifest_path),
                    "selection_policy": case_manifest["selection_policy"],
                },
            }
        )
    manifest["target_override"] = {
        "suite": args.suite,
        "user_task": args.user_task,
        "injection_task": args.injection_task,
        "case_manifest": args.case_manifest,
    }
    write_json(root / "protocol_manifest.json", manifest)
    server: subprocess.Popen[str] | None = None
    try:
        # External-API mode (e.g. DeepSeek): no local llama.cpp server needed.
        if not os.getenv("E77_LLM_BASE_URL"):
            server = start_server(root, args.port, args.context)
        env = {
            **os.environ,
            "CUDA_VISIBLE_DEVICES": "",
            "PYTHONPATH": str(ROOT / "code"),
            "E77_PLAN_CACHE": str(root / "plan_cache.json"),
            "E77_AUDIT_JSONL": str(root / "runtime_audit.jsonl"),
            "E77_RUNTIME_CATALOG": str(
                ROOT
                / "experiments/security-analysis-ablation-and-overhead/evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
            ),
            "E77_REGISTERED_DESCRIPTOR_JSONL": str(RESULTS / "registered-effect-diff-descriptors.jsonl"),
            "E77_RELATION_CATALOG": str(RELATION_CATALOG),
            "E77_EXECUTION_DATE": args.execution_date,
            "E77_PLANNER_PORT": str(args.port),
            "E77_AGENT_MAX_TOKENS": "4096",
            "E77_MAX_PLAN_REVISIONS": "3",
            "E77_MAX_TOTAL_PLAN_REVISIONS": "12",
            "E77_UNCERTAINTY_POLICY": args.uncertainty_policy,
            "E77_PLANNER_REPAIR_ATTEMPTS": "2",
            "E77_REVISION_MAX_TOKENS": "2048",
            "E75_LIVE_MODEL_NAME": MODEL.name,
        }
        commands: list[tuple[str, list[str]]]
        if case_groups:
            commands = [
                (
                    suite,
                    live_command(
                        args.mode,
                        root,
                        args.port,
                        args.timeout,
                        suite=suite,
                        user_tasks=sorted(task_ids),
                        live_modes="benign",
                    ),
                )
                for suite, task_ids in sorted(case_groups.items())
            ]
        else:
            commands = [
                (
                    args.suite or "combined",
                    live_command(
                        args.mode,
                        root,
                        args.port,
                        args.timeout,
                        suite=args.suite,
                        user_task=args.user_task,
                        injection_task=args.injection_task,
                    ),
                )
            ]

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        command_statuses: dict[str, Any] = {}
        return_codes: list[int] = []
        shared_status = COMPAT_RESULTS / "e75_agentdojo_official_live_run_status.json"
        for command_name, command in commands:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=args.timeout or None,
            )
            return_codes.append(completed.returncode)
            stdout_parts.append(f"## {command_name}\n{completed.stdout}")
            stderr_parts.append(f"## {command_name}\n{completed.stderr}")
            command_status = (
                json.loads(shared_status.read_text(encoding="utf-8"))
                if shared_status.exists()
                else {}
            )
            command_statuses[command_name] = command_status
            write_json(root / f"command_status.{command_name}.json", command_status)
            if completed.returncode != 0:
                break
        (root / "runner_stdout.log").write_text(
            "\n".join(stdout_parts), encoding="utf-8"
        )
        (root / "runner_stderr.log").write_text(
            "\n".join(stderr_parts), encoding="utf-8"
        )
        write_json(root / "command_status.json", command_statuses)
        runner_returncode = next((code for code in return_codes if code), 0)
        manifest.update(
            {
                "status": (
                    "runner_completed" if runner_returncode == 0 else "runner_failed"
                ),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "runner_returncode": runner_returncode,
                "command_status": str((root / "command_status.json").relative_to(ROOT)),
            }
        )
        write_json(root / "protocol_manifest.json", manifest)
        print(json.dumps(status(root), indent=2, sort_keys=True))
        return runner_returncode
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
