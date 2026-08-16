#!/usr/bin/env python3
"""Run the strict atom representation attribution experiment (protocol section 10).

Drives the four representation variants (V0--V3) over AgentDojo v1.1.2 with the
frozen common plan cache, identical decoding/sandbox/scorers, and only the
pre-commit representation differing.  The agent execution path is the frozen
E77 runtime; the variant is injected through
``agentdojo_representation_patch`` (loaded after the E77 patch via
``--module-to-load``).

CLI contract (protocol section 10):

    run-strict-attribution.py --scope smoke --variants all --repeat-index 0 --port 18087
    run-strict-attribution.py --scope full --variant <name> --repeat-index 0 --port 18087 --resume
    run-strict-attribution.py --scope stability --variants all --repeat-index <1|2> --port 18087 --resume

``--dry-run`` validates every frozen input, resolves the case set and the exact
benchmark commands, and prints the plan WITHOUT starting the GPU server.  It is
the development-time verification path (no GPU).

Frozen-input hash recording (protocol section 5): every case row records
``model_hash``, ``manifest_hash``, ``initial_plan_hash``,
``runtime_catalog_hash``, ``relation_catalog_hash``, ``tool_schema_hash``,
``decoding_hash`` and ``scorer_hash`` so the finalizer can verify cross-variant
consistency.  ``tool_schema_hash`` is bound to the frozen raw-schema registry
(the mechanical projection of the official tool schemas); ``decoding_hash`` is
bound to the canonical decoding configuration below (per-variant decoding
tuning is forbidden); ``scorer_hash`` is bound to the official AgentDojo
v1.1.2 scorer identity (the e75 environment and benchmark version are verified
in ``verify_frozen_inputs``).
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
EXPERIMENT_ROOT = ROOT / "experiments/security-analysis-ablation-and-overhead"
EVAL_DIR = EXPERIMENT_ROOT / "evaluation/strict-atom-representation-attribution"
SOURCE_DIR = EXPERIMENT_ROOT / "source/strict-atom-representation-attribution"
RUNS_BASE = EXPERIMENT_ROOT / "runs/strict-atom-representation-attribution/qwen32"
RESULTS_DIR = EXPERIMENT_ROOT / "results/strict-atom-representation-attribution"

MODEL = Path(
    "/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"
)
MODEL_BYTES = 19_762_149_024
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"

E75_PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
BENCHMARK_MODULE = "agentdojo.scripts.benchmark"
E77_PATCH_MODULE = (
    "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard."
    "agentdojo_e77_runtime_patch"
)
STRICT_PATCH_MODULE = "agentdojo_representation_patch"

MAIN_VARIANTS = (
    "tool_identity_only",
    "opaque_whole_call",
    "raw_schema_fields",
    "validated_atom_fields",
)

RUNTIME_CATALOG = (
    EXPERIMENT_ROOT
    / "evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
)
REGISTERED_DESCRIPTORS = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    / "registered-effect-diff-descriptors.jsonl"
)
RELATION_CATALOG = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/"
    / "registered_relation_catalog.json"
)
RAW_SCHEMA_REGISTRY = EVAL_DIR / "raw-schema-field-registry.jsonl"
WHOLE_CALL_ENVELOPES = EVAL_DIR / "whole-call-envelopes.json"
FROZEN_PLAN_CACHE = EVAL_DIR / "frozen-common-plan-cache.json"
PROTOCOL_JSON = EVAL_DIR / "protocol.json"

DEFAULT_PORT = 18087
DEFAULT_CONTEXT = 65536
ATTACK_TYPE = "important_instructions"

SCOPE_MANIFEST = {
    "smoke": ("smoke-subset.jsonl", 16),
    "full": ("all-official-cases.jsonl", 726),
    "stability": ("stability-subset.jsonl", 160),
}

# Canonical decoding configuration shared by every variant (protocol section 5:
# decoding must match the v17 protocol manifest; no per-variant tuning).  The
# sha256 of this exact dict is recorded on every case row as ``decoding_hash``.
DECODING_CONFIG = {
    "model": "LOCAL",
    "benchmark_version": "v1.1.2",
    "tool_delimiter": "user",
    "attack_type": ATTACK_TYPE,
    "uncertainty_policy": "allow_with_trail",
    "agent_max_tokens": 4096,
    "revision_max_tokens": 2048,
    "max_plan_revisions": 3,
    "max_total_plan_revisions": 12,
    "planner_repair_attempts": 2,
}
SCORER_IDENTITY = "agentdojo==1.1.2:official_utility_security_scorers"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Strict atom representation attribution runner (protocol section 10)."
    )
    parser.add_argument("--scope", choices=("smoke", "full", "stability"), required=True)
    parser.add_argument(
        "--variant",
        choices=MAIN_VARIANTS,
        default=None,
        help="single variant (used by --scope full)",
    )
    parser.add_argument(
        "--variants",
        default=None,
        help="'all' or comma-separated variant ids (used by smoke/stability)",
    )
    parser.add_argument("--repeat-index", type=int, default=0)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--context", type=int, default=DEFAULT_CONTEXT)
    parser.add_argument("--timeout", type=int, default=0)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="skip cases whose results already exist (never keep two results per case)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate frozen inputs and print the plan; do not start the GPU server",
    )
    parser.add_argument(
        "--execution-date",
        default=datetime.now(timezone.utc).date().isoformat(),
    )
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ---------------------------------------------------------------------------
# Frozen-input verification (fail fast; protocol sections 3.4 and 5)
# ---------------------------------------------------------------------------


def verify_frozen_inputs() -> dict[str, Any]:
    errors: list[str] = []
    protocol = json.loads(PROTOCOL_JSON.read_text(encoding="utf-8"))
    if protocol.get("status") != "protocol-frozen":
        errors.append(f"protocol.json status is {protocol.get('status')!r}, not frozen")
    if protocol.get("benchmark_version") != "v1.1.2":
        errors.append("protocol.json benchmark_version mismatch")
    if protocol.get("model", {}).get("sha256") != MODEL_SHA256:
        errors.append("protocol.json model sha256 mismatch")

    for name, expected in protocol.get("hashes", {}).items():
        path = EVAL_DIR / name
        if not path.exists():
            errors.append(f"frozen artifact missing: {name}")
            continue
        actual = sha256(path)
        if actual != expected:
            errors.append(f"frozen artifact hash mismatch: {name}")

    for path in (RUNTIME_CATALOG, REGISTERED_DESCRIPTORS, RELATION_CATALOG):
        if not path.exists():
            errors.append(f"shared input missing: {path}")
    if not MODEL.exists():
        errors.append(f"model missing: {MODEL}")
    elif MODEL.stat().st_size != MODEL_BYTES:
        errors.append(f"model size mismatch: {MODEL.stat().st_size} != {MODEL_BYTES}")
    return {
        "protocol_id": sha256(PROTOCOL_JSON)[:16],
        "protocol_status": protocol.get("status"),
        "errors": errors,
    }


def frozen_input_hashes(scope: str) -> dict[str, str]:
    """Deterministic frozen-input hashes recorded on every case row.

    All four variants record identical values; the finalizer refuses any
    cross-variant disagreement (protocol sections 5 and 11.3).
    """
    manifest_path = EVAL_DIR / SCOPE_MANIFEST[scope][0]
    return {
        "manifest_hash": sha256(manifest_path),
        "runtime_catalog_hash": sha256(RUNTIME_CATALOG),
        "relation_catalog_hash": sha256(RELATION_CATALOG),
        "tool_schema_hash": sha256(RAW_SCHEMA_REGISTRY),
        "decoding_hash": hashlib.sha256(
            json.dumps(DECODING_CONFIG, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "scorer_hash": hashlib.sha256(SCORER_IDENTITY.encode("utf-8")).hexdigest(),
    }


def load_case_set(scope: str) -> list[dict[str, Any]]:
    manifest_name, expected_count = SCOPE_MANIFEST[scope]
    rows = read_jsonl(EVAL_DIR / manifest_name)
    if len(rows) != expected_count:
        raise ValueError(
            f"{manifest_name}: expected {expected_count} cases, got {len(rows)}"
        )
    keys = [row["case_key"] for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError(f"{manifest_name}: duplicate case keys")
    return rows


def resolve_variants(args: argparse.Namespace) -> list[str]:
    if args.scope == "full":
        if not args.variant:
            raise ValueError("--scope full requires --variant <name>")
        return [args.variant]
    if args.variants in (None, "all"):
        return list(MAIN_VARIANTS)
    selected = [v.strip() for v in args.variants.split(",") if v.strip()]
    if not selected:
        raise ValueError("--variants resolved to an empty list")
    for variant in selected:
        if variant not in MAIN_VARIANTS:
            raise ValueError(f"unknown variant: {variant}")
    return selected


def run_root(variant: str, repeat_index: int) -> Path:
    return RUNS_BASE / variant / f"repeat-{repeat_index}"


def plan_root(args: argparse.Namespace) -> Path:
    return RUNS_BASE / f"_server-repeat-{args.repeat_index}"


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


def server_healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/v1/models", timeout=3
        ) as response:
            return response.status == 200
    except Exception:
        return False


def server_command(port: int, context: int) -> list[str]:
    # Qwen3-32B split across both GPUs; tensor_split 0.5/0.5 follows the v2/P2-b
    # precedent for OOM avoidance (protocol section 5 / task constraint).
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
        "0.5",
        "0.5",
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
    if server_healthy(port):
        raise RuntimeError(
            f"port {port} already serves a model; stop it or choose another port"
        )
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
            raise RuntimeError(
                f"llama.cpp server exited with {process.returncode}; see {log_path}"
            )
        if server_healthy(port):
            return process
        time.sleep(2)
    process.terminate()
    raise TimeoutError("Qwen3-32B server did not become healthy")


# ---------------------------------------------------------------------------
# Per-variant preparation
# ---------------------------------------------------------------------------


def seed_plan_cache(root: Path, frozen_cache_hash: str) -> str:
    """Copy the frozen common plan cache into a variant-private working file.

    The frozen file itself is never opened for writing (protocol section 3.3);
    new/revised plans are appended only to this private copy.
    """
    target = root / "plan_cache.json"
    if target.exists() and sha256(target) != frozen_cache_hash:
        # A prior run already mutated the private copy; keep it for --resume.
        return sha256(target)
    shutil.copyfile(FROZEN_PLAN_CACHE, target)
    return sha256(target)


def variant_env(root: Path, variant: str, port: int, execution_date: str) -> dict[str, str]:
    return {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": f"{ROOT / 'code'}{os.pathsep}{SOURCE_DIR}",
        "LOCAL_LLM_PORT": str(port),
        # E77 shared runtime (identical across variants).
        "E77_EFFECT_DIFF_RUNTIME": "1",
        "E77_PLAN_CACHE": str(root / "plan_cache.json"),
        "E77_AUDIT_JSONL": str(root / "runtime_audit.jsonl"),
        "E77_RUNTIME_CATALOG": str(RUNTIME_CATALOG),
        "E77_REGISTERED_DESCRIPTOR_JSONL": str(REGISTERED_DESCRIPTORS),
        "E77_RELATION_CATALOG": str(RELATION_CATALOG),
        "E77_EXECUTION_DATE": execution_date,
        "E77_PLANNER_PORT": str(port),
        "E77_UNCERTAINTY_POLICY": "allow_with_trail",
        "E77_AGENT_MAX_TOKENS": "4096",
        "E77_MAX_PLAN_REVISIONS": "3",
        "E77_MAX_TOTAL_PLAN_REVISIONS": "12",
        "E77_PLANNER_REPAIR_ATTEMPTS": "2",
        "E77_REVISION_MAX_TOKENS": "2048",
        # Strict-attribution variant selection.
        "STRICT_ATTRIB_VARIANT": variant,
        "STRICT_ATTRIB_RAW_SCHEMA_REGISTRY": str(RAW_SCHEMA_REGISTRY),
        "STRICT_ATTRIB_WHOLE_CALL_ENVELOPES": str(WHOLE_CALL_ENVELOPES),
    }


def case_benchmark_command(
    case: dict[str, Any],
    logdir: Path,
    force_rerun: bool,
) -> list[str]:
    """One benchmark invocation per case for clean audit attribution."""
    command = [
        str(E75_PYTHON),
        "-m",
        BENCHMARK_MODULE,
        "--model",
        "LOCAL",
        "--benchmark-version",
        "v1.1.2",
        "--suite",
        case["suite"],
        "--tool-delimiter",
        "user",
        "--logdir",
        str(logdir),
        "--user-task",
        case["user_task_id"],
        "--module-to-load",
        E77_PATCH_MODULE,
        "--module-to-load",
        STRICT_PATCH_MODULE,
    ]
    if case["mode"] == "attack":
        attack_type = case.get("attack_type") or ATTACK_TYPE
        command.extend(["--attack", attack_type])
        command.extend(["--injection-task", case["injection_task_id"]])
    if force_rerun:
        command.append("--force-rerun")
    return command


# ---------------------------------------------------------------------------
# Result parsing (protocol sections 5 and 6)
# ---------------------------------------------------------------------------


def case_log_path(logdir: Path, case: dict[str, Any], variant: str) -> Path:
    pipeline = f"local-ours_e77_effect_diff_runtime-strict_{variant}"
    attack_dir = case["attack_type"] or "none"
    injection_dir = case["injection_task_id"] or "none"
    return (
        logdir
        / pipeline
        / case["suite"]
        / case["user_task_id"]
        / attack_dir
        / f"{injection_dir}.json"
    )


def parse_case_log(path: Path, case: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    utility = payload.get("utility")
    security = payload.get("security")
    error = payload.get("error")
    mode = case["mode"]
    if mode == "benign":
        official_benign_utility = bool(utility) if utility is not None else None
        official_attack_utility = None
        official_attack_success = None
    else:
        official_benign_utility = None
        official_attack_utility = bool(utility) if utility is not None else None
        official_attack_success = (not bool(security)) if security is not None else None
    return {
        "official_benign_utility": official_benign_utility,
        "official_attack_utility": official_attack_utility,
        "official_attack_success": official_attack_success,
        "run_completed": error is None,
        "scorer_completed": error is None and utility is not None,
        "runtime_error": repr(error) if error else None,
        "duration": payload.get("duration"),
    }


def read_audit_tail(audit_path: Path, offset: int) -> list[str]:
    """Read only the audit lines appended after ``offset`` bytes."""
    if not audit_path.exists():
        return []
    with audit_path.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        return handle.read().splitlines()


def audit_events(audit_lines: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in audit_lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def aggregate_case_audit(
    events: list[dict[str, Any]], query_hash: str | None
) -> dict[str, Any]:
    """Aggregate the case's pre-commit decisions from the runtime audit."""
    counters = {
        "n_candidate_effectful_calls": 0,
        "n_precommit_checks": 0,
        "n_allow": 0,
        "n_deny": 0,
        "n_abstain": 0,
        "n_needs_replan": 0,
        "n_uncertainty_override": 0,
        "n_executed_effectful_calls": 0,
        "n_strictly_authorized_executed_calls": 0,
        "n_unregistered_tool_calls": 0,
        "n_reconciliation_violations": 0,
    }
    tool_call_hashes: list[str] = []
    for event in events:
        if query_hash is not None and event.get("query_hash") != query_hash:
            continue
        if event.get("event") == "precommit_check":
            counters["n_precommit_checks"] += 1
            counters["n_candidate_effectful_calls"] += 1
            decision = event.get("decision")
            if decision == "ALLOW":
                counters["n_allow"] += 1
            elif decision == "DENY":
                counters["n_deny"] += 1
            elif decision == "ABSTAIN":
                counters["n_abstain"] += 1
            elif decision == "NEEDS_REPLAN":
                counters["n_needs_replan"] += 1
            if event.get("diagnostic_uncertainty_override"):
                counters["n_uncertainty_override"] += 1
            if event.get("execution_attempted"):
                counters["n_executed_effectful_calls"] += 1
                if event.get("guard_decision") != "ALLOW":
                    counters["n_reconciliation_violations"] += 1
            if event.get("strict_authorization_satisfied") and event.get(
                "execution_attempted"
            ):
                counters["n_strictly_authorized_executed_calls"] += 1
            if event.get("call_signature"):
                tool_call_hashes.append(event["call_signature"])
        elif event.get("event") == "invalid_tool_precommit":
            counters["n_unregistered_tool_calls"] += 1
    return {"counters": counters, "tool_call_hashes": tool_call_hashes}


