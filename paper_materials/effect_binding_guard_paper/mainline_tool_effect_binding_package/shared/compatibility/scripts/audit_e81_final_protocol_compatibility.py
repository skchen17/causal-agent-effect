#!/usr/bin/env python3
"""Audit whether each E81 kernel row is operationally distinct in the final protocol."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.experiments.effect_binding_guard.e81_runtime_ablation_kernel import ABLATIONS, config_diff


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"
E77 = RESULTS / "e77_registered_effect_diff_descriptors.jsonl"
E76 = RESULTS / "e76_registered_llm_tool_descriptors.jsonl"
E84 = ROOT / "evaluation/e84_authority_manifests/validation_report.json"
E84_TRUSTED = ROOT / "evaluation/e84_authority_manifests/trusted_manifests.jsonl"
E85 = ROOT / "evaluation/e85_security_effect_projections/validation_report.json"
E85_TRUSTED = ROOT / "evaluation/e85_security_effect_projections/trusted_security_effect_projections.jsonl"
E77_V3_PROTOCOL = ROOT / "runs/e77_v3_qwen32_full/protocol_manifest.json"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build() -> dict:
    e77 = read_jsonl(E77)
    e76 = read_jsonl(E76)
    e84 = json.loads(E84.read_text(encoding="utf-8"))
    e84_trusted = read_jsonl(E84_TRUSTED)
    e85 = json.loads(E85.read_text(encoding="utf-8"))
    e85_trusted = read_jsonl(E85_TRUSTED)
    e77_v3 = json.loads(E77_V3_PROTOCOL.read_text(encoding="utf-8")) if E77_V3_PROTOCOL.exists() else {}
    provenance_rows = sum(
        "provenance_source" in row.get("security_fields", []) or "control_source" in row.get("security_fields", [])
        for row in e77
    )
    optional_security_fields = sum(
        len(set(row.get("security_fields", [])) - set(row.get("required_fields", []))) for row in e77
    )
    rows = {
        "A1": {"status": "reviewed_interface_ready_common_runner_pending", "reason": f"totalization and typed-resolver mediation are integrated; {len(e84_trusted)} independently reviewed task manifests are compiled"},
        "A2": {"status": "kernel_ready_common_runner_pending", "reason": "tool-call-level branch is implemented and behaviorally distinct"},
        "A7": {"status": "kernel_ready_common_runner_pending", "reason": "kernel removes typed evidence provenance and admits the parallel untrusted evidence stream"},
        "A9": {"status": "registry_ready_common_runner_pending", "reason": "24 E76 round-0 descriptors are compiled to a frozen raw registry; 13 remain fail-closed and 11 register"},
        "A11": {"status": "kernel_ready_common_runner_pending", "reason": "no-envelope branch is implemented and behaviorally distinct"},
        "A12": {"status": "typed_interface_ready_runner_pending", "reason": "reviewed fixed-query typed projection compiler exists; AgentDojo executor wiring remains"},
        "A13": {"status": "totalization_catalog_ready_runner_pending", "reason": "all AgentDojo v1.1.2 defaults are frozen; common executor wiring remains"},
        "A15": {"status": "kernel_ready_common_runner_pending", "reason": "terminal-deny branch is implemented and behaviorally distinct"},
    }
    expected = {"A1", "A2", "A7", "A9", "A11", "A12", "A13", "A15"}
    errors = []
    if set(ABLATIONS) != expected:
        errors.append(f"kernel rows differ from required main set: {sorted(set(ABLATIONS) ^ expected)}")
    if any(row != "A1" and len(config_diff(row)) != 1 for row in ABLATIONS):
        errors.append("an ablation changes more or less than one configuration component")
    if provenance_rows:
        errors.append("audit assumption changed: E77 now has provenance/control fields")
    if e84.get("status") != "passed_with_rejections" or len(e84_trusted) != 44:
        errors.append("E84 reviewed authority interface is not frozen at 44 accepted tasks")
    if e85.get("status") != "passed_with_rejections" or len(e85_trusted) != 16:
        errors.append("E85 reviewed effect projections are not frozen at 16 accepted tool instances")
    status = "reviewed_inputs_ready_waiting_e77_v3_and_common_runner" if not errors else "failed"
    return {
        "experiment": "E81",
        "audit_type": "final_protocol_ablation_compatibility",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "kernel_rows": sorted(ABLATIONS),
        "e77_registered_descriptors": len(e77),
        "e77_descriptors_with_provenance_or_control_fields": provenance_rows,
        "e77_optional_security_field_occurrences": optional_security_fields,
        "e76_raw_descriptor_rows": len(e76),
        "e76_registration_status_counts": dict(sorted(Counter(str(row.get("registered")) for row in e76).items())),
        "e84_authority_validation_status": e84.get("status"),
        "e84_trusted_manifests": len(e84_trusted),
        "e85_projection_validation_status": e85.get("status"),
        "e85_trusted_effect_projections": len(e85_trusted),
        "e77_v3_full_run_status": e77_v3.get("status", "not_started"),
        "rows": rows,
        "errors": errors,
        "claim_boundary": (
            "Pure counterexamples establish that each configured mechanism can matter. This audit prevents those kernels from being "
            "reported as an AgentDojo ablation until every row changes an operationally instantiated component of one hardened A1 runner."
        ),
    }


def main() -> int:
    report = build()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e81_final_protocol_compatibility_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E81 Final-Protocol Compatibility Audit", "", f"Status: `{report['status']}`.", "",
        "| Row | Status | Reason |", "|---|---|---|",
        *[f"| {row} | `{item['status']}` | {item['reason']} |" for row, item in report["rows"].items()],
        "", "## Claim Boundary", "", report["claim_boundary"], "",
    ]
    (RESULTS / "e81_final_protocol_compatibility_audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "reviewed_inputs_ready_waiting_e77_v3_and_common_runner" else 1


if __name__ == "__main__":
    raise SystemExit(main())
