"""Run a fixed A--E AgentDojo self-governance smoke or pilot."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .descriptors import CONDITIONS


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir()
)
EXPERIMENT = ROOT / "experiments/intent-bound-runtime-guard"
SOURCE_RESULTS = EXPERIMENT / "results/atomized-tool-description-self-governance"
RUNS = EXPERIMENT / "runs/atomized-tool-description-self-governance"
PYTHON = ROOT / "experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python"
MODEL = Path(
    "/data/CSK/causal-agent-safety-research/models/"
    "Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"
)
UNVALIDATED = EXPERIMENT / "results/llm-descriptor-agent-runtime/llm-descriptor-candidates.jsonl"
VALIDATED = EXPERIMENT / "results/effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl"
NEUTRAL = SOURCE_RESULTS / "token-matched-neutral-control.json"
RUNTIME_CATALOG = ROOT / "experiments/security-analysis-ablation-and-overhead/evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
RELATION_CATALOG = EXPERIMENT / "evaluation/effect-difference-runtime-guard/registered_relation_catalog.json"
MODULE = "src.experiments.effect_binding_guard.atomized_tool_description_self_governance.agentdojo_patch"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "pilot", "summarize"), default="smoke")
    parser.add_argument("--port", type=int, default=18089)
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--case-kind", choices=("both", "benign", "attack"), default="both")
    parser.add_argument("--case-timeout", type=int, default=720)
    parser.add_argument("--merge-run", action="append", default=[])
    return parser.parse_args()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def _start_server(root: Path, port: int) -> subprocess.Popen[str]:
    log = (root / "llama_cpp_server.log").open("a", encoding="utf-8")
    command = [
        "/home/user/anaconda3/bin/python", "-m", "llama_cpp.server",
        "--model", str(MODEL), "--model_alias", "qwen3_32b_local",
        "--host", "127.0.0.1", "--port", str(port),
        "--n_gpu_layers", "65", "--split_mode", "1", "--tensor_split", "0.35", "0.65",
        "--n_ctx", "65536", "--n_batch", "1024", "--n_ubatch", "512", "--flash_attn", "true",
    ]
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"},
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for _ in range(300):
        if process.poll() is not None:
            raise RuntimeError("local Qwen server exited during startup")
        if _healthy(port):
            return process
        time.sleep(2)
    process.terminate()
    raise TimeoutError("local Qwen server did not become healthy")


def _cases(mode: str) -> list[tuple[str, str, str | None]]:
    if mode == "smoke":
        return [
            ("banking", "user_task_11", None),
            ("banking", "user_task_11", "injection_task_4"),
        ]
    return [
        ("banking", "user_task_12", None),
        ("banking", "user_task_12", "injection_task_7"),
        ("slack", "user_task_0", None),
        ("slack", "user_task_0", "injection_task_1"),
        ("workspace", "user_task_16", None),
        ("workspace", "user_task_16", "injection_task_1"),
        ("travel", "user_task_0", None),
        ("travel", "user_task_0", "injection_task_6"),
    ]


def _child_env(condition: str, run_root: Path, port: int) -> dict[str, str]:
    audit = run_root / f"forecast-audit-{condition}.jsonl"
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "code"),
        "LOCAL_LLM_PORT": str(port),
        "ATOM_DESC_SELF_GOVERNANCE": "1",
        "ATOM_DESC_CONDITION": condition,
        "ATOM_DESC_AUDIT_JSONL": str(audit),
        "ATOM_DESC_REVIEW_JSONL": str(run_root / "precommit-review-audit.jsonl"),
        "ATOM_DESC_UNVALIDATED_JSONL": str(UNVALIDATED),
        "ATOM_DESC_VALIDATED_JSONL": str(VALIDATED),
        "ATOM_DESC_NEUTRAL_JSON": str(NEUTRAL),
        "ATOM_DESC_AGENT_MAX_TOKENS": "4096",
        "E77_EFFECT_DIFF_RUNTIME": "1" if condition == "e_validated_atoms_guard" else "0",
        "E77_UNCERTAINTY_POLICY": "fail_closed",
        "E77_REGISTERED_DESCRIPTOR_JSONL": str(VALIDATED),
        "E77_RUNTIME_CATALOG": str(RUNTIME_CATALOG),
        "E77_RELATION_CATALOG": str(RELATION_CATALOG),
        "E77_PLAN_CACHE": str(run_root / "e77-plan-cache.json"),
        "E77_AUDIT_JSONL": str(run_root / "e77-guard-audit.jsonl"),
        "E77_AGENT_MAX_TOKENS": "4096",
        "E77_PLANNER_PORT": str(port),
        "E77_PLANNER_MODEL": "qwen3_32b_local",
    }
    return env


def _run_case(
    condition: str,
    suite: str,
    user_task: str,
    injection_task: str | None,
    run_root: Path,
    port: int,
    timeout: int,
) -> dict[str, Any]:
    command = [
        str(PYTHON), "-m", "agentdojo.scripts.benchmark",
        "--model", "LOCAL", "--benchmark-version", "v1.1.2",
        "--suite", suite, "--tool-delimiter", "user",
        "--logdir", str(run_root / "agentdojo_logs"),
        "--module-to-load", MODULE,
        "--user-task", user_task,
        "--force-rerun",
    ]
    if injection_task:
        command.extend(["--attack", "important_instructions", "--injection-task", injection_task])
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=_child_env(condition, run_root, port),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "condition": condition,
            "suite": suite,
            "user_task": user_task,
            "injection_task": injection_task,
            "returncode": 124,
            "stdout_tail": (exc.stdout or "")[-2500:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": "case_timeout",
        }
    return {
        "condition": condition,
        "suite": suite,
        "user_task": user_task,
        "injection_task": injection_task,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2500:],
        "stderr_tail": completed.stderr[-2500:],
    }


def _load_outcomes(run_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((run_root / "agentdojo_logs").glob("**/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        # AgentDojo additionally evaluates an injection task as a standalone
        # user task. That auxiliary row is not one of this experiment's fixed
        # benign/attack keys and must not enter the A--E denominators.
        if not str(payload.get("user_task_id", "")).startswith("user_task_"):
            continue
        # AgentDojo writes an intermediate trajectory file before scoring it.
        # A timed-out process may leave that file behind with null metrics. It
        # is useful forensic evidence but is not a completed outcome.
        if payload.get("duration") is None or not isinstance(payload.get("utility"), bool):
            continue
        rows.append(
            {
                "condition": payload.get("pipeline_name", "").rsplit("-atom-self-governance-", 1)[-1],
                "suite": payload.get("suite_name"),
                "user_task": payload.get("user_task_id"),
                "injection_task": payload.get("injection_task_id"),
                "utility": payload.get("utility"),
                "attack_success": bool(payload.get("security")) if payload.get("injection_task_id") else None,
                "error": payload.get("error"),
                "duration": payload.get("duration"),
                "source": str(path.relative_to(ROOT)),
            }
        )
    return rows


def _load_forecasts(run_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(run_root.glob("forecast-audit-*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            rows.extend(json.loads(line) for line in handle if line.strip())
    return rows


def _load_reviews(run_root: Path) -> list[dict[str, Any]]:
    path = run_root / "precommit-review-audit.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _summarize(run_root: Path, extra_roots: tuple[Path, ...] = ()) -> dict[str, Any]:
    run_roots = (run_root, *extra_roots)
    outcome_index: dict[tuple[Any, ...], dict[str, Any]] = {}
    for root in run_roots:
        for row in _load_outcomes(root):
            key = (
                row["condition"], row["suite"], row["user_task"],
                row["injection_task"],
            )
            # Later merge roots are explicit replacement runs (for example, a
            # corrected descriptor condition) and deterministically supersede
            # the earlier copy of the same fixed case.
            outcome_index[key] = row
    outcomes = list(outcome_index.values())
    commands: list[dict[str, Any]] = []
    for root in run_roots:
        command_path = root / "command_status.json"
        if command_path.exists():
            payload = json.loads(command_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                commands.extend(row for row in payload if isinstance(row, dict))
    case_failures = [row for row in commands if row.get("returncode") != 0]
    manifests: list[dict[str, Any]] = []
    for root in run_roots:
        manifest_path = root / "protocol_manifest.json"
        manifests.append(
            json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest_path.exists() else {}
        )
    expected_conditions = tuple(dict.fromkeys(
        condition
        for manifest in manifests
        for condition in manifest.get("conditions", [])
    )) or CONDITIONS
    expected_cases = {
        condition: len(manifest.get("cases", []))
        for manifest in manifests
        for condition in manifest.get("conditions", [])
    }
    forecasts = _load_forecasts(run_root)
    reviews = _load_reviews(run_root)
    for extra_root, extra_manifest in zip(extra_roots, manifests[1:]):
        extra_conditions = set(extra_manifest.get("conditions", []))
        forecasts = [
            row for row in forecasts
            if row.get("condition") not in extra_conditions
        ]
        forecasts.extend(_load_forecasts(extra_root))
        extra_conditions = set(extra_manifest.get("conditions", []))
        reviews = [row for row in reviews if row.get("condition") not in extra_conditions]
        reviews.extend(_load_reviews(extra_root))
    metrics: dict[str, Any] = {}
    for condition in expected_conditions:
        selected = [row for row in outcomes if row["condition"] == condition]
        benign = [row for row in selected if row["injection_task"] is None]
        attacks = [row for row in selected if row["injection_task"] is not None]
        condition_forecasts = [
            row for row in forecasts
            if row.get("event") == "precall_effect_forecast" and row.get("condition") == condition
        ]
        condition_reviews = [
            row for row in reviews
            if row.get("event") == "llm_precommit_review" and row.get("condition") == condition
        ]
        metrics[condition] = {
            "n_outcomes": len(selected),
            "expected_outcomes": expected_cases.get(condition, 0),
            "complete": len(selected) == expected_cases.get(condition, 0),
            "benign_utility": sum(row["utility"] is True for row in benign),
            "benign_total": len(benign),
            "attack_success": sum(row["attack_success"] is True for row in attacks),
            "attack_total": len(attacks),
            "attack_utility": sum(row["utility"] is True for row in attacks),
            "forecast_rows": len(condition_forecasts),
            "forecast_parse_valid": sum(row.get("forecast_parse_valid") is True for row in condition_forecasts),
            "mean_duration_seconds": (
                sum(float(row["duration"]) for row in selected) / len(selected)
                if selected else None
            ),
            "supplement_char_counts": sorted({
                int(row.get("supplement_char_count", 0))
                for row in forecasts
                if row.get("event") == "description_condition"
                and row.get("condition") == condition
            }),
            "forecast_error_counts": dict(Counter(
                error for row in condition_forecasts for error in row.get("forecast_errors", [])
            )),
            "review_calls": len(condition_reviews),
            "review_parse_valid": sum(row.get("parse_valid") is True for row in condition_reviews),
            "review_decision_counts": dict(Counter(
                str(row.get("decision")) for row in condition_reviews
            )),
        }
    report = {
        "status": (
            "passed"
            if outcomes
            and all(row["error"] is None for row in outcomes)
            and all(
                sum(row["condition"] == condition for row in outcomes)
                == expected_cases.get(condition, 0)
                for condition in expected_conditions
            )
            else "incomplete_or_failed"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_roots": [str(root.relative_to(ROOT)) for root in run_roots],
        "conditions": list(expected_conditions),
        "metrics": metrics,
        "outcomes": outcomes,
        "case_failures": case_failures,
        "prompt_leakage_violations": sum(
            len(row.get("prompt_leakage_violations", []))
            for row in forecasts if row.get("event") == "description_condition"
        ),
        "guard_audit_rows": sum(
            sum(1 for line in (root / "e77-guard-audit.jsonl").open(encoding="utf-8") if line.strip())
            for root in run_roots
            if (root / "e77-guard-audit.jsonl").exists()
        ),
        "claim_boundary": (
            "This fixed AgentDojo pilot tests whether model-visible effect representations alter "
            "the agent's own tool decisions. A-D do not enforce the forecast. E composes the same "
            "validated descriptor with the deterministic fail-closed runtime. Pilot results are "
            "not full-benchmark evidence."
        ),
    }
    _write_json(SOURCE_RESULTS / "self-governance-pilot-report.json", report)
    _write_json(run_root / "self-governance-pilot-report.json", report)
    lines = [
        "# Atomized Tool Description Self-Governance Pilot",
        "",
        f"Status: `{report['status']}`.",
        "",
        "| Condition | Benign utility | Attack success | Attack utility | Forecast parse-valid | Mean seconds |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for condition, row in metrics.items():
        duration = (
            f"{row['mean_duration_seconds']:.1f}"
            if row["mean_duration_seconds"] is not None else "-"
        )
        lines.append(
            f"| {condition} | {row['benign_utility']}/{row['benign_total']} | "
            f"{row['attack_success']}/{row['attack_total']} | "
            f"{row['attack_utility']}/{row['attack_total']} | "
            f"{row['forecast_parse_valid']}/{row['forecast_rows']} | {duration} |"
        )
    lines.extend(["", report["claim_boundary"], ""])
    (SOURCE_RESULTS / "self-governance-pilot-report.md").write_text("\n".join(lines), encoding="utf-8")
    (run_root / "self-governance-pilot-report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> int:
    args = parse_args()
    tag = args.run_tag or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_root = RUNS / f"{args.mode}-{tag}"
    if args.mode == "summarize":
        if not args.run_tag:
            raise ValueError("--run-tag must name an existing run for summarize mode")
        print(json.dumps(
            _summarize(
                RUNS / args.run_tag,
                tuple(RUNS / value for value in args.merge_run),
            ),
            indent=2,
            sort_keys=True,
        ))
        return 0
    conditions = tuple(value.strip() for value in args.conditions.split(",") if value.strip())
    unknown = sorted(set(conditions) - set(CONDITIONS))
    if unknown:
        raise ValueError(f"unknown conditions: {unknown}")
    run_root.mkdir(parents=True, exist_ok=True)
    selected_cases = [
        case for case in _cases(args.mode)
        if args.case_kind == "both"
        or (args.case_kind == "benign" and case[2] is None)
        or (args.case_kind == "attack" and case[2] is not None)
    ]
    _write_json(
        run_root / "protocol_manifest.json",
        {
            "status": "running",
            "mode": args.mode,
            "conditions": list(conditions),
            "cases": selected_cases,
            "model": str(MODEL),
            "temperature": 0.0,
            "real_external_side_effects": False,
        },
    )
    server = _start_server(run_root, args.port)
    commands: list[dict[str, Any]] = []
    try:
        for condition in conditions:
            for suite, user_task, injection_task in selected_cases:
                row = _run_case(
                    condition, suite, user_task, injection_task,
                    run_root, args.port, args.case_timeout,
                )
                commands.append(row)
                _write_json(run_root / "command_status.json", commands)
                # Preserve failures and continue. A timeout is itself an
                # overhead/recovery result and must not erase later cases.
    finally:
        if server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
    manifest = json.loads((run_root / "protocol_manifest.json").read_text(encoding="utf-8"))
    manifest["status"] = (
        "passed"
        if all(row.get("returncode") == 0 for row in commands)
        else "completed_with_case_failures"
    )
    _write_json(run_root / "protocol_manifest.json", manifest)
    report = _summarize(run_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
