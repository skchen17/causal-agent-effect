#!/usr/bin/env python3
"""Build the current USENIX paper-evidence and artifact-release ledger."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAPER_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = PAPER_ROOT / "artifact"

REQUIRED = {
    "active_claim_reproduction": (
        "paper/current-usenix/reproduction/reproduction_status.json",
        lambda value: value == "passed",
    ),
    "registration_sufficiency": (
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "registration_sufficiency_audit_v2.json",
        lambda value: value == "passed",
    ),
    "finite_representation_validation": (
        "experiments/human-authority-and-causal-validation/results/"
        "finite-domain-effect-binding-validation/finite-domain-validation-report.json",
        lambda value: value == "passed",
    ),
    "heldout_toolsandbox_validation": (
        "experiments/human-authority-and-causal-validation/results/"
        "heldout-toolsandbox-effect-binding-validation/heldout-validation-report.json",
        lambda value: value == "passed",
    ),
    "authorization_interface_economy": (
        "experiments/human-authority-and-causal-validation/results/"
        "authorization-interface-economy/interface_economy_report.json",
        lambda value: value == "passed",
    ),
    "native_delta_mechanical_validation": (
        "experiments/human-authority-and-causal-validation/results/"
        "native-delta-mechanical-validation/native_delta_validation_report.json",
        lambda value: value == "passed",
    ),
    "frozen_c1f_runtime": (
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "final_guard_repair_report_2026-08-08.json",
        lambda value: value == "passed",
    ),
    "closed_loop_granularity_attribution": (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "representation-closed-loop-attribution/closed-loop-attribution-report.json",
        lambda value: value == "passed",
    ),
    "runtime_policy_view_diagnostic": (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "runtime-policy-view-ablation/runtime-policy-view-report.json",
        lambda value: value == "passed",
    ),
    "deepseek_repeated_benign": (
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "deepseek_benign_interleaved_results.json",
        lambda value: value == "passed",
    ),
    "qwen32_matched_full": (
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "qwen32_matched_results.json",
        lambda value: value == "passed",
    ),
    "deepseek_locked_heldout": (
        "experiments/adaptive-injection-benchmark/results/"
        "usenix-heldout-public-families/results.json",
        lambda value: value == "passed",
    ),
    "agentlab_current_c1f": (
        "analysis/results/e79_agentlab_saved_transfer_current_pair_results.json",
        lambda value: value == "passed",
    ),
    "current_c1f_closed_loop_four_view": (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "c1f-closed-loop-four-view/closed-loop-four-view-report.json",
        lambda value: value == "passed",
    ),
    "current_c1f_bounded_adaptive": (
        "experiments/adaptive-injection-benchmark/results/"
        "bounded-public-family-search-current-c1f/results.json",
        lambda value: value == "passed",
    ),
    "current_c1f_raw_field_attribution": (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "c1f-raw-field-attribution/raw-field-attribution-report.json",
        lambda value: value == "passed",
    ),
    "current_c1f_qwen32_strong_baselines": (
        "experiments/unified-agent-security-baselines/results/"
        "current-c1f-strong-baseline-rerun/results.json",
        lambda value: value == "passed",
    ),
    "final_case_outcomes": (
        "paper/current-usenix/reproduction/final_case_outcomes_summary.json",
        lambda value: value == "passed",
    ),
    "generated_final_validation": (
        "paper/current-usenix/reproduction/generated_final_validation_manifest.json",
        lambda value: value == "passed",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_json(relative: str, status_ok: Any) -> dict[str, Any]:
    path = PACKAGE_ROOT / relative
    if not path.exists():
        return {
            "path": relative,
            "present": False,
            "status": "missing",
            "sha256": None,
            "gate_passed": False,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "path": relative,
            "present": True,
            "status": "malformed_json",
            "sha256": sha256(path),
            "gate_passed": False,
        }
    status = payload.get("status", "unrecorded")
    return {
        "path": relative,
        "present": True,
        "status": status,
        "sha256": sha256(path),
        "gate_passed": bool(status_ok(status)),
    }


def build() -> dict[str, Any]:
    entries = {
        name: inspect_json(path, status_ok)
        for name, (path, status_ok) in REQUIRED.items()
    }
    pdf = PAPER_ROOT / "main.pdf"
    paper_files = {
        "main_pdf": {
            "path": "paper/current-usenix/main.pdf",
            "present": pdf.exists(),
            "sha256": sha256(pdf) if pdf.exists() else None,
        },
        "claim_to_source": {
            "path": "paper/current-usenix/claim_to_source.md",
            "present": (PAPER_ROOT / "claim_to_source.md").exists(),
            "sha256": (
                sha256(PAPER_ROOT / "claim_to_source.md")
                if (PAPER_ROOT / "claim_to_source.md").exists()
                else None
            ),
        },
        "reference_verification": {
            "path": "paper/current-usenix/reference_verification_report.json",
            "present": (PAPER_ROOT / "reference_verification_report.json").exists(),
            "sha256": (
                sha256(PAPER_ROOT / "reference_verification_report.json")
                if (PAPER_ROOT / "reference_verification_report.json").exists()
                else None
            ),
        },
    }
    evidence_ready = (
        all(row["gate_passed"] for row in entries.values())
        and all(row["present"] for row in paper_files.values())
    )
    release_gates = {
        "paper_evidence_gates_passed": evidence_ready,
        "anonymous_stable_url_inserted": False,
        "full_artifact_credential_identity_path_scan_passed": False,
        "clean_environment_reproduction_passed": False,
    }
    return {
        "artifact": "anonymous_usenix27_effect_binding_candidate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": (
            "paper_evidence_ready_artifact_release_pending"
            if evidence_ready
            else "paper_evidence_incomplete"
        ),
        "required_evidence": entries,
        "paper_files": paper_files,
        "release_gates": release_gates,
        "claim_boundary": (
            "Paper-evidence readiness does not certify a released artifact. "
            "Release additionally requires an anonymous stable URL, a complete "
            "scrub, and reproduction in a clean environment."
        ),
    }


def main() -> int:
    manifest = build()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    hashes = []
    for row in [
        *manifest["required_evidence"].values(),
        *manifest["paper_files"].values(),
    ]:
        if row.get("sha256"):
            hashes.append(f"{row['sha256']}  ../../../{row['path']}")
    (OUTPUT / "checksums.sha256").write_text(
        "\n".join(sorted(hashes)) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": manifest["status"], "entries": len(hashes)}))
    return 0 if manifest["release_gates"]["paper_evidence_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
