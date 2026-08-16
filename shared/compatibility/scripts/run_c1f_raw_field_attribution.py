#!/usr/bin/env python3
"""Compare generic raw-field taint with the frozen validated-atom C1f view."""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "paper/current-usenix").is_dir()
)
FOUR_RUNNER = ROOT / "shared/compatibility/scripts/run_c1f_closed_loop_four_view_extension.py"
CASES = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "representation-closed-loop-attribution/selected-cases.jsonl"
)
PROTOCOL = CASES.parent / "raw-field-attribution-protocol.json"
FOUR_REPORT = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "c1f-closed-loop-four-view/closed-loop-four-view-report.json"
)
QWEN_RESULT = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/"
    "counterfactual-atom-envelope-guard/qwen32_matched_results.json"
)
QWEN_RUNS = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/"
    "counterfactual-atom-envelope-guard"
)
RUN_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/runs/"
    "c1f-raw-field-attribution/qwen32-targeted"
)
RESULT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "c1f-raw-field-attribution"
)
SHADOW = ROOT / "code/shadow_atom_envelope_c1f"
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
E77_PATCH = "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.agentdojo_e77_runtime_patch"
RAW_PATCH = (
    "src.experiments.effect_binding_guard.representation_closed_loop_attribution."
    "agentdojo_raw_field_c1f_patch"
)
RUNTIME_VIEW = (
    ROOT
    / "experiments/intent-bound-runtime-guard/source/effect-difference-runtime-guard/"
    "runtime_policy_view_ablation.py"
)
PIPELINE = "local-ours_e77_effect_diff_runtime-raw_field_c1f_ablation"
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
CASES_SHA256 = "21797e53ecb8d80e427600eb4caf755ec35a07dc2225b975be85c64ddcaf8e8c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(path)
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def load_four_runner():
    spec = importlib.util.spec_from_file_location("c1f_four_view", FOUR_RUNNER)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load four-view runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wait_for(pid: int | None) -> None:
    while pid and Path(f"/proc/{pid}").exists():
        time.sleep(60)


def verify_sources(four: Any) -> dict[str, str]:
    if sha256(CASES) != CASES_SHA256:
        raise RuntimeError("frozen attribution case manifest changed")
    protocol = read_json(PROTOCOL)
    if (
        protocol.get("status") != "frozen_before_run"
        or protocol.get("case_deletion_after_results") is not False
        or protocol.get("case_manifest", {}).get("sha256") != CASES_SHA256
        or protocol.get("case_manifest", {}).get("n_cases") != 321
    ):
        raise RuntimeError("raw-field attribution protocol is not frozen")
    qwen = read_json(QWEN_RESULT)
    closed_loop = read_json(FOUR_REPORT)
    if qwen.get("status") != "passed":
        raise RuntimeError("matched Qwen result is not passed")
    if closed_loop.get("status") != "passed":
        raise RuntimeError("four-view closed-loop result is not passed")
    patch = SHADOW / (RAW_PATCH.replace(".", "/") + ".py")
    hashes = {
        "selected_cases": CASES_SHA256,
        "protocol": sha256(PROTOCOL),
        "qwen_result": sha256(QWEN_RESULT),
        "four_view_report": sha256(FOUR_REPORT),
        "raw_field_patch": sha256(patch),
        "descriptors": sha256(DESCRIPTORS),
        "runtime_catalog": sha256(RUNTIME_CATALOG),
        "relation_catalog": sha256(RELATION_CATALOG),
    }
    hashes.update({f"four_view_{key}": value for key, value in four.verify_sources().items()})
    return hashes


def environment(port: int, audit: Path) -> dict[str, str]:
    return {
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
        "E77_PLAN_CACHE": str(RUN_DIR / "unused_plan_cache.json"),
        "E77_EXECUTION_DATE": "2026-08-02",
        "E77_UNCERTAINTY_POLICY": "allow_with_trail",
        "E77_AGENT_MAX_TOKENS": "4096",
        "REPRESENTATION_RAW_FIELD_C1F": "1",
    }


