#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reproduction"

REQUIRED_ARTIFACTS = [
    "evaluation/e60_heldout_contract/e60_artifact_level_review.json",
    "evaluation/e60_heldout_contract/deployable_inputs.jsonl",
    "evaluation/e60_heldout_contract/gold_atoms.jsonl",
    "evaluation/e60_heldout_contract/gold_labels.jsonl",
    "evaluation/e60_heldout_contract/leakage_report.json",
    "evaluation/e60_heldout_contract/results_e60.json",
    "evaluation/e61_realistic_trace_replay/external_trace_subset/raw_manifest.json",
    "evaluation/e61_realistic_trace_replay/external_trace_subset/trace_manifest_external.json",
    "evaluation/e61_realistic_trace_replay/external_trace_subset/leakage_report_external.json",
    "evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json",
    "evaluation/e61_realistic_trace_replay/external_trace_subset/results_combined_external_available.json",
    "baselines/b8_released_guardrail/results_b8_e55.json",
    "baselines/b8_released_guardrail/results_b8_e60.json",
    "baselines/b8_released_guardrail/results_b8_e61_artifact.json",
    "baselines/b8_released_guardrail/results_b8_e61_external.json",
    "evaluation/e65_real_llm_judge/results_e65.json",
    "evaluation/e65_real_llm_judge/results_e55_local_qwen.json",
    "evaluation/e65_real_llm_judge/results_e60_local_qwen.json",
    "evaluation/e65_real_llm_judge/results_e61_artifact_local_qwen.json",
    "evaluation/e65_real_llm_judge/results_e61_external_local_qwen.json",
    "evaluation/e66_real_llm_atom_extractor/results_e66.json",
    "evaluation/e66_real_llm_atom_extractor/results_e60_local_qwen_atoms.json",
    "evaluation/e66_real_llm_atom_extractor/results_e61_artifact_local_qwen_atoms.json",
    "evaluation/e66_real_llm_atom_extractor/results_e61_external_local_qwen_atoms.json",
    "baselines/b8_official_checkpoints/results_b8_official.json",
    "baselines/b8_official_checkpoints/results_ts_guard_e55.json",
    "baselines/b8_official_checkpoints/results_ts_guard_e60.json",
    "baselines/b8_official_checkpoints/results_ts_guard_e61_artifact.json",
    "baselines/b8_official_checkpoints/results_ts_guard_e61_external.json",
    "baselines/b8_official_checkpoints/results_safiron_e55.json",
    "baselines/b8_official_checkpoints/results_safiron_e60.json",
    "baselines/b8_official_checkpoints/results_safiron_e61_artifact.json",
    "baselines/b8_official_checkpoints/results_safiron_e61_external.json",
]


