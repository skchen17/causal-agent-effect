#!/usr/bin/env python3
"""Complete the current-C1f four-view closed-loop attribution on 321 fixed cases."""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "paper/current-usenix").is_dir()
)
BASE_SCRIPT = ROOT / "shared/compatibility/scripts/run_representation_closed_loop_attribution.py"
CASES = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "representation-closed-loop-attribution/selected-cases.jsonl"
)
RUN_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/runs/"
    "c1f-closed-loop-four-view/qwen32-targeted"
)
RESULT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "c1f-closed-loop-four-view"
)
QWEN_RUNS = ROOT / "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard"
SHADOW = ROOT / "code/shadow_atom_envelope_c1f"
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
E77_PATCH = "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.agentdojo_e77_runtime_patch"
PATCHES = {
    "whole_call_provenance": (
        "src.experiments.effect_binding_guard.representation_closed_loop_attribution."
        "agentdojo_whole_call_c1f_patch"
    ),
    "effect_only": (
        "src.experiments.effect_binding_guard.representation_closed_loop_attribution."
        "agentdojo_effect_only_c1f_patch"
    ),
}
PIPELINES = {
    "no_guard": "local",
    "whole_call_provenance": "local-ours_e77_effect_diff_runtime-whole_call_c1f_ablation",
    "effect_only": "local-ours_e77_effect_diff_runtime-effect_only_c1f_ablation",
    "registered_field_c1f": "local-ours_e77_effect_diff_runtime",
}
DESCRIPTORS = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)
RUNTIME_CATALOG = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
)
RELATION_CATALOG = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/"
    "registered_relation_catalog.json"
)
C1F_FREEZE = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/"
    "counterfactual-atom-envelope-guard/c1f_frozen_candidate_2026-08-08.json"
)
CASES_SHA256 = "21797e53ecb8d80e427600eb4caf755ec35a07dc2225b975be85c64ddcaf8e8c"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sources() -> dict[str, str]:
    if sha256(CASES) != CASES_SHA256:
        raise RuntimeError("frozen four-view case manifest changed")
    frozen = json.loads(C1F_FREEZE.read_text(encoding="utf-8"))
    if frozen.get("status") != "frozen_before_c1f_live_regression":
        raise RuntimeError("C1f candidate is not frozen")
    hashes = {"selected_cases": CASES_SHA256, "c1f_freeze": sha256(C1F_FREEZE)}
    for name, artifact in frozen["source_artifacts"].items():
        path = ROOT / artifact["path"]
        observed = sha256(path)
        if observed != artifact["sha256"]:
            raise RuntimeError(f"frozen C1f artifact changed: {artifact['path']}")
        hashes[f"c1f_{name}"] = observed
    for variant, module_name in PATCHES.items():
        path = SHADOW / (module_name.replace(".", "/") + ".py")
        hashes[f"patch_{variant}"] = sha256(path)
    return hashes


