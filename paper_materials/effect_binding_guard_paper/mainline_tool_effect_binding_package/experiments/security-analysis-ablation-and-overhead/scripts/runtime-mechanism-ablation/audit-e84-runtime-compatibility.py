#!/usr/bin/env python3
"""Execute reviewed E84 read resolvers in clean AgentDojo sandboxes."""

from __future__ import annotations

import collections
import copy
import json
import sys
from pathlib import Path
from typing import Any

from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir()
)
sys.path.insert(0, str(ROOT / "code"))

from src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime import (  # noqa: E402
    build_typed_resolver_ledger_entry,
    compile_trusted_interface,
)


TRUSTED = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/authority-manifest-human-review/trusted_manifests.jsonl"
)
RESULTS = ROOT / "experiments/security-analysis-ablation-and-overhead/results/runtime-mechanism-ablation"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def concrete_query_arguments(spec: Any) -> tuple[dict[str, Any] | None, list[str]]:
    arguments: dict[str, Any] = {}
    errors: list[str] = []
    for field, constraint in spec.query_arguments.items():
        mode = constraint.get("mode")
        if mode == "forbidden":
            continue
        values = constraint.get("values")
        if mode != "exact" or not isinstance(values, list) or len(values) != 1:
            errors.append(f"query_not_singleton_exact:{field}")
            continue
        arguments[field] = values[0]
    return (arguments if not errors else None), errors


def result_shape(value: Any) -> str:
    if isinstance(value, list):
        child_types = sorted({type(item).__name__ for item in value})
        return f"list[{','.join(child_types)}]"
    return type(value).__name__


def result_fields(value: Any) -> list[str]:
    candidates = value if isinstance(value, list) else [value]
    fields: set[str] = set()
    for item in candidates:
        if isinstance(item, dict):
            fields.update(str(key) for key in item)
        elif hasattr(type(item), "model_fields"):
            fields.update(str(key) for key in type(item).model_fields)
        elif hasattr(item, "model_dump"):
            dumped = item.model_dump()
            if isinstance(dumped, dict):
                fields.update(str(key) for key in dumped)
    return sorted(fields)


