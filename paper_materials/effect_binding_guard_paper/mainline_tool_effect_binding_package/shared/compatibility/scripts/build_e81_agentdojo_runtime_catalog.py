#!/usr/bin/env python3
"""Freeze AgentDojo field/default semantics for hardened pre-commit mediation."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentdojo.task_suite.load_suites import get_suite


ROOT = Path(__file__).resolve().parents[1]
DESCRIPTORS = ROOT / "analysis/results/e77_registered_effect_diff_descriptors.jsonl"
OUTPUT = ROOT / "evaluation/e81_ablation"
RESULTS = ROOT / "analysis/results"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def static_json_value(value: Any) -> tuple[bool, Any]:
    if value is None or isinstance(value, (str, int, float, bool, list, dict)):
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            return False, None
        return True, value
    return False, None


def build() -> dict[str, Any]:
    descriptors = {row["tool_name"]: row for row in read_jsonl(DESCRIPTORS)}
    suites = {}
    errors = []
    default_counts = Counter()
    security_defaults = Counter()
    effectful_instances = 0
    for suite_name in ("workspace", "slack", "travel", "banking"):
        suite = get_suite("v1.1.2", suite_name)
        tools = {}
        for tool in suite.tools:
            descriptor = descriptors.get(tool.name)
            security_fields = list(descriptor.get("security_fields", [])) if descriptor else []
            if tool.name == "get_webpage":
                security_fields = ["url"]
            effectful = bool(descriptor) or tool.name == "get_webpage"
            effectful_instances += effectful
            schema_fields = set(tool.parameters.model_fields)
            unknown = sorted(set(security_fields) - schema_fields)
            if unknown:
                errors.append(f"{suite_name}/{tool.name}: security fields absent from schema: {unknown}")
            fields = {}
            for field_name, field in sorted(tool.parameters.model_fields.items()):
                if field.is_required():
                    semantics = {"kind": "required"}
                else:
                    supported, value = static_json_value(field.default)
                    semantics = {"kind": "static", "value": value} if supported else {"kind": "dynamic_or_unknown"}
                default_counts[semantics["kind"]] += 1
                if field_name in security_fields:
                    security_defaults[semantics["kind"]] += 1
                fields[field_name] = semantics
            tools[tool.name] = {
                "effectful_or_external": effectful,
                "security_fields": security_fields,
                "inactive_values": {
                    field: [fields[field]["value"]]
                    for field in security_fields
                    if fields.get(field, {}).get("kind") == "static"
                    and fields[field].get("value") in (None, "", [], {})
                },
                "fields": fields,
            }
        suites[suite_name] = tools
    status = "passed" if not errors else "failed"
    return {
        "experiment": "E81",
        "artifact_type": "agentdojo_v1_1_2_runtime_field_semantics_catalog",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "agentdojo_version": "v1.1.2",
        "suites": suites,
        "effectful_tool_instances": effectful_instances,
        "registered_effectful_tool_names": len(descriptors),
        "field_semantics_counts": dict(sorted(default_counts.items())),
        "security_field_semantics_counts": dict(sorted(security_defaults.items())),
        "errors": errors,
        "claim_boundary": (
            "This catalog records local AgentDojo schema defaults and registered E77 security fields. It enables exact call totalization "
            "for this benchmark version only and does not infer hidden defaults of remote services."
        ),
    }


def main() -> int:
    catalog = build()
    if catalog["status"] != "passed":
        raise RuntimeError(json.dumps(catalog["errors"], indent=2))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "agentdojo_runtime_catalog.json").write_text(
        json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {key: catalog[key] for key in (
        "experiment", "artifact_type", "generated_at", "status", "agentdojo_version",
        "effectful_tool_instances", "registered_effectful_tool_names", "field_semantics_counts",
        "security_field_semantics_counts", "errors", "claim_boundary",
    )}
    (RESULTS / "e81_agentdojo_runtime_catalog_readiness.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E81 AgentDojo Runtime Catalog", "", f"Status: `{catalog['status']}`.", "",
        f"- Effectful tool instances: `{catalog['effectful_tool_instances']}`.",
        f"- Field semantics: `{json.dumps(catalog['field_semantics_counts'], sort_keys=True)}`.",
        f"- Security-field semantics: `{json.dumps(catalog['security_field_semantics_counts'], sort_keys=True)}`.",
        "", "## Claim Boundary", "", catalog["claim_boundary"], "",
    ]
    (RESULTS / "e81_agentdojo_runtime_catalog_readiness.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
