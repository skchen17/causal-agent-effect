#!/usr/bin/env python3
"""Build a fail-fast, path-relative USENIX artifact readiness manifest."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "usenix27_candidate/artifact"

REQUIRED = {
    "e77_official_agentdojo": ("analysis/results/e77_agentdojo_official_full_run_report.json", {"passed"}, True),
    "e78_protocol_manifest": ("analysis/results/e78_qwen32_protocol_manifest.json", set(), False),
    "e78_common_model_baselines": ("analysis/results/e78_qwen32_strong_baseline_report.json", {"passed"}, True),
    "e79_agentlab_no_guard": ("analysis/results/e79_agentlab_saved_transfer_no_guard_results.json", {"passed"}, True),
    "e79_agentlab_effect_guard": ("analysis/results/e79_agentlab_saved_transfer_e77_results.json", {"passed"}, True),
    "e79_toolsandbox_paired_utility": ("analysis/results/e79_toolsandbox_local_comparison_report.json", {"passed"}, True),
    "e80_finite_model": ("analysis/results/e80_security_model_checks.json", {"passed"}, True),
    "e80_implementation_audit": ("analysis/results/e80_e77_implementation_obligation_audit.json", {"passed_with_conditional_gaps"}, True),
    "e80_compound_contract": ("analysis/results/e80_compound_contract_checks.json", {"passed_with_scope_boundary"}, True),
    "e80_o2_o5_hardening": ("analysis/results/e80_contract_obligation_hardening.json", {"passed"}, True),
    "e80_extended_authority_default_model": ("analysis/results/e80_extended_authority_default_model.json", {"passed"}, True),
    "e80_hardened_runtime_kernel": ("analysis/results/e80_hardened_runtime_kernel_readiness.json", set(), False),
    "e81_ablation_results": ("analysis/results/e81_ablation_report.json", {"passed"}, True),
    "e81_runtime_catalog": ("analysis/results/e81_agentdojo_runtime_catalog_readiness.json", set(), False),
    "e81_a9_raw_registry": ("analysis/results/e81_a9_raw_descriptor_registry_readiness.json", set(), False),
    "e81_compatibility_audit": ("analysis/results/e81_final_protocol_compatibility_audit.json", set(), False),
    "e82_adaptive_protocol": ("evaluation/e82_adaptive_attacks/attack_manifest.json", set(), False),
    "e82_adaptive_case_manifest": ("evaluation/e82_adaptive_attacks/case_manifest_summary.json", set(), False),
    "e82_adaptive_attack_results": ("analysis/results/e82_adaptive_attack_report.json", {"passed"}, True),
    "e83_overhead_results": ("analysis/results/e83_overhead_report.json", {"passed"}, True),
    "e83_runtime_microbenchmark": ("analysis/results/e83_runtime_microbenchmark.json", set(), False),
    "e84_authority_review_packet": ("analysis/results/e84_agentdojo_authority_interface_burden.json", set(), False),
    "e84_authority_review_validation": ("evaluation/e84_authority_manifests/validation_report.json", {"passed"}, True),
    "e85_causal_mediation_finite_model": ("analysis/results/e85_causal_mediation_report.json", {"passed_bounded_finite_model"}, True),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_json(relative: str, accepted_statuses: set[str], final_gate: bool) -> dict[str, Any]:
    path = ROOT / relative
    if not path.exists():
        return {"path": relative, "present": False, "status": "missing", "sha256": None, "final_gate": final_gate, "accepted_statuses": sorted(accepted_statuses), "gate_passed": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"path": relative, "present": True, "status": "malformed_json", "sha256": sha256(path), "final_gate": final_gate, "accepted_statuses": sorted(accepted_statuses), "gate_passed": False}
    status = payload.get("status", "unrecorded")
    return {
        "path": relative,
        "present": True,
        "status": status,
        "sha256": sha256(path),
        "final_gate": final_gate,
        "accepted_statuses": sorted(accepted_statuses),
        "gate_passed": (not final_gate) or status in accepted_statuses,
    }


def build() -> dict[str, Any]:
    entries = {
        name: inspect_json(path, accepted_statuses, final_gate)
        for name, (path, accepted_statuses, final_gate) in REQUIRED.items()
    }
    missing = sorted(name for name, row in entries.items() if not row["present"])
    malformed = sorted(name for name, row in entries.items() if row["status"] == "malformed_json")
    failed_status_gates = sorted(
        name for name, row in entries.items() if row["final_gate"] and row["present"] and not row["gate_passed"]
    )
    final_ready = not missing and not malformed and not failed_status_gates
    return {
        "artifact": "anonymous_usenix27_effect_contract_candidate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready" if final_ready else "incomplete",
        "required_evidence": entries,
        "missing_required_evidence": missing,
        "malformed_required_evidence": malformed,
        "failed_status_gates": failed_status_gates,
        "final_release_gates": {
            "all_required_results_present": not missing,
            "all_required_json_well_formed": not malformed,
            "all_result_statuses_accepted": not failed_status_gates,
            "anonymous_stable_url_inserted": False,
            "credential_and_absolute_path_scan_passed": False,
            "clean_environment_table_reproduction_passed": False,
        },
        "claim_boundary": (
            "An incomplete manifest is a readiness ledger, not a released artifact or evidence that pending experiments ran."
        ),
    }


def main() -> int:
    manifest = build()
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    (ARTIFACT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksums = [
        f"{row['sha256']}  ../../{row['path']}"
        for row in manifest["required_evidence"].values() if row["sha256"]
    ]
    (ARTIFACT / "checksums.sha256").write_text("\n".join(sorted(checksums)) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
