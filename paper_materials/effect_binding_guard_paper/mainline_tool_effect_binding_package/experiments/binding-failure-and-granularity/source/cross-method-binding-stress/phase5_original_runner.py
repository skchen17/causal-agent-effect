from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .io_utils import read_jsonl, write_json, write_jsonl
from .phase5_camel import build_camel_structural_counterfactuals, validate_camel_cases
from .phase5_ipiguard import build_ipiguard_counterfactuals, validate_ipiguard_cases
from .phase5_local_server import health, load_state


DEFAULT_OUTPUT = Path("analysis/results/tool_effect_fragmentation_phase5_reproduction.json")
TRACE_OUTPUTS = {
    "ipiguard": Path("data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl"),
    "camel": Path("data/tool_effect_fragmentation/camel_phase5_traces.jsonl"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 5 original pipeline smokes and reproduction audit.")
    parser.add_argument("--system", choices=("ipiguard", "camel", "both"), default="both")
    parser.add_argument("--stage", choices=("audit", "build", "smoke", "all"), default="all")
    parser.add_argument("--suite", default="workspace", help="Suite name, comma-separated names, or all.")
    parser.add_argument("--attack", default="important_instructions")
    parser.add_argument("--max-cases", type=int, default=5)
    parser.add_argument("--base-url", default="http://127.0.0.1:18080/v1")
    parser.add_argument("--model", default="Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf")
    parser.add_argument("--worker-timeout", type=int, default=600)
    parser.add_argument("--case-protocol", choices=("paired", "full_cross_product"), default="paired")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force-rerun", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def reproduction_audit(root: Path, base_url: str) -> dict[str, Any]:
    ipiguard_repo = root / "external/systems/ipiguard"
    camel_repo = root / "external/systems/camel"
    server_state = load_state(root / "runs/tool_effect_fragmentation_phase5/local_server_state.json")
    return {
        "schema_version": "tool_effect_fragmentation_phase5_reproduction_audit_v1",
        "local_server": {
            "state_available": server_state is not None,
            "health": health(base_url),
            "state": server_state,
        },
        "systems": {
            "ipiguard": {
                "repo_exists": ipiguard_repo.exists(),
                "commit": git_commit(ipiguard_repo),
                "original_pipeline_entry": str(ipiguard_repo / "run/eval.py"),
                "base_url_native_support": True,
                "claim_scope_if_run": "original_pipeline_local_model",
                "real_side_effects": False,
            },
            "camel": {
                "repo_exists": camel_repo.exists(),
                "commit": git_commit(camel_repo),
                "original_pipeline_entry": str(camel_repo / "main.py"),
                "base_url_native_support": False,
                "compatibility_adapter": "monkeypatch openai.OpenAI base_url in isolated worker",
                "quarantined_llm_risk": "pydantic_ai provider compatibility must pass smoke",
                "claim_scope_if_run": "original_pipeline_local_model",
                "real_side_effects": False,
            },
        },
    }


def build_counterfactuals(root: Path) -> dict[str, Any]:
    ipiguard = build_ipiguard_counterfactuals(read_jsonl(root / "data/agentdojo_effect_verifier_t122_core.jsonl"))
    camel = build_camel_structural_counterfactuals()
    write_jsonl(root / "data/tool_effect_fragmentation/ipiguard_counterfactual_phase5.jsonl", ipiguard)
    write_jsonl(root / "data/tool_effect_fragmentation/camel_structural_counterfactual_phase5.jsonl", camel)
    return {"ipiguard": validate_ipiguard_cases(ipiguard), "camel": validate_camel_cases(camel)}


def run_smokes(
    root: Path,
    systems: list[str],
    *,
    suites: list[str],
    attack: str,
    max_cases: int,
    base_url: str,
    model: str,
    worker_timeout: int = 600,
    case_protocol: str = "paired",
    resume: bool = False,
    force_rerun: bool = False,
) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for system in systems:
        rows = []
        system_summaries: dict[str, Any] = {}
        modes = (("benign", "none"), ("attack", attack))
        policy_modes = ("none", "normal") if system == "ipiguard" else ("none", "normal", "strict")
        for suite in suites:
            for mode, attack_name in modes:
                for policy_mode in policy_modes:
                    output = root / "runs/tool_effect_fragmentation_phase5" / (
                        f"{system}_{suite}_{mode}_{policy_mode}_{case_protocol}.json"
                    )
                    legacy_output = root / "runs/tool_effect_fragmentation_phase5" / (
                        f"{system}_{suite}_{mode}_{policy_mode}.json"
                    )
                    if resume and not force_rerun and output.exists():
                        payload = json.loads(output.read_text(encoding="utf-8"))
                        if payload.get("run_complete", True):
                            rows.extend(contextualize_cases(payload))
                            system_summaries[f"{suite}:{mode}:{policy_mode}"] = payload
                            continue
                    if resume and not force_rerun and case_protocol == "paired" and legacy_output.exists():
                        payload = json.loads(legacy_output.read_text(encoding="utf-8"))
                        if payload.get("run_complete", True):
                            rows.extend(contextualize_cases(payload))
                            system_summaries[f"{suite}:{mode}:{policy_mode}"] = payload
                            continue
                    worker_python = (
                        root / "external/systems/ipiguard/agentdojo/.venv/bin/python"
                        if system == "ipiguard"
                        else root / "external/systems/camel/.venv/bin/python"
                    )
                    command = [
                        str(worker_python if worker_python.exists() else Path(sys.executable)),
                        "-m",
                        "src.experiments.tool_effect_fragmentation.phase5_pipeline_worker",
                        "--system",
                        system,
                        "--suite",
                        suite,
                        "--mode",
                        mode,
                        "--attack",
                        attack_name,
                        "--model",
                        model,
                        "--base-url",
                        base_url,
                        "--max-cases",
                        str(max_cases),
                        "--case-protocol",
                        case_protocol,
                        "--policy-mode",
                        policy_mode,
                        "--output",
                        str(output),
                    ]
                    if resume:
                        command.append("--resume")
                    env = os.environ.copy()
                    try:
                        completed = subprocess.run(
                            command,
                            cwd=root,
                            env=env,
                            text=True,
                            capture_output=True,
                            timeout=worker_timeout,
                        )
                    except subprocess.TimeoutExpired as error:
                        completed = subprocess.CompletedProcess(
                            command,
                            124,
                            stdout=error.stdout or "",
                            stderr=f"worker_timeout_after_{worker_timeout}s\n{error.stderr or ''}",
                        )
                    if output.exists():
                        payload = json.loads(output.read_text(encoding="utf-8"))
                        rows.extend(contextualize_cases(payload))
                    else:
                        payload = {
                            "system": system,
                            "suite": suite,
                            "mode": mode,
                            "policy_mode": policy_mode,
                            "case_protocol": case_protocol,
                            "claim_scope": "adapter_failed",
                            "n_cases": 0,
                            "n_errors": 1,
                            "worker_failure": {
                                "returncode": completed.returncode,
                                "stdout": completed.stdout[-4000:],
                                "stderr": completed.stderr[-4000:],
                            },
                        }
                    system_summaries[f"{suite}:{mode}:{policy_mode}"] = payload
        write_jsonl(root / TRACE_OUTPUTS[system], rows)
        summaries[system] = system_summaries
    return summaries


def contextualize_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    context = {
        "system": payload.get("system"),
        "component": payload.get("component"),
        "claim_scope": payload.get("claim_scope"),
        "model": payload.get("model"),
        "suite": payload.get("suite"),
        "mode": payload.get("mode"),
        "attack": payload.get("attack"),
        "policy_mode": payload.get("policy_mode"),
        "case_protocol": payload.get("case_protocol", "paired"),
    }
    return [{**row, **context} for row in payload.get("cases", [])]


def git_commit(repo: Path) -> str:
    if not repo.exists():
        return ""
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    systems = ["ipiguard", "camel"] if args.system == "both" else [args.system]
    suites = ["workspace", "slack", "travel", "banking"] if args.suite == "all" else [
        item.strip() for item in args.suite.split(",") if item.strip()
    ]
    payload: dict[str, Any] = {"audit": reproduction_audit(root, args.base_url)}
    if args.stage in {"build", "all"}:
        payload["counterfactual_build"] = build_counterfactuals(root)
    if args.stage in {"smoke", "all"}:
        if not health(args.base_url)["ok"]:
            payload["smoke"] = {"status": "adapter_failed", "reason": "local_server_health_gate_failed"}
        else:
            payload["smoke"] = run_smokes(
                root,
                systems,
                suites=suites,
                attack=args.attack,
                max_cases=args.max_cases,
                base_url=args.base_url,
                model=args.model,
                worker_timeout=args.worker_timeout,
                case_protocol=args.case_protocol,
                resume=args.resume,
                force_rerun=args.force_rerun,
            )
    write_json(root / args.output, payload)


if __name__ == "__main__":
    main()
