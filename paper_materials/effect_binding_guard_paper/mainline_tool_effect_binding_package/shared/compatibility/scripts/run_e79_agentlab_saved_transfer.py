#!/usr/bin/env python3
"""Run the frozen AgentLAB 303-pair saved-attack transfer protocol.

The runner never generates attacks. It invokes the vendored deterministic
AgentDojo v1.2.1 evaluator with identical saved attacks for no guard or E77.
The ``c1f_pn`` method adds a format-only provenance normalization adapter while
preserving the frozen C1f descriptors and deterministic policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
VENDOR = ROOT / "runs/e79_external_benchmarks/AgentLAB/Task-Injection/agentdojo"
VENDOR_SRC = VENDOR / "src"
CASES = ROOT / "evaluation/e79_long_horizon/agentlab_saved_attack_cases.jsonl"
RESULTS = ROOT / "analysis/results"
RUNS = ROOT / "runs/e79_agentlab_saved_transfer"
CONDA = Path("/home/user/anaconda3/bin/conda")

ATTACK_MODULE = "src.experiments.effect_binding_guard.e79_agentlab_saved_attack_adapter.attack"
COMPAT_MODULE = "src.experiments.effect_binding_guard.e79_agentlab_saved_attack_adapter.local_runtime_compat"
GUARD_MODULE = "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.agentdojo_e77_runtime_patch"
PROVENANCE_NORMALIZATION_MODULE = "agentlab_provenance_normalized_patch"
DEEPSEEK_MODULE = (
    "src.experiments.effect_binding_guard.atom_utility_preservation_confirmatory."
    "deepseek_agentdojo_patch"
)
SHADOW_C1F = ROOT / "code/shadow_atom_envelope_c1f"
FREEZE_C1F = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/"
    "counterfactual-atom-envelope-guard/c1f_frozen_candidate_2026-08-08.json"
)
CURRENT_C1F_DESCRIPTORS = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)
CURRENT_C1F_RUNTIME_CATALOG = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
)
CURRENT_C1F_RELATION_CATALOG = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/"
    "registered_relation_catalog.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_c1f_sources() -> dict[str, str]:
    frozen = json.loads(FREEZE_C1F.read_text(encoding="utf-8"))
    if frozen.get("status") != "frozen_before_c1f_live_regression":
        raise RuntimeError("C1f candidate is not frozen for live evaluation")
    verified = {"freeze_manifest": sha256(FREEZE_C1F)}
    for name, artifact in frozen["source_artifacts"].items():
        path = ROOT / artifact["path"]
        observed = sha256(path)
        if observed != artifact["sha256"]:
            raise RuntimeError(f"frozen C1f artifact changed: {artifact['path']}")
        verified[name] = observed
    return verified


def read_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]


def selection_by_suite(cases: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    grouped: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"users": set(), "injections": set()})
    for row in cases:
        grouped[row["suite"]]["users"].add(row["user_task_id"])
        grouped[row["suite"]]["injections"].add(row["injection_task_id"])
    return {
        suite: {
            "users": sorted(values["users"], key=lambda value: int(value.rsplit("_", 1)[1])),
            "injections": sorted(values["injections"], key=lambda value: int(value.rsplit("_", 1)[1])),
        }
        for suite, values in sorted(grouped.items())
    }


def build_command(
    *,
    suite: str,
    users: list[str],
    injections: list[str],
    method: str,
    model_id: str,
    logdir: Path,
    force_rerun: bool,
    agent_backend: str = "local",
) -> list[str]:
    command = [
        str(CONDA), "run", "-n", "causal-safety", "python", "-B", "-m", "agentdojo.scripts.benchmark",
        "--model", "LOCAL",
        "--model-id", model_id,
        "--benchmark-version", "v1.2.1",
        "--suite", suite,
        "--attack", "e79_agentlab_saved_transfer",
        "--tool-delimiter", "user",
        "--logdir", str(logdir),
        "--module-to-load", ATTACK_MODULE,
        "--module-to-load", COMPAT_MODULE,
    ]
    if method in {"e77", "c1f", "c1f_pn"}:
        command.extend(["--module-to-load", GUARD_MODULE])
    if method == "c1f_pn":
        command.extend(["--module-to-load", PROVENANCE_NORMALIZATION_MODULE])
    if agent_backend == "deepseek":
        command.extend(["--module-to-load", DEEPSEEK_MODULE])
    for user in users:
        command.extend(["--user-task", user])
    for injection in injections:
        command.extend(["--injection-task", injection])
    if force_rerun:
        command.append("--force-rerun")
    return command


def expected_case_count(selection: dict[str, dict[str, list[str]]]) -> int:
    return sum(len(row["users"]) * len(row["injections"]) for row in selection.values())


def targeted_selection(
    cases: list[dict[str, Any]],
    case_key: str | None,
) -> dict[str, dict[str, list[str]]]:
    if not case_key:
        raise ValueError("--case-key is required in targeted mode")
    parts = case_key.split(":")
    if len(parts) != 3:
        raise ValueError("--case-key must be SUITE:USER_TASK_ID:INJECTION_TASK_ID")
    suite, user, injection = parts
    known = {
        (row["suite"], row["user_task_id"], row["injection_task_id"])
        for row in cases
    }
    if (suite, user, injection) not in known:
        raise ValueError(f"case is not in the fixed E79 manifest: {case_key}")
    return {suite: {"users": [user], "injections": [injection]}}


def frozen_manifest_selection(path: Path, cases: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    selection = payload.get("selection")
    expected_keys = payload.get("case_keys")
    if not isinstance(selection, dict) or not isinstance(expected_keys, list):
        raise ValueError("pilot manifest requires selection and case_keys")
    normalized = {
        str(suite): {
            "users": [str(value) for value in row.get("users", [])],
            "injections": [str(value) for value in row.get("injections", [])],
        }
        for suite, row in selection.items()
        if isinstance(row, dict)
    }
    reconstructed = {
        f"{suite}:{user}:{injection}"
        for suite, row in normalized.items()
        for user in row["users"]
        for injection in row["injections"]
    }
    if reconstructed != set(expected_keys) or len(expected_keys) != len(set(expected_keys)):
        raise ValueError("pilot manifest case_keys do not match its Cartesian selection")
    known = {
        f"{row['suite']}:{row['user_task_id']}:{row['injection_task_id']}"
        for row in cases
    }
    if not reconstructed or not reconstructed.issubset(known):
        raise ValueError("pilot manifest contains keys outside the fixed E79 manifest")
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=("no_guard", "e77", "c1f", "c1f_pn"), required=True)
    parser.add_argument("--mode", choices=("dry-run", "smoke", "targeted", "pilot", "full"), default="dry-run")
    parser.add_argument("--case-key", help="Fixed manifest key SUITE:USER_TASK_ID:INJECTION_TASK_ID")
    parser.add_argument("--selection-manifest", type=Path)
    parser.add_argument("--port", type=int, default=18082)
    parser.add_argument("--model-id", default="qwen3_32b_local")
    parser.add_argument("--agent-backend", choices=("local", "deepseek"), default="local")
    parser.add_argument("--logdir", type=Path)
    parser.add_argument("--force-rerun", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    c1f_source_hashes = verify_c1f_sources() if args.method in {"c1f", "c1f_pn"} else None
    cases = read_cases()
    selection = selection_by_suite(cases)
    if expected_case_count(selection) != 303:
        raise RuntimeError("saved-attack selection does not reconstruct exactly 303 Cartesian keys")
    if args.mode == "smoke":
        selection = {"workspace": {"users": ["user_task_2"], "injections": ["injection_task_5"]}}
    elif args.mode == "targeted":
        selection = targeted_selection(cases, args.case_key)
    elif args.mode == "pilot":
        if args.selection_manifest is None:
            raise ValueError("--selection-manifest is required in pilot mode")
        selection = frozen_manifest_selection(args.selection_manifest, cases)

    run_root = args.logdir or RUNS / f"{args.method}_{args.agent_backend}"
    if not run_root.is_absolute():
        run_root = ROOT / run_root
    commands = []
    results = []
    for suite, selected in selection.items():
        command = build_command(
            suite=suite,
            users=selected["users"],
            injections=selected["injections"],
            method=args.method,
            model_id=args.model_id,
            logdir=run_root,
            force_rerun=args.force_rerun,
            agent_backend=args.agent_backend,
        )
        commands.append({"suite": suite, "command": command})
        if args.mode == "dry-run":
            continue
        env = {
            **os.environ,
            "PYTHONPATH": (
                f"{SHADOW_C1F}:{ROOT / 'code'}:{VENDOR_SRC}"
                if args.method in {"c1f", "c1f_pn"}
                else f"{ROOT / 'code'}:{VENDOR_SRC}"
            ),
            "LOCAL_LLM_PORT": str(args.port),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "E79_AGENTLAB_SAVED_ATTACK_ROOT": str(
                ROOT / "runs/e79_external_benchmarks/AgentLAB/Task-Injection/agentdojo/res/long_horizon/gpt-4o-backip"
            ),
            "E77_EFFECT_DIFF_RUNTIME": "1" if args.method in {"e77", "c1f", "c1f_pn"} else "0",
            "E77_REGISTERED_DESCRIPTOR_JSONL": str(
                CURRENT_C1F_DESCRIPTORS
                if args.method in {"c1f", "c1f_pn"}
                else ROOT / "analysis/results/e77_registered_effect_diff_descriptors.jsonl"
            ),
            "E77_RUNTIME_CATALOG": str(
                CURRENT_C1F_RUNTIME_CATALOG
                if args.method in {"c1f", "c1f_pn"}
                else ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"
            ),
            "E77_PLAN_CACHE": str(run_root / "e77_plan_cache.json"),
            "E77_AUDIT_JSONL": str(run_root / "e77_runtime_audit.jsonl"),
            "E77_PLANNER_PORT": str(args.port),
            "E77_AGENT_MAX_TOKENS": "4096",
            "E79_STRICT_LOCAL_RUNTIME": "1",
        }
        if args.method in {"c1f", "c1f_pn"}:
            env.update(
                {
                    "E77_POLICY_VARIANT": "atom_control_taint_envelope",
                    "E77_UNCERTAINTY_POLICY": "allow_with_trail",
                    "E77_RELATION_CATALOG": str(CURRENT_C1F_RELATION_CATALOG),
                    "E77_EXECUTION_DATE": "2026-08-02",
                }
            )
        if args.agent_backend == "deepseek":
            if not env.get("DEEPSEEK_API_KEY"):
                raise RuntimeError("DEEPSEEK_API_KEY is required for --agent-backend deepseek")
            env.update(
                {
                    "ATOM_UTILITY_DEEPSEEK": "1",
                    "ATOM_UTILITY_CONDITION": "pristine",
                    "ATOM_UTILITY_AUDIT_JSONL": str(run_root / "deepseek_agent_audit.jsonl"),
                    "DEEPSEEK_BASE_URL": env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                    "DEEPSEEK_MODEL": env.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
                }
            )
        completed = subprocess.run(
            command,
            cwd=VENDOR,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        results.append({
            "suite": suite,
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        })
        if completed.returncode != 0:
            break

    executed = args.mode != "dry-run"
    all_clean = executed and len(results) == len(selection) and all(row["returncode"] == 0 for row in results)
    report = {
        "experiment": "E79",
        "run_type": "agentlab_saved_attack_transfer",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "dry_run_ready" if not executed else "execution_completed_unfinalized" if all_clean else "execution_failed",
        "method": args.method,
        "mode": args.mode,
        "model_id": args.model_id,
        "agent_backend": args.agent_backend,
        "api_key_serialized": False,
        "local_llm_port": args.port,
        "source_manifest": "evaluation/e79_long_horizon/agentlab_saved_attack_manifest.json",
        "selection_manifest": str(args.selection_manifest) if args.selection_manifest else None,
        "selection": selection,
        "expected_case_keys": expected_case_count(selection),
        "commands": commands,
        "command_results": results,
        "c1f_source_hashes": c1f_source_hashes,
        "logdir": str(run_root.relative_to(ROOT)),
        "claim_boundary": (
            "This runner transfers fixed public AgentLAB attacks to identical victims and deterministic v1.2.1 evaluators. "
            "It does not regenerate attacks, reproduce the artifact's cumulative optimization protocol, or establish a result "
            "until a separate finalizer verifies every expected key, metric, error, and precommit record."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / f"e79_agentlab_saved_transfer_{args.method}_{args.mode.replace('-', '_')}_status.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {"dry_run_ready", "execution_completed_unfinalized"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
