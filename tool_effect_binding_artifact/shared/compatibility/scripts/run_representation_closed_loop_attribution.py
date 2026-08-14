#!/usr/bin/env python3
"""Run a targeted AgentDojo atom-vs-tool-call representation ablation.

The case manifest is derived from a completed 726-key E77 run. It contains all
official cases whose runtime feedback exercised an atom-field mismatch, plus a
small deterministic sample of effectful no-mismatch controls. The two variants
share the model, task, attack, initial plan cache, totalization, recovery code,
and execution environment. Only the pre-commit comparison representation
changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
MODEL = Path(
    os.environ.get(
        "C1F_QWEN32_MODEL",
        str(ROOT / "models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"),
    )
)
MODEL_BYTES = 19_762_149_024
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
AGENTDOJO_PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
E77_PATCH = (
    "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard."
    "agentdojo_e77_runtime_patch"
)
TOOL_CALL_PATCH = (
    "src.experiments.effect_binding_guard.representation_closed_loop_attribution."
    "agentdojo_tool_call_ablation_patch"
)
SOURCE_RUN = (
    ROOT
    / "experiments/unified-agent-security-baselines/runs/"
    "strong-model-baseline-comparison/qwen32-strong-baselines"
)
SOURCE_LOG_ROOT = (
    SOURCE_RUN
    / "agentdojo_logs/ours_e77_effect_diff_runtime/"
    "local-ours_e77_effect_diff_runtime"
)
SOURCE_PLAN_CACHE = SOURCE_RUN / "cache/e77_plan_cache.json"
DESCRIPTORS = ROOT / "analysis/results/e77_registered_effect_diff_descriptors.jsonl"
RUNTIME_CATALOG = ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"
EVALUATION_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "representation-closed-loop-attribution"
)
RUN_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/runs/"
    "representation-closed-loop-attribution/qwen32-targeted"
)
RESULT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "representation-closed-loop-attribution"
)
CASE_MANIFEST = EVALUATION_DIR / "selected-cases.jsonl"
MANIFEST_REPORT = EVALUATION_DIR / "selection-manifest.json"
PAIRED_RESULTS = RESULT_DIR / "paired-case-results.jsonl"
REPORT_JSON = RESULT_DIR / "closed-loop-attribution-report.json"
REPORT_MD = RESULT_DIR / "closed-loop-attribution-report.md"
QUEUE_STATUS = RUN_DIR / "queue-status.json"
BATCH_STATUS = RUN_DIR / "batch-status.jsonl"

FEEDBACK_STATUSES = (
    "outside_exact_plan",
    "resolver_fill_requires_replan",
    "forbidden_field_used",
    "unbound_field",
)
VARIANTS = {
    "atom_field": {
        "label": "Atom-field monitor",
        "modules": [E77_PATCH],
        "pipeline_suffix": "ours_e77_effect_diff_runtime",
    },
    "tool_call": {
        "label": "Tool-call-level monitor",
        "modules": [E77_PATCH, TOOL_CALL_PATCH],
        "pipeline_suffix": "tool_call_representation_ablation",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("build-manifest", "run", "finalize", "status"),
        default="status",
    )
    parser.add_argument("--wait-pid", type=int)
    parser.add_argument("--port", type=int, default=18086)
    parser.add_argument("--controls-per-stratum", type=int, default=2)
    parser.add_argument("--no-force-rerun", action="store_true")
    return parser.parse_args()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


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


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def content_text(content: Any) -> str:
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


def original_query(payload: dict[str, Any]) -> str:
    for message in payload.get("messages", []):
        if message.get("role") == "user":
            return content_text(message.get("content"))
    raise ValueError("AgentDojo log has no user query")


def official_case_key(payload: dict[str, Any]) -> str:
    injection = payload.get("injection_task_id") or "none"
    return (
        f"{payload['suite_name']}:{payload['user_task_id']}:"
        f"{payload.get('attack_type') or 'none'}:{injection}"
    )


def effectful_tool_names() -> set[str]:
    return {row["tool_name"] for row in read_jsonl(DESCRIPTORS)}


def tool_calls(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        call
        for message in payload.get("messages", [])
        if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
        if isinstance(call, dict)
    ]


def feedback_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    hits = []
    for message in payload.get("messages", []):
        if message.get("role") != "tool":
            continue
        text = content_text(message.get("content"))
        statuses = [status for status in FEEDBACK_STATUSES if status in text]
        if not statuses:
            continue
        call = message.get("tool_call") or {}
        hits.append(
            {
                "tool_name": call.get("function"),
                "statuses": statuses,
                "feedback_sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        )
    return hits


def source_case_rows() -> list[dict[str, Any]]:
    files = sorted(SOURCE_LOG_ROOT.glob("**/*.json"))
    effectful = effectful_tool_names()
    rows = []
    seen = set()
    for path in files:
        payload = read_json(path)
        user_task = str(payload.get("user_task_id", ""))
        if not user_task.startswith("user_task_"):
            continue
        key = official_case_key(payload)
        if key in seen:
            raise RuntimeError(f"duplicate official source case: {key}")
        seen.add(key)
        query = original_query(payload)
        calls = tool_calls(payload)
        hits = feedback_hits(payload)
        rows.append(
            {
                "case_key": key,
                "suite": payload["suite_name"],
                "mode": "attack" if payload.get("injection_task_id") else "benign",
                "user_task_id": user_task,
                "injection_task_id": payload.get("injection_task_id"),
                "attack_type": payload.get("attack_type"),
                "query_sha256": hashlib.sha256(query.encode()).hexdigest(),
                "source_log": str(path.relative_to(ROOT)),
                "source_utility": payload.get("utility"),
                "source_security": payload.get("security"),
                "effectful_tools_called": sorted(
                    {
                        str(call.get("function"))
                        for call in calls
                        if call.get("function") in effectful
                    }
                ),
                "field_mismatch_feedback": hits,
            }
        )
    if len(rows) != 726:
        raise RuntimeError(
            f"expected 726 official E77 source cases after filtering, found {len(rows)}"
        )
    return rows


def build_case_manifest(controls_per_stratum: int = 2) -> dict[str, Any]:
    source_rows = source_case_rows()
    selected: list[dict[str, Any]] = []
    controls: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        if row["field_mismatch_feedback"]:
            selected.append({**row, "cohort": "field_mismatch_exercised"})
        elif row["effectful_tools_called"]:
            controls[(row["suite"], row["mode"])].append(row)

    for stratum, rows in sorted(controls.items()):
        for row in sorted(rows, key=lambda item: item["case_key"])[
            :controls_per_stratum
        ]:
            selected.append({**row, "cohort": "effectful_no_mismatch_control"})

    selected.sort(key=lambda row: row["case_key"])
    if len({row["case_key"] for row in selected}) != len(selected):
        raise RuntimeError("duplicate selected case key")
    exercised = sum(
        row["cohort"] == "field_mismatch_exercised" for row in selected
    )
    if exercised <= 0:
        raise RuntimeError("no field-mismatch cases selected")
    source_hashes = {
        "source_plan_cache": sha256(SOURCE_PLAN_CACHE),
        "registered_descriptors": sha256(DESCRIPTORS),
        "runtime_catalog": sha256(RUNTIME_CATALOG),
        "e77_runtime_patch": sha256(
            ROOT
            / "code/src/experiments/effect_binding_guard/"
            "e77_effect_diff_runtime_guard/agentdojo_e77_runtime_patch.py"
        ),
        "tool_call_ablation_patch": sha256(
            ROOT
            / "code/src/experiments/effect_binding_guard/"
            "representation_closed_loop_attribution/"
            "agentdojo_tool_call_ablation_patch.py"
        ),
    }
    report = {
        "experiment": "representation_closed_loop_attribution",
        "status": "manifest_ready",
        "source_protocol": {
            "benchmark": "AgentDojo",
            "version": "v1.1.2",
            "official_source_keys": len(source_rows),
            "source_run": str(SOURCE_RUN.relative_to(ROOT)),
        },
        "selection": {
            "n_selected": len(selected),
            "field_mismatch_exercised": exercised,
            "effectful_no_mismatch_control": len(selected) - exercised,
            "controls_per_suite_mode_stratum": controls_per_stratum,
            "feedback_statuses": list(FEEDBACK_STATUSES),
            "by_suite_mode_cohort": {
                "|".join(key): value
                for key, value in sorted(
                    Counter(
                        (row["suite"], row["mode"], row["cohort"])
                        for row in selected
                    ).items()
                )
            },
        },
        "held_fixed": [
            "Qwen3-32B checkpoint and decoding",
            "official AgentDojo task and attack",
            "initial E77 plan cache",
            "tool descriptors",
            "call totalization",
            "recovery implementation",
            "tool execution environment",
        ],
        "changed": "precommit monitor representation only",
        "source_sha256": source_hashes,
        "claim_boundary": (
            "Targeted mechanism-attribution subset selected because the atom-field "
            "monitor was exercised; not an unbiased full-benchmark performance estimate."
        ),
    }
    write_jsonl(CASE_MANIFEST, selected)
    write_json(MANIFEST_REPORT, report)
    return report


def wait_for_pid(pid: int | None) -> None:
    if not pid:
        return
    write_json(
        QUEUE_STATUS,
        {
            "status": "waiting",
            "wait_pid": pid,
            "runner_pid": os.getpid(),
            "updated_at": now(),
        },
    )
    while True:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError):
            return
        time.sleep(30)


def healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/v1/models", timeout=3
        ) as response:
            return response.status == 200
    except Exception:
        return False


def start_server(port: int) -> tuple[subprocess.Popen[str], Any]:
    if not MODEL.exists() or MODEL.stat().st_size != MODEL_BYTES:
        raise FileNotFoundError(f"expected model is unavailable: {MODEL}")
    if sha256(MODEL) != MODEL_SHA256:
        raise RuntimeError("Qwen3-32B checkpoint checksum mismatch")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = (RUN_DIR / "llama-cpp-server.log").open("a", encoding="utf-8")
    command = [
        os.environ.get("C1F_SERVER_PYTHON", "python"),
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
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    (RUN_DIR / "server.pid").write_text(f"{process.pid}\n", encoding="utf-8")
    for _ in range(300):
        if process.poll() is not None:
            log_handle.close()
            raise RuntimeError(
                f"llama.cpp exited with {process.returncode}; inspect server log"
            )
        if healthy(port):
            return process, log_handle
        time.sleep(2)
    process.terminate()
    log_handle.close()
    raise TimeoutError("Qwen3-32B server did not become healthy")


def stop_server(process: subprocess.Popen[str], handle: Any) -> None:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    handle.close()


def prepare_variant_cache(variant: str) -> Path:
    destination = RUN_DIR / variant / "frozen_plan_cache.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE_PLAN_CACHE, destination)
    if sha256(destination) != sha256(SOURCE_PLAN_CACHE):
        raise RuntimeError(f"failed to freeze identical plan cache for {variant}")
    return destination


def batch_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str | None], list[dict[str, Any]]] = defaultdict(
        list
    )
    for row in cases:
        grouped[(row["suite"], row["mode"], row["injection_task_id"])].append(row)
    batches = []
    for (suite, mode, injection), rows in sorted(grouped.items()):
        batches.append(
            {
                "suite": suite,
                "mode": mode,
                "injection_task_id": injection,
                "user_task_ids": sorted(
                    {row["user_task_id"] for row in rows},
                    key=lambda value: int(value.rsplit("_", 1)[1]),
                ),
                "case_keys": sorted(row["case_key"] for row in rows),
            }
        )
    return batches


def benchmark_command(
    variant: str,
    batch: dict[str, Any],
    *,
    force_rerun: bool,
) -> list[str]:
    command = [
        str(AGENTDOJO_PYTHON),
        "-B",
        "-m",
        "agentdojo.scripts.benchmark",
        "--model",
        "LOCAL",
        "--model-id",
        "qwen3_32b_local",
        "--benchmark-version",
        "v1.1.2",
        "--suite",
        batch["suite"],
        "--tool-delimiter",
        "user",
        "--logdir",
        str(RUN_DIR / variant / "agentdojo_logs"),
    ]
    if batch["mode"] == "attack":
        command.extend(
            [
                "--attack",
                "important_instructions",
                "--injection-task",
                str(batch["injection_task_id"]),
            ]
        )
    for module in VARIANTS[variant]["modules"]:
        command.extend(["--module-to-load", module])
    for user_task in batch["user_task_ids"]:
        command.extend(["--user-task", user_task])
    if force_rerun:
        command.append("--force-rerun")
    return command


def run_variant(
    variant: str,
    cases: list[dict[str, Any]],
    *,
    port: int,
    force_rerun: bool,
) -> list[dict[str, Any]]:
    cache = prepare_variant_cache(variant)
    audit = RUN_DIR / variant / "runtime-audit.jsonl"
    if force_rerun and audit.exists():
        audit.unlink()
    env = {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": str(ROOT / "code"),
        "LOCAL_LLM_PORT": str(port),
        "E77_EFFECT_DIFF_RUNTIME": "1",
        "E77_PLAN_CACHE": str(cache),
        "E77_AUDIT_JSONL": str(audit),
        "E77_RUNTIME_CATALOG": str(RUNTIME_CATALOG),
        "E77_REGISTERED_DESCRIPTOR_JSONL": str(DESCRIPTORS),
        "E77_PLANNER_PORT": str(port),
        "E77_PLANNER_MODEL": "qwen3_32b_local",
        "E77_AGENT_MAX_TOKENS": "4096",
        "E77_PLANNER_MAX_TOKENS": "4096",
        "E77_PLANNER_REPAIR_ATTEMPTS": "1",
        "E77_MAX_PLAN_REVISIONS": "3",
        "E77_REVISION_MAX_TOKENS": "2048",
    }
    if variant == "tool_call":
        env["REPRESENTATION_TOOL_CALL_ABLATION"] = "1"

    statuses = []
    for index, batch in enumerate(batch_rows(cases)):
        command = benchmark_command(variant, batch, force_rerun=force_rerun)
        started = time.time()
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        row = {
            "variant": variant,
            "batch_index": index,
            **batch,
            "returncode": completed.returncode,
            "duration_seconds": time.time() - started,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
            "completed_at": now(),
        }
        statuses.append(row)
        with BATCH_STATUS.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        if completed.returncode != 0:
            raise RuntimeError(
                f"{variant} batch {index} failed; inspect {BATCH_STATUS}"
            )
    return statuses


def result_index(variant: str) -> dict[str, dict[str, Any]]:
    paths = sorted((RUN_DIR / variant / "agentdojo_logs").glob("**/*.json"))
    index = {}
    for path in paths:
        payload = read_json(path)
        user_task = str(payload.get("user_task_id", ""))
        if not user_task.startswith("user_task_"):
            continue
        key = official_case_key(payload)
        if key in index:
            raise RuntimeError(f"duplicate {variant} output for {key}")
        if payload.get("error") is not None:
            raise RuntimeError(f"{variant} output contains error: {path}")
        if not isinstance(payload.get("utility"), bool):
            raise RuntimeError(f"{variant} output lacks native utility: {path}")
        if payload.get("injection_task_id") and not isinstance(
            payload.get("security"), bool
        ):
            raise RuntimeError(f"{variant} attack output lacks native security: {path}")
        index[key] = {
            "utility": payload["utility"],
            "native_injection_goal_achieved": payload.get("security", False),
            "attack_success": (
                payload["security"] if payload.get("injection_task_id") else False
            ),
            "attack_blocked": (
                not payload["security"] if payload.get("injection_task_id") else True
            ),
            "duration": payload.get("duration"),
            "pipeline_name": payload.get("pipeline_name"),
            "source_file": str(path.relative_to(ROOT)),
        }
    return index


def plan_audit_index(variant: str) -> dict[str, set[tuple[Any, ...]]]:
    path = RUN_DIR / variant / "runtime-audit.jsonl"
    grouped: dict[str, set[tuple[Any, ...]]] = defaultdict(set)
    for row in read_jsonl(path):
        if row.get("event") != "task_plan":
            continue
        grouped[row["query_hash"]].add(
            (
                row.get("prompt_hash"),
                row.get("parse_valid"),
                row.get("validation_passed"),
                row.get("plan_accepted"),
                row.get("raw_output_prefix"),
            )
        )
    return grouped


def aggregate(rows: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    selected = [row for row in rows if row["variant"] == variant]
    attack = [row for row in selected if row["mode"] == "attack"]
    benign = [row for row in selected if row["mode"] == "benign"]
    return {
        "variant": variant,
        "label": VARIANTS[variant]["label"],
        "n_cases": len(selected),
        "benign_n": len(benign),
        "benign_utility": (
            sum(row["utility"] for row in benign) / len(benign) if benign else None
        ),
        "attack_n": len(attack),
        "attack_utility": (
            sum(row["utility"] for row in attack) / len(attack) if attack else None
        ),
        "attack_successes": sum(row["attack_success"] for row in attack),
        "attack_success_rate": (
            sum(row["attack_success"] for row in attack) / len(attack)
            if attack
            else None
        ),
        "security_rate": (
            sum(row["attack_blocked"] for row in attack) / len(attack)
            if attack
            else None
        ),
    }


def finalize() -> dict[str, Any]:
    cases = read_jsonl(CASE_MANIFEST)
    expected = {row["case_key"]: row for row in cases}
    indexes = {variant: result_index(variant) for variant in VARIANTS}
    for variant, index in indexes.items():
        missing = sorted(set(expected) - set(index))
        extras = sorted(set(index) - set(expected))
        if missing or extras:
            raise RuntimeError(
                f"{variant} result key mismatch missing={len(missing)} "
                f"extras={len(extras)}"
            )

    paired = []
    flat = []
    for key, case in sorted(expected.items()):
        pair = {
            "case_key": key,
            "suite": case["suite"],
            "mode": case["mode"],
            "cohort": case["cohort"],
            "query_sha256": case["query_sha256"],
            "atom_field": indexes["atom_field"][key],
            "tool_call": indexes["tool_call"][key],
        }
        paired.append(pair)
        for variant in VARIANTS:
            flat.append(
                {
                    "case_key": key,
                    "suite": case["suite"],
                    "mode": case["mode"],
                    "cohort": case["cohort"],
                    "variant": variant,
                    **indexes[variant][key],
                }
            )

    plan_indexes = {variant: plan_audit_index(variant) for variant in VARIANTS}
    query_hashes = {row["query_sha256"] for row in cases}
    missing_plan = {
        variant: sorted(query_hashes - set(index))
        for variant, index in plan_indexes.items()
    }
    if any(missing_plan.values()):
        raise RuntimeError(f"plan audits missing selected queries: {missing_plan}")
    plan_mismatches = sorted(
        query_hash
        for query_hash in query_hashes
        if plan_indexes["atom_field"][query_hash]
        != plan_indexes["tool_call"][query_hash]
    )
    if plan_mismatches:
        raise RuntimeError(
            f"initial plan material differs across variants: {len(plan_mismatches)}"
        )

    aggregates = [aggregate(flat, variant) for variant in VARIANTS]
    by_cohort = []
    for cohort in sorted({row["cohort"] for row in flat}):
        cohort_rows = [row for row in flat if row["cohort"] == cohort]
        by_cohort.extend(aggregate(cohort_rows, variant) for variant in VARIANTS)

    report = {
        "experiment": "representation_closed_loop_attribution",
        "status": "passed",
        "model": {
            "checkpoint": MODEL.name,
            "sha256": MODEL_SHA256,
            "context_window": 65536,
            "temperature": 0.0,
        },
        "benchmark": {
            "name": "AgentDojo",
            "version": "v1.1.2",
            "selected_cases": len(cases),
            "field_mismatch_exercised": sum(
                row["cohort"] == "field_mismatch_exercised" for row in cases
            ),
            "effectful_no_mismatch_control": sum(
                row["cohort"] == "effectful_no_mismatch_control" for row in cases
            ),
        },
        "held_fixed": read_json(MANIFEST_REPORT)["held_fixed"],
        "changed": "precommit monitor representation only",
        "initial_plan_material_equal": True,
        "aggregates": aggregates,
        "by_cohort": by_cohort,
        "paired_outcome_changes": {
            "utility": sum(
                row["atom_field"]["utility"] != row["tool_call"]["utility"]
                for row in paired
            ),
            "security": sum(
                row["mode"] == "attack"
                and row["atom_field"]["attack_success"]
                != row["tool_call"]["attack_success"]
                for row in paired
            ),
        },
        "artifacts": {
            "case_manifest": str(CASE_MANIFEST.relative_to(ROOT)),
            "paired_results": str(PAIRED_RESULTS.relative_to(ROOT)),
            "batch_status": str(BATCH_STATUS.relative_to(ROOT)),
        },
        "claim_boundary": (
            "Closed-loop effect of monitor granularity on a targeted applicability "
            "subset. Selection is conditioned on the atom-field monitor having emitted "
            "field-level feedback, so aggregate rates are not full-benchmark estimates."
        ),
    }
    write_jsonl(PAIRED_RESULTS, paired)
    write_json(REPORT_JSON, report)
    REPORT_MD.write_text(render_report(report), encoding="utf-8")
    return report


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "# Closed-Loop Monitor Representation Attribution",
        "",
        "## Design",
        "",
        (
            f"The run contains {report['benchmark']['selected_cases']} frozen "
            "AgentDojo v1.1.2 cases. The atom-field and tool-call variants use "
            "identical initial plan material, model, tasks, attacks, descriptors, "
            "totalization, recovery implementation, and tool environment."
        ),
        "",
        "## Results",
        "",
        "| Variant | Benign n | Benign utility | Attack n | Attack utility | ASR |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["aggregates"]:
        lines.append(
            f"| {row['label']} | {row['benign_n']} | "
            f"{pct(row['benign_utility'])} | {row['attack_n']} | "
            f"{pct(row['attack_utility'])} | "
            f"{pct(row['attack_success_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def run_experiment(
    *,
    wait_pid: int | None,
    port: int,
    controls_per_stratum: int,
    force_rerun: bool,
) -> dict[str, Any]:
    manifest = build_case_manifest(controls_per_stratum)
    cases = read_jsonl(CASE_MANIFEST)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "runner.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
    write_json(
        QUEUE_STATUS,
        {
            "status": "waiting" if wait_pid else "starting",
            "runner_pid": os.getpid(),
            "wait_pid": wait_pid,
            "n_selected_cases": len(cases),
            "created_at": now(),
        },
    )
    wait_for_pid(wait_pid)
    if BATCH_STATUS.exists() and force_rerun:
        BATCH_STATUS.unlink()
    write_json(
        QUEUE_STATUS,
        {
            "status": "starting_server",
            "runner_pid": os.getpid(),
            "n_selected_cases": len(cases),
            "updated_at": now(),
        },
    )
    server, handle = start_server(port)
    try:
        write_json(
            QUEUE_STATUS,
            {
                "status": "running",
                "runner_pid": os.getpid(),
                "server_pid": server.pid,
                "port": port,
                "n_selected_cases": len(cases),
                "updated_at": now(),
            },
        )
        for variant in VARIANTS:
            run_variant(
                variant,
                cases,
                port=port,
                force_rerun=force_rerun,
            )
        report = finalize()
        write_json(
            QUEUE_STATUS,
            {
                "status": "passed",
                "runner_pid": os.getpid(),
                "report": str(REPORT_JSON.relative_to(ROOT)),
                "completed_at": now(),
            },
        )
        return report
    except BaseException as exc:
        write_json(
            QUEUE_STATUS,
            {
                "status": "failed",
                "runner_pid": os.getpid(),
                "error": repr(exc),
                "updated_at": now(),
            },
        )
        raise
    finally:
        stop_server(server, handle)


def status() -> dict[str, Any]:
    value = read_json(QUEUE_STATUS) if QUEUE_STATUS.exists() else {"status": "not_queued"}
    value["case_manifest_exists"] = CASE_MANIFEST.exists()
    value["report_exists"] = REPORT_JSON.exists()
    if BATCH_STATUS.exists():
        value["completed_batches"] = len(read_jsonl(BATCH_STATUS))
    return value


def main() -> int:
    args = parse_args()
    if args.mode == "build-manifest":
        print(
            json.dumps(
                build_case_manifest(args.controls_per_stratum),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.mode == "finalize":
        print(json.dumps(finalize(), indent=2, sort_keys=True))
        return 0
    if args.mode == "status":
        print(json.dumps(status(), indent=2, sort_keys=True))
        return 0
    report = run_experiment(
        wait_pid=args.wait_pid,
        port=args.port,
        controls_per_stratum=args.controls_per_stratum,
        force_rerun=not args.no_force_rerun,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