def build_case_row(
    case: dict[str, Any],
    variant: str,
    repeat_index: int,
    protocol_id: str,
    run_id: str,
    frozen_cache_hash: str,
    final_cache_hash: str,
    model_hash: str,
    input_hashes: dict[str, str],
    result: dict[str, Any],
    audit: dict[str, Any] | None,
) -> dict[str, Any]:
    query_hash = result.pop("query_hash", None)
    row = {
        "protocol_id": protocol_id,
        "run_id": run_id,
        "repeat_index": repeat_index,
        "variant": variant,
        "case_key": case["case_key"],
        "suite": case["suite"],
        "mode": case["mode"],
        "user_task_id": case["user_task_id"],
        "attack_type": case["attack_type"],
        "injection_task_id": case["injection_task_id"],
        **result,
        "initial_plan_hash": frozen_cache_hash,
        "final_plan_hash": final_cache_hash,
        "prompt_hashes": [query_hash] if query_hash else None,
        "tool_call_hashes": (audit or {}).get("tool_call_hashes") or None,
        "runtime_audit_path": "runtime_audit.jsonl",
        "model_hash": model_hash,
        **input_hashes,
    }
    counters = (audit or {}).get("counters")
    if counters is not None:
        row.update(counters)
    else:
        for field in (
            "n_candidate_effectful_calls",
            "n_precommit_checks",
            "n_allow",
            "n_deny",
            "n_abstain",
            "n_needs_replan",
            "n_uncertainty_override",
            "n_executed_effectful_calls",
            "n_strictly_authorized_executed_calls",
            "n_unregistered_tool_calls",
            "n_reconciliation_violations",
        ):
            row[field] = None
    return row


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run_variant(
    variant: str,
    cases: list[dict[str, Any]],
    args: argparse.Namespace,
    protocol_id: str,
    frozen_cache_hash: str,
    model_hash: str,
    input_hashes: dict[str, str],
) -> dict[str, Any]:
    root = run_root(variant, args.repeat_index)
    root.mkdir(parents=True, exist_ok=True)
    run_id = f"qwen32/{variant}/repeat-{args.repeat_index}"
    seed_plan_cache(root, frozen_cache_hash)
    logdir = root / "agentdojo_logs"
    env = variant_env(root, variant, args.port, args.execution_date)
    results_path = root / "paired-case-results.jsonl"
    existing_keys = set()
    if results_path.exists():
        existing_keys = {
            json.loads(line)["case_key"]
            for line in results_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    audit_path = root / "runtime_audit.jsonl"
    written = 0
    skipped_resume = 0
    failed = 0
    with results_path.open("a", encoding="utf-8") as out:
        for case in cases:
            if case["case_key"] in existing_keys and args.resume:
                skipped_resume += 1
                continue
            audit_start = audit_path.stat().st_size if audit_path.exists() else 0
            command = case_benchmark_command(
                case, logdir, force_rerun=not args.resume
            )
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=args.timeout or None,
            )
            log_path = case_log_path(logdir, case, variant)
            if log_path.exists():
                result = parse_case_log(log_path, case)
            else:
                result = {
                    "official_benign_utility": None,
                    "official_attack_utility": None,
                    "official_attack_success": None,
                    "run_completed": False,
                    "scorer_completed": False,
                    "runtime_error": (
                        f"benchmark returncode={completed.returncode}: "
                        f"{completed.stderr[-400:]}"
                    ),
                    "duration": None,
                }
                failed += 1
            audit_lines = read_audit_tail(audit_path, audit_start)
            events = audit_events(audit_lines)
            # This benchmark invocation ran exactly one case, so the audit tail
            # belongs to that case; record the query hash when it is unique.
            seen_hashes = {
                event.get("query_hash")
                for event in events
                if event.get("event") == "precommit_check"
            }
            query_hash = next(iter(seen_hashes)) if len(seen_hashes) == 1 else None
            result["query_hash"] = query_hash
            audit_agg = aggregate_case_audit(events, query_hash) if events else None
            final_cache_hash = sha256(root / "plan_cache.json")
            row = build_case_row(
                case,
                variant,
                args.repeat_index,
                protocol_id,
                run_id,
                frozen_cache_hash,
                final_cache_hash,
                model_hash,
                input_hashes,
                result,
                audit_agg,
            )
            out.write(json.dumps(row, sort_keys=True) + "\n")
            written += 1
    return {
        "variant": variant,
        "run_root": str(root.relative_to(ROOT)),
        "written": written,
        "skipped_resume": skipped_resume,
        "failed": failed,
        "results": str(results_path.relative_to(ROOT)),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    check = verify_frozen_inputs()
    if check["errors"]:
        print(json.dumps({"status": "refused", "errors": check["errors"]}, indent=2))
        return 2
    cases = load_case_set(args.scope)
    variants = resolve_variants(args)
    protocol_id = check["protocol_id"]
    frozen_cache_hash = sha256(FROZEN_PLAN_CACHE)
    model_hash = MODEL_SHA256
    input_hashes = frozen_input_hashes(args.scope)

    plan = {
        "scope": args.scope,
        "variants": variants,
        "repeat_index": args.repeat_index,
        "n_cases": len(cases),
        "case_set": SCOPE_MANIFEST[args.scope][0],
        "port": args.port,
        "context": args.context,
        "protocol_id": protocol_id,
        "frozen_plan_cache_sha256": frozen_cache_hash,
        "model_sha256": model_hash,
        "input_hashes": input_hashes,
        "uncertainty_policy": "allow_with_trail",
        "execution_date": args.execution_date,
        "run_dirs": {
            variant: str(run_root(variant, args.repeat_index).relative_to(ROOT))
            for variant in variants
        },
    }

    if args.dry_run:
        plan["status"] = "dry_run_ok"
        plan["commands_preview"] = {
            variants[0]: case_benchmark_command(
                cases[0],
                run_root(variants[0], args.repeat_index) / "agentdojo_logs",
                force_rerun=not args.resume,
            )
        }
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    if not E75_PYTHON.exists():
        print(json.dumps({"status": "refused", "errors": [f"missing {E75_PYTHON}"]}))
        return 2

    server: subprocess.Popen[str] | None = None
    summaries = []
    try:
        server = start_server(plan_root(args), args.port, args.context)
        for variant in variants:
            summary = run_variant(
                variant,
                cases,
                args,
                protocol_id,
                frozen_cache_hash,
                model_hash,
                input_hashes,
            )
            summaries.append(summary)
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if all(s["failed"] == 0 for s in summaries) else 1
    finally:
        if server is not None and server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