def load_base():
    spec = importlib.util.spec_from_file_location("closed_loop_base", BASE_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load closed-loop base runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def audit_summary(variant: str) -> dict[str, Any] | None:
    if variant in {"no_guard", "registered_field_c1f"}:
        return None
    rows = read_jsonl(RUN_DIR / variant / "runtime-audit.jsonl")
    checks = [row for row in rows if row.get("event") == "precommit_check"]
    if not checks:
        raise RuntimeError(f"{variant} emitted no precommit checks")
    executed_without_allow = sum(
        bool(row.get("execution_attempted")) and row.get("decision") != "ALLOW"
        for row in checks
    )
    return {
        "precommit_checks": len(checks),
        "execution_attempts": sum(bool(row.get("execution_attempted")) for row in checks),
        "executed_without_allow": executed_without_allow,
        "decisions": dict(sorted(collections.Counter(str(row.get("decision")) for row in checks).items())),
        "runtime_llm_calls": sum(bool(row.get("runtime_called_llm")) for row in checks),
    }


def wait_for(pid: int | None) -> None:
    while pid and Path(f"/proc/{pid}").exists():
        time.sleep(60)


def command(base: Any, variant: str, batch: dict[str, Any], port: int) -> list[str]:
    row = [
        str(PYTHON), "-B", "-m", "agentdojo.scripts.benchmark",
        "--model", "LOCAL", "--model-id", "qwen3_32b_local",
        "--benchmark-version", "v1.1.2", "--suite", batch["suite"],
        "--tool-delimiter", "user", "--logdir", str(RUN_DIR / variant / "agentdojo_logs"),
        "--module-to-load", E77_PATCH, "--module-to-load", PATCHES[variant],
    ]
    if batch["mode"] == "attack":
        row.extend(["--attack", "important_instructions", "--injection-task", str(batch["injection_task_id"])])
    for task in batch["user_task_ids"]:
        row.extend(["--user-task", task])
    row.append("--force-rerun")
    return row


def run_variant(base: Any, variant: str, cases: list[dict[str, Any]], port: int) -> None:
    audit = RUN_DIR / variant / "runtime-audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    if audit.exists():
        audit.unlink()
    env = {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": f"{SHADOW}:{ROOT / 'code'}",
        "LOCAL_LLM_PORT": str(port),
        "E77_EFFECT_DIFF_RUNTIME": "1",
        "E77_POLICY_VARIANT": "atom_control_taint_envelope",
        "E77_REGISTERED_DESCRIPTOR_JSONL": str(DESCRIPTORS),
        "E77_RUNTIME_CATALOG": str(RUNTIME_CATALOG),
        "E77_RELATION_CATALOG": str(RELATION_CATALOG),
        "E77_AUDIT_JSONL": str(audit),
        "E77_PLAN_CACHE": str(RUN_DIR / variant / "unused_plan_cache.json"),
        "E77_EXECUTION_DATE": "2026-08-02",
        "E77_UNCERTAINTY_POLICY": "allow_with_trail",
        "E77_AGENT_MAX_TOKENS": "4096",
        ("REPRESENTATION_WHOLE_CALL_C1F" if variant == "whole_call_provenance" else "REPRESENTATION_EFFECT_ONLY_C1F"): "1",
    }
    status = RUN_DIR / "batch-status.jsonl"
    for index, batch in enumerate(base.batch_rows(cases)):
        started = time.time()
        completed = subprocess.run(command(base, variant, batch, port), cwd=ROOT, env=env, capture_output=True, text=True)
        record = {
            "variant": variant,
            "batch_index": index,
            "suite": batch["suite"],
            "mode": batch["mode"],
            "injection_task_id": batch["injection_task_id"],
            "n_case_keys": len(batch["case_keys"]),
            "returncode": completed.returncode,
            "duration_seconds": time.time() - started,
        }
        with status.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        if completed.returncode != 0:
            raise RuntimeError(f"{variant} batch {index} failed")


def official_key(payload: dict[str, Any]) -> str:
    attack = payload.get("attack_type") or "none"
    injection = payload.get("injection_task_id") or "none"
    return f'{payload["suite_name"]}:{payload["user_task_id"]}:{attack}:{injection}'


def index_new(variant: str) -> dict[str, dict[str, Any]]:
    result = {}
    root = RUN_DIR / variant / "agentdojo_logs" / PIPELINES[variant]
    for path in sorted(root.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not str(payload.get("user_task_id", "")).startswith("user_task_"):
            continue
        key = official_key(payload)
        if (
            key in result
            or payload.get("error") is not None
            or not isinstance(payload.get("utility"), bool)
            or not isinstance(payload.get("security"), bool)
        ):
            raise RuntimeError(f"bad {variant} output: {key}")
        result[key] = payload
    return result


def index_current(variant: str) -> dict[str, dict[str, Any]]:
    result = {}
    for mode in ("benign", "attack"):
        condition = "no_guard" if variant == "no_guard" else "c1f"
        root = QWEN_RUNS / f"qwen32-matched-{condition}-{mode}-r1"
        for path in sorted(root.rglob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not str(payload.get("user_task_id", "")).startswith("user_task_"):
                continue
            key = official_key(payload)
            if (
                key in result
                or payload.get("error") is not None
                or not isinstance(payload.get("utility"), bool)
                or (mode == "attack" and not isinstance(payload.get("security"), bool))
            ):
                raise RuntimeError(f"bad current {variant} output: {key}")
            result[key] = payload
    return result


def summarize(variant: str, cases: list[dict[str, Any]], index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    expected = {row["case_key"] for row in cases}
    if not expected <= set(index):
        raise RuntimeError(f"{variant} missing {len(expected - set(index))} selected keys")
    rows = [(case, index[case["case_key"]]) for case in cases]
    benign = [payload for case, payload in rows if case["mode"] == "benign"]
    attack = [payload for case, payload in rows if case["mode"] == "attack"]
    return {
        "variant": variant,
        "n_cases": len(rows),
        "benign_n": len(benign),
        "benign_utility_successes": sum(row["utility"] for row in benign),
        "attack_n": len(attack),
        "attack_utility_successes": sum(row["utility"] for row in attack),
        "attack_successes": sum(row["security"] for row in attack),
        "precommit_audit": audit_summary(variant),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int)
    parser.add_argument("--port", type=int, default=18089)
    args = parser.parse_args()
    wait_for(args.wait_pid)
    source_hashes = verify_sources()
    qwen_result = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/qwen32_matched_results.json"
    if not qwen_result.is_file() or json.loads(qwen_result.read_text()).get("status") != "passed":
        raise RuntimeError("matched Qwen result must pass before four-view extension")
    cases = read_jsonl(CASES)
    if len(cases) != 321:
        raise RuntimeError("frozen four-view manifest must contain 321 cases")
    base = load_base()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    server, handle = base.start_server(args.port)
    try:
        for variant in ("whole_call_provenance", "effect_only"):
            run_variant(base, variant, cases, args.port)
    finally:
        base.stop_server(server, handle)
    if verify_sources() != source_hashes:
        raise RuntimeError("four-view sources changed during execution")
    indexes = {
        "no_guard": index_current("no_guard"),
        "whole_call_provenance": index_new("whole_call_provenance"),
        "effect_only": index_new("effect_only"),
        "registered_field_c1f": index_current("registered_field_c1f"),
    }
    aggregates = [summarize(variant, cases, index) for variant, index in indexes.items()]
    report = {
        "experiment": "current_c1f_closed_loop_four_view",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "Qwen3-32B-Q4_K_M",
        "model_sha256": base.MODEL_SHA256,
        "benchmark": "AgentDojo v1.1.2",
        "n_cases": 321,
        "selection_conditioned": True,
        "source_hashes": source_hashes,
        "aggregates": aggregates,
        "gates": {
            "all_selected_keys_present": True,
            "no_error_rows": True,
            "new_variants_emit_precommit_checks": all(
                row["precommit_audit"] and row["precommit_audit"]["precommit_checks"] > 0
                for row in aggregates
                if row["variant"] in {"whole_call_provenance", "effect_only"}
            ),
            "no_execution_without_allow": all(
                not row["precommit_audit"]
                or row["precommit_audit"]["executed_without_allow"] == 0
                for row in aggregates
            ),
        },
        "claim_boundary": (
            "Closed-loop comparison on a fixed subset selected for prior field-mismatch applicability; "
            "rates are mechanism evidence, not full-benchmark estimates."
        ),
    }
    if not all(report["gates"].values()):
        raise RuntimeError(f"four-view completion gates failed: {report['gates']}")
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "closed-loop-four-view-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