def load_json(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.exists():
        raise FileNotFoundError(f"missing required artifact: {relative}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_required_artifacts() -> list[dict[str, Any]]:
    status = []
    missing = []
    for relative in REQUIRED_ARTIFACTS:
        path = ROOT / relative
        exists = path.exists()
        status.append({"path": relative, "exists": exists})
        if not exists:
            missing.append(relative)
    if missing:
        raise FileNotFoundError("missing required artifacts: " + ", ".join(missing))
    return status


def require(obj: Any, key_path: str) -> Any:
    cur = obj
    for part in key_path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            raise KeyError(f"missing key path: {key_path}")
    return cur


def metric(label: str, source: str, key: str, paper_table: str) -> dict[str, Any]:
    obj = load_json(source)
    value = require(obj, key)
    return metric_from_value(label, value, source, key, paper_table)


def metric_from_value(label: str, value: Any, source: str, key: str, paper_table: str) -> dict[str, Any]:
    successes = None
    total = None
    if isinstance(value, dict) and "rate" in value:
        successes = value.get("successes")
        if successes is None:
            successes = value.get("agree")
        if successes is None:
            successes = value.get("count")
        total = value.get("total")
        value = value["rate"]
    return {
        "label": label,
        "value": value,
        "successes": successes,
        "total": total,
        "source": source,
        "key_path": key,
        "paper_table": paper_table,
    }


def add_table1(rows: list[dict[str, Any]]) -> None:
    source = "results/analysis/results/tool_effect_fragmentation_capability_matrix_phase6.json"
    matrix = load_json(source)
    by_method = {row["method"]: row for row in matrix["main_matrix"]}
    table_methods = {
        "Tool-name proxy": "tool_name_rule_proxy",
        "Static/plan/trajectory text proxy": "static_text_rule_proxy",
        "Local Qwen self-audit": "local_qwen_self_audit",
        "TS-Guard checkpoint": "ts_guard_official_counterfactual_stress",
        "Safiron checkpoint": "safiron_official_counterfactual_stress",
        "Local Qwen effect/resource mapper": "local_qwen_effect_resource_mapper",
        "IPIGuard topology-only": "ipiguard_topology_only",
        "CaMeL structural-policy stress": "camel_structural_policy",
    }
    for display, method in table_methods.items():
        if method not in by_method:
            raise KeyError(f"missing Table 1 method: {method}")
        method_row = by_method[method]
        for key in ("surface_invariance", "effect_sensitivity", "authorization_sensitivity", "resource_awareness", "unsafe_pre_allow"):
            if key in method_row:
                rows.append(metric_from_value(f"Table 1 {display} {key}", method_row[key], source, f"main_matrix[{method}].{key}", "Table 1"))
        if "abstain_rate" in method_row:
            coverage = None if method_row["abstain_rate"] is None else round(1 - float(method_row["abstain_rate"]), 3)
            rows.append(metric_from_value(f"Table 1 {display} coverage", coverage, source, f"main_matrix[{method}].1-abstain_rate", "Table 1"))


def add_existing(rows: list[dict[str, Any]]) -> None:
    e48 = "results/analysis/results/e48_tuple_guard_results.json"
    e50 = "results/analysis/results/e50_hard_guard_robustness_results.json"
    e55 = "audit/analysis/results/e55_v2_precommit_authz_results_strict.json"
    e56 = "audit/analysis/results/e56_final_report.json"
    e57 = "audit/analysis/results/e57_v2_validity_checks_report.json"
    human = "audit/analysis/results/e57_human_audit_validation.json"
    decision = "audit/analysis/results/e55_decision_path_audit.json"
    for label, source, key, table in (
        ("E48 rows", e48, "manifest.n_rows", "Table 2"),
        ("E48 pairwise relations", e48, "manifest.n_pairs", "Table 2"),
        ("E48 full coverage", e48, "methods.effect_binding_guard_full.overall.coverage", "Table 2"),
        ("E48 full UPA", e48, "methods.effect_binding_guard_full.overall.unsafe_pre_allow", "Table 2"),
        ("E48 full FDeny", e48, "methods.effect_binding_guard_full.overall.safe_false_deny", "Table 2"),
        ("E48 held-out coverage", e48, "methods.effect_binding_guard_full.by_split.test.coverage", "Table 2"),
        ("E48 held-out UPA", e48, "methods.effect_binding_guard_full.by_split.test.unsafe_pre_allow", "Table 2"),
        ("E48 held-out FDeny", e48, "methods.effect_binding_guard_full.by_split.test.safe_false_deny", "Table 2"),
        ("E50 source-balanced coverage", e50, "source_balanced.aggregate_fixed_policy.coverage.mean", "Table 2"),
        ("E50 source-balanced UPA", e50, "source_balanced.aggregate_fixed_policy.unsafe_pre_allow.mean", "Table 2"),
        ("E50 source-balanced FDeny", e50, "source_balanced.aggregate_fixed_policy.safe_false_deny.mean", "Table 2"),
        ("E50 resource/auth rows", e50, "resource_authorization_stress.n_rows", "Table 3"),
        ("E50 resource/auth coverage", e50, "resource_authorization_stress.methods.effect_binding_guard_full.overall.coverage", "Table 3"),
        ("E50 resource/auth UPA", e50, "resource_authorization_stress.methods.effect_binding_guard_full.overall.unsafe_pre_allow", "Table 3"),
        ("E50 resource/auth FDeny", e50, "resource_authorization_stress.methods.effect_binding_guard_full.overall.safe_false_deny", "Table 3"),
        ("E50 provenance rows", e50, "control_provenance_stress.n_rows", "Table 3"),
        ("E50 provenance coverage", e50, "control_provenance_stress.methods.effect_binding_guard_full.overall.coverage", "Table 3"),
        ("E50 provenance UPA", e50, "control_provenance_stress.methods.effect_binding_guard_full.overall.unsafe_pre_allow", "Table 3"),
        ("E50 provenance FDeny", e50, "control_provenance_stress.methods.effect_binding_guard_full.overall.safe_false_deny", "Table 3"),
        ("E55-v2 rows", e55, "dataset.n_rows", "Table 4"),
        ("E55-v2 existing coverage", e55, "methods.existing_hard_effect_binding_guard.overall.coverage", "Table 4"),
        ("E55-v2 existing UPA", e55, "methods.existing_hard_effect_binding_guard.overall.unsafe_pre_allow", "Table 4"),
        ("E55-v2 existing FDeny", e55, "methods.existing_hard_effect_binding_guard.overall.safe_false_deny", "Table 4"),
        ("E55-v2 existing abstain", e55, "methods.existing_hard_effect_binding_guard.overall.abstain_rate", "Table 4"),
        ("E55-v2 full coverage", e55, "methods.authz_aware_effect_binding_guard.overall.coverage", "Table 4"),
        ("E55-v2 full UPA", e55, "methods.authz_aware_effect_binding_guard.overall.unsafe_pre_allow", "Table 4"),
        ("E55-v2 full FDeny", e55, "methods.authz_aware_effect_binding_guard.overall.safe_false_deny", "Table 4"),
        ("E55-v2 full abstain", e55, "methods.authz_aware_effect_binding_guard.overall.abstain_rate", "Table 4"),
        ("E55-v2 no multi-resource UPA", e55, "methods.authz_aware_no_multi_resource_expansion.overall.unsafe_pre_allow", "Table 5"),
        ("E55-v2 no operation-mode UPA", e55, "methods.authz_aware_no_operation_mode.overall.unsafe_pre_allow", "Table 5"),
        ("E55-v2 no provenance UPA", e55, "methods.authz_aware_no_provenance_overlay.overall.unsafe_pre_allow", "Table 5"),
        ("E55-v2 no alias FDeny", e55, "methods.authz_aware_no_alias_resolution.overall.safe_false_deny", "Table 5"),
        ("E55 decision-path audit passed", decision, "passed", "Table 6"),
        ("E56 strict replay passed", e56, "strict_mode_passed", "Table 6"),
        ("E56 decision-path audit passed", e56, "decision_path_audit_passed", "Table 6"),
        ("E57-v2 validity gates passed", e57, "all_validity_gates_passed", "Table 6"),
        ("E57-v2 perturbation UPA delta", e57, "perturbation.authz_aware_upa_delta", "Table 6"),
        ("E57-v2 perturbation coverage delta", e57, "perturbation.authz_aware_coverage_delta", "Table 6"),
        ("E57-v2 changed decisions", e57, "perturbation.changed_decision_count", "Table 6"),
        ("E57-v2 reference decision agreement", e57, "reference_authorizer.decision_agreement", "Table 6"),
        ("E57-v2 reference atom-count agreement", e57, "reference_authorizer.atom_count_agreement", "Table 6"),
        ("E57-v2 reference atom-resource agreement", e57, "reference_authorizer.atom_resource_set_agreement", "Table 6"),
        ("E57-v2 spot-audit rows", e57, "spot_audit.n_rows", "Table 6"),
        ("E57 human decision agreement", human, "decision_agreement", "Table 6"),
        ("E57 human all-checks-true", human, "all_checks_true", "Table 6"),
        ("E57 human decision corrections", human, "corrected_label_subset.decision_corrections", "Table 6"),
        ("E57 human atom corrections", human, "corrected_label_subset.atom_corrections", "Table 6"),
        ("E57 human violation-reason corrections", human, "corrected_label_subset.violation_reason_corrections", "Table 6"),
    ):
        rows.append(metric(label, source, key, table))


def add_new(rows: list[dict[str, Any]]) -> None:
    for label, source, key, table in (
        ("E60 artifact review status", "evaluation/e60_heldout_contract/e60_artifact_level_review.json", "artifact_review_status", "E60 claim boundary"),
        ("E60 strict authorship status", "evaluation/e60_heldout_contract/e60_artifact_level_review.json", "strict_authorship_status", "E60 claim boundary"),
        ("E60 safe paper wording", "evaluation/e60_heldout_contract/e60_artifact_level_review.json", "safe_paper_wording", "E60 claim boundary"),
        ("E60 manifest cases", "evaluation/e60_heldout_contract/dataset_manifest.json", "n_cases", "E60 table"),
        ("E60 manifest tool names differ from E55", "evaluation/e60_heldout_contract/dataset_manifest.json", "contract_independence.tool_names_differ_from_e55", "E60 table"),
        ("E60 deployable leakage-free", "evaluation/e60_heldout_contract/leakage_report.json", "leakage_free", "E60 table"),
        ("E60 deployable leakage violations", "evaluation/e60_heldout_contract/leakage_report.json", "n_violations", "E60 table"),
        ("E61 external raw source rows", "evaluation/e61_realistic_trace_replay/external_trace_subset/raw_manifest.json", "source_rows", "E61 external table"),
        ("E61 external raw selected rows", "evaluation/e61_realistic_trace_replay/external_trace_subset/raw_manifest.json", "selected_rows", "E61 external table"),
        ("E61 external raw source hash", "evaluation/e61_realistic_trace_replay/external_trace_subset/raw_manifest.json", "source_hash_sha256", "E61 external table"),
        ("E61 external raw annotation boundary", "evaluation/e61_realistic_trace_replay/external_trace_subset/raw_manifest.json", "annotation_boundary", "E61 external claim boundary"),
        ("E61 manifest traces", "evaluation/e61_realistic_trace_replay/trace_manifest.json", "n_traces", "E61 table"),
        ("E61 no real external side effects", "evaluation/e61_realistic_trace_replay/trace_manifest.json", "no_real_external_side_effects", "E61 table"),
        ("E61 untrusted content rate", "evaluation/e61_realistic_trace_replay/trace_manifest.json", "trace_properties.untrusted_tool_returned_content_rate", "E61 table"),
        ("E61 nested/multi-resource rate", "evaluation/e61_realistic_trace_replay/trace_manifest.json", "trace_properties.multi_resource_or_nested_args_rate", "E61 table"),
        ("E61 incomplete context rate", "evaluation/e61_realistic_trace_replay/trace_manifest.json", "trace_properties.incomplete_or_ambiguous_context_rate", "E61 table"),
        ("E61 operation-mode distinction rate", "evaluation/e61_realistic_trace_replay/trace_manifest.json", "trace_properties.operation_mode_distinction_rate", "E61 table"),
        ("E61 deployable leakage-free", "evaluation/e61_realistic_trace_replay/leakage_report.json", "leakage_free", "E61 table"),
        ("E61 deployable leakage violations", "evaluation/e61_realistic_trace_replay/leakage_report.json", "n_violations", "E61 table"),
    ):
        rows.append(metric(label, source, key, table))

    for label, source, key, table in (
        ("E60 rows", "evaluation/e60_heldout_contract/results_e60.json", "full_atom_mediation.n_rows", "E60 table"),
        ("E60 UPA", "evaluation/e60_heldout_contract/results_e60.json", "full_atom_mediation.unsafe_pre_allow", "E60 table"),
        ("E60 FDeny", "evaluation/e60_heldout_contract/results_e60.json", "full_atom_mediation.safe_false_deny", "E60 table"),
        ("E60 coverage", "evaluation/e60_heldout_contract/results_e60.json", "full_atom_mediation.coverage", "E60 table"),
        ("E60 atom exact", "evaluation/e60_heldout_contract/results_e60.json", "full_atom_mediation.atom_exact_set_match", "E60 table"),
        ("E60 resource canonicalization accuracy", "evaluation/e60_heldout_contract/results_e60.json", "full_atom_mediation.resource_canonicalization_accuracy", "E60 report"),
        ("E60 provenance/control-source accuracy", "evaluation/e60_heldout_contract/results_e60.json", "full_atom_mediation.provenance_control_source_accuracy", "E60 report"),
        ("E60 operation-mode accuracy", "evaluation/e60_heldout_contract/results_e60.json", "full_atom_mediation.operation_mode_accuracy", "E60 report"),
        ("E61 rows", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.n_rows", "E61 table"),
        ("E61 UPA", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.unsafe_pre_allow", "E61 table"),
        ("E61 FDeny", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.safe_false_deny", "E61 table"),
        ("E61 coverage", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.coverage", "E61 table"),
        ("E61 atom exact", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.atom_exact_set_match", "E61 table"),
        ("E61 resource canonicalization accuracy", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.resource_canonicalization_accuracy", "E61 report"),
        ("E61 provenance/control-source accuracy", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.provenance_control_source_accuracy", "E61 report"),
        ("E61 operation-mode accuracy", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.operation_mode_accuracy", "E61 report"),
        ("E61 resource-id F1", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.field_level_prf1.resource_id.f1", "E61 report"),
        ("E61 control-source F1", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.field_level_prf1.control_source.f1", "E61 report"),
        ("E61 commit-mode F1", "evaluation/e61_realistic_trace_replay/results_e61.json", "full_atom_mediation.field_level_prf1.commit_mode.f1", "E61 report"),
    ):
        rows.append(metric(label, source, key, table))

    for source_name in ("A_clean_sandbox", "B_realistic_noisy", "C_adversarial_provenance_shift"):
        for metric_name in ("n_rows", "unsafe_pre_allow", "safe_false_deny", "coverage", "atom_exact_set_match"):
            rows.append(metric(f"E61 {source_name} {metric_name}", "evaluation/e61_realistic_trace_replay/results_e61.json", f"by_trace_source.{source_name}.{metric_name}", "E61 table"))

    for label, source, key, table in (
        ("E61 external manifest traces", "evaluation/e61_realistic_trace_replay/external_trace_subset/trace_manifest_external.json", "n_traces", "E61 external table"),
        ("E61 external no real side effects", "evaluation/e61_realistic_trace_replay/external_trace_subset/trace_manifest_external.json", "no_real_external_side_effects", "E61 external table"),
        ("E61 external untrusted content rate", "evaluation/e61_realistic_trace_replay/external_trace_subset/trace_manifest_external.json", "trace_properties.untrusted_tool_returned_content_rate", "E61 external table"),
        ("E61 external nested/multi-resource rate", "evaluation/e61_realistic_trace_replay/external_trace_subset/trace_manifest_external.json", "trace_properties.multi_resource_or_nested_args_rate", "E61 external table"),
        ("E61 external deployable leakage-free", "evaluation/e61_realistic_trace_replay/external_trace_subset/leakage_report_external.json", "leakage_free", "E61 external table"),
        ("E61 external deployable leakage violations", "evaluation/e61_realistic_trace_replay/external_trace_subset/leakage_report_external.json", "n_violations", "E61 external table"),
        ("E61 external rows", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json", "full_atom_mediation.n_rows", "E61 external table"),
        ("E61 external UPA", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json", "full_atom_mediation.unsafe_pre_allow", "E61 external table"),
        ("E61 external FDeny", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json", "full_atom_mediation.safe_false_deny", "E61 external table"),
        ("E61 external coverage", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json", "full_atom_mediation.coverage", "E61 external table"),
        ("E61 external abstain", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json", "full_atom_mediation.abstain_rate", "E61 external table"),
        ("E61 external atom exact", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json", "full_atom_mediation.atom_exact_set_match", "E61 external table"),
        ("E61 external resource canonicalization accuracy", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json", "full_atom_mediation.resource_canonicalization_accuracy", "E61 external report"),
        ("E61 external provenance/control-source accuracy", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json", "full_atom_mediation.provenance_control_source_accuracy", "E61 external report"),
        ("E61 external operation-mode accuracy", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json", "full_atom_mediation.operation_mode_accuracy", "E61 external report"),
        ("E61 combined available rows", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_combined_external_available.json", "combined_n_rows", "E61 combined table"),
        ("E61 combined artifact rows", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_combined_external_available.json", "artifact_generated.n_rows", "E61 combined table"),
        ("E61 combined external rows", "evaluation/e61_realistic_trace_replay/external_trace_subset/results_combined_external_available.json", "external_subset.n_rows", "E61 combined table"),
    ):
        rows.append(metric(label, source, key, table))

    for dataset, source in (
        ("E55-v2", "evaluation/e62_extraction_decomposition/results_e55.json"),
        ("E60", "evaluation/e62_extraction_decomposition/results_e60.json"),
        ("E61", "evaluation/e62_extraction_decomposition/results_e61.json"),
    ):
        for mode in ("A_gold_atoms_gold_context", "B_extracted_atoms_gold_context", "C_extracted_atoms_noisy_context"):
            for metric_name in ("n_rows", "unsafe_pre_allow", "safe_false_deny", "coverage", "atom_exact_set_match"):
                rows.append(metric(f"E62 {dataset} {mode} {metric_name}", source, f"modes.{mode}.{metric_name}", "E62 table"))
            for field in ("resource_id", "control_source", "commit_mode"):
                rows.append(metric(f"E62 {dataset} {mode} {field} F1", source, f"modes.{mode}.field_level_prf1.{field}.f1", "E62 report"))

    perturbations = load_json("evaluation/e63_interface_burden/context_degradation_results.json")["context_degradation"]
    for perturbation in perturbations:
        for metric_name in ("unsafe_pre_allow", "safe_false_deny", "coverage", "abstain_rate"):
            rows.append(metric(f"E63 {perturbation} {metric_name}", "evaluation/e63_interface_burden/context_degradation_results.json", f"context_degradation.{perturbation}.{metric_name}", "E63 degradation table"))

    burden = load_json("evaluation/e63_interface_burden/burden_manifest.json")["domains"]
    for index, row in enumerate(burden):
        domain = row["domain"]
        for key in ("cases_per_domain", "number_of_tools", "number_of_atom_expansion_rules", "number_of_authorization_fields", "number_of_alias_entries", "estimated_authoring_time_minutes"):
            rows.append(metric(f"E63 burden {domain} {key}", "evaluation/e63_interface_burden/burden_manifest.json", f"domains.{index}.{key}", "E63 burden table"))

    baseline_results = load_json("baselines/baseline_results.json")
    for dataset in ("E55-v2", "E60", "E61"):
        dataset_key = dataset
        for baseline in baseline_results[dataset_key]:
            for metric_name in ("unsafe_pre_allow", "safe_false_deny", "coverage", "abstain_rate"):
                rows.append(metric(f"E64 {dataset} {baseline} {metric_name}", "baselines/baseline_results.json", f"{dataset_key}.{baseline}.{metric_name}", f"E64 {dataset} baseline table"))

    for dataset, source in (
        ("E55-v2", "baselines/b8_released_guardrail/results_b8_e55.json"),
        ("E60", "baselines/b8_released_guardrail/results_b8_e60.json"),
        ("E61 artifact-generated", "baselines/b8_released_guardrail/results_b8_e61_artifact.json"),
        ("E61 external subset", "baselines/b8_released_guardrail/results_b8_e61_external.json"),
    ):
        for metric_name in ("unsafe_pre_allow", "safe_false_deny", "coverage", "abstain_rate", "decision_accuracy"):
            rows.append(metric(f"B8 {dataset} {metric_name}", source, f"overall.{metric_name}", "B8 released adapter table"))
        rows.append(metric(f"B8 {dataset} unsupported cases", source, "overall.unsupported_case_count", "B8 released adapter table"))
        rows.append(metric(f"B8 {dataset} adapter failures", source, "overall.adapter_failure_count", "B8 released adapter table"))

    for dataset_key, dataset_label in (
        ("e55", "E55-v2"),
        ("e60", "E60"),
        ("e61_artifact", "E61 artifact-generated"),
        ("e61_external", "E61 external subset"),
    ):
        for metric_name in ("n_rows", "unsafe_pre_allow", "safe_false_deny", "coverage", "abstain_rate", "decision_accuracy", "parse_valid_rate"):
            rows.append(
                metric(
                    f"E65 real-LLM judge {dataset_label} {metric_name}",
                    "evaluation/e65_real_llm_judge/results_e65.json",
                    f"datasets.{dataset_key}.metrics.{metric_name}",
                    "E65 real-LLM judge table",
                )
            )

    for dataset_key, dataset_label in (
        ("e60", "E60"),
        ("e61_artifact", "E61 artifact-generated"),
        ("e61_external", "E61 external subset"),
    ):
        for metric_name in ("n_rows", "unsafe_pre_allow", "safe_false_deny", "coverage", "abstain_rate", "decision_accuracy", "atom_exact_set_match", "atom_count_match", "parse_valid_rate"):
            rows.append(
                metric(
                    f"E66 real-LLM atoms {dataset_label} {metric_name}",
                    "evaluation/e66_real_llm_atom_extractor/results_e66.json",
                    f"datasets.{dataset_key}.metrics.{metric_name}",
                    "E66 real-LLM atom table",
                )
            )
        for field in ("resource_id", "control_source", "commit_mode"):
            rows.append(
                metric(
                    f"E66 real-LLM atoms {dataset_label} {field} F1",
                    "evaluation/e66_real_llm_atom_extractor/results_e66.json",
                    f"datasets.{dataset_key}.metrics.field_level_prf1.{field}.f1",
                    "E66 real-LLM atom table",
                )
            )

    for model_key, model_label in (("ts_guard", "TS-Guard"), ("safiron", "Safiron")):
        for dataset_key, dataset_label in (
            ("e55", "E55-v2"),
            ("e60", "E60"),
            ("e61_artifact", "E61 artifact-generated"),
            ("e61_external", "E61 external subset"),
        ):
            for metric_name in ("n_rows", "unsafe_pre_allow", "safe_false_deny", "coverage", "abstain_rate", "decision_accuracy", "parse_valid_rate"):
                rows.append(
                    metric(
                        f"B8-official {model_label} {dataset_label} {metric_name}",
                        "baselines/b8_official_checkpoints/results_b8_official.json",
                        f"models.{model_key}.datasets.{dataset_key}.metrics.{metric_name}",
                        "B8-official/E67 checkpoint table",
                    )
                )
            rows.append(
                metric(
                    f"B8-official {model_label} {dataset_label} adapter failures",
                    "baselines/b8_official_checkpoints/results_b8_official.json",
                    f"models.{model_key}.datasets.{dataset_key}.metrics.adapter_failure_count",
                    "B8-official/E67 checkpoint table",
                )
            )


def value_text(row: dict[str, Any]) -> str:
    value = row["value"]
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def count_text(row: dict[str, Any]) -> str:
    if row["successes"] is None or row["total"] is None:
        return ""
    return f"{row['successes']}/{row['total']}"


def claim_boundaries() -> dict[str, Any]:
    e60 = load_json("evaluation/e60_heldout_contract/e60_artifact_level_review.json")
    e61_manifest = load_json("evaluation/e61_realistic_trace_replay/external_trace_subset/raw_manifest.json")
    e61_result = load_json("evaluation/e61_realistic_trace_replay/external_trace_subset/results_external.json")
    b8 = load_json("baselines/b8_released_guardrail/results_b8_e61_external.json")
    e65 = load_json("evaluation/e65_real_llm_judge/results_e65.json")
    e66 = load_json("evaluation/e66_real_llm_atom_extractor/results_e66.json")
    b8_official = load_json("baselines/b8_official_checkpoints/results_b8_official.json")
    return {
        "E60": {
            "strict_authorship_status": e60["strict_authorship_status"],
            "claim_boundary": e60["claim_boundary"],
            "safe_wording": e60["safe_paper_wording"],
        },
        "E61_external": {
            "source_type": e61_manifest["source_type"],
            "annotation_boundary": e61_manifest["annotation_boundary"],
            "result_annotation_boundary": e61_result["annotation_boundary"],
            "safe_wording": "saved external replay subset with metadata-derived labels and rule-derived atom sidecars; not real deployed traces or human-gold annotations",
        },
        "B8": {
            "adapter": b8["adapter"],
            "claim_scope": b8["claim_scope"],
            "safe_wording": "ToolSafe/TS-Guard-style comparable local adapter under label-hidden deployable-input restrictions; not original benchmark reproduction",
        },
        "E65_real_LLM_judge": {
            "model": e65["model"],
            "claim_scope": e65["claim_scope"],
            "safe_wording": "real local LLM judge baseline over label-hidden deployable inputs; no tool execution and no deployed-safety claim",
        },
        "E66_real_LLM_atom_extractor": {
            "model": e66["model"],
            "claim_scope": e66["claim_scope"],
            "safe_wording": "real local LLM atom extraction followed by the reference authorizer; extraction evidence, not a production guarantee",
        },
        "B8_official_E67": {
            "claim_scope": b8_official["claim_scope"],
            "safe_wording": "released checkpoints on this paper's adapted common-input stress view; not original ToolSafe, TS-Guard, or Safiron benchmark reproduction",
        },
    }


def main() -> None:
    required_status = verify_required_artifacts()
    rows: list[dict[str, Any]] = []
    add_table1(rows)
    add_existing(rows)
    add_new(rows)
    for row in rows:
        if not row.get("source") or not row.get("key_path"):
            raise KeyError(f"row lacks source or key path: {row}")
    boundaries = claim_boundaries()
    OUT.mkdir(parents=True, exist_ok=True)
    write_payload = {"rows": rows, "n_rows": len(rows), "claim_boundaries": boundaries, "required_artifacts": required_status}
    (OUT / "all_main_tables.json").write_text(json.dumps(write_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (OUT / "all_main_tables.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["label", "value", "successes", "total", "source", "key_path", "paper_table"])
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# All Main Tables Reproduced from Result Artifacts",
        "",
        "Generated by `python scripts/reproduce_all_main_tables.py`. The script fails fast if any required result artifact or JSON key is absent.",
        "",
        "| Label | Value | Count | Source key | Paper table |",
        "|---|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['label']} | {value_text(row)} | {count_text(row)} | `{row['source']}::{row['key_path']}` | {row['paper_table']} |")
    lines.append("")
    (OUT / "all_main_tables.md").write_text("\n".join(lines), encoding="utf-8")
    claim_rows = [
        {
            "claim_id": f"R{index:03d}",
            "paper_location": row["paper_table"],
            "claim_text": row["label"],
            "result_source": row["source"],
            "result_key": row["key_path"],
            "status": "traceable",
        }
        for index, row in enumerate(rows, start=1)
    ]
    (OUT / "claim_to_source_map.json").write_text(json.dumps({"rows": claim_rows, "n_rows": len(claim_rows)}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    claim_lines = [
        "# Reproduced Claim-to-Source Map",
        "",
        "Generated by `python scripts/reproduce_all_main_tables.py` from result artifacts.",
        "",
        "| ID | Paper location | Claim/value label | Source key | Status |",
        "|---|---|---|---|---|",
    ]
    for row in claim_rows:
        claim_lines.append(f"| {row['claim_id']} | {row['paper_location']} | {row['claim_text']} | `{row['result_source']}::{row['result_key']}` | {row['status']} |")
    claim_lines.append("")
    (OUT / "claim_to_source_map.md").write_text("\n".join(claim_lines), encoding="utf-8")
    status = {
        "status": "passed",
        "n_rows": len(rows),
        "required_artifacts": required_status,
        "claim_boundaries": boundaries,
        "outputs": [
            "reproduction/all_main_tables.json",
            "reproduction/all_main_tables.csv",
            "reproduction/all_main_tables.md",
            "reproduction/claim_to_source_map.json",
            "reproduction/claim_to_source_map.md",
        ],
    }
    (OUT / "reproduction_status.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        status = {"status": "failed", "error": str(exc)}
        (OUT / "reproduction_status.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(status, indent=2), file=sys.stderr)
        sys.exit(1)
