#!/usr/bin/env python3
"""Parameterized context-repair toolchain for the v17 full run (P2-b path).

Approved context: pm_process_review_research_2026-08-05.md section 4 decision
tree, branch P2-b (400 recurrence on long-context cases -> parameterized
context repair -> immutable overlay merge -> freeze).  This script generalizes
the v2 precedent (run-qwen32-context-repair.py / merge-qwen32-context-repairs.py)
without modifying it:

  v2 hardcoded                          v17 parameterized (this script)
  -----------------------------------   -------------------------------------
  FULL_RUN / RUN_ROOT / MERGED dirs     --run-root / --repair-root / --merged-root
  RUNTIME_VERSION v2                    --runtime-version (default v17)
  METHOD (log dir) fixed                --method (default local-ours_e77_effect_diff_runtime)
  REPAIR_GROUPS_R1/R2/R3 literals       --cases / --cases-file / auto-detection
  REPLACEMENTS (12 literal rows)        selection derived from per-stage validation
  stages r1/r2/r3 manually edited       --window sequence (default 73728,81920,122880)
  plan_cache merge: not handled         explicit plan_cache merge rule + hashes
  merge refused if MERGED existed       merge is idempotent (same plan -> no-op)

Subcommands:
  detect    CPU-only dry-run: identify truncated cases (post-tool empty
            assistant trajectories), emit the affected-case list, the rerun
            command list, and the merge plan.  Never touches the GPU and never
            writes into any run directory (plan file goes to results/).
  repair    Rerun ONLY the affected cases under an enlarged context window
            into an independent repair run directory (GPU; run only after the
            base runner and its server have exited).
  merge     Immutable overlay merge: base run stays read-only; repaired rows
            are hard-linked into a new merged directory; writes repair_metadata
            and claim_boundary; rewrites command_status.json to a clean
            structure; merges plan_cache (repair-touched keys take the repair
            entry, all other keys keep the base entry); then runs the full
            finalizer against the merged directory and, on 15/15 gates passed,
            writes the finalizer-passed.json marker consumed by
            build-protocol.py --freeze --run-root <merged>.
  selftest  Synthetic end-to-end fixture test (CPU-only, temp directory).

Protocol alignment (strict_atom_representation_attribution_protocol_2026-08-03.md):
  - section 2.2: no judgment threshold is changed here; repaired cases are
    re-executed from scratch with the same runtime, only the context window
    differs, and the repair is disclosed via repair_metadata + claim_boundary;
  - section 3.3: the frozen plan cache may only come from a finalized run; the
    merged plan_cache.json produced here is the protocol input only AFTER the
    finalizer passes on the merged directory.

Python standard library only.  CPU paths never start a server.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_PLAN = "context-repair-v17-plan/1"
SCHEMA_REPAIR_REPORT = "context-repair-v17-repair-report/1"
SCHEMA_MERGE_MANIFEST = "context-repair-v17-merge-manifest/1"

ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
EXPERIMENT = ROOT / "experiments/intent-bound-runtime-guard"
RUNS = EXPERIMENT / "runs/effect-difference-runtime-guard"
RESULTS = EXPERIMENT / "results/effect-difference-runtime-guard"

DEFAULT_RUNTIME_VERSION = "effect_diff_runtime_relation_onboarding_v17"
DEFAULT_METHOD = "local-ours_e77_effect_diff_runtime"  # agentdojo_logs pipeline dir
DEFAULT_WINDOWS = (73728, 81920, 122880)
DEFAULT_PORT = 18088  # main v17 run uses 18087; repair must not collide
SUITES = ("workspace", "slack", "travel", "banking")
PATCH_MODULE = (
    "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard."
    "agentdojo_e77_runtime_patch"
)
FINALIZER = (
    EXPERIMENT
    / "scripts/effect-difference-runtime-guard/finalize-recovery-normalization-qwen32-full.py"
)
MODEL = Path(
    "/data/CSK/causal-agent-safety-research/models/"
    "Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"
)
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
MODEL_BYTES = 19_762_149_024
DEFAULT_BENCH_PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
SERVER_PYTHON = "/home/user/anaconda3/bin/python"
DESCRIPTORS = RESULTS / "registered-effect-diff-descriptors.jsonl"
CATALOG = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
)
RELATION_CATALOG = (
    EXPERIMENT / "evaluation/effect-difference-runtime-guard/registered_relation_catalog.json"
)
KV_CACHE_TYPE_IDS = {"f16": "1", "q8_0": "8"}
RUNNER_PROCESS_PATTERN = "run-recovery-normalization-qwen32.py --mode full"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def message_text(content: Any) -> str:
    """Same flattening as run_e75.message_content_text / the v2 scripts."""
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


def has_post_tool_empty_assistant(messages: list[Any]) -> bool:
    """Identical semantics to run_e75.has_post_tool_empty_assistant."""
    for index, message in enumerate(messages[1:], start=1):
        if not isinstance(message, dict):
            continue
        if message.get("role") == "assistant" and not message_text(message.get("content")).strip():
            if any(
                isinstance(prev, dict) and prev.get("role") == "tool"
                for prev in messages[:index]
            ):
                return True
    return False


@dataclass(frozen=True)
class CaseRef:
    suite: str
    mode: str  # "benign" | "attack"
    user_task_id: str
    injection_task_id: str | None  # None for benign

    @property
    def case_key(self) -> str:
        attack = "important_instructions" if self.mode == "attack" else "none"
        injection = self.injection_task_id or "none"
        return f"{self.suite}:{self.user_task_id}:{attack}:{injection}"

    @property
    def relative_log_path(self) -> str:
        attack = "important_instructions" if self.mode == "attack" else "none"
        injection = self.injection_task_id or "none"
        return f"{self.suite}/{self.user_task_id}/{attack}/{injection}.json"


def parse_case_key(raw: str) -> CaseRef:
    """Parse the official case-key format suite:user_task:attack_type:injection."""
    parts = raw.strip().split(":")
    if len(parts) != 4:
        raise ValueError(f"case key must have 4 colon-separated fields: {raw!r}")
    suite, user_task_id, attack_type, injection = parts
    if suite not in SUITES:
        raise ValueError(f"unsupported suite in case key: {raw!r}")
    if not user_task_id.startswith("user_task_"):
        raise ValueError(f"case key must reference a user task: {raw!r}")
    if attack_type == "none":
        if injection != "none":
            raise ValueError(f"benign case key must end with ':none': {raw!r}")
        return CaseRef(suite, "benign", user_task_id, None)
    if attack_type != "important_instructions":
        raise ValueError(f"only important_instructions attacks are official: {raw!r}")
    if not injection.startswith("injection_task_"):
        raise ValueError(f"attack case key needs an injection task: {raw!r}")
    return CaseRef(suite, "attack", user_task_id, injection)


def load_case_list(args: argparse.Namespace) -> list[CaseRef] | None:
    """Read --cases / --cases-file; None when neither is given."""
    raw: list[str] = list(args.cases or [])
    if args.cases_file:
        payload = json.loads(Path(args.cases_file).read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("--cases-file must contain a JSON list of case keys")
        raw.extend(str(item) for item in payload)
    if not raw:
        return None
    cases = [parse_case_key(item) for item in raw]
    unique: dict[str, CaseRef] = {}
    for case in cases:
        unique[case.case_key] = case
    return sorted(unique.values(), key=lambda case: case.case_key)


# ---------------------------------------------------------------------------
# Base-run inspection / detection (read-only, CPU-only)
# ---------------------------------------------------------------------------

def inspect_base_run(run_root: Path, runtime_version: str) -> dict[str, Any]:
    manifest_path = run_root / "protocol_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"protocol_manifest.json missing under {run_root}")
    manifest = read_json(manifest_path)
    recorded = manifest.get("runtime_version")
    if recorded != runtime_version:
        raise ValueError(
            f"runtime version mismatch: run manifest records {recorded!r}, "
            f"expected {runtime_version!r} (--runtime-version)"
        )
    return manifest


def is_official_case_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    """Mirror the official-key filtering of run_e75.import_official_agentdojo_live_logs."""
    suite = str(payload.get("suite_name"))
    user_task_id = str(payload.get("user_task_id"))
    injection_task_id = payload.get("injection_task_id")
    attack_type = payload.get("attack_type")
    if suite not in SUITES:
        return False, "suite_not_official"
    benign_injection = injection_task_id in {None, "none", ""}
    benign_attack = attack_type in {None, "none", ""}
    if benign_injection or benign_attack:
        if user_task_id.startswith("injection_task_"):
            return False, "auxiliary_injection_task_utility_log"
        if not benign_attack:
            return False, "benign_row_with_attack_type"
        return True, "benign"
    if attack_type != "important_instructions":
        return False, "non_official_attack_type"
    return True, "attack"


def case_log_path(run_root: Path, method: str, case: CaseRef) -> Path:
    return run_root / "agentdojo_logs" / method / case.relative_log_path


def detect_truncated_cases(
    run_root: Path, method: str
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Scan agentdojo_logs for official rows with post-tool empty assistants.

    Read-only.  Returns (affected_rows, scan_stats).  An affected row is an
    official case log whose trajectory contains the truncation signature
    (empty assistant continuation after a tool message), the documented effect
    of AgentDojo LocalLLM swallowing a 400/context-length error.
    """
    logs_root = run_root / "agentdojo_logs" / method
    if not logs_root.is_dir():
        raise FileNotFoundError(f"agentdojo_logs method directory missing: {logs_root}")
    stats = {"files": 0, "unparseable": 0, "official_rows": 0, "skipped": 0}
    affected: list[dict[str, Any]] = []
    for path in sorted(logs_root.rglob("*.json")):
        stats["files"] += 1
        try:
            payload = read_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            stats["unparseable"] += 1
            continue
        official, kind = is_official_case_payload(payload)
        if not official:
            stats["skipped"] += 1
            continue
        stats["official_rows"] += 1
        if not has_post_tool_empty_assistant(payload.get("messages") or []):
            continue
        case = CaseRef(
            suite=str(payload.get("suite_name")),
            mode="benign" if kind == "benign" else "attack",
            user_task_id=str(payload.get("user_task_id")),
            injection_task_id=(
                None if kind == "benign" else str(payload.get("injection_task_id"))
            ),
        )
        affected.append(
            {
                "case_key": case.case_key,
                "suite": case.suite,
                "mode": case.mode,
                "user_task_id": case.user_task_id,
                "injection_task_id": case.injection_task_id,
                "utility": payload.get("utility"),
                "security": payload.get("security"),
                "error": payload.get("error"),
                "source_file": str(
                    path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
                ),
            }
        )
    affected.sort(key=lambda row: row["case_key"])
    return affected, stats


