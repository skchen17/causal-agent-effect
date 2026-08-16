#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any


PAPER_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = PAPER_ROOT.parent
OUT_DIR = PAPER_ROOT / "reproduction"


def load_json(*relative_candidates: str) -> tuple[str, dict[str, Any]]:
    for relative in relative_candidates:
        path = PACKAGE_ROOT / relative
        if path.exists():
            return relative, json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("missing required artifact: " + " or ".join(relative_candidates))


def require(obj: Any, key_path: str) -> Any:
    cur = obj
    for part in key_path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(f"missing key path: {key_path}")
    return cur


def metric(source: str, key_path: str, obj: dict[str, Any], *, label: str, paper: str) -> dict[str, Any]:
    value = require(obj, key_path)
    if isinstance(value, dict) and "rate" in value:
        successes = value.get("successes")
        if successes is None:
            successes = value.get("agree")
        if successes is None:
            successes = value.get("count")
        return {
            "label": label,
            "value": value["rate"],
            "successes": successes,
            "total": value.get("total"),
            "source": source,
            "key_path": key_path,
            "paper_location": paper,
        }
    return {
        "label": label,
        "value": value,
        "successes": None,
        "total": None,
        "source": source,
        "key_path": key_path,
        "paper_location": paper,
    }


def rate_text(row: dict[str, Any]) -> str:
    value = row["value"]
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def count_text(row: dict[str, Any]) -> str:
    if row["successes"] is None or row["total"] is None:
        return ""
    return f"{row['successes']}/{row['total']}"


