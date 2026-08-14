"""Execute field counterfactuals in copied AgentDojo sandbox environments."""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import (
    SIDE_EFFECT_TO_EFFECT,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logdir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="v1.1.2")
    return parser.parse_args()


def jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(child) for child in value]
    return value


def observed_calls(logdir: Path) -> dict[tuple[str, str], list[dict[str, Any]]]:
    calls: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    seen: dict[tuple[str, str], set[str]] = defaultdict(set)
    for path in logdir.rglob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        suite = payload.get("suite_name")
        if not isinstance(suite, str):
            continue
        for message in payload.get("messages", []):
            if message.get("role") != "assistant":
                continue
            for call in message.get("tool_calls") or []:
                tool_name = call.get("function")
                args = call.get("args")
                if tool_name not in SIDE_EFFECT_TO_EFFECT or not isinstance(args, dict):
                    continue
                key = (suite, tool_name)
                signature = json.dumps(args, sort_keys=True, default=str)
                if signature not in seen[key]:
                    seen[key].add(signature)
                    calls[key].append(copy.deepcopy(args))
    return calls


def mutate_value(value: Any, alternatives: list[Any], field: str) -> Any:
    for candidate in alternatives:
        if candidate != value and type(candidate) is type(value):
            return copy.deepcopy(candidate)
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 1.0
    if isinstance(value, list):
        if value:
            changed = copy.deepcopy(value)
            changed[0] = mutate_value(changed[0], [], field)
            return changed
        return ["counterfactual-value"]
    if isinstance(value, dict):
        changed = copy.deepcopy(value)
        changed["counterfactual_marker"] = True
        return changed
    if value is None:
        return "counterfactual-value"
    text = str(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return (datetime.strptime(text, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    if "@" in text:
        return "counterfactual-recipient@example.com"
    if "url" in field.lower() or text.startswith(("http://", "https://", "www.")):
        return "www.counterfactual-destination.example"
    return text + "-counterfactual"


def execute(suite: Any, runtime: FunctionsRuntime, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    env = suite.load_and_inject_default_environment({})
    before = jsonable(env)
    output, error = runtime.run_function(env, tool_name, args)
    return {
        "error": error,
        "before": before,
        "after": jsonable(env),
        "output": jsonable(output),
    }


def main() -> int:
    args = parse_args()
    calls = observed_calls(args.logdir)
    findings = []
    for suite_name in ("workspace", "slack", "travel", "banking"):
        suite = get_suite(args.version, suite_name)
        runtime = FunctionsRuntime(suite.tools)
        for tool in suite.tools:
            if tool.name not in SIDE_EFFECT_TO_EFFECT:
                continue
            schema = tool.parameters.model_json_schema()
            tool_calls = calls.get((suite_name, tool.name), [])
            base_args = copy.deepcopy(tool_calls[0]) if tool_calls else {}
            alternatives_by_field: dict[str, list[Any]] = defaultdict(list)
            for call in tool_calls:
                for field, value in call.items():
                    alternatives_by_field[field].append(value)
            for field in sorted(schema.get("properties", {})):
                field_base = base_args.get(field)
                mutated_args = copy.deepcopy(base_args)
                mutated_args[field] = mutate_value(field_base, alternatives_by_field[field], field)
                base_result = execute(suite, runtime, tool.name, base_args)
                mutated_result = execute(suite, runtime, tool.name, mutated_args)
                if base_result["error"] or mutated_result["error"]:
                    status = "unresolved_fail_closed"
                else:
                    base_effect = {"after": base_result["after"], "output": base_result["output"]}
                    mutated_effect = {"after": mutated_result["after"], "output": mutated_result["output"]}
                    status = "effect_changed" if base_effect != mutated_effect else "effect_invariant"
                findings.append(
                    {
                        "suite": suite_name,
                        "tool_name": tool.name,
                        "field": field,
                        "required": field in set(schema.get("required", [])),
                        "base_args": base_args,
                        "mutated_value": mutated_args[field],
                        "base_error": base_result["error"],
                        "mutated_error": mutated_result["error"],
                        "status": status,
                        "security_relevant": status != "effect_invariant",
                        "evidence": "sandbox_state_and_output_diff",
                    }
                )
    report = {
        "status": "passed",
        "agentdojo_version": args.version,
        "source_logdir": str(args.logdir.resolve()),
        "n_findings": len(findings),
        "status_counts": dict(__import__("collections").Counter(row["status"] for row in findings)),
        "findings": findings,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "n_findings", "status_counts")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
