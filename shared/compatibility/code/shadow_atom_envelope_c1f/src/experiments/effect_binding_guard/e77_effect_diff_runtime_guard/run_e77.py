"""Compile E77 descriptors from LLM effects and sandbox field differences."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75 import PACKAGE_ROOT
from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.e77_runtime import validate_compiled_row


RESULTS = PACKAGE_ROOT / "analysis/results"
E76_ROWS = RESULTS / "e76_registered_llm_tool_descriptors.jsonl"
E76_TOOL_VIEWS = RESULTS / "e76_agentdojo_tool_onboarding_views.jsonl"
EFFECT_DIFF = RESULTS / "e77_agentdojo_field_effect_diff.json"
REGISTERED = RESULTS / "e77_registered_effect_diff_descriptors.jsonl"
REPORT_JSON = RESULTS / "e77_descriptor_registration_report.json"
REPORT_MD = RESULTS / "e77_descriptor_registration_report.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--effect-diff", type=Path, default=EFFECT_DIFF)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def field_role(field: str) -> str:
    name = field.lower()
    if any(token in name for token in ("recipient", "participant", "user", "channel", "email")):
        return "target_principal"
    if any(token in name for token in ("body", "content", "subject", "attachment")):
        return "data_payload"
    if any(token in name for token in ("amount", "date", "day", "time", "permission", "visibility")):
        return "scope_constraint"
    return "resource_or_operation"


def main() -> None:
    args = parse_args()
    effect_diff = json.loads(args.effect_diff.read_text(encoding="utf-8"))
    e76 = {row["tool_name"]: row for row in read_jsonl(E76_ROWS)}
    views = {row["tool_name"]: row for row in read_jsonl(E76_TOOL_VIEWS)}
    findings: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for finding in effect_diff["findings"]:
        findings[finding["tool_name"]][finding["field"]].append(finding)

    rows = []
    for tool_name, view in sorted(views.items()):
        source = e76[tool_name]
        descriptor = source.get("descriptor") or source.get("best_nonregistered_descriptor") or {}
        effects = descriptor.get("effect_inventory") or []
        effect_kind = effects[0].get("effect") if effects else "tool_effect"
        required = set(view.get("required_fields", []))
        security_fields = []
        non_security_fields = []
        evidence = []
        for field in sorted(view.get("parameters", {})):
            field_findings = findings[tool_name].get(field, [])
            proven_invariant = (
                len(field_findings) >= 1
                and all(item["status"] == "effect_invariant" for item in field_findings)
                and field not in required
            )
            (non_security_fields if proven_invariant else security_fields).append(field)
            evidence.append(
                {
                    "field": field,
                    "role": field_role(field),
                    "statuses": sorted({item["status"] for item in field_findings}) or ["missing_evidence_fail_closed"],
                    "security_relevant": not proven_invariant,
                    "n_sandbox_checks": len(field_findings),
                }
            )
        row = {
            "tool_name": tool_name,
            "effect_kind": effect_kind,
            "tool_fields": sorted(view.get("parameters", {})),
            "required_fields": sorted(required),
            "security_fields": security_fields,
            "non_security_fields": non_security_fields,
            "field_roles": {field: field_role(field) for field in security_fields},
            "field_counterfactual_evidence": evidence,
            "llm_effect_source_candidate": source.get("candidate_id"),
            "registration_policy": "llm_effect_plus_independent_sandbox_state_output_diff_fail_closed",
        }
        valid, failures = validate_compiled_row(row)
        row["registered"] = valid
        row["failure_categories"] = failures
        rows.append(row)

    network_row = {
        "tool_name": "get_webpage",
        "effect_kind": "network_request",
        "tool_fields": ["url"],
        "required_fields": ["url"],
        "security_fields": ["url"],
        "non_security_fields": [],
        "field_roles": {"url": "network_destination"},
        "field_counterfactual_evidence": [
            {
                "field": "url",
                "role": "network_destination",
                "statuses": ["external_request_destination_changes"],
                "security_relevant": True,
                "n_sandbox_checks": 1,
            }
        ],
        "llm_effect_source_candidate": None,
        "registration_policy": "explicit_external_network_effect_rule",
    }
    network_row["registered"], network_row["failure_categories"] = validate_compiled_row(network_row)
    rows.append(network_row)

    REGISTERED.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    status_counts = effect_diff.get("status_counts", {})
    report = {
        "status": "passed" if all(row["registered"] for row in rows) else "failed",
        "n_llm_effect_tools": len(views),
        "n_registered_tools": sum(row["registered"] for row in rows),
        "n_network_effect_tools": 1,
        "n_fields": sum(len(row["tool_fields"]) for row in rows),
        "n_security_fields": sum(len(row["security_fields"]) for row in rows),
        "n_non_security_fields": sum(len(row["non_security_fields"]) for row in rows),
        "sandbox_counterfactual_status_counts": status_counts,
        "registered_descriptor_path": str(REGISTERED),
        "claim_boundary": (
            "E77 reuses local-LLM effect inventories but does not trust the LLM to declare fields non-security. "
            "Each schema field is checked by a one-field sandbox state/output counterfactual when executable; "
            "unresolved fields fail closed into the security atom set. External webpage reads are modeled as "
            "network-request effects. Registration is experimental, not production certification."
        ),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "# E77 Descriptor Registration Report\n\n"
        f"- Status: `{report['status']}`\n"
        f"- Registered tools: `{report['n_registered_tools']}/{len(rows)}`\n"
        f"- Security fields: `{report['n_security_fields']}/{report['n_fields']}`\n"
        f"- Sandbox outcomes: `{json.dumps(status_counts, sort_keys=True)}`\n\n"
        "## Claim Boundary\n\n" + report["claim_boundary"] + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
