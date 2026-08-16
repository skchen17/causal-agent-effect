#!/usr/bin/env python3
"""Check E77 guard registration compatibility with AgentLAB AgentDojo v1.2.1."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agentdojo.task_suite.load_suites import get_suite

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import (
    SIDE_EFFECT_TO_EFFECT,
)
from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.e77_runtime import read_jsonl


ROOT = Path(__file__).resolve().parents[1]
DESCRIPTORS = ROOT / "analysis/results/e77_registered_effect_diff_descriptors.jsonl"
RESULTS = ROOT / "analysis/results"


def main() -> int:
    descriptors = read_jsonl(DESCRIPTORS)
    suites = {}
    missing = []
    extra_schema_fields = []
    for suite_name in ("workspace", "travel", "banking", "slack"):
        suite = get_suite("v1.2.1", suite_name)
        effectful = []
        for tool in suite.tools:
            if tool.name not in SIDE_EFFECT_TO_EFFECT:
                continue
            effectful.append(tool.name)
            row = descriptors.get(tool.name)
            if row is None or not row.get("registered"):
                missing.append({"suite": suite_name, "tool_name": tool.name})
                continue
            schema_fields = set(tool.parameters.model_json_schema().get("properties", {}))
            registered_fields = set(row.get("tool_fields", []))
            if schema_fields != registered_fields:
                extra_schema_fields.append({
                    "suite": suite_name,
                    "tool_name": tool.name,
                    "v121_only": sorted(schema_fields - registered_fields),
                    "descriptor_only": sorted(registered_fields - schema_fields),
                })
        suites[suite_name] = {
            "n_tools": len(suite.tools),
            "effectful_tools": sorted(effectful),
            "n_effectful_tools": len(effectful),
        }
    passed = not missing and not extra_schema_fields
    report = {
        "experiment": "E79",
        "audit_type": "agentlab_v121_e77_guard_schema_compatibility",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "schema_compatible_not_runtime_validated" if passed else "failed",
        "suite_inventory": suites,
        "missing_registered_effectful_tools": missing,
        "schema_field_mismatches": extra_schema_fields,
        "registered_descriptor_source": str(DESCRIPTORS.relative_to(ROOT)),
        "next_gate": (
            "Run one saved-attack victim case for no guard and E77 with exact precommit audit reconciliation, "
            "then execute the frozen 303-pair set under one checkpoint."
        ),
        "claim_boundary": (
            "All AgentLAB AgentDojo v1.2.1 tools classified effectful by the E77 map have registered descriptors "
            "with matching schema fields. This is a schema gate only; the E77 patch has not yet mediated a v1.2.1 victim trajectory."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e79_agentlab_guard_compatibility.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "schema_compatible_not_runtime_validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