def build_rows() -> list[dict[str, Any]]:
    e48_src, e48 = load_json("results/analysis/results/e48_tuple_guard_results.json")
    e50_src, e50 = load_json("results/analysis/results/e50_hard_guard_robustness_results.json")
    e55_src, e55 = load_json(
        "audit/analysis/results/e55_v2_precommit_authz_results_strict.json",
        "results/analysis/results/e55_v2_precommit_authz_results_strict.json",
    )
    e57_src, e57 = load_json(
        "audit/analysis/results/e57_v2_validity_checks_report.json",
        "results/analysis/results/e57_v2_validity_checks_report.json",
    )
    e56_src, e56 = load_json(
        "audit/analysis/results/e56_final_report.json",
        "results/analysis/results/e56_final_report.json",
    )
    decision_path_src, decision_path = load_json(
        "audit/analysis/results/e55_decision_path_audit.json",
        "results/analysis/results/e55_decision_path_audit.json",
    )
    human_src, human = load_json(
        "audit/analysis/results/e57_human_audit_validation.json",
        "results/analysis/results/e57_human_audit_validation.json",
    )

    rows: list[dict[str, Any]] = []
    add = rows.append

    for label, key in (
        ("E48 rows", "manifest.n_rows"),
        ("E48 pairwise relations", "manifest.n_pairs"),
        ("E48 full hard guard coverage", "methods.effect_binding_guard_full.overall.coverage"),
        ("E48 full hard guard UPA", "methods.effect_binding_guard_full.overall.unsafe_pre_allow"),
        ("E48 full hard guard FDeny", "methods.effect_binding_guard_full.overall.safe_false_deny"),
        ("E48 held-out coverage", "methods.effect_binding_guard_full.by_split.test.coverage"),
        ("E48 held-out UPA", "methods.effect_binding_guard_full.by_split.test.unsafe_pre_allow"),
        ("E48 held-out FDeny", "methods.effect_binding_guard_full.by_split.test.safe_false_deny"),
    ):
        add(metric(e48_src, key, e48, label=label, paper="Tables 2; Results"))

    for label, key in (
        ("E50 source-balanced coverage mean", "source_balanced.aggregate_fixed_policy.coverage.mean"),
        ("E50 source-balanced UPA mean", "source_balanced.aggregate_fixed_policy.unsafe_pre_allow.mean"),
        ("E50 source-balanced FDeny mean", "source_balanced.aggregate_fixed_policy.safe_false_deny.mean"),
        ("E50 resource/auth rows", "resource_authorization_stress.n_rows"),
        ("E50 resource/auth coverage", "resource_authorization_stress.methods.effect_binding_guard_full.overall.coverage"),
        ("E50 resource/auth UPA", "resource_authorization_stress.methods.effect_binding_guard_full.overall.unsafe_pre_allow"),
        ("E50 resource/auth FDeny", "resource_authorization_stress.methods.effect_binding_guard_full.overall.safe_false_deny"),
        ("E50 provenance rows", "control_provenance_stress.n_rows"),
        ("E50 provenance coverage", "control_provenance_stress.methods.effect_binding_guard_full.overall.coverage"),
        ("E50 provenance UPA", "control_provenance_stress.methods.effect_binding_guard_full.overall.unsafe_pre_allow"),
        ("E50 provenance FDeny", "control_provenance_stress.methods.effect_binding_guard_full.overall.safe_false_deny"),
    ):
        add(metric(e50_src, key, e50, label=label, paper="Tables 2-3; Results"))

    for label, key in (
        ("E55-v2 strict label-hidden", "strict_label_hidden"),
        ("E55-v2 leakage-free", "leakage_audit.leakage_free"),
        ("E55-v2 leakage violations", "leakage_audit.n_violations"),
        ("E55-v2 rows", "dataset.n_rows"),
        ("E55-v2 existing hard guard coverage", "methods.existing_hard_effect_binding_guard.overall.coverage"),
        ("E55-v2 existing hard guard UPA", "methods.existing_hard_effect_binding_guard.overall.unsafe_pre_allow"),
        ("E55-v2 existing hard guard FDeny", "methods.existing_hard_effect_binding_guard.overall.safe_false_deny"),
        ("E55-v2 existing hard guard abstain", "methods.existing_hard_effect_binding_guard.overall.abstain_rate"),
        ("E55-v2 authz-aware coverage", "methods.authz_aware_effect_binding_guard.overall.coverage"),
        ("E55-v2 authz-aware UPA", "methods.authz_aware_effect_binding_guard.overall.unsafe_pre_allow"),
        ("E55-v2 authz-aware FDeny", "methods.authz_aware_effect_binding_guard.overall.safe_false_deny"),
        ("E55-v2 authz-aware abstain", "methods.authz_aware_effect_binding_guard.overall.abstain_rate"),
        ("E55-v2 no multi-resource UPA", "methods.authz_aware_no_multi_resource_expansion.overall.unsafe_pre_allow"),
        ("E55-v2 no operation-mode UPA", "methods.authz_aware_no_operation_mode.overall.unsafe_pre_allow"),
        ("E55-v2 no provenance UPA", "methods.authz_aware_no_provenance_overlay.overall.unsafe_pre_allow"),
        ("E55-v2 no alias FDeny", "methods.authz_aware_no_alias_resolution.overall.safe_false_deny"),
    ):
        add(metric(e55_src, key, e55, label=label, paper="Tables 4-5; Results"))

    for label, key in (
        ("E55 decision-path audit passed", "passed"),
    ):
        add(metric(decision_path_src, key, decision_path, label=label, paper="Table 6; Audit appendix"))

    for label, key in (
        ("E56 strict replay passed", "strict_mode_passed"),
        ("E56 decision-path audit passed", "decision_path_audit_passed"),
    ):
        add(metric(e56_src, key, e56, label=label, paper="Table 6; Audit appendix"))

    for label, key in (
        ("E57-v2 all validity gates passed", "all_validity_gates_passed"),
        ("E57-v2 perturbation stability passed", "perturbation_stability_passed"),
        ("E57-v2 perturbation UPA delta", "perturbation.authz_aware_upa_delta"),
        ("E57-v2 perturbation coverage delta", "perturbation.authz_aware_coverage_delta"),
        ("E57-v2 changed decisions", "perturbation.changed_decision_count"),
        ("E57-v2 reference agreement passed", "reference_authorizer_agreement_passed"),
        ("E57-v2 reference decision agreement", "reference_authorizer.decision_agreement"),
        ("E57-v2 reference atom-count agreement", "reference_authorizer.atom_count_agreement"),
        ("E57-v2 reference atom-resource agreement", "reference_authorizer.atom_resource_set_agreement"),
        ("E57-v2 spot-audit packet created", "spot_audit_packet_created"),
        ("E57-v2 spot-audit rows", "spot_audit.n_rows"),
    ):
        add(metric(e57_src, key, e57, label=label, paper="Table 6; Audit appendix"))

    for label, key in (
        ("E57 human audit rows", "row_count"),
        ("E57 human decision agreement", "decision_agreement"),
        ("E57 human all-checks-true rate", "all_checks_true"),
        ("E57 human decision corrections", "corrected_label_subset.decision_corrections"),
        ("E57 human atom corrections", "corrected_label_subset.atom_corrections"),
        ("E57 human violation-reason corrections", "corrected_label_subset.violation_reason_corrections"),
    ):
        add(metric(human_src, key, human, label=label, paper="Table 6; Audit appendix"))

    return rows


def main() -> None:
    rows = build_rows()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    error_path = OUT_DIR / "main_numbers_reproduced.ERROR.txt"
    if error_path.exists():
        error_path.unlink()

    json_path = OUT_DIR / "main_numbers_reproduced.json"
    json_path.write_text(json.dumps({"rows": rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    csv_path = OUT_DIR / "main_numbers_reproduced.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["label", "value", "successes", "total", "source", "key_path", "paper_location"],
        )
        writer.writeheader()
        writer.writerows(rows)

    md_lines = [
        "# Main Numbers Reproduced from Result JSONs",
        "",
        "This file is generated by `python reproduce_main_numbers.py`. It validates reported values from fixed result artifacts.",
        "",
        "| Label | Value | Count | Source key |",
        "|---|---:|---:|---|",
    ]
    for row in rows:
        md_lines.append(f"| {row['label']} | {rate_text(row)} | {count_text(row)} | `{row['source']}::{row['key_path']}` |")
    md_lines.append("")
    (OUT_DIR / "main_numbers_reproduced.md").write_text("\n".join(md_lines), encoding="utf-8")

    print(json.dumps({"rows": len(rows), "output_dir": str(OUT_DIR.relative_to(PAPER_ROOT))}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        message = f"reproduction failed: {exc}"
        (OUT_DIR / "main_numbers_reproduced.ERROR.txt").write_text(message + "\n", encoding="utf-8")
        print(message, file=sys.stderr)
        sys.exit(1)
