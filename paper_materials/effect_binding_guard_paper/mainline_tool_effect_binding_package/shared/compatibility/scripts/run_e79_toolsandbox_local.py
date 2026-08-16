#!/usr/bin/env python3
"""Run the frozen 30-scenario ToolSandbox subset on a localhost victim model."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOL_SANDBOX = ROOT / "runs/e79_external_benchmarks/ToolSandbox"
MANIFEST = ROOT / "evaluation/e79_long_horizon/toolsandbox_feasibility_manifest.json"
RUN_ROOT = ROOT / "runs/e79_toolsandbox_local"
RESULTS = ROOT / "analysis/results"


def configure_imports() -> None:
    for path in (str(ROOT), str(ROOT / "code"), str(TOOL_SANDBOX)):
        if path not in sys.path:
            sys.path.insert(0, path)


@contextmanager
def localhost_only() -> Iterator[None]:
    original_connect = socket.socket.connect
    original_create = socket.create_connection

    def allowed_address(address: Any) -> bool:
        return isinstance(address, tuple) and address and address[0] in {"127.0.0.1", "localhost", "::1"}

    def guarded_connect(sock: socket.socket, address: Any) -> Any:
        if not allowed_address(address):
            raise RuntimeError("E79 forbids non-localhost network connections")
        return original_connect(sock, address)

    def guarded_create(address: Any, *args: Any, **kwargs: Any) -> Any:
        if not allowed_address(address):
            raise RuntimeError("E79 forbids non-localhost network connections")
        return original_create(address, *args, **kwargs)

    with patch.object(socket.socket, "connect", guarded_connect), patch.object(socket, "create_connection", guarded_create):
        yield


def server_healthy(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/models", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def frozen_scenarios() -> tuple[dict[str, Any], dict[str, Any]]:
    configure_imports()
    from tool_sandbox.common.execution_context import ToolBackend
    from tool_sandbox.scenarios import named_scenarios

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    all_scenarios = named_scenarios(preferred_tool_backend=ToolBackend.DEFAULT)
    selected = {}
    for row in manifest["scenarios"]:
        name = row["scenario_name"]
        if name not in all_scenarios:
            raise RuntimeError(f"frozen ToolSandbox scenario missing: {name}")
        scenario = all_scenarios[name]
        if sorted(scenario.starting_context.tool_allow_list or []) != sorted(row["allowed_tools"]):
            raise RuntimeError(f"tool allow-list drift: {name}")
        if len(scenario.evaluation.milestone_matcher.milestones) != row["n_milestones"]:
            raise RuntimeError(f"milestone drift: {name}")
        if len(scenario.evaluation.minefield_matcher.milestones) != row["n_minefields"]:
            raise RuntimeError(f"minefield drift: {name}")
        selected[name] = scenario
    if len(selected) != 30:
        raise RuntimeError(f"expected 30 frozen scenarios, found {len(selected)}")
    return manifest, selected


def run_one(name: str, scenario: Any, method: str, output: Path) -> dict[str, Any]:
    from tool_sandbox.common.execution_context import RoleType
    from tool_sandbox.roles.execution_environment import ExecutionEnvironment
    from src.experiments.effect_binding_guard.e79_toolsandbox_local_runner import (
        GuardedExecutionEnvironment,
        LocalOpenAIAgent,
        LocalOpenAIUser,
        ToolSandboxEffectGuard,
    )

    guard = None
    execution_environment: Any = ExecutionEnvironment()
    if method == "effect_guard":
        from scripts.run_e79_toolsandbox_adapter_smoke import build_tool_inventory

        inventory, _ = build_tool_inventory({name: scenario})
        guard = ToolSandboxEffectGuard(
            {row.name: row for row in inventory}, audit_path=output / "guard_audit" / f"{name}.jsonl"
        )
        execution_environment = GuardedExecutionEnvironment(guard)
    roles = {
        RoleType.USER: LocalOpenAIUser(),
        RoleType.EXECUTION_ENVIRONMENT: execution_environment,
        RoleType.AGENT: LocalOpenAIAgent(),
    }
    started = time.perf_counter()
    try:
        result = scenario.play_and_evaluate(roles, output, name)
        evaluation = result.evaluation_result
        return {
            "scenario_name": name,
            "status": "passed",
            "similarity": float(evaluation.similarity),
            "milestone_similarity": float(evaluation.milestone_similarity),
            "minefield_similarity": float(evaluation.minefield_similarity),
            "turn_count": int(evaluation.turn_count),
            "duration_seconds": time.perf_counter() - started,
            "error_type": None,
            "precommit_checks": guard.precommit_count if guard else None,
            "effectful_executions": guard.executed_effect_count if guard else None,
            "all_effectful_executions_precommitted": (
                guard.precommit_count >= guard.executed_effect_count if guard else None
            ),
        }
    except Exception as exc:  # retain failures in denominator
        return {
            "scenario_name": name,
            "status": "error",
            "similarity": 0.0,
            "milestone_similarity": 0.0,
            "minefield_similarity": 0.0,
            "turn_count": scenario.max_messages,
            "duration_seconds": time.perf_counter() - started,
            "error_type": type(exc).__name__,
            "precommit_checks": guard.precommit_count if guard else None,
            "effectful_executions": guard.executed_effect_count if guard else None,
            "all_effectful_executions_precommitted": (
                guard.precommit_count >= guard.executed_effect_count if guard else None
            ),
        }
    finally:
        for role in roles.values():
            role.teardown()


def summarize(method: str, names: list[str], run_dir: Path) -> dict[str, Any]:
    rows = []
    missing = []
    for name in names:
        path = run_dir / "rows" / f"{name}.json"
        if not path.exists():
            missing.append(name)
        else:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
    errors = sum(row["status"] != "passed" for row in rows)
    complete = not missing and len(rows) == 30
    return {
        "experiment": "E79 ToolSandbox local victim",
        "method": method,
        "status": "passed" if complete else "incomplete",
        "n_expected": 30,
        "n_rows": len(rows),
        "missing_scenarios": missing,
        "error_rows": errors,
        "mean_similarity": sum(row["similarity"] for row in rows) / len(rows) if rows else None,
        "mean_milestone_similarity": sum(row["milestone_similarity"] for row in rows) / len(rows) if rows else None,
        "mean_minefield_similarity": sum(row["minefield_similarity"] for row in rows) / len(rows) if rows else None,
        "mean_turn_count": sum(row["turn_count"] for row in rows) / len(rows) if rows else None,
        "precommit_checks": sum(row.get("precommit_checks") or 0 for row in rows) if method == "effect_guard" else None,
        "effectful_executions": sum(row.get("effectful_executions") or 0 for row in rows) if method == "effect_guard" else None,
        "all_effectful_executions_precommitted": (
            all(row.get("all_effectful_executions_precommitted") is True for row in rows)
            if method == "effect_guard" and rows else None
        ),
        "claim_boundary": (
            "This is local ToolSandbox stateful utility with native milestones/minefields. The no-guard row is not an injection-security result, "
            "and the runner permits only localhost model traffic and local sandbox tools."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "smoke", "full", "summarize"), default="dry-run")
    parser.add_argument("--method", choices=("no_guard", "effect_guard"), default="no_guard")
    parser.add_argument("--base-url", default="http://127.0.0.1:18082/v1")
    parser.add_argument("--model", default="qwen3_32b_local")
    parser.add_argument("--max-tokens", type=int, default=4096)
    args = parser.parse_args()
    manifest, scenarios = frozen_scenarios()
    run_dir = RUN_ROOT / args.method
    run_dir.mkdir(parents=True, exist_ok=True)
    protocol = {
        "status": "dry_run_passed" if args.mode == "dry-run" else "running",
        "method": args.method,
        "n_scenarios": len(scenarios),
        "scenario_names": sorted(scenarios),
        "selection_hash": manifest["selection_hash"],
        "base_url_scope": "localhost_only",
        "model": args.model,
        "max_tokens": args.max_tokens,
        "external_tool_side_effects": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / "protocol.json").write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.mode == "dry-run":
        print(json.dumps(protocol, indent=2, sort_keys=True))
        return 0
    if args.mode != "summarize" and not server_healthy(args.base_url):
        raise RuntimeError("configured localhost model server is unavailable")
    os.environ.update({
        "E79_TOOLSANDBOX_BASE_URL": args.base_url,
        "E79_TOOLSANDBOX_MODEL": args.model,
        "E79_TOOLSANDBOX_MAX_TOKENS": str(args.max_tokens),
        "E79_TOOLSANDBOX_USAGE_JSONL": str(run_dir / "usage.jsonl"),
    })
    names = sorted(scenarios)
    if args.mode == "smoke":
        names = names[:1]
    if args.mode in {"smoke", "full"}:
        with localhost_only():
            for name in names:
                path = run_dir / "rows" / f"{name}.json"
                if path.exists():
                    continue
                row = run_one(name, scenarios[name], args.method, run_dir)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = summarize(args.method, sorted(scenarios), run_dir)
    RESULTS.mkdir(parents=True, exist_ok=True)
    target = RESULTS / f"e79_toolsandbox_{args.method}_results.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" or args.mode == "smoke" else 1


if __name__ == "__main__":
    raise SystemExit(main())