def main() -> int:
    rows = read_jsonl(TRUSTED)
    resolver_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    suite_cache: dict[str, tuple[Any, FunctionsRuntime]] = {}

    for row in rows:
        suite_name = row["suite"]
        task_id = row["user_task_id"]
        interface = compile_trusted_interface(row)
        if suite_name not in suite_cache:
            suite = get_suite("v1.1.2", suite_name)
            suite_cache[suite_name] = (suite, FunctionsRuntime(suite.tools))
        suite, runtime = suite_cache[suite_name]
        task = suite.user_tasks[task_id]
        base_environment = task.init_environment(suite.load_and_inject_default_environment({}))
        task_resolvers: list[dict[str, Any]] = []

        for resolver_id, spec in interface.resolver_specs.items():
            arguments, query_errors = concrete_query_arguments(spec)
            value: Any = None
            runtime_error: str | None = None
            entry = None
            if arguments is not None:
                environment = copy.deepcopy(base_environment)
                value, runtime_error = runtime.run_function(environment, spec.read_tool, arguments)
                if runtime_error is None:
                    entry = build_typed_resolver_ledger_entry(
                        spec,
                        tool_name=spec.read_tool,
                        arguments=arguments,
                        result=value,
                    )
            item = {
                "suite": suite_name,
                "user_task_id": task_id,
                "resolver_id": resolver_id,
                "read_tool": spec.read_tool,
                "projection_kind": spec.projection_kind,
                "projection_field": spec.projection_field,
                "query_arguments": arguments,
                "query_errors": query_errors,
                "runtime_error": runtime_error,
                "runtime_result_shape": result_shape(value) if arguments is not None and runtime_error is None else None,
                "runtime_result_fields": result_fields(value) if arguments is not None and runtime_error is None else [],
                "typed_projection_succeeded": entry is not None,
                "projected_scalar_count": len(entry["values"]) if entry is not None else 0,
                "real_external_side_effects": False,
            }
            resolver_rows.append(item)
            task_resolvers.append(item)

        transforms = [
            {
                "tool_name": tool_name,
                "field": field_name,
                "canonical_transform": binding.get("canonical_transform"),
            }
            for tool_name, fields in row.get("authority_tools", {}).items()
            for field_name, binding in fields.items()
            if binding.get("canonical_transform")
        ]
        manifest_rows.append(
            {
                "suite": suite_name,
                "user_task_id": task_id,
                "resolver_specs": len(task_resolvers),
                "compatible_resolvers": sum(item["typed_projection_succeeded"] for item in task_resolvers),
                "canonical_transforms": transforms,
                "runtime_ready": (
                    all(item["typed_projection_succeeded"] for item in task_resolvers) and not transforms
                ),
                "runtime_blockers": [
                    *(
                        ["one_or_more_typed_resolvers_failed"]
                        if not all(item["typed_projection_succeeded"] for item in task_resolvers)
                        else []
                    ),
                    *(["canonical_transform_not_compiled"] if transforms else []),
                ],
            }
        )

    projection_successes = sum(row["typed_projection_succeeded"] for row in resolver_rows)
    report = {
        "experiment": "E84-AgentDojo-runtime-compatibility",
        "status": "passed_audit_with_runtime_gaps",
        "agentdojo_version": "v1.1.2",
        "trusted_manifests": len(rows),
        "resolver_specs": len(resolver_rows),
        "resolver_projection_successes": projection_successes,
        "resolver_projection_success_rate": projection_successes / len(resolver_rows) if resolver_rows else 1.0,
        "runtime_ready_manifests": sum(row["runtime_ready"] for row in manifest_rows),
        "manifests_with_resolvers": sum(row["resolver_specs"] > 0 for row in manifest_rows),
        "manifests_with_uncompiled_canonical_transforms": sum(bool(row["canonical_transforms"]) for row in manifest_rows),
        "projection_success_by_read_tool": {
            tool: {
                "successes": sum(row["typed_projection_succeeded"] for row in group),
                "total": len(group),
            }
            for tool, group in sorted(
                (
                    (tool, [row for row in resolver_rows if row["read_tool"] == tool])
                    for tool in {row["read_tool"] for row in resolver_rows}
                )
            )
        },
        "runtime_result_shape_counts": dict(
            collections.Counter(str(row["runtime_result_shape"]) for row in resolver_rows)
        ),
        "resolver_rows": resolver_rows,
        "manifest_rows": manifest_rows,
        "real_external_side_effects": False,
        "claim_boundary": (
            "This audit executes only independently approved read resolvers in clean AgentDojo sandbox states. "
            "It validates query and projection compatibility, not authority correctness, attack robustness, or "
            "end-to-end utility. A reviewed manifest remains unavailable to the runtime when any required typed "
            "projection or canonical transform is not executable."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS / "e84-runtime-compatibility-audit.json"
    md_path = RESULTS / "e84-runtime-compatibility-audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = [
        "# E84 Runtime Compatibility Audit",
        "",
        f"- Trusted manifests: `{len(rows)}`",
        f"- Resolver specs: `{len(resolver_rows)}`",
        f"- Typed projection successes: `{projection_successes}/{len(resolver_rows)}`",
        f"- Runtime-ready manifests: `{report['runtime_ready_manifests']}/{len(rows)}`",
        f"- Manifests with uncompiled canonical transforms: `{report['manifests_with_uncompiled_canonical_transforms']}`",
        "- External side effects: `0`",
        "",
        "## By Read Tool",
        "",
    ]
    lines.extend(
        f"- `{tool}`: `{counts['successes']}/{counts['total']}`"
        for tool, counts in report["projection_success_by_read_tool"].items()
    )
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "resolver_projection_successes": f"{projection_successes}/{len(resolver_rows)}",
                "runtime_ready_manifests": f"{report['runtime_ready_manifests']}/{len(rows)}",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
