#!/usr/bin/env python3
"""Compile E76 round-0 LLM descriptors for the A9 no-validation ablation."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "analysis/results/e76_llm_descriptor_candidates.jsonl"
VALIDATED = ROOT / "analysis/results/e77_registered_effect_diff_descriptors.jsonl"
CATALOG = ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"
OUTPUT = ROOT / "evaluation/e81_ablation"
RESULTS = ROOT / "analysis/results"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parameter_references(descriptor: dict[str, Any]) -> set[str]:
    references = set()
    bindings = []
    bindings.extend((descriptor.get("field_bindings") or {}).values())
    for template in descriptor.get("atom_templates") or []:
        bindings.extend((template.get("field_bindings") or {}).values())
    for binding in bindings:
        if isinstance(binding, str) and binding.startswith("param:") and binding.count(":") == 1:
            references.add(binding.split(":", 1)[1])
    return references


def build() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = [row for row in read_jsonl(CANDIDATES) if row.get("round_index") == 0]
    if len(candidates) != 24 or len({row["tool_name"] for row in candidates}) != 24:
        raise RuntimeError("A9 requires exactly one round-0 candidate for each of 24 E76 tools")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    schema_by_tool: dict[str, set[str]] = {}
    for tools in catalog["suites"].values():
        for tool_name, tool in tools.items():
            fields = set(tool["fields"])
            previous = schema_by_tool.setdefault(tool_name, fields)
            if previous != fields:
                raise RuntimeError(f"tool schema differs across suites: {tool_name}")
    validated = {row["tool_name"]: set(row["security_fields"]) for row in read_jsonl(VALIDATED)}
    compiled = []
    for row in sorted(candidates, key=lambda item: item["tool_name"]):
        tool_name = row["tool_name"]
        schema = schema_by_tool.get(tool_name)
        descriptor = row.get("descriptor")
        if not row.get("parse_valid") or not isinstance(descriptor, dict) or schema is None:
            compiled.append({
                "tool_name": tool_name,
                "registered": False,
                "failure_categories": sorted(set(row.get("failure_categories", [])) | {"raw_descriptor_unavailable"}),
                "security_fields": [],
                "non_security_fields": sorted(schema or []),
                "unclassified_fields": sorted(schema or []),
                "candidate_id": row.get("candidate_id"),
                "round_index": 0,
            })
            continue
        referenced = parameter_references(descriptor)
        unknown = sorted(referenced - schema)
        security = sorted(referenced & schema)
        declared_nonsecurity = set(descriptor.get("non_security_fields") or []) & schema
        unclassified = sorted(schema - set(security) - declared_nonsecurity)
        compiled.append({
            "tool_name": tool_name,
            "registered": not unknown and bool(security),
            "failure_categories": sorted(set(row.get("failure_categories", [])) | ({"unknown_parameter_reference"} if unknown else set())),
            "security_fields": security,
            "non_security_fields": sorted(schema - set(security)),
            "unclassified_fields": unclassified,
            "unknown_parameter_references": unknown,
            "candidate_id": row.get("candidate_id"),
            "round_index": 0,
            "descriptor_source": "e76_round0_llm_schema_description_only",
            "counterfactual_validation_applied": False,
        })
    differing = [
        row["tool_name"] for row in compiled
        if row["tool_name"] in validated and set(row["security_fields"]) != validated[row["tool_name"]]
    ]
    summary = {
        "experiment": "E81-A9",
        "artifact_type": "raw_llm_descriptor_registry",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "round0_candidates": len(candidates),
        "compiled_rows": len(compiled),
        "registration_counts": dict(sorted(Counter(str(row["registered"]) for row in compiled).items())),
        "tools_differing_from_counterfactually_validated_e77": len(differing),
        "differing_tool_names": sorted(differing),
        "total_unclassified_fields": sum(len(row["unclassified_fields"]) for row in compiled),
        "contains_gold_labels_or_atoms": False,
        "claim_boundary": (
            "A9 freezes raw round-0 LLM schema/description descriptors before counterfactual validation. Omitted fields remain "
            "non-security-relevant for this ablation; parse/compile failures remain unregistered and fail closed."
        ),
    }
    return compiled, summary


def main() -> int:
    rows, summary = build()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "a9_raw_descriptor_registry.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    (RESULTS / "e81_a9_raw_descriptor_registry_readiness.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E81 A9 Raw Descriptor Registry", "", f"Status: `{summary['status']}`.", "",
        f"- Round-0 candidates/compiled rows: `{summary['round0_candidates']}` / `{summary['compiled_rows']}`.",
        f"- Registration counts: `{json.dumps(summary['registration_counts'], sort_keys=True)}`.",
        f"- Tools differing from E77: `{summary['tools_differing_from_counterfactually_validated_e77']}`.",
        f"- Unclassified schema fields: `{summary['total_unclassified_fields']}`.",
        "", "## Claim Boundary", "", summary["claim_boundary"], "",
    ]
    (RESULTS / "e81_a9_raw_descriptor_registry_readiness.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