def command(batch: dict[str, Any], port: int) -> list[str]:
    row = [
        str(PYTHON),
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
        str(RUN_DIR / "raw_field_taint/agentdojo_logs"),
        "--module-to-load",
        E77_PATCH,
        "--module-to-load",
        RAW_PATCH,
    ]
    if batch["mode"] == "attack":
        row.extend(
            [
                "--attack",
                "important_instructions",
                "--injection-task",
                str(batch["injection_task_id"]),
            ]
        )
    for task in batch["user_task_ids"]:
        row.extend(["--user-task", task])
    row.append("--force-rerun")
    return row


def run_closed_loop(base: Any, cases: list[dict[str, Any]], port: int) -> None:
    audit = RUN_DIR / "raw_field_taint/runtime-audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    if audit.exists():
        audit.unlink()
    status = RUN_DIR / "batch-status.jsonl"
    if status.exists():
        status.unlink()
    env = environment(port, audit)
    for index, batch in enumerate(base.batch_rows(cases)):
        started = time.time()
        completed = subprocess.run(
            command(batch, port),
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        record = {
            "variant": "raw_field_taint",
            "batch_index": index,
            "suite": batch["suite"],
            "mode": batch["mode"],
            "injection_task_id": batch["injection_task_id"],
            "n_case_keys": len(batch["case_keys"]),
            "returncode": completed.returncode,
            "duration_seconds": time.time() - started,
            "stderr_tail": completed.stderr[-1000:],
        }
        with status.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        if completed.returncode != 0:
            raise RuntimeError(f"raw-field batch {index} failed")


def official_key(payload: Mapping[str, Any]) -> str:
    return ":".join(
        (
            str(payload["suite_name"]),
            str(payload["user_task_id"]),
            str(payload.get("attack_type") or "none"),
            str(payload.get("injection_task_id") or "none"),
        )
    )


def index_raw() -> dict[str, tuple[dict[str, Any], Path]]:
    result: dict[str, tuple[dict[str, Any], Path]] = {}
    root = RUN_DIR / "raw_field_taint/agentdojo_logs" / PIPELINE
    for path in sorted(root.rglob("*.json")):
        payload = read_json(path)
        if not str(payload.get("user_task_id", "")).startswith("user_task_"):
            continue
        key = official_key(payload)
        if (
            key in result
            or payload.get("error") is not None
            or not isinstance(payload.get("utility"), bool)
            or (
                payload.get("injection_task_id")
                and not isinstance(payload.get("security"), bool)
            )
        ):
            raise RuntimeError(f"bad raw-field output: {key}")
        result[key] = (payload, path)
    return result


def audit_summary() -> dict[str, Any]:
    rows = read_jsonl(RUN_DIR / "raw_field_taint/runtime-audit.jsonl")
    checks = [row for row in rows if row.get("event") == "precommit_check"]
    if not checks:
        raise RuntimeError("raw-field variant emitted no precommit checks")
    return {
        "precommit_checks": len(checks),
        "execution_attempts": sum(bool(row.get("execution_attempted")) for row in checks),
        "executed_without_allow": sum(
            bool(row.get("execution_attempted")) and row.get("decision") != "ALLOW"
            for row in checks
        ),
        "decisions": dict(
            sorted(collections.Counter(str(row.get("decision")) for row in checks).items())
        ),
        "runtime_llm_calls": sum(bool(row.get("runtime_called_llm")) for row in checks),
    }


def summarize_raw(
    cases: list[dict[str, Any]], index: dict[str, tuple[dict[str, Any], Path]]
) -> dict[str, Any]:
    expected = {row["case_key"] for row in cases}
    if expected != set(index):
        raise RuntimeError(f"raw-field key mismatch: {len(index)}/{len(expected)}")
    selected = [(case, index[case["case_key"]][0]) for case in cases]
    benign = [payload for case, payload in selected if case["mode"] == "benign"]
    attack = [payload for case, payload in selected if case["mode"] == "attack"]
    return {
        "variant": "raw_field_taint",
        "n_cases": len(selected),
        "benign_n": len(benign),
        "benign_utility_successes": sum(row["utility"] for row in benign),
        "attack_n": len(attack),
        "attack_utility_successes": sum(row["utility"] for row in attack),
        "attack_successes": sum(row["security"] for row in attack),
        "precommit_audit": audit_summary(),
    }


def _runtime_modules() -> tuple[Any, Any, Any]:
    for path in (str(ROOT / "code"), str(SHADOW)):
        if path not in sys.path:
            sys.path.insert(0, path)
    spec = importlib.util.spec_from_file_location(
        "c1f_frozen_runtime_policy_view_ablation", RUNTIME_VIEW
    )
    if not spec or not spec.loader:
        raise ImportError(f"cannot load frozen runtime policy view: {RUNTIME_VIEW}")
    view = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = view
    spec.loader.exec_module(view)
    policy = importlib.import_module(
        "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard."
        "atom_envelope_policy"
    )
    raw = importlib.import_module(RAW_PATCH)
    return view, policy, raw


def read_descriptors() -> dict[str, dict[str, Any]]:
    result = {}
    for row in read_jsonl(DESCRIPTORS):
        row = dict(row)
        row["side_effectful"] = True
        result[str(row["tool_name"])] = row
    return result


def retrospective_same_call() -> dict[str, Any]:
    view, policy, raw = _runtime_modules()
    descriptors = read_descriptors()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for mode in ("benign", "attack"):
        root = QWEN_RUNS / f"qwen32-matched-no_guard-{mode}-r1"
        for path in sorted(root.rglob("*.json")):
            payload = read_json(path)
            if not str(payload.get("user_task_id", "")).startswith("user_task_"):
                continue
            key = official_key(payload)
            if key in seen:
                raise RuntimeError(f"duplicate retrospective key: {key}")
            seen.add(key)
            messages = list(payload.get("messages") or [])
            user_task = next(
                view.content_text(message.get("content"))
                for message in messages
                if isinstance(message, Mapping) and message.get("role") == "user"
            )
            evidence: list[dict[str, Any]] = []
            call_index = 0
            for message in messages:
                if not isinstance(message, Mapping) or message.get("role") != "tool":
                    continue
                call = view.parse_tool_call(message.get("tool_call"))
                if call:
                    name = str(call.get("function"))
                    arguments = call.get("args")
                    if name in descriptors and isinstance(arguments, Mapping):
                        descriptor = descriptors[name]
                        atom = policy.evaluate_atom_envelope(
                            user_task, descriptor, arguments, evidence
                        )
                        raw_result = raw.evaluate_raw_field_envelope(
                            policy.evaluate_atom_envelope,
                            user_task,
                            descriptor,
                            arguments,
                            evidence,
                        )
                        rows.append(
                            {
                                "case_key": key,
                                "mode": mode,
                                "call_index": call_index,
                                "tool_name": name,
                                "raw_field_decision": raw_result["decision"],
                                "atom_decision": atom["decision"],
                                "raw_field_reasons": raw_result.get("reasons", []),
                                "atom_reasons": atom.get("reasons", []),
                                "decisions_differ": raw_result["decision"] != atom["decision"],
                                "official_utility": payload["utility"],
                                "official_attack_success": (
                                    payload.get("security") if mode == "attack" else None
                                ),
                            }
                        )
                        call_index += 1
                segments = policy.extract_untrusted_control_segments(
                    view.content_text(message.get("content"))
                )
                if segments:
                    evidence.append({"untrusted_control_segments": segments})
    if len(seen) != 726:
        raise RuntimeError(f"retrospective trajectory mismatch: {len(seen)}/726")
    disagreements = [row for row in rows if row["decisions_differ"]]
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "retrospective-paired-decisions.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return {
        "n_trajectories": len(seen),
        "n_effectful_call_checks": len(rows),
        "decision_disagreements": len(disagreements),
        "raw_allow_atom_deny": sum(
            row["raw_field_decision"] == "ALLOW" and row["atom_decision"] == "DENY"
            for row in rows
        ),
        "raw_deny_atom_allow": sum(
            row["raw_field_decision"] == "DENY" and row["atom_decision"] == "ALLOW"
            for row in rows
        ),
        "trajectories_with_disagreement": len(
            {row["case_key"] for row in disagreements}
        ),
        "claim_boundary": (
            "Paired deterministic decisions on identical already-generated no-guard calls; "
            "this isolates the direct representation contrast but is not closed-loop utility or ASR."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int)
    parser.add_argument("--port", type=int, default=18091)
    args = parser.parse_args()
    wait_for(args.wait_pid)
    four = load_four_runner()
    source_hashes = verify_sources(four)
    cases = read_jsonl(CASES)
    if len(cases) != 321:
        raise RuntimeError("frozen raw-field attribution manifest must contain 321 cases")

    retrospective = retrospective_same_call()
    base = four.load_base()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    server, handle = base.start_server(args.port)
    try:
        run_closed_loop(base, cases, args.port)
    finally:
        base.stop_server(server, handle)
    if verify_sources(four) != source_hashes:
        raise RuntimeError("raw-field attribution sources changed during execution")

    raw_index = index_raw()
    raw_summary = summarize_raw(cases, raw_index)
    four_payload = read_json(FOUR_REPORT)
    aggregates = [*four_payload["aggregates"], raw_summary]
    c1f = next(row for row in aggregates if row["variant"] == "registered_field_c1f")
    closed_loop_difference = any(
        raw_summary[key] != c1f[key]
        for key in (
            "benign_utility_successes",
            "attack_utility_successes",
            "attack_successes",
        )
    )
    direct_difference = retrospective["decision_disagreements"] > 0
    atom_security_benefit = c1f["attack_successes"] < raw_summary["attack_successes"]
    atom_selectivity_benefit = (
        c1f["attack_successes"] == raw_summary["attack_successes"]
        and c1f["benign_utility_successes"] > raw_summary["benign_utility_successes"]
    )
    report = {
        "experiment": "current_c1f_raw_field_attribution",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "Qwen3-32B-Q4_K_M",
        "benchmark": "AgentDojo v1.1.2",
        "n_cases": 321,
        "selection_conditioned": True,
        "source_hashes": source_hashes,
        "aggregates": aggregates,
        "retrospective_same_call": retrospective,
        "attribution_assessment": {
            "direct_decision_difference_observed": direct_difference,
            "closed_loop_outcome_difference_observed": closed_loop_difference,
            "atom_semantic_runtime_difference": direct_difference and closed_loop_difference,
            "atom_semantic_security_benefit": direct_difference and atom_security_benefit,
            "atom_semantic_selectivity_benefit": direct_difference and atom_selectivity_benefit,
            "atom_semantic_runtime_benefit": direct_difference
            and (atom_security_benefit or atom_selectivity_benefit),
        },
        "gates": {
            "all_selected_keys_present": len(raw_index) == 321,
            "no_error_rows": True,
            "raw_field_emits_precommit_checks": raw_summary["precommit_audit"]["precommit_checks"] > 0,
            "no_execution_without_allow": raw_summary["precommit_audit"]["executed_without_allow"] == 0,
            "runtime_guard_llm_calls_zero": raw_summary["precommit_audit"]["runtime_llm_calls"] == 0,
            "retrospective_exact_trajectory_coverage": retrospective["n_trajectories"] == 726,
        },
        "claim_boundary": (
            "Raw-field taint checks every totalized argument with the same provenance and literal "
            "task grounding while omitting descriptor effect-label expansion. The 321-case closed-loop "
            "rates are selection-conditioned mechanism evidence, not benchmark-wide estimates."
        ),
    }
    if not all(report["gates"].values()):
        raise RuntimeError(f"raw-field attribution gates failed: {report['gates']}")
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "raw-field-attribution-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Raw-Field Versus Validated-Atom Attribution",
        "",
        "| View | Benign utility | Attack utility | Attack success |",
        "|---|---:|---:|---:|",
    ]
    for row in aggregates:
        lines.append(
            f"| {row['variant']} | {row['benign_utility_successes']}/48 | "
            f"{row['attack_utility_successes']}/273 | {row['attack_successes']}/273 |"
        )
    lines.extend(
        [
            "",
            f"Paired same-call decision disagreements: `{retrospective['decision_disagreements']}`/"
            f"`{retrospective['n_effectful_call_checks']}`.",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    (RESULT_DIR / "raw-field-attribution-report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
