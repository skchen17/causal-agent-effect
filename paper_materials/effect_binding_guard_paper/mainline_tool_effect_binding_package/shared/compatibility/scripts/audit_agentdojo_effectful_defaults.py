#!/usr/bin/env python3
"""Audit default-bearing AgentDojo effectful tools and default equivalence."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
BUILDER = ROOT / "scripts/build_e85_agentdojo_projection_review_packet.py"
OUTPUT = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "conditional-effect-contract-security-model"
)
REPORT_JSON = OUTPUT / "agentdojo-effectful-default-audit.json"
REPORT_MD = OUTPUT / "agentdojo-effectful-default-audit.md"


BASE_ARGUMENTS: dict[tuple[str, str], dict[str, Any]] = {
    ("workspace", "send_email"): {
        "recipients": ["finite.a@example.com"],
        "subject": "Default equivalence",
        "body": "bounded sandbox check",
    },
    ("workspace", "create_calendar_event"): {
        "title": "Default equivalence",
        "start_time": "2024-05-16 10:00",
        "end_time": "2024-05-16 11:00",
    },
    ("workspace", "reschedule_calendar_event"): {
        "event_id": "6",
        "new_start_time": "2024-05-15 10:30",
    },
    ("travel", "create_calendar_event"): {
        "title": "Default equivalence",
        "start_time": "2024-05-16 10:00",
        "end_time": "2024-05-16 11:00",
    },
    ("travel", "send_email"): {
        "recipients": ["finite.a@example.com"],
        "subject": "Default equivalence",
        "body": "bounded sandbox check",
    },
    ("banking", "update_scheduled_transaction"): {"id": 6},
    ("banking", "update_user_info"): {},
}


VOLATILE_KEYS = {"timestamp", "last_modified"}


def stable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return stable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {
            str(key): stable(item)
            for key, item in sorted(value.items())
            if str(key) not in VOLATILE_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [stable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def digest(value: Any) -> str:
    payload = json.dumps(stable(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def is_nonempty_default(value: Any) -> bool:
    return value not in (None, "", False, 0, [], {})


def load_candidate_tool_names() -> set[str]:
    spec = importlib.util.spec_from_file_location("e85_packet_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {BUILDER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.candidate_projections())


def execute(
    suite: Any, runtime: Any, tool_name: str, args: dict[str, Any]
) -> dict[str, Any]:
    environment = suite.load_and_inject_default_environment({})
    before = stable(environment)
    output, error = runtime.run_function(environment, tool_name, copy.deepcopy(args))
    after = stable(environment)
    return {
        "arguments": stable(args),
        "before_digest": digest(before),
        "after_digest": digest(after),
        "effect_digest": digest({"before": before, "after": after}),
        "output_digest": digest(output),
        "error": error,
    }


def run() -> dict[str, Any]:
    from agentdojo.functions_runtime import FunctionsRuntime
    from agentdojo.task_suite.load_suites import get_suite

    candidate_names = load_candidate_tool_names()
    rows: list[dict[str, Any]] = []
    for suite_name in ("workspace", "slack", "travel", "banking"):
        suite = get_suite("v1.1.2", suite_name)
        runtime = FunctionsRuntime(suite.tools)
        for tool in suite.tools:
            if tool.name not in candidate_names:
                continue
            schema = tool.parameters.model_json_schema()
            required = set(schema.get("required", []))
            optional = {
                field: definition.get("default")
                for field, definition in schema.get("properties", {}).items()
                if field not in required and "default" in definition
            }
            if not optional:
                continue
            key = (suite_name, tool.name)
            if key not in BASE_ARGUMENTS:
                raise RuntimeError(f"missing frozen base arguments for {key}")
            omitted_args = copy.deepcopy(BASE_ARGUMENTS[key])
            explicit_args = copy.deepcopy(omitted_args)
            explicit_args.update(optional)
            omitted = execute(suite, runtime, tool.name, omitted_args)
            explicit = execute(suite, runtime, tool.name, explicit_args)
            source_path = Path(inspect.getsourcefile(tool.run) or "")
            source_lines, start_line = inspect.getsourcelines(tool.run)
            rows.append(
                {
                    "tool_instance_key": f"{suite_name}/{tool.name}",
                    "optional_defaults": stable(optional),
                    "n_optional_fields": len(optional),
                    "nonempty_default_fields": sorted(
                        field
                        for field, value in optional.items()
                        if is_nonempty_default(value)
                    ),
                    "dynamic_default_fields": [],
                    "omitted_call": omitted,
                    "explicit_default_call": explicit,
                    "omitted_explicit_effect_equivalent": (
                        omitted["error"] is None
                        and explicit["error"] is None
                        and omitted["effect_digest"] == explicit["effect_digest"]
                    ),
                    "omitted_explicit_output_equivalent": (
                        omitted["error"] is None
                        and explicit["error"] is None
                        and omitted["output_digest"] == explicit["output_digest"]
                    ),
                    "source_evidence": {
                        "relative_module": tool.run.__module__,
                        "function_name": tool.run.__name__,
                        "function_start_line": start_line,
                        "function_source_sha256": hashlib.sha256(
                            "".join(source_lines).encode()
                        ).hexdigest(),
                        "source_file_sha256": hashlib.sha256(
                            source_path.read_bytes()
                        ).hexdigest(),
                    },
                }
            )

    n_optional = sum(row["n_optional_fields"] for row in rows)
    n_nonempty = sum(len(row["nonempty_default_fields"]) for row in rows)
    n_dynamic = sum(len(row["dynamic_default_fields"]) for row in rows)
    n_equivalent = sum(
        row["omitted_explicit_effect_equivalent"]
        and row["omitted_explicit_output_equivalent"]
        for row in rows
    )
    errors = [
        row["tool_instance_key"]
        for row in rows
        if row["omitted_call"]["error"] is not None
        or row["explicit_default_call"]["error"] is not None
    ]
    status = (
        "passed_no_effect_bearing_nonempty_defaults"
        if not errors
        and n_nonempty == 0
        and n_dynamic == 0
        and n_equivalent == len(rows)
        else "failed"
    )
    return {
        "experiment": "agentdojo_effectful_default_applicability_audit",
        "status": status,
        "benchmark": "AgentDojo v1.1.2",
        "n_default_bearing_effectful_tool_instances": len(rows),
        "n_optional_default_fields": n_optional,
        "n_nonempty_static_defaults": n_nonempty,
        "n_dynamic_defaults": n_dynamic,
        "n_omitted_explicit_equivalent_tools": n_equivalent,
        "execution_error_tools": errors,
        "tools": rows,
        "interpretation": (
            "The current AgentDojo effectful tool schemas exercise only empty "
            "or None defaults. They validate omitted/explicit equivalence but "
            "cannot empirically test fail-closed handling of nonempty or dynamic "
            "effect-bearing defaults."
        ),
        "claim_boundary": (
            "This is a source-hash-recorded applicability audit for AgentDojo "
            "v1.1.2. It does not establish default safety for external APIs, "
            "undocumented server defaults, callbacks, or state-dependent defaults."
        ),
    }


def render(report: dict[str, Any]) -> str:
    lines = [
        "# AgentDojo Effectful Default Applicability Audit",
        "",
        f"- Status: `{report['status']}`",
        (
            "- Default-bearing effectful tool instances: "
            f"`{report['n_default_bearing_effectful_tool_instances']}`"
        ),
        f"- Optional fields: `{report['n_optional_default_fields']}`",
        f"- Nonempty static defaults: `{report['n_nonempty_static_defaults']}`",
        f"- Dynamic defaults: `{report['n_dynamic_defaults']}`",
        (
            "- Omitted/explicit default-equivalent tools: "
            f"`{report['n_omitted_explicit_equivalent_tools']}/"
            f"{report['n_default_bearing_effectful_tool_instances']}`"
        ),
        "",
        "## Per-Tool Results",
        "",
        "| Tool | Optional fields | Nonempty | Equivalent |",
        "|---|---:|---:|:---:|",
    ]
    for row in report["tools"]:
        lines.append(
            f"| `{row['tool_instance_key']}` | {row['n_optional_fields']} | "
            f"{len(row['nonempty_default_fields'])} | "
            f"{'yes' if row['omitted_explicit_effect_equivalent'] and row['omitted_explicit_output_equivalent'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            report["interpretation"],
            "",
            "## Claim Boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = run()
    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(render(report), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"].startswith("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