def group_cases_for_rerun(cases: Iterable[CaseRef]) -> list[dict[str, Any]]:
    """Group cases into one benchmark invocation per (suite, mode, user_task).

    AgentDojo's benchmark CLI treats repeated --user-task/--injection-task as a
    cross product, so grouping per user task is what keeps the repair scope
    exactly equal to the affected set.
    """
    groups: dict[tuple[str, str, str], list[str]] = {}
    for case in cases:
        key = (case.suite, case.mode, case.user_task_id)
        if case.mode == "attack":
            assert case.injection_task_id is not None
            groups.setdefault(key, []).append(case.injection_task_id)
        else:
            groups.setdefault(key, [])
    out = []
    for (suite, mode, user_task_id), injection_ids in sorted(groups.items()):
        out.append(
            {
                "suite": suite,
                "mode": mode,
                "user_task_id": user_task_id,
                "injection_task_ids": sorted(injection_ids),
                "n_rows": len(injection_ids) if mode == "attack" else 1,
            }
        )
    return out


def benchmark_command(
    group: dict[str, Any], logdir: Path, bench_python: Path, force_rerun: bool
) -> list[str]:
    """Same command shape as run_e75.run_official_agentdojo_live (plus rerun flag)."""
    command = [
        str(bench_python),
        "-m",
        "agentdojo.scripts.benchmark",
        "--model",
        "LOCAL",
        "--benchmark-version",
        "v1.1.2",
        "--suite",
        group["suite"],
        "--tool-delimiter",
        "user",
        "--logdir",
        str(logdir),
    ]
    if group["mode"] == "attack":
        command.extend(["--attack", "important_instructions"])
    command.extend(["--module-to-load", PATCH_MODULE])
    command.extend(["--user-task", group["user_task_id"]])
    if group["mode"] == "attack":
        for injection_task_id in group["injection_task_ids"]:
            command.extend(["--injection-task", injection_task_id])
    if force_rerun:
        command.append("--force-rerun")
    return command


def server_command(
    port: int, window: int, n_gpu_layers: int, tensor_split: str, kv_type: str
) -> list[str]:
    """llama.cpp server configuration of the v17 runner, with --n_ctx set to the
    stage window; --tensor_split is parameterized (v2 precedent: 0.5/0.5 when the
    base-run split cannot fit the enlarged window on this hardware)."""
    split_a, split_b = tensor_split.split(",")
    command = [
        SERVER_PYTHON,
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
        str(n_gpu_layers),
        "--split_mode",
        "1",
        "--tensor_split",
        split_a,
        split_b,
        "--n_ctx",
        str(window),
        "--n_batch",
        "1024",
        "--n_ubatch",
        "512",
        "--flash_attn",
        "true",
    ]
    if kv_type != "f16":
        command.extend(["--type_k", KV_CACHE_TYPE_IDS[kv_type]])
        command.extend(["--type_v", KV_CACHE_TYPE_IDS[kv_type]])
    return command


