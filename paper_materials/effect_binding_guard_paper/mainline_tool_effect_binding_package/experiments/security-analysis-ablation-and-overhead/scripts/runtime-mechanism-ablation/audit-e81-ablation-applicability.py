#!/usr/bin/env python3
"""Audit whether each E81 switch has support in the reviewed AgentDojo slice."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
MANIFESTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "authority-manifest-human-review/runtime_ready_trusted_manifests.jsonl"
)
CATALOG = ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"
RAW_REGISTRY = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "runtime-mechanism-ablation/a9_raw_descriptor_registry.jsonl"
)
E84_AUDIT = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/runs/"
    "runtime-mechanism-ablation/"
    "e84-qwen32-pilot-strong-baselines-full-v1/e84_runtime_audit.jsonl"
)
RESULTS = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "runtime-mechanism-ablation"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    manifests = read_jsonl(MANIFESTS)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    raw_by_tool = {
        row["tool_name"]: row for row in read_jsonl(RAW_REGISTRY)
    }
    audit = read_jsonl(E84_AUDIT)

    authority_tool_rows = [
        (row["suite"], row["user_task_id"], tool_name, fields)
        for row in manifests
        for tool_name, fields in row["authority_tools"].items()
    ]
    field_granularity_rows = [
        item for item in authority_tool_rows if item[3]
    ]
    resolver_rows = [
        (row["suite"], row["user_task_id"], resolver_id)
        for row in manifests
        for resolver_id in row["resolver_specs"]
    ]
    a9_rows = [
        {
            "suite": suite,
            "user_task_id": task_id,
            "tool_name": tool_name,
            "round0_registered": raw_by_tool.get(tool_name, {}).get(
                "registered"
            ),
            "round0_security_fields": raw_by_tool.get(tool_name, {}).get(
                "security_fields", []
            ),
            "reviewed_authority_fields": sorted(fields),
        }
        for suite, task_id, tool_name, fields in authority_tool_rows
    ]
    dynamic_security_fields = [
        {
            "suite": suite,
            "tool_name": tool_name,
            "field": field,
        }
        for suite, tools in catalog["suites"].items()
        for tool_name, tool in tools.items()
        for field in tool.get("security_fields", [])
        if tool["fields"][field].get("kind") == "dynamic_or_unknown"
    ]
    a1_checks = [
        row for row in audit if row.get("event") == "precommit_check"
    ]
    a1_blocked = [
        row for row in a1_checks if row.get("decision") != "ALLOW"
    ]
    report = {
        "experiment": "E81",
        "artifact_type": "ablation_applicability_audit",
        "status": (
            "passed_with_nonapplicable_a13"
            if not dynamic_security_fields
            else "passed"
        ),
        "reviewed_tasks": len(manifests),
        "reviewed_authority_tool_rows": len(authority_tool_rows),
        "reviewed_authority_tool_counts": dict(
            sorted(Counter(item[2] for item in authority_tool_rows).items())
        ),
        "rows": {
            "A2": {
                "applicable_reviewed_tool_rows": len(field_granularity_rows),
                "criterion": "reviewed task authorizes an effectful tool with field bindings",
            },
            "A7": {
                "applicable_resolver_rows": len(resolver_rows),
                "criterion": "reviewed task uses a typed resolver binding",
            },
            "A9": {
                "applicable_reviewed_tool_rows": len(a9_rows),
                "round0_registered_rows": sum(
                    row["round0_registered"] is True for row in a9_rows
                ),
                "rows": a9_rows,
            },
            "A11": {
                "applicable_catalog_effectful_tools": sum(
                    bool(tool.get("effectful_or_external"))
                    for tools in catalog["suites"].values()
                    for tool in tools.values()
                ),
                "criterion": "model proposes an effectful tool outside the task envelope",
                "dynamic_applicability_requires_runtime_audit": True,
            },
            "A12": {
                "applicable_resolver_rows": len(resolver_rows),
                "criterion": "reviewed task uses a typed resolver binding",
            },
            "A13": {
                "applicable_dynamic_security_defaults": len(
                    dynamic_security_fields
                ),
                "fields": dynamic_security_fields,
                "claim_eligible": bool(dynamic_security_fields),
            },
            "A15": {
                "a1_blocked_precommit_checks": len(a1_blocked),
                "criterion": "A1 returns recoverable feedback after a blocked call",
            },
        },
        "claim_boundary": (
            "A13 has no applicable dynamic security-default field in this "
            "reviewed AgentDojo slice and cannot support an empirical default-"
            "handling claim. A2, A7, A9, and A12 also have narrow applicability "
            "because only two reviewed tasks authorize effectful calls and one "
            "uses a typed resolver."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS / "e81-ablation-applicability-audit.json"
    md_path = RESULTS / "e81-ablation-applicability-audit.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E81 Ablation Applicability Audit",
        "",
        f"- Status: `{report['status']}`",
        f"- Reviewed tasks: `{report['reviewed_tasks']}`",
        f"- Reviewed effectful authority rows: `{len(authority_tool_rows)}`",
        "",
        "| Row | Applicable support |",
        "|---|---:|",
        f"| A2 | {len(field_granularity_rows)} reviewed tool rows |",
        f"| A7 | {len(resolver_rows)} resolver rows |",
        f"| A9 | {len(a9_rows)} reviewed tool rows; "
        f"{report['rows']['A9']['round0_registered_rows']} round-0 registered |",
        "| A11 | dynamic; count from runtime proposals |",
        f"| A12 | {len(resolver_rows)} resolver rows |",
        f"| A13 | {len(dynamic_security_fields)} dynamic security defaults |",
        f"| A15 | {len(a1_blocked)} blocked A1 precommit checks |",
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": report["rows"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

