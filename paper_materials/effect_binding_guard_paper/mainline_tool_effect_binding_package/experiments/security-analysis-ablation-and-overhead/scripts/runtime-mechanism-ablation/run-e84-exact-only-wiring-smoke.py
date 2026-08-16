#!/usr/bin/env python3
"""Validate the independently reviewed exact-only AgentDojo runtime subset."""

from __future__ import annotations

import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from agentdojo.task_suite.load_suites import get_suite


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir()
)
sys.path.insert(0, str(ROOT / "code"))

from src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime import (  # noqa: E402
    compile_trusted_interface,
    mediate_reviewed_agentdojo_call,
)


E84 = ROOT / "experiments/human-authority-and-causal-validation/evaluation/authority-manifest-human-review"
RESULTS = ROOT / "experiments/security-analysis-ablation-and-overhead/results/runtime-mechanism-ablation"
CATALOG = ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def changed_value(value: Any) -> Any:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 1.0
    if isinstance(value, list):
        return [*value, "outside-reviewed-authority"]
    return "outside-reviewed-authority"


def main() -> int:
    manifest_path = E84 / "runtime_ready_exact_only_manifests.jsonl"
    manifests = read_jsonl(manifest_path)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for manifest in manifests:
        suite_name = manifest["suite"]
        task_id = manifest["user_task_id"]
        interface = compile_trusted_interface(manifest)
        task = get_suite("v1.1.2", suite_name).user_tasks[task_id]
        observed_hash = hashlib.sha256(task.PROMPT.encode()).hexdigest()
        if observed_hash != interface.original_task_sha256:
            errors.append(f"{suite_name}/{task_id}:task_hash_mismatch")
        if interface.resolver_specs:
            errors.append(f"{suite_name}/{task_id}:unexpected_resolver")
        if any(
            authority.canonical_transform
            for fields in interface.manifest.tools.values()
            for authority in fields.values()
        ):
            errors.append(f"{suite_name}/{task_id}:unexpected_canonical_transform")

        checks = []
        for tool_name, fields in interface.manifest.tools.items():
            exact_arguments = {
                field_name: authority.exact_values[0]
                for field_name, authority in fields.items()
                if authority.mode == "exact" and authority.exact_values
            }
            positive = mediate_reviewed_agentdojo_call(
                original_task=task.PROMPT,
                suite=suite_name,
                tool_name=tool_name,
                arguments=exact_arguments,
                runtime_catalog=catalog,
                interface=interface,
                resolver_ledger=[],
                registry_hash="e84-exact-only-smoke",
            )
            mutable = next((name for name in exact_arguments), None)
            negative = None
            if mutable is not None:
                outside_arguments = dict(exact_arguments)
                outside_arguments[mutable] = changed_value(outside_arguments[mutable])
                negative = mediate_reviewed_agentdojo_call(
                    original_task=task.PROMPT,
                    suite=suite_name,
                    tool_name=tool_name,
                    arguments=outside_arguments,
                    runtime_catalog=catalog,
                    interface=interface,
                    resolver_ledger=[],
                    registry_hash="e84-exact-only-smoke",
                )
            checks.append(
                {
                    "tool_name": tool_name,
                    "exact_call_decision": positive["decision"],
                    "outside_authority_decision": negative["decision"] if negative else None,
                    "argument_values_logged": False,
                    "runtime_called_llm": positive["runtime_called_llm"],
                    "runtime_executed_tool": positive["runtime_executed_tool"],
                }
            )
            if positive["decision"] != "ALLOW":
                errors.append(f"{suite_name}/{task_id}/{tool_name}:exact_call_not_allowed")
            if negative is not None and negative["decision"] != "DENY":
                errors.append(f"{suite_name}/{task_id}/{tool_name}:outside_call_not_denied")
        rows.append(
            {
                "suite": suite_name,
                "user_task_id": task_id,
                "task_hash_matches": observed_hash == interface.original_task_sha256,
                "authority_tool_count": len(interface.manifest.tools),
                "effectful_checks": checks,
            }
        )

    effectful_manifests = [row for row in rows if row["authority_tool_count"]]
    report = {
        "experiment": "E84-exact-only-AgentDojo-wiring-smoke",
        "status": "passed" if not errors else "failed",
        "agentdojo_version": "v1.1.2",
        "manifest_count": len(rows),
        "suite_counts": dict(collections.Counter(row["suite"] for row in rows)),
        "read_only_task_manifests": sum(row["authority_tool_count"] == 0 for row in rows),
        "effectful_task_manifests": len(effectful_manifests),
        "effectful_tool_checks": sum(len(row["effectful_checks"]) for row in rows),
        "exact_allow_checks": sum(
            check["exact_call_decision"] == "ALLOW" for row in rows for check in row["effectful_checks"]
        ),
        "outside_authority_deny_checks": sum(
            check["outside_authority_decision"] == "DENY"
            for row in rows
            for check in row["effectful_checks"]
        ),
        "errors": errors,
        "rows": rows,
        "runtime_values_logged": False,
        "real_external_side_effects": False,
        "claim_boundary": (
            "This smoke validates task-hash selection and deterministic exact-authority mediation against the "
            "reviewed AgentDojo manifests and frozen runtime catalog. Twenty-four manifests are read-only and only "
            "one contains an effectful authority tool, so this artifact is wiring evidence, not an end-to-end "
            "security or utility result. Resolver-dependent tasks remain blocked by independent human review."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS / "e84-exact-only-wiring-smoke.json"
    md_path = RESULTS / "e84-exact-only-wiring-smoke.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# E84 Exact-Only AgentDojo Wiring Smoke",
                "",
                f"- Status: `{report['status']}`",
                f"- Reviewed manifests: `{report['manifest_count']}`",
                f"- Read-only task manifests: `{report['read_only_task_manifests']}`",
                f"- Effectful task manifests: `{report['effectful_task_manifests']}`",
                f"- Exact-authority ALLOW checks: `{report['exact_allow_checks']}`",
                f"- Outside-authority DENY checks: `{report['outside_authority_deny_checks']}`",
                "- External side effects: `0`",
                "",
                "## Claim Boundary",
                "",
                report["claim_boundary"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({key: report[key] for key in (
        "status", "manifest_count", "read_only_task_manifests", "effectful_task_manifests",
        "exact_allow_checks", "outside_authority_deny_checks"
    )}, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