def validate_repaired_row(run_root: Path, method: str, case: CaseRef) -> dict[str, Any]:
    """Validate one repaired trajectory; raises on any integrity problem."""
    path = case_log_path(run_root, method, case)
    if not path.is_file():
        raise FileNotFoundError(f"repaired row missing: {path}")
    payload = read_json(path)
    if payload.get("error") is not None:
        raise ValueError(f"repair row contains an error: {path}")
    if not isinstance(payload.get("utility"), bool) or not isinstance(
        payload.get("security"), bool
    ):
        raise ValueError(f"repair row lacks native metrics: {path}")
    if has_post_tool_empty_assistant(payload.get("messages") or []):
        raise ValueError(f"repair row still has a post-tool empty continuation: {path}")
    return {
        "case_key": case.case_key,
        "relative_case_path": case.relative_log_path,
        "utility": payload["utility"],
        "security": payload["security"],
        "source_sha256": sha256_file(path),
    }


def row_is_clean(run_root: Path, method: str, case: CaseRef) -> bool:
    try:
        validate_repaired_row(run_root, method, case)
        return True
    except (OSError, ValueError, FileNotFoundError):
        return False


# ---------------------------------------------------------------------------
# detect: CPU-only dry-run planning
# ---------------------------------------------------------------------------

def runner_process_alive() -> bool:
    """True when a v17 full-run runner process is still running (pgrep -f)."""
    completed = subprocess.run(
        ["pgrep", "-f", RUNNER_PROCESS_PATTERN],
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def stage_window_kwargs(index: int, args: argparse.Namespace) -> tuple[int, str]:
    """Resolve (window, kv_type) for a stage from the window sequence."""
    windows = list(args.windows)
    if index >= len(windows):
        raise ValueError(f"stage index {index} exceeds window sequence {windows}")
    return windows[index], args.kv_types[index] if args.kv_types else "f16"


def build_repair_plan(
    run_root: Path,
    manifest: dict[str, Any],
    method: str,
    affected: list[dict[str, Any]],
    requested: list[CaseRef] | None,
    windows: tuple[int, ...],
) -> dict[str, Any]:
    """Assemble the full dry-run repair plan (pure function, no side effects)."""
    affected_keys = {row["case_key"] for row in affected}
    if requested is not None:
        requested_keys = {case.case_key for case in requested}
        scope = sorted(requested_keys & affected_keys)
        unconfirmed = sorted(requested_keys - affected_keys)
    else:
        scope = sorted(affected_keys)
        unconfirmed = []
    cases = [parse_case_key(key) for key in scope]
    groups = group_cases_for_rerun(cases)
    plan_cache = run_root / "plan_cache.json"
    plan: dict[str, Any] = {
        "schema": SCHEMA_PLAN,
        "generated_at": utc_now(),
        "mode": "dry-run",
        "run_root": str(run_root),
        "runtime_version": manifest.get("runtime_version"),
        "method": method,
        "base_manifest_sha256": sha256_file(run_root / "protocol_manifest.json"),
        "base_plan_cache_sha256": sha256_file(plan_cache) if plan_cache.is_file() else None,
        "detection": {
            "affected_cases": affected,
            "n_affected": len(affected),
        },
        "requested_cases": sorted(c.case_key for c in requested) if requested else None,
        "unconfirmed_requested_cases": unconfirmed,
        "repair_scope": scope,
        "n_repair_rows": len(scope),
        "rerun_groups": groups,
        "n_benchmark_commands": len(groups),
        "stages": [],
        "merge_plan": {
            "base_run_root_read_only": str(run_root),
            "overlay": "hard-linked copy of the base run, repaired rows replaced",
            "selection_rule": (
                "per affected case, take the row from the LAST stage whose row "
                "validates clean (no error, native bool metrics, no post-tool "
                "empty assistant continuation)"
            ),
            "plan_cache_rule": (
                "keys touched by repair audits (task_plan / planner_replan / "
                "plan_revision prompt_hash entries) take the repair-run entry; "
                "all other keys keep the base entry"
            ),
            "finalizer": (
                "full 15-gate finalizer against the merged directory; on pass, "
                "write finalizer-passed.json for build-protocol.py --freeze"
            ),
            "freeze_command_hint": (
                "python3 experiments/security-analysis-ablation-and-overhead/"
                "scripts/strict-atom-representation-attribution/build-protocol.py "
                "--freeze --run-root <merged-root>"
            ),
        },
    }
    repair_logdir_placeholder = "<repair-root>/agentdojo_logs"
    for stage_index, window in enumerate(windows):
        kv_type = "q8_0" if window >= 122880 else "f16"
        stage = {
            "stage": stage_index + 1,
            "window": window,
            "kv_cache_type": kv_type,
            "server_command": server_command(
                DEFAULT_PORT, window, 65, "0.35,0.65", kv_type
            ),
            "benchmark_commands": [
                benchmark_command(group, Path(repair_logdir_placeholder), DEFAULT_BENCH_PYTHON, True)
                for group in groups
            ]
            if stage_index == 0
            else "(conditional: only cases still truncated after the previous stage)",
        }
        plan["stages"].append(stage)
    return plan


def command_detect(args: argparse.Namespace) -> int:
    run_root = Path(args.run_root).expanduser().resolve()
    manifest = inspect_base_run(run_root, args.runtime_version)
    try:
        requested = load_case_list(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    affected, stats = detect_truncated_cases(run_root, args.method)
    plan = build_repair_plan(run_root, manifest, args.method, affected, requested, args.windows)
    plan["detection"]["stats"] = stats

    warnings: list[str] = []
    if runner_process_alive():
        warnings.append(
            "a v17 full-run runner process is alive; this detection is a PARTIAL "
            "SNAPSHOT of a run in progress - rerun detect after completion"
        )
    if not (run_root / "finalizer-passed.json").is_file():
        warnings.append("base run has no finalizer-passed.json (not yet finalized)")
    if plan["unconfirmed_requested_cases"]:
        warnings.append(
            "requested cases without the truncation signature (not repaired): "
            + ", ".join(plan["unconfirmed_requested_cases"])
        )
    plan["warnings"] = warnings

    out_path = Path(args.out).expanduser().resolve() if args.out else (
        RESULTS / "context-repair-v17-plans" / f"{run_root.name}-repair-plan.json"
    )
    write_json(out_path, plan)
    print(json.dumps(plan, indent=2))
    print(f"\n[detect] plan written to {out_path}", file=sys.stderr)
    for warning in warnings:
        print(f"[detect][warning] {warning}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# repair: rerun only affected cases under an enlarged window (GPU)
# ---------------------------------------------------------------------------

def base_env_for_repair(
    repair_root: Path, repair_cache: Path, port: int, manifest: dict[str, Any]
) -> dict[str, str]:
    """Replicate the v17 runner environment EXACTLY (only paths/port differ).

    uncertainty_policy and execution_date are read from the base manifest so
    the repair inherits the frozen base-run configuration instead of drifting.
    """
    runtime_config = manifest.get("runtime_configuration") or {}
    uncertainty_policy = runtime_config.get("uncertainty_policy")
    execution_date = (runtime_config.get("runtime_defaults") or {}).get("execution_date")
    if not uncertainty_policy or not execution_date:
        raise ValueError(
            "base manifest lacks runtime_configuration.uncertainty_policy / "
            "runtime_defaults.execution_date; refuse to fabricate repair settings"
        )
    return {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": str(ROOT / "code"),
        "LOCAL_LLM_PORT": str(port),
        "E77_EFFECT_DIFF_RUNTIME": "1",  # v2 precedent (vestigial, kept for parity)
        "E77_PLAN_CACHE": str(repair_cache),
        "E77_AUDIT_JSONL": str(repair_root / "runtime_audit.jsonl"),
        "E77_RUNTIME_CATALOG": str(CATALOG),
        "E77_REGISTERED_DESCRIPTOR_JSONL": str(DESCRIPTORS),
        "E77_RELATION_CATALOG": str(RELATION_CATALOG),
        "E77_EXECUTION_DATE": str(execution_date),
        "E77_PLANNER_PORT": str(port),
        "E77_AGENT_MAX_TOKENS": "4096",
        "E77_MAX_PLAN_REVISIONS": "3",
        "E77_MAX_TOTAL_PLAN_REVISIONS": "12",
        "E77_UNCERTAINTY_POLICY": str(uncertainty_policy),
        "E77_PLANNER_REPAIR_ATTEMPTS": "2",
        "E77_REVISION_MAX_TOKENS": "2048",
        "E75_LIVE_MODEL_NAME": MODEL.name,
    }


def wait_for_server(port: int, timeout_s: int = 900) -> None:
    # /v1/models is the liveness probe used by the v17 runner and the v2
    # context-repair precedent; this llama_cpp.server build has no /health route.
    deadline = time.time() + timeout_s
    url = f"http://127.0.0.1:{port}/v1/models"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(5)
    raise TimeoutError(f"llama.cpp server did not become healthy on port {port}")


def command_repair(args: argparse.Namespace) -> int:
    run_root = Path(args.run_root).expanduser().resolve()
    repair_root = Path(args.repair_root).expanduser().resolve()
    manifest = inspect_base_run(run_root, args.runtime_version)

    if str(repair_root) == str(run_root):
        print("error: --repair-root must differ from --run-root (base stays read-only)", file=sys.stderr)
        return 2
    if run_root not in repair_root.parents and repair_root in run_root.parents:
        print("error: repair root must not contain the base run root", file=sys.stderr)
        return 2

    try:
        requested = load_case_list(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    affected, stats = detect_truncated_cases(run_root, args.method)
    plan = build_repair_plan(run_root, manifest, args.method, affected, requested, (args.window,))
    scope = plan["repair_scope"]
    if not scope:
        print("[repair] no truncated cases in scope; nothing to repair", file=sys.stderr)
        return 0
    if requested is not None and plan["unconfirmed_requested_cases"]:
        print(
            "error: requested cases without the truncation signature refuse repair: "
            + ", ".join(plan["unconfirmed_requested_cases"]),
            file=sys.stderr,
        )
        return 2

    kv_type = args.kv_type
    window = args.window
    server_cmd = server_command(args.port, window, args.n_gpu_layers, args.tensor_split, kv_type)
    env = base_env_for_repair(repair_root, repair_root / "plan_cache.json", args.port, manifest)
    groups = plan["rerun_groups"]
    logdir = repair_root / "agentdojo_logs"
    commands = [
        benchmark_command(group, logdir, Path(args.bench_python), args.force_rerun)
        for group in groups
    ]

    if args.dry_run:
        dry = {
            **plan,
            "mode": "repair-dry-run",
            "window": window,
            "kv_cache_type": kv_type,
            "port": args.port,
            "repair_root": str(repair_root),
            "server_command": server_cmd,
            "benchmark_commands": commands,
            "environment_contract": {
                key: value for key, value in sorted(env.items()) if key.startswith(("E75_", "E77_"))
            },
        }
        print(json.dumps(dry, indent=2))
        if runner_process_alive():
            print(
                "[repair][dry-run][warning] a v17 full-run runner is alive; the "
                "base-run detection is a PARTIAL SNAPSHOT and live repair is "
                "blocked until the runner exits",
                file=sys.stderr,
            )
        print("[repair][dry-run] no GPU work executed", file=sys.stderr)
        return 0

    # ---- live execution -----------------------------------------------------
    if runner_process_alive():
        print(
            "error: a v17 full-run runner process is alive; repair must not share "
            "the GPU with the base run. Re-run after the base runner exits.",
            file=sys.stderr,
        )
        return 2
    if repair_root.exists() and any(repair_root.iterdir()):
        print(f"error: repair root already exists and is not empty: {repair_root}", file=sys.stderr)
        return 2
    repair_root.mkdir(parents=True)
    repair_cache = repair_root / "plan_cache.json"
    shutil.copy2(run_root / "plan_cache.json", repair_cache)  # v2 precedent: seed from base

    repair_manifest = {
        "schema": "context-repair-v17-repair-manifest/1",
        "created_at": utc_now(),
        "base_run_root": str(run_root),
        "base_manifest_sha256": plan["base_manifest_sha256"],
        "runtime_version": args.runtime_version,
        "method": args.method,
        "window": window,
        "kv_cache_type": kv_type,
        "port": args.port,
        "repair_scope": scope,
        "n_repair_rows": len(scope),
        "rerun_groups": groups,
        "model": {
            "file_name": MODEL.name,
            "sha256": MODEL_SHA256,
            "bytes": MODEL_BYTES,
            "temperature": 0.0,
            "agent_output_cap": 4096,
            "context_window": window,
        },
        "gpu_configuration": {
            "visible_devices": [0, 1],
            "n_gpu_layers": args.n_gpu_layers,
            "tensor_split": [float(part) for part in args.tensor_split.split(",")],
            "flash_attention": True,
            "kv_cache_type": kv_type,
        },
        "claim_boundary": (
            "This repair run re-executes only the enumerated official rows whose "
            "base-run trajectories recorded context-length truncation. Runtime, "
            "checkpoint, decoding temperature, output caps, descriptors, catalogs "
            "and validators are identical to the base run. The available context "
            f"window is {window} and the GPU tensor split is {args.tensor_split} "
            "(both recorded in gpu_configuration; the split follows the v2 "
            "context-repair precedent when the base-run split cannot fit the "
            "enlarged window on this hardware). Base-run artifacts remain immutable."
        ),
    }
    write_json(repair_root / "protocol_manifest.json", repair_manifest)

    server = subprocess.Popen(server_cmd, cwd=ROOT)
    report_rows = []
    try:
        wait_for_server(args.port)
        for index, (group, command) in enumerate(zip(groups, commands)):
            log_path = repair_root / f"runner_{index}_{group['mode']}_{group['user_task_id']}.log"
            completed = subprocess.run(
                command, cwd=ROOT, env=env, capture_output=True, text=True
            )
            log_path.write_text(
                f"$ {' '.join(command)}\n--- stdout ---\n{completed.stdout}\n"
                f"--- stderr ---\n{completed.stderr}\n--- returncode {completed.returncode}\n",
                encoding="utf-8",
            )
            if completed.returncode != 0:
                print(
                    f"[repair] group {group['suite']}/{group['user_task_id']} exited "
                    f"{completed.returncode}; continuing to classify per-case",
                    file=sys.stderr,
                )
    finally:
        server.send_signal(signal.SIGINT)
        try:
            server.wait(timeout=60)
        except subprocess.TimeoutExpired:
            server.kill()

    for key in scope:
        case = parse_case_key(key)
        if row_is_clean(repair_root, args.method, case):
            status = "repaired_clean"
        elif case_log_path(repair_root, args.method, case).is_file():
            status = "still_truncated_or_invalid"
        else:
            status = "missing_row"
        report_rows.append({"case_key": key, "status": status})

    report = {
        "schema": SCHEMA_REPAIR_REPORT,
        "created_at": utc_now(),
        "repair_root": str(repair_root),
        "window": window,
        "kv_cache_type": kv_type,
        "cases": report_rows,
        "n_repaired": sum(1 for row in report_rows if row["status"] == "repaired_clean"),
        "n_still_broken": sum(
            1 for row in report_rows if row["status"] != "repaired_clean"
        ),
    }
    write_json(repair_root / "repair_report.json", report)
    print(json.dumps(report, indent=2))
    if report["n_still_broken"]:
        print(
            f"[repair] {report['n_still_broken']} case(s) not clean at window "
            f"{window}; escalate to the next window stage",
            file=sys.stderr,
        )
        return 1
    return 0


# ---------------------------------------------------------------------------
# merge: immutable overlay merge (v2 semantics, parameterized + idempotent)
# ---------------------------------------------------------------------------

PLAN_CACHE_EVENTS = ("task_plan", "planner_replan", "plan_revision")


def select_repaired_rows(
    method: str, cases: list[CaseRef], stage_roots: list[Path]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Per affected case, take the LAST stage whose row validates clean."""
    selected: list[dict[str, Any]] = []
    unrepaired: list[str] = []
    for case in cases:
        choice: dict[str, Any] | None = None
        for stage_root in stage_roots:
            if not row_is_clean(stage_root, method, case):
                continue
            detail = validate_repaired_row(stage_root, method, case)
            stage_manifest = read_json(stage_root / "protocol_manifest.json")
            choice = {
                "case_key": case.case_key,
                "relative_case_path": case.relative_log_path,
                "stage_root": str(stage_root),
                "window": stage_manifest.get("window"),
                "kv_cache_type": stage_manifest.get("kv_cache_type"),
                **{k: detail[k] for k in ("utility", "security", "source_sha256")},
            }
        if choice is None:
            unrepaired.append(case.case_key)
        else:
            selected.append(choice)
    selected.sort(key=lambda row: row["case_key"])
    return selected, unrepaired


def collect_plan_cache_keys(audit_path: Path) -> set[str]:
    """prompt_hash keys touched by planner events in one audit file."""
    keys: set[str] = set()
    if not audit_path.is_file():
        return keys
    with audit_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("event") in PLAN_CACHE_EVENTS and row.get("prompt_hash"):
                keys.add(str(row["prompt_hash"]))
    return keys


def merge_plan_caches(
    base_cache_path: Path, stage_cache_paths: list[Path], touched_keys: set[str]
) -> dict[str, Any]:
    """repair-touched keys take the repair entry; others keep the base entry."""
    merged = read_json(base_cache_path)
    stage_caches = [read_json(path) for path in stage_cache_paths]
    for key in sorted(touched_keys):
        entry = None
        for cache in stage_caches:  # later stages override earlier ones
            if key in cache:
                entry = cache[key]
        if entry is None:
            raise ValueError(
                f"plan_cache merge is fail-closed: touched key {key[:16]}... has "
                f"no entry in any repair-stage plan cache"
            )
        merged[key] = entry
    return merged


def compute_plan_hash(
    base_manifest_sha256: str,
    selected: list[dict[str, Any]],
    stage_roots: list[Path],
) -> str:
    canonical = {
        "base_manifest_sha256": base_manifest_sha256,
        "selected_rows": [
            {
                "case_key": row["case_key"],
                "stage_root": row["stage_root"],
                "source_sha256": row["source_sha256"],
                "window": row["window"],
            }
            for row in selected
        ],
        "stage_manifest_sha256s": [
            sha256_file(stage / "protocol_manifest.json") for stage in stage_roots
        ],
    }
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True).encode("utf-8")
    ).hexdigest()


def run_finalizer_on_merged(
    merged_root: Path,
    finalizer: Path,
    finalizer_python: Path,
    runtime_version: str,
    report_stem: str,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "RECOVERY_FINALIZER_RUN_ROOT": str(merged_root),
        "RECOVERY_FINALIZER_REPORT_STEM": report_stem,
        "RECOVERY_FINALIZER_EXPECTED_RUNTIME": runtime_version,
    }
    completed = subprocess.run(
        [str(finalizer_python), str(finalizer), "--expected-runtime", runtime_version],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    (merged_root / "finalizer.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (merged_root / "finalizer.stderr.log").write_text(completed.stderr, encoding="utf-8")
    return completed


def command_merge(args: argparse.Namespace) -> int:
    run_root = Path(args.run_root).expanduser().resolve()
    merged_root = Path(args.merged_root).expanduser().resolve()
    stage_roots = [Path(stage).expanduser().resolve() for stage in args.stage]
    manifest = inspect_base_run(run_root, args.runtime_version)

    involved = {run_root, merged_root, *stage_roots}
    if len(involved) != len(args.stage) + 2:
        print("error: --run-root, --stage roots and --merged-root must all differ", file=sys.stderr)
        return 2
    for stage_root in stage_roots:
        if not (stage_root / "protocol_manifest.json").is_file():
            print(f"error: stage lacks protocol_manifest.json: {stage_root}", file=sys.stderr)
            return 2
        stage_manifest = read_json(stage_root / "protocol_manifest.json")
        if stage_manifest.get("runtime_version") != args.runtime_version:
            print(
                f"error: stage runtime version mismatch: {stage_root} "
                f"({stage_manifest.get('runtime_version')!r})",
                file=sys.stderr,
            )
            return 2
        if str(stage_manifest.get("base_run_root", "")) != str(run_root):
            print(
                f"error: stage does not descend from the given base run: {stage_root}",
                file=sys.stderr,
            )
            return 2

    try:
        requested = load_case_list(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    affected, stats = detect_truncated_cases(run_root, args.method)
    plan = build_repair_plan(run_root, manifest, args.method, affected, requested, (0,))
    scope_keys = plan["repair_scope"]
    if not scope_keys:
        print("[merge] no truncated cases in scope; nothing to merge", file=sys.stderr)
        return 0
    cases = [parse_case_key(key) for key in scope_keys]

    selected, unrepaired = select_repaired_rows(args.method, cases, stage_roots)
    if unrepaired:
        print(
            "error: these cases validate clean in NO stage (fail-closed, merge refused): "
            + ", ".join(unrepaired),
            file=sys.stderr,
        )
        return 2

    base_manifest_sha256 = sha256_file(run_root / "protocol_manifest.json")
    plan_hash = compute_plan_hash(base_manifest_sha256, selected, stage_roots)
    stage_cache_paths = [stage_root / "plan_cache.json" for stage_root in stage_roots]
    for path in stage_cache_paths + [run_root / "plan_cache.json"]:
        if not path.is_file():
            print(f"error: plan_cache.json missing: {path}", file=sys.stderr)
            return 2
    touched_keys: set[str] = set()
    for stage_root in stage_roots:
        touched_keys |= collect_plan_cache_keys(stage_root / "runtime_audit.jsonl")
    merged_cache = merge_plan_caches(run_root / "plan_cache.json", stage_cache_paths, touched_keys)
    merged_cache_bytes = (json.dumps(merged_cache, indent=2, sort_keys=True) + "\n").encode("utf-8")
    merged_cache_sha256 = hashlib.sha256(merged_cache_bytes).hexdigest()

    merge_plan = {
        "schema": SCHEMA_MERGE_MANIFEST,
        "generated_at": utc_now(),
        "base_run_root": str(run_root),
        "base_manifest_sha256": base_manifest_sha256,
        "stage_roots": [str(stage_root) for stage_root in stage_roots],
        "merged_root": str(merged_root),
        "plan_hash": plan_hash,
        "selected_rows": selected,
        "n_selected": len(selected),
        "n_retained_from_base": stats["official_rows"] - len(selected),
        "plan_cache_merge": {
            "base_entries": len(read_json(run_root / "plan_cache.json")),
            "touched_keys": len(touched_keys),
            "merged_entries": len(merged_cache),
            "merged_plan_cache_sha256": merged_cache_sha256,
        },
        "claim_boundary": (
            "The 726-row overlay retains the base-run rows for all cases except the "
            "enumerated truncated ones, which are replaced by targeted reruns under "
            "enlarged context windows. Checkpoint, decoding temperature, output caps, "
            "descriptors, runtime logic, catalogs and native AgentDojo evaluators are "
            "unchanged; only the available context capacity differs for repaired rows. "
            "The repair covers ONLY the enumerated cases (claim boundary); base-run "
            "artifacts remain immutable."
        ),
    }

    # ---- idempotency gate ---------------------------------------------------
    existing_manifest_path = merged_root / "merge_manifest.json"
    if existing_manifest_path.is_file():
        existing = read_json(existing_manifest_path)
        if existing.get("plan_hash") != plan_hash:
            print(
                "error: merged directory exists with a DIFFERENT plan_hash; refusing "
                "to overwrite (remove it manually after inspection)",
                file=sys.stderr,
            )
            return 2
        if existing.get("status") == "passed" and (merged_root / "finalizer-passed.json").is_file():
            print("[merge] identical plan already merged and finalized; no-op")
            return 0
        print("[merge] identical plan found in ready_for_finalizer state; re-running finalizer only")
        completed = run_finalizer_on_merged(
            merged_root, Path(args.finalizer), Path(args.finalizer_python),
            args.runtime_version, args.report_stem or merged_root.name,
        )
        if completed.returncode != 0:
            print(f"error: finalizer failed on merged directory:\n{completed.stdout[-1500:]}\n{completed.stderr[-1500:]}", file=sys.stderr)
            return 1
        existing["status"] = "passed"
        write_json(existing_manifest_path, existing)
        write_json(
            merged_root / "finalizer-passed.json",
            {"status": "passed", "finalized_at": utc_now()},
        )
        print("[merge] finalizer passed; freeze marker written")
        return 0

    if args.dry_run:
        merge_plan["mode"] = "merge-dry-run"
        merge_plan["finalizer_command"] = [
            str(args.finalizer_python), str(args.finalizer),
            "--expected-runtime", args.runtime_version,
        ]
        print(json.dumps(merge_plan, indent=2))
        print("[merge][dry-run] nothing written", file=sys.stderr)
        return 0

    # ---- live merge -----------------------------------------------------------
    if merged_root.exists():
        print(f"error: merged root exists without a merge manifest: {merged_root}", file=sys.stderr)
        return 2
    shutil.copytree(run_root, merged_root, copy_function=os.link)  # v2 precedent
    for row in selected:
        stage_row = Path(row["stage_root"]) / "agentdojo_logs" / args.method / row["relative_case_path"]
        merged_row = merged_root / "agentdojo_logs" / args.method / row["relative_case_path"]
        merged_row.unlink()
        shutil.copy2(stage_row, merged_row)

    # Break hardlinks for every file that is about to be rewritten: in-place
    # writes would otherwise modify the READ-ONLY base run through the shared
    # inode.  This is the core base-immutability guarantee of the overlay.
    for name in (
        "protocol_manifest.json",
        "command_status.json",
        "runtime_audit.jsonl",
        "plan_cache.json",
        "merge_manifest.json",
        "finalizer-passed.json",
        "finalizer.stdout.log",
        "finalizer.stderr.log",
    ):
        (merged_root / name).unlink(missing_ok=True)

    # audit concatenation: base first, then stages in order (v2 precedent)
    merged_audit = merged_root / "runtime_audit.jsonl"
    merged_audit.write_bytes((run_root / "runtime_audit.jsonl").read_bytes())
    with merged_audit.open("ab") as out:
        for stage_root in stage_roots:
            stage_audit = stage_root / "runtime_audit.jsonl"
            if not stage_audit.is_file():
                raise FileNotFoundError(f"stage audit missing: {stage_audit}")
            out.write(stage_audit.read_bytes())

    (merged_root / "plan_cache.json").write_bytes(merged_cache_bytes)

    merged_manifest = dict(manifest)
    merged_manifest.update(
        {
            "experiment": (
                "v17 Qwen3-32B AgentDojo full run with targeted context repair "
                "(parameterized overlay merge)"
            ),
            "status": "merged_context_repair_completed",
            "completed_at": utc_now(),
            "repair_metadata": {
                "repaired_official_rows": len(selected),
                "original_official_rows_retained": stats["official_rows"] - len(selected),
                "uniform_context_window": False,
                "base_context_window": (manifest.get("model") or {}).get("context_window"),
                "repair_context_windows": sorted(
                    {row["window"] for row in selected}
                ),
                "kv_cache_types": sorted(
                    {str(row["kv_cache_type"]) for row in selected}
                ),
                "replacement_rows": selected,
            },
            "claim_boundary": merge_plan["claim_boundary"],
        }
    )
    write_json(merged_root / "protocol_manifest.json", merged_manifest)
    write_json(
        merged_root / "command_status.json",
        {
            "status": "targeted_repair_overlay",
            "commands": [
                {
                    "repair_row": row["relative_case_path"],
                    "returncode": 0,
                    "server_400_error": False,
                    "server_500_error": False,
                    "context_length_exceeded": False,
                }
                for row in selected
            ],
        },
    )
    write_json(
        existing_manifest_path,
        merge_plan | {"status": "ready_for_finalizer", "original_artifacts_modified": False},
    )

    completed = run_finalizer_on_merged(
        merged_root, Path(args.finalizer), Path(args.finalizer_python),
        args.runtime_version, args.report_stem or merged_root.name,
    )
    if completed.returncode != 0:
        print(
            "error: context-repaired finalizer failed (merged directory kept in "
            f"ready_for_finalizer state):\n{completed.stdout[-1500:]}\n{completed.stderr[-1500:]}",
            file=sys.stderr,
        )
        return 1
    final_manifest = read_json(existing_manifest_path)
    final_manifest["status"] = "passed"
    write_json(existing_manifest_path, final_manifest)
    write_json(
        merged_root / "finalizer-passed.json",
        {"status": "passed", "finalized_at": utc_now()},
    )
    print(completed.stdout)
    print(
        f"[merge] finalizer passed; freeze marker written to {merged_root}/finalizer-passed.json"
    )
    return 0


# ---------------------------------------------------------------------------
# selftest: synthetic end-to-end fixture (CPU-only, temp directory)
# ---------------------------------------------------------------------------

def _fixture_row(suite: str, user_task: str, attack: str, injection: str, truncated: bool) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [{"role": "user", "content": "do the task"}]
    if truncated:
        messages += [{"role": "tool", "content": "tool result"}, {"role": "assistant", "content": ""}]
    else:
        messages += [{"role": "assistant", "content": "done"}]
    return {
        "suite_name": suite,
        "user_task_id": user_task,
        "injection_task_id": None if attack == "none" else injection,
        "attack_type": None if attack == "none" else attack,
        "utility": True,
        "security": attack == "none",
        "error": None,
        "messages": messages,
    }


def _write_fixture_case(run_root: Path, method: str, case: CaseRef, truncated: bool, marker: str) -> None:
    payload = _fixture_row(case.suite, case.user_task_id, "important_instructions" if case.mode == "attack" else "none", case.injection_task_id or "none", truncated)
    payload["fixture_marker"] = marker
    path = run_root / "agentdojo_logs" / method / case.relative_log_path
    write_json(path, payload)


def command_selftest(_args: argparse.Namespace) -> int:
    import tempfile

    method = DEFAULT_METHOD
    case_a = CaseRef("workspace", "benign", "user_task_0", None)
    case_b = CaseRef("workspace", "benign", "user_task_1", None)
    case_c = CaseRef("slack", "attack", "user_task_2", "injection_task_1")

    with tempfile.TemporaryDirectory(prefix="context-repair-v17-selftest-") as tmp:
        tmp_path = Path(tmp)
        base = tmp_path / "base-run"
        stage1 = tmp_path / "stage-73728"
        stage2 = tmp_path / "stage-81920"
        merged = tmp_path / "merged"

        # --- base run fixture (A and C truncated, B clean) -------------------
        _write_fixture_case(base, method, case_a, True, "base-A")
        _write_fixture_case(base, method, case_b, False, "base-B")
        _write_fixture_case(base, method, case_c, True, "base-C")
        write_json(
            base / "protocol_manifest.json",
            {
                "runtime_version": DEFAULT_RUNTIME_VERSION,
                "model": {"file_name": MODEL.name, "context_window": 65536},
            },
        )
        write_json(base / "plan_cache.json", {"hA": {"plan": "base-A"}, "hB": {"plan": "base-B"}})
        (base / "runtime_audit.jsonl").write_text(
            json.dumps({"event": "task_plan", "prompt_hash": "hA", "query_hash": "qA"}) + "\n"
            + json.dumps({"event": "task_plan", "prompt_hash": "hB", "query_hash": "qB"}) + "\n",
            encoding="utf-8",
        )

        # --- stage fixtures ---------------------------------------------------
        for stage_root, window, repaired in ((stage1, 73728, [case_a]), (stage2, 81920, [case_c])):
            for case in repaired:
                _write_fixture_case(stage_root, method, case, False, f"stage{window}-{case.case_key}")
            write_json(
                stage_root / "protocol_manifest.json",
                {
                    "schema": "context-repair-v17-repair-manifest/1",
                    "runtime_version": DEFAULT_RUNTIME_VERSION,
                    "base_run_root": str(base),
                    "window": window,
                    "kv_cache_type": "f16",
                },
            )
            hash_key = {"user_task_0": "hA", "user_task_2": "hC"}[case.user_task_id]
            write_json(stage_root / "plan_cache.json", {hash_key: {"plan": f"repaired-{window}"}})
            (stage_root / "runtime_audit.jsonl").write_text(
                json.dumps({"event": "task_plan", "prompt_hash": hash_key, "query_hash": "qx"}) + "\n",
                encoding="utf-8",
            )

        fake_finalizer = tmp_path / "fake-finalizer.py"
        fake_finalizer.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")

        # --- detect -----------------------------------------------------------
        ns_detect = argparse.Namespace(
            run_root=str(base), runtime_version=DEFAULT_RUNTIME_VERSION, method=method,
            cases=None, cases_file=None, windows=tuple(DEFAULT_WINDOWS),
            kv_types=None, out=str(tmp_path / "plan.json"),
        )
        assert command_detect(ns_detect) == 0, "detect failed"
        plan = read_json(tmp_path / "plan.json")
        assert sorted(row["case_key"] for row in plan["detection"]["affected_cases"]) == sorted(
            [case_a.case_key, case_c.case_key]
        ), "detect must find exactly the two truncated cases"
        assert plan["detection"]["stats"]["official_rows"] == 3

        # --- merge dry-run ------------------------------------------------------
        merge_kwargs = dict(
            run_root=str(base), merged_root=str(merged),
            stage=[str(stage1), str(stage2)], cases=None, cases_file=None,
            finalizer=str(fake_finalizer), finalizer_python=sys.executable,
            report_stem=None, runtime_version=DEFAULT_RUNTIME_VERSION, method=method,
        )
        assert command_merge(argparse.Namespace(dry_run=True, **merge_kwargs)) == 0, "merge dry-run failed"
        assert not merged.exists(), "dry-run must not create the merged directory"

        # --- merge live (fake finalizer) ---------------------------------------
        base_fingerprints = {
            str(path): sha256_file(path) for path in base.rglob("*") if path.is_file()
        }
        assert command_merge(argparse.Namespace(dry_run=False, **merge_kwargs)) == 0, "merge failed"
        for path in base.rglob("*"):
            if path.is_file():
                assert sha256_file(path) == base_fingerprints[str(path)], (
                    f"BASE RUN MUTATED by merge: {path}"
                )
        assert sorted(base_fingerprints) == sorted(
            str(path) for path in base.rglob("*") if path.is_file()
        ), "merge must not add or remove files in the base run"
        merged_row_a = read_json(merged / "agentdojo_logs" / method / case_a.relative_log_path)
        merged_row_b = read_json(merged / "agentdojo_logs" / method / case_b.relative_log_path)
        merged_row_c = read_json(merged / "agentdojo_logs" / method / case_c.relative_log_path)
        assert merged_row_a["fixture_marker"] == f"stage73728-{case_a.case_key}"
        assert merged_row_b["fixture_marker"] == "base-B"
        assert merged_row_c["fixture_marker"] == f"stage81920-{case_c.case_key}"
        merged_cache = read_json(merged / "plan_cache.json")
        assert merged_cache["hA"] == {"plan": "repaired-73728"}, "touched key must take repair entry"
        assert merged_cache["hB"] == {"plan": "base-B"}, "untouched key must keep base entry"
        command_status = read_json(merged / "command_status.json")
        assert command_status["status"] == "targeted_repair_overlay"
        assert len(command_status["commands"]) == 2
        assert (merged / "finalizer-passed.json").is_file()
        n_audit_lines = sum(1 for _ in (merged / "runtime_audit.jsonl").open(encoding="utf-8"))
        assert n_audit_lines == 4, "audit must concatenate base + both stages"
        manifest_out = read_json(merged / "protocol_manifest.json")
        assert manifest_out["repair_metadata"]["repaired_official_rows"] == 2
        assert manifest_out["repair_metadata"]["original_official_rows_retained"] == 1

        # --- idempotency: identical inputs -> no-op -----------------------------
        assert command_merge(argparse.Namespace(dry_run=False, **merge_kwargs)) == 0, "idempotent rerun failed"

        # --- plan_hash divergence -> refusal -------------------------------------
        _write_fixture_case(stage1, method, case_a, False, "tampered-A")
        completed = command_merge(argparse.Namespace(dry_run=False, **merge_kwargs))
        assert completed == 2, "tampered stage input must be refused"

    print("[selftest] all assertions passed")
    return 0


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------

def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-root", required=True, help="base v17 run directory (read-only)")
    parser.add_argument("--runtime-version", default=DEFAULT_RUNTIME_VERSION)
    parser.add_argument("--method", default=DEFAULT_METHOD, help="agentdojo_logs pipeline directory name")
    parser.add_argument("--cases", nargs="*", default=None, help="official case keys (suite:user_task:attack:injection)")
    parser.add_argument("--cases-file", default=None, help="JSON list of official case keys")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect = subparsers.add_parser(
        "detect", help="CPU-only dry-run: affected cases + rerun commands + merge plan"
    )
    add_common_arguments(detect)
    detect.add_argument("--windows", nargs="*", type=int, default=list(DEFAULT_WINDOWS),
                        help="graded context-window sequence (default: 73728 81920 122880)")
    detect.add_argument("--kv-types", nargs="*", default=None,
                        help="optional KV cache type per stage (f16|q8_0)")
    detect.add_argument("--out", default=None, help="plan JSON output path (default: results/)")

    repair = subparsers.add_parser(
        "repair", help="rerun ONLY the affected cases under one enlarged window (GPU)"
    )
    add_common_arguments(repair)
    repair.add_argument("--repair-root", required=True, help="independent repair run directory to create")
    repair.add_argument("--window", type=int, required=True, help="context window for this stage")
    repair.add_argument("--kv-type", default="f16", choices=sorted(KV_CACHE_TYPE_IDS))
    repair.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"planner/server port (default {DEFAULT_PORT}; main v17 run uses 18087)")
    repair.add_argument("--n-gpu-layers", type=int, default=65)
    repair.add_argument("--tensor-split", default="0.35,0.65")
    repair.add_argument("--bench-python", default=str(DEFAULT_BENCH_PYTHON))
    repair.add_argument("--force-rerun", action="store_true")
    repair.add_argument("--dry-run", action="store_true", help="print commands and environment contract; no GPU")

    merge = subparsers.add_parser(
        "merge", help="immutable overlay merge (base read-only) + finalizer + freeze marker"
    )
    add_common_arguments(merge)
    merge.add_argument("--stage", action="append", required=True,
                       help="repair stage directory, repeat in ascending window order")
    merge.add_argument("--merged-root", required=True, help="new merged directory to create")
    merge.add_argument("--dry-run", action="store_true", help="print the merge plan; write nothing")
    merge.add_argument("--finalizer", default=str(FINALIZER))
    merge.add_argument("--finalizer-python", default=sys.executable)
    merge.add_argument("--report-stem", default=None)

    subparsers.add_parser("selftest", help="synthetic end-to-end fixture test (CPU-only)")

    args = parser.parse_args(argv)
    handlers = {
        "detect": command_detect,
        "repair": command_repair,
        "merge": command_merge,
        "selftest": command_selftest,
    }
    try:
        return handlers[args.command](args)
    except (FileNotFoundError, ValueError, TimeoutError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
