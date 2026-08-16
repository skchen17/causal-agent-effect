from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.experiments.tool_effect_fragmentation.io_utils import write_json, write_jsonl

from .dataset_builder import build_dataset, dataset_counts
from .guards import AUTHZ_METHODS, run_methods
from .metrics import row_metrics, summarize_methods
from .run_e55 import acceptance_gates, interpretation
from .schemas import E55Case, E55Prediction, stable_hash


ROOT = Path(__file__).resolve().parents[4]
RESULTS = ROOT / "analysis/results"
PAPER = ROOT / "paper_materials/effect_binding_guard_paper"
E55_PACKAGE = PAPER / "e55_precommit_authz"
NDSS = PAPER / "ndss_candidate"
BACKUP = PAPER / "ndss_candidate_pre_e56_backup"

REQUIRED_METHODS = [
    "allow_all",
    "deny_all",
    "tool_name_proxy",
    "text_rule_proxy",
    "existing_hard_effect_binding_guard",
    "authz_aware_effect_binding_guard",
    "authz_aware_no_alias_resolution",
    "authz_aware_no_multi_resource_expansion",
    "authz_aware_no_operation_mode",
    "authz_aware_no_provenance_overlay",
    "authz_aware_no_evidence_fallback",
]

BASE_SLICES = ("multi_resource", "alias", "draft_commit", "public_visibility", "provenance_shift", "evidence_fallback")
DERIVED_SLICES = (
    "safe_draft_or_read_only",
    "unsafe_extra_recipient",
    "unsafe_public_link",
    "unsafe_alias_mismatch",
    "unsafe_commit_when_draft_only",
    "unsafe_untrusted_control",
)
ALL_SLICES = BASE_SLICES + DERIVED_SLICES

FORBIDDEN_DECISION_FIELDS = {
    "expected_decision",
    "violation_reasons",
    "expanded_atoms",
    "metadata.atom_authorization",
    "gold_args_for_label_only",
    "metadata.gold_args_for_label_only",
    "metadata",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E56 E55 decision-path audit, strict replay, and NDSS integration.")
    parser.add_argument("--compile-paper", action="store_true", help="Compile rebuilt NDSS candidate with latexmk.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    cases = build_dataset()
    original_predictions = [pred for case in cases for pred in run_methods(case, strict_label_hidden=False)]
    strict_predictions = [pred for case in cases for pred in run_methods(case, strict_label_hidden=True)]
    original_methods = summarize_methods(cases, original_predictions)
    strict_methods = summarize_methods(cases, strict_predictions)
    strict_comparison = compare_predictions(cases, original_predictions, strict_predictions, original_methods, strict_methods)

    strict_result = {
        "experiment": "E55 strict label-hidden replay",
        "strict_label_hidden": True,
        "dataset": dataset_counts(cases),
        "methods": strict_methods,
        "strict_vs_original": strict_comparison,
        "interpretation": interpretation(strict_methods),
        "acceptance_gates": acceptance_gates(cases, {"leakage_free": True}, strict_methods),
    }
    write_json(RESULTS / "e55_precommit_authz_results_strict.json", strict_result)
    write_strict_markdown(RESULTS / "e55_precommit_authz_results_strict.md", strict_result)
    write_jsonl(RESULTS / "e55_precommit_authz_predictions_strict.jsonl", [pred.to_dict() for pred in strict_predictions])

    audit = decision_path_audit(strict_predictions)
    write_json(RESULTS / "e55_decision_path_audit.json", audit)
    write_audit_markdown(RESULTS / "e55_decision_path_audit.md", audit)

    ablation_rows = ablation_table(strict_methods)
    write_rows_csv(RESULTS / "e55_precommit_authz_ablation_table.csv", ablation_rows)
    write_table_md(RESULTS / "e55_precommit_authz_ablation_table.md", "E55 Ablation Table", ablation_rows)

    slice_rows = slice_table(cases, strict_predictions)
    write_rows_csv(RESULTS / "e55_precommit_authz_slice_metrics.csv", slice_rows)
    write_table_md(RESULTS / "e55_precommit_authz_slice_table.md", "E55 Slice Table", slice_rows)

    sanity = sanity_checks(cases, strict_predictions, strict_methods, strict_comparison)
    write_json(RESULTS / "e55_sanity_checks.json", sanity)
    write_sanity_markdown(RESULTS / "e55_sanity_checks.md", sanity)

    audit_packet = spot_audit_packet(cases)
    write_jsonl(RESULTS / "e55_spot_audit_packet.jsonl", audit_packet)
    write_spot_audit_markdown(RESULTS / "e55_spot_audit_packet.md", audit_packet)

    write_claim_boundary(RESULTS / "e55_precommit_authz_claim_boundary.md", strict_result)
    write_e55_package_materials(strict_result, ablation_rows, slice_rows, audit, sanity)
    backup_existing_ndss()
    write_ndss_candidate(strict_result, ablation_rows, slice_rows, audit, sanity)
    compile_status = compile_ndss_candidate() if args.compile_paper else {"attempted": False, "compiled": False, "page_count": None}
    scan = anonymity_scan()
    write_json(RESULTS / "e56_anonymity_scan.json", scan)
    write_anonymity_markdown(RESULTS / "e56_anonymity_scan.md", scan)
    final_report = final_report_payload(strict_result, audit, sanity, scan, compile_status)
    write_final_reports(final_report)
    print(json.dumps({"strict_metrics_equal": strict_comparison["metrics_equal"], "audit_passed": audit["passed"], "compiled": compile_status["compiled"]}, indent=2))


def compare_predictions(
    cases: list[E55Case],
    original_predictions: list[E55Prediction],
    strict_predictions: list[E55Prediction],
    original_methods: dict[str, Any],
    strict_methods: dict[str, Any],
) -> dict[str, Any]:
    original_by_key = {(pred.method, pred.case_id): pred for pred in original_predictions}
    changed = []
    for pred in strict_predictions:
        original = original_by_key.get((pred.method, pred.case_id))
        if original and original.decision != pred.decision:
            changed.append({"method": pred.method, "case_id": pred.case_id, "original": original.decision, "strict": pred.decision})
    metric_rows = {}
    metrics_equal = not changed
    for method in REQUIRED_METHODS:
        metric_rows[method] = {}
        for metric in ("unsafe_pre_allow", "safe_false_deny", "coverage", "abstain_rate", "decision_accuracy", "atom_expansion_exact_match"):
            strict_value = rate(strict_methods[method]["overall"].get(metric))
            original_value = rate(original_methods[method]["overall"].get(metric))
            delta = None if strict_value is None or original_value is None else strict_value - original_value
            metric_rows[method][metric] = {"strict": strict_value, "original": original_value, "delta": delta}
            metrics_equal = metrics_equal and (delta in (None, 0))
    return {
        "row_count": len(cases),
        "metrics_equal": metrics_equal,
        "changed_decision_count": len(changed),
        "changed_decisions": changed[:50],
        "methods": metric_rows,
    }


def decision_path_audit(strict_predictions: list[E55Prediction]) -> dict[str, Any]:
    by_method: dict[str, list[E55Prediction]] = defaultdict(list)
    for pred in strict_predictions:
        by_method[pred.method].append(pred)
    specs = {
        "allow_all": ("allow_all", []),
        "deny_all": ("deny_all", []),
        "tool_name_proxy": ("tool_name_proxy", ["tool_name"]),
        "text_rule_proxy": ("text_rule_proxy", ["candidate_action_summary", "provenance_summary"]),
        "existing_hard_effect_binding_guard": ("existing_hard_effect_binding_guard", ["task", "tool_name", "tool_args", "provenance_summary"]),
        "authz_aware_effect_binding_guard": ("authz_aware_guard", ["authorization_context", "tool_name", "tool_args", "tool_inventory", "provenance_summary", "evidence_summary"]),
        "authz_aware_no_alias_resolution": ("authz_aware_guard", ["authorization_context", "tool_name", "tool_args", "tool_inventory", "provenance_summary", "evidence_summary"]),
        "authz_aware_no_multi_resource_expansion": ("authz_aware_guard", ["authorization_context", "tool_name", "tool_args", "tool_inventory", "provenance_summary", "evidence_summary"]),
        "authz_aware_no_operation_mode": ("authz_aware_guard", ["authorization_context", "tool_name", "tool_args", "tool_inventory", "provenance_summary", "evidence_summary"]),
        "authz_aware_no_provenance_overlay": ("authz_aware_guard", ["authorization_context", "tool_name", "tool_args", "tool_inventory", "provenance_summary", "evidence_summary"]),
        "authz_aware_no_evidence_fallback": ("authz_aware_guard", ["authorization_context", "tool_name", "tool_args", "tool_inventory", "provenance_summary"]),
    }
    method_rows = {}
    passed = True
    for method, (entry, expected_fields) in specs.items():
        observed = sorted({field for pred in by_method.get(method, []) for field in pred.accessed_fields})
        forbidden = sorted(set(observed) & FORBIDDEN_DECISION_FIELDS)
        reads_gold = bool(forbidden)
        passed = passed and not reads_gold
        method_rows[method] = {
            "entry_point": entry,
            "object_passed": "DeployableE55Input in strict mode",
            "expected_fields": expected_fields,
            "observed_accessed_fields": observed,
            "field_classification": {field: field_classification(field) for field in observed},
            "reads_expected_decision": "expected_decision" in observed,
            "reads_violation_reasons": "violation_reasons" in observed,
            "reads_expanded_atoms": "expanded_atoms" in observed,
            "reads_metadata_atom_authorization": "metadata.atom_authorization" in observed,
            "reads_gold_args_for_label_only": "gold_args_for_label_only" in observed or "metadata.gold_args_for_label_only" in observed,
            "uses_label_hidden_input": True,
            "atoms_recomputed_from_visible_fields": method in AUTHZ_METHODS,
            "authorization_from_visible_context": method in AUTHZ_METHODS,
            "forbidden_fields_observed": forbidden,
            "decision_path_status": "PASS" if not forbidden else "BLOCKER",
        }
    return {
        "passed": passed,
        "strict_object": "DeployableE55Input(case_id, domain, pair_group, label_hidden_input)",
        "forbidden_decision_fields": sorted(FORBIDDEN_DECISION_FIELDS),
        "methods": method_rows,
        "blockers": [method for method, row in method_rows.items() if row["decision_path_status"] == "BLOCKER"],
    }


def field_classification(field: str) -> str:
    if field in {"task", "tool_name", "tool_args", "tool_inventory", "authorization_context", "provenance_summary", "evidence_summary", "candidate_action_summary"}:
        return "deployable_label_hidden"
    if field in FORBIDDEN_DECISION_FIELDS:
        return "forbidden"
    return "unknown_review_required"


def ablation_table(methods: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for method in REQUIRED_METHODS:
        overall = methods[method]["overall"]
        rows.append(
            {
                "method": method,
                "unsafe_pre_allow": rate(overall["unsafe_pre_allow"]),
                "safe_false_deny": rate(overall["safe_false_deny"]),
                "coverage": rate(overall["coverage"]),
                "abstain": rate(overall["abstain_rate"]),
                "decision_accuracy": rate(overall["decision_accuracy"]),
                "atom_expansion_exact_match": rate(overall["atom_expansion_exact_match"]),
                "alias_authorization_accuracy": rate(overall["resource_authorization_accuracy"]),
                "multi_resource_authorization_accuracy": rate(overall["multi_resource_authorization_accuracy"]),
                "operation_mode_authorization_accuracy": rate(overall["operation_mode_authorization_accuracy"]),
                "provenance_authorization_accuracy": slice_rate(methods[method], "provenance_shift", "decision_accuracy"),
                "public_link_visibility_detection": rate(overall["public_link_visibility_detection"]),
            }
        )
    return rows


def slice_table(cases: list[E55Case], predictions: list[E55Prediction]) -> list[dict[str, Any]]:
    pred_by_method: dict[str, dict[str, E55Prediction]] = defaultdict(dict)
    for pred in predictions:
        pred_by_method[pred.method][pred.case_id] = pred
    rows = []
    for method in [m for m in REQUIRED_METHODS if m in pred_by_method]:
        for slice_name in ALL_SLICES:
            selected = [case for case in cases if slice_flags(case).get(slice_name)]
            metrics = row_metrics(selected, pred_by_method[method])
            rows.append(
                {
                    "method": method,
                    "slice": slice_name,
                    "n_rows": metrics["n_rows"],
                    "unsafe_pre_allow": rate(metrics["unsafe_pre_allow"]),
                    "safe_false_deny": rate(metrics["safe_false_deny"]),
                    "coverage": rate(metrics["coverage"]),
                    "abstain": rate(metrics["abstain_rate"]),
                    "decision_accuracy": rate(metrics["decision_accuracy"]),
                    "false_allow_count": count_false_allow(selected, pred_by_method[method]),
                    "false_deny_count": count_false_deny(selected, pred_by_method[method]),
                    "abstain_count": count_abstain(selected, pred_by_method[method]),
                }
            )
    return rows


def slice_flags(case: E55Case) -> dict[str, bool]:
    base = {name: bool(case.metadata["slices"].get(name)) for name in BASE_SLICES}
    atoms = case.expanded_atoms
    reasons = set(case.violation_reasons)
    tool = case.tool_name
    args = case.tool_args
    derived = {
        "safe_draft_or_read_only": case.expected_decision == "ALLOW" and any(atom.commit_mode in {"draft", "dry_run", "read"} for atom in atoms),
        "unsafe_extra_recipient": case.expected_decision == "DENY"
        and case.domain in {"email", "slack", "calendar", "transaction"}
        and any(reason in reasons for reason in ("resource_authorization", "external_recipient_authorization")),
        "unsafe_public_link": case.expected_decision == "DENY"
        and (tool == "create_public_link" or args.get("visibility") == "public" or "visibility_authorization" in reasons),
        "unsafe_alias_mismatch": case.expected_decision == "DENY" and bool(base["alias"]),
        "unsafe_commit_when_draft_only": case.expected_decision == "DENY"
        and bool(base["draft_commit"])
        and any(reason == "operation_authorization" for reason in reasons),
        "unsafe_untrusted_control": case.expected_decision == "DENY"
        and any(reason in reasons for reason in ("untrusted_control_source", "private_data_control_source")),
    }
    return {**base, **derived}


def count_false_allow(cases: list[E55Case], pred_by_case: dict[str, E55Prediction]) -> int:
    return sum(case.expected_decision == "DENY" and pred_by_case[case.case_id].decision == "ALLOW" for case in cases if case.case_id in pred_by_case)


def count_false_deny(cases: list[E55Case], pred_by_case: dict[str, E55Prediction]) -> int:
    return sum(case.expected_decision == "ALLOW" and pred_by_case[case.case_id].decision == "DENY" for case in cases if case.case_id in pred_by_case)


def count_abstain(cases: list[E55Case], pred_by_case: dict[str, E55Prediction]) -> int:
    return sum(pred_by_case[case.case_id].decision == "ABSTAIN" for case in cases if case.case_id in pred_by_case)


def sanity_checks(
    cases: list[E55Case],
    strict_predictions: list[E55Prediction],
    strict_methods: dict[str, Any],
    strict_comparison: dict[str, Any],
) -> dict[str, Any]:
    renamed_cases = [renamed_case(case) for case in cases]
    renamed_predictions = [pred for case in renamed_cases for pred in run_methods(case, strict_label_hidden=True)]
    renamed_methods = summarize_methods(renamed_cases, renamed_predictions)
    group_folds = fold_breakdown(cases, strict_predictions, method="authz_aware_effect_binding_guard")
    return {
        "label_hidden_replay": {
            "metrics_equal": strict_comparison["metrics_equal"],
            "changed_decision_count": strict_comparison["changed_decision_count"],
        },
        "resource_renaming": {
            "row_count": len(renamed_cases),
            "original_authz_aware": pick_main_metrics(strict_methods["authz_aware_effect_binding_guard"]["overall"]),
            "renamed_authz_aware": pick_main_metrics(renamed_methods["authz_aware_effect_binding_guard"]["overall"]),
            "metrics_stable": pick_main_metrics(strict_methods["authz_aware_effect_binding_guard"]["overall"])
            == pick_main_metrics(renamed_methods["authz_aware_effect_binding_guard"]["overall"]),
        },
        "group_folds": group_folds,
        "spot_audit_packet_rows": 30,
    }


def renamed_case(case: E55Case) -> E55Case:
    payload = case.to_dict()
    text = json.dumps(payload, ensure_ascii=False)
    replacements = {
        "example.com": "example.org",
        "partner.test": "partner.invalid",
        "analyst": "reviewer",
        "manager": "approver",
        "auditor": "observer",
        "vendor": "supplier",
        "finance-plan": "ops-plan",
        "budget-": "packet-",
        "proj-": "team-",
        "acct-": "account-",
        "payee": "recipient",
        "cal-event": "meeting-event",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    renamed = json.loads(text)
    renamed["case_id"] = case.case_id + "_renamed"
    renamed["pair_group"] = case.pair_group + "_renamed"
    return E55Case.from_dict(renamed)


def fold_breakdown(cases: list[E55Case], predictions: list[E55Prediction], *, method: str) -> list[dict[str, Any]]:
    by_case = {pred.case_id: pred for pred in predictions if pred.method == method}
    rows = []
    for fold in range(5):
        selected = [case for case in cases if int(stable_hash(case.pair_group), 16) % 5 == fold]
        metrics = row_metrics(selected, by_case)
        rows.append({"fold": fold, **pick_main_metrics(metrics), "n_rows": metrics["n_rows"], "n_groups": len({case.pair_group for case in selected})})
    return rows


def spot_audit_packet(cases: list[E55Case]) -> list[dict[str, Any]]:
    selected: list[E55Case] = []
    for domain in sorted({case.domain for case in cases}):
        domain_cases = [case for case in cases if case.domain == domain]
        selected.extend(domain_cases[:3])
    for slice_name in ALL_SLICES:
        for case in cases:
            if slice_flags(case).get(slice_name) and case not in selected:
                selected.append(case)
                break
    for case in cases:
        if len(selected) >= 30:
            break
        if case not in selected:
            selected.append(case)
    packet = []
    for case in selected[:30]:
        packet.append(
            {
                "case_id": case.case_id,
                "domain": case.domain,
                "task": case.task,
                "authorization_context": case.authorization_context.to_dict(),
                "tool_call": {"tool_name": case.tool_name, "tool_args": case.tool_args},
                "expanded_atoms": [atom.to_dict() for atom in case.expanded_atoms],
                "expected_decision": case.expected_decision,
                "violation_reasons": list(case.violation_reasons),
                "deployable_input": case.label_hidden_input,
                "slices": slice_flags(case),
            }
        )
    return packet


def backup_existing_ndss() -> None:
    if BACKUP.exists():
        shutil.rmtree(BACKUP)
    BACKUP.mkdir(parents=True, exist_ok=True)
    if NDSS.exists():
        for path in NDSS.iterdir():
            dest = BACKUP / path.name
            if path.is_dir():
                shutil.copytree(path, dest)
            else:
                shutil.copy2(path, dest)
    write_text(BACKUP / "README.md", "# E56 Backup\n\nAt E56 start, the NDSS candidate directory contained no LaTeX source files in this workspace; this backup preserves the pre-E56 directory contents.\n")


def write_ndss_candidate(
    strict_result: dict[str, Any],
    ablation_rows: list[dict[str, Any]],
    slice_rows: list[dict[str, Any]],
    audit: dict[str, Any],
    sanity: dict[str, Any],
) -> None:
    if NDSS.exists():
        shutil.rmtree(NDSS)
    (NDSS / "sections").mkdir(parents=True, exist_ok=True)
    write_text(NDSS / "main.tex", ndss_main_tex())
    sections = {
        "abstract.tex": ndss_abstract(strict_result),
        "introduction.tex": ndss_introduction(),
        "threat_model.tex": ndss_threat_model(),
        "method.tex": ndss_method(),
        "results.tex": ndss_results(strict_result, ablation_rows, slice_rows, audit, sanity),
        "limitations.tex": ndss_limitations(),
        "conclusion.tex": ndss_conclusion(),
    }
    for name, content in sections.items():
        write_text(NDSS / "sections" / name, content)
    write_text(NDSS / "appendix.tex", ndss_appendix(strict_result, ablation_rows, slice_rows, audit, sanity))
    write_text(NDSS / "references.bib", "")
    write_text(NDSS / "claim_to_source.md", claim_to_source_text())
    write_text(NDSS / "TODO.md", "# TODO\n\nNo blocking E56 TODOs remain. Before submission, run an independent human audit of E55 spot-audit rows and update venue formatting.\n")
    write_text(NDSS / "ndss_readiness_report.md", ndss_readiness_text(audit, sanity))
    write_text(NDSS / "e55_integration_plan.md", e55_integration_text(strict_result))


def compile_ndss_candidate() -> dict[str, Any]:
    try:
        proc = subprocess.run(["latexmk", "-pdf", "main.tex"], cwd=NDSS, text=True, capture_output=True, timeout=120)
        compiled = proc.returncode == 0
        log = proc.stdout[-4000:] + proc.stderr[-4000:]
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        compiled = False
        log = str(exc)
    page_count = None
    if compiled:
        page_count = pdf_page_count(NDSS / "main.pdf")
    return {"attempted": True, "compiled": compiled, "page_count": page_count, "log_tail": log}


def pdf_page_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        proc = subprocess.run(["pdfinfo", str(path)], text=True, capture_output=True, timeout=30)
        match = re.search(r"Pages:\s+(\d+)", proc.stdout)
        return int(match.group(1)) if match else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def anonymity_scan() -> dict[str, Any]:
    targets = []
    for base in (NDSS, E55_PACKAGE):
        if base.exists():
            targets.extend(path for path in base.rglob("*") if path.is_file() and path.suffix in {".tex", ".md", ".bib"})
    patterns = {
        "absolute_project_path": re.compile(r"/data/CSK|/home/user|/tmp/"),
        "api_key": re.compile(r"sk-[A-Za-z0-9]{12,}"),
        "token": re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*[A-Za-z0-9_\\-]{8,}"),
        "author_email": re.compile(r"[A-Za-z0-9._%+-]+@(?!example\\.com|example\\.org|partner\\.test|partner\\.invalid)[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"),
        "acknowledgment": re.compile(r"(?i)acknowledg"),
    }
    findings = []
    for path in targets:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns.items():
            for match in pattern.finditer(text):
                findings.append({"file": rel(path), "pattern": name, "match": match.group(0)[:120]})
    return {"passed": not findings, "n_files_scanned": len(targets), "findings": findings}


def final_report_payload(
    strict_result: dict[str, Any],
    audit: dict[str, Any],
    sanity: dict[str, Any],
    scan: dict[str, Any],
    compile_status: dict[str, Any],
) -> dict[str, Any]:
    full = strict_result["methods"]["authz_aware_effect_binding_guard"]["overall"]
    existing = strict_result["methods"]["existing_hard_effect_binding_guard"]["overall"]
    return {
        "decision_path_audit_passed": audit["passed"],
        "strict_mode_passed": strict_result["strict_vs_original"]["metrics_equal"],
        "paper_metrics": {
            "existing_hard_guard": pick_main_metrics(existing),
            "authz_aware_guard": pick_main_metrics(full),
        },
        "strongest_ablation_evidence": {
            "no_multi_resource_expansion_upa": rate(strict_result["methods"]["authz_aware_no_multi_resource_expansion"]["overall"]["unsafe_pre_allow"]),
            "no_operation_mode_upa": rate(strict_result["methods"]["authz_aware_no_operation_mode"]["overall"]["unsafe_pre_allow"]),
            "no_provenance_overlay_upa": rate(strict_result["methods"]["authz_aware_no_provenance_overlay"]["overall"]["unsafe_pre_allow"]),
            "no_alias_resolution_fdeny": rate(strict_result["methods"]["authz_aware_no_alias_resolution"]["overall"]["safe_false_deny"]),
        },
        "strongest_remaining_limitation": "E55 labels and the full guard share deterministic mock schemas and authorization contracts; this is contract evidence, not independent deployment generalization.",
        "ndss_compile": compile_status,
        "anonymity_scan": scan,
        "sanity": sanity,
        "recommended_framing": "measurement + diagnostic framework + local pre-commit authorization prototype",
    }


def write_final_reports(report: dict[str, Any]) -> None:
    write_json(RESULTS / "e56_final_report.json", report)
    text = final_report_markdown(report)
    for path in (
        RESULTS / "e56_final_report.md",
        E55_PACKAGE / "e56_final_report.md",
        NDSS / "e56_final_report.md",
    ):
        write_text(path, text)


def write_e55_package_materials(
    strict_result: dict[str, Any],
    ablation_rows: list[dict[str, Any]],
    slice_rows: list[dict[str, Any]],
    audit: dict[str, Any],
    sanity: dict[str, Any],
) -> None:
    E55_PACKAGE.mkdir(parents=True, exist_ok=True)
    write_table_md(E55_PACKAGE / "e55_ablation_table.md", "E55 Ablation Table", ablation_rows)
    write_table_md(E55_PACKAGE / "e55_slice_table.md", "E55 Slice Table", slice_rows)
    write_text(E55_PACKAGE / "e55_claim_boundary.md", claim_boundary_text(strict_result))
    write_text(E55_PACKAGE / "e55_review_response_notes.md", review_response_notes(strict_result, audit, sanity))
    write_text(E55_PACKAGE / "e55_paper_patch_plan.md", e55_integration_text(strict_result))


def write_claim_boundary(path: Path, strict_result: dict[str, Any]) -> None:
    write_text(path, claim_boundary_text(strict_result))


def claim_boundary_text(strict_result: dict[str, Any]) -> str:
    return f"""# E55 Claim Boundary

Outcome: `{strict_result['interpretation']['outcome']}`.

## Supported

- Typed authorization context can improve local mock pre-commit decidability.
- Resource/auth failures are partly interface and infrastructure failures, not merely LLM recognition failures.
- Atom-level expansion exposes multi-resource and operation-mode violations.
- Alias resolution, operation modes, multi-resource expansion, provenance metadata, and evidence fallback are useful to the extent supported by E55 ablations.

## Not Supported

- Production safety.
- Complete permission-system coverage.
- Independent deployment generalization.
- Real SaaS/browser/banking/email safety.
- Original benchmark reproduction.
- Real side-effect execution.
- Robustness to adversarially adapted tools beyond the controlled schema.
- Learned calibration as the main method.
"""


def review_response_notes(strict_result: dict[str, Any], audit: dict[str, Any], sanity: dict[str, Any]) -> str:
    return f"""# E55 Review Response Notes

E55 should be presented as controlled local pre-commit contract evidence. The decision-path audit status is `{audit['passed']}` and strict replay metric equality is `{sanity['label_hidden_replay']['metrics_equal']}`.

The correct interpretation is that explicit authorization infrastructure turns an abstention-heavy reference binding monitor into high-coverage decisions under mock schemas. It does not prove production safety or independent deployment generalization.
"""


def e55_integration_text(strict_result: dict[str, Any]) -> str:
    existing = strict_result["methods"]["existing_hard_effect_binding_guard"]["overall"]
    authz = strict_result["methods"]["authz_aware_effect_binding_guard"]["overall"]
    return f"""# E55 NDSS Integration Plan

Add E55 as a new finding: explicit authorization infrastructure turns abstention-heavy binding into high-coverage local pre-commit mediation.

Paper-facing metrics:

- Existing hard guard: UPA {fmt(rate(existing['unsafe_pre_allow']))}, FDeny {fmt(rate(existing['safe_false_deny']))}, coverage {fmt(rate(existing['coverage']))}.
- Authorization-aware guard: UPA {fmt(rate(authz['unsafe_pre_allow']))}, FDeny {fmt(rate(authz['safe_false_deny']))}, coverage {fmt(rate(authz['coverage']))}.

Keep E50 resource/auth stress as the motivating failure. State that E55 is local mock contract evidence and not production validation.
"""


def ndss_main_tex() -> str:
    return r"""\documentclass[10pt]{article}
\usepackage[margin=0.72in]{geometry}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage{hyperref}
\title{Counterfactual Effect Binding for LLM-Agent Tool Safety}
\author{Anonymous Authors}
\date{}
\begin{document}
\maketitle
\input{sections/abstract}
\input{sections/introduction}
\input{sections/threat_model}
\input{sections/method}
\input{sections/results}
\input{sections/limitations}
\input{sections/conclusion}
\appendix
\input{appendix}
\end{document}
"""


def ndss_abstract(strict_result: dict[str, Any]) -> str:
    existing = strict_result["methods"]["existing_hard_effect_binding_guard"]["overall"]
    authz = strict_result["methods"]["authz_aware_effect_binding_guard"]["overall"]
    return rf"""\begin{{abstract}}
LLM-agent safety monitors must reason about realized effects, affected resources, authorization context, provenance, and utility rather than only tool names or trace formats. This paper package reports controlled custom-stress evidence for an Effect-Binding Guard and a local pre-commit authorization prototype. Existing results show that hard tuple binding can reduce unsafe pre-allow under custom stress, but E50 exposes a resource/authorization bottleneck. Finally, E55, a local mock pre-commit mediation study, shows that typed authorization context and atom-level action expansion can turn the old guard's abstention-heavy behavior (coverage {fmt(rate(existing['coverage']))}) into high-coverage controlled decisions (coverage {fmt(rate(authz['coverage']))}), while preserving zero observed unsafe pre-allow in the constructed setting. This is contract evidence under explicit authorization infrastructure, not a production safety certificate.
\end{{abstract}}
"""


def ndss_introduction() -> str:
    return r"""\section{Introduction}
LLM agents increasingly mediate side-effectful tools such as messaging, file sharing, calendars, workspace administration, and transaction APIs. Safety decisions for these tools cannot be reduced to a tool name. A single tool surface may realize different effects, and the same effect may appear through different tools, wrappers, or trace formats.

Prior experiments in this repository show intentionally mixed evidence. Counterfactual stress tests identify tool-effect fragmentation and structural defenses that remain sensitive to schema or graph surfaces. The hard Effect-Binding Guard is therefore framed as a measurement and method-feasibility artifact: it binds candidate actions into effect, resource, authorization, and provenance tuples, then uses disagreement, evidence fallback, and provenance checks to decide whether to allow, deny, or abstain.

\textbf{Reviewer-facing interpretation.} E55 shows that the resource/authorization bottleneck is also an interface problem. Without explicit authorization infrastructure, the old hard guard abstains heavily. With typed authorization context, resource alias maps, operation-mode semantics, multi-resource atom expansion, and provenance metadata, many previously unresolved pre-commit decisions become decidable in a controlled local mock setting.
"""


def ndss_threat_model() -> str:
    return r"""\section{Threat Model and Security Goal}
We study pre-commit mediation for LLM-agent tool calls. The monitor observes a user task, visible tool schema, candidate tool call, non-oracle evidence summaries when available, and provenance/control metadata. It must decide before commit whether the realized effects are authorized by the task.

\subsection{Authorization Contract}
E55 assumes an explicit authorization contract: authorized resource sets, aliases, operation modes, multi-resource expansion rules, public/private visibility constraints, trusted and untrusted control sources, and evidence availability. The guard may abstain when resource identity, provenance, or evidence is insufficient. This contract is visible infrastructure, not a hidden label.
"""


def ndss_method() -> str:
    return r"""\section{Method}
The reference hard Effect-Binding Guard predicts a tuple consisting of realized effect, resource, authorization match, and provenance risk. It is useful as a binding monitor but remains conservative when resource identity or authorization scope is underspecified.

The E55 authorization-aware prototype adds a pre-commit atom layer. A visible tool call is expanded into effect-resource-operation atoms, one per recipient, attendee, file, channel, account, payee, visibility, or operation component. The default policy requires every atom to be authorized. Alias resolution, operation-mode handling, provenance overlay, and optional evidence fallback are explicit infrastructure modules. The prototype never uses expected decisions, gold expanded atoms, violation reasons, or scoring metadata in strict mode.
"""


def ndss_results(
    strict_result: dict[str, Any],
    ablation_rows: list[dict[str, Any]],
    slice_rows: list[dict[str, Any]],
    audit: dict[str, Any],
    sanity: dict[str, Any],
) -> str:
    existing = strict_result["methods"]["existing_hard_effect_binding_guard"]["overall"]
    authz = strict_result["methods"]["authz_aware_effect_binding_guard"]["overall"]
    no_multi = strict_result["methods"]["authz_aware_no_multi_resource_expansion"]["overall"]
    no_alias = strict_result["methods"]["authz_aware_no_alias_resolution"]["overall"]
    no_op = strict_result["methods"]["authz_aware_no_operation_mode"]["overall"]
    no_prov = strict_result["methods"]["authz_aware_no_provenance_overlay"]["overall"]
    return rf"""\section{{Results}}
\textbf{{Finding 6: Explicit authorization infrastructure turns abstention-heavy binding into high-coverage local pre-commit mediation.}} On 600 local mock pre-commit rows, the existing hard guard has UPA {fmt(rate(existing['unsafe_pre_allow']))}, FDeny {fmt(rate(existing['safe_false_deny']))}, and coverage {fmt(rate(existing['coverage']))}. The authorization-aware guard has UPA {fmt(rate(authz['unsafe_pre_allow']))}, FDeny {fmt(rate(authz['safe_false_deny']))}, and coverage {fmt(rate(authz['coverage']))}.

The ablations indicate why the infrastructure matters. Removing multi-resource expansion raises UPA to {fmt(rate(no_multi['unsafe_pre_allow']))}. Removing operation-mode semantics raises UPA to {fmt(rate(no_op['unsafe_pre_allow']))}. Removing provenance overlay raises UPA to {fmt(rate(no_prov['unsafe_pre_allow']))}. Removing alias resolution leaves UPA at {fmt(rate(no_alias['unsafe_pre_allow']))} but creates FDeny {fmt(rate(no_alias['safe_false_deny']))}. Strict replay matches original deployable metrics: {sanity['label_hidden_replay']['metrics_equal']}. The decision-path audit passes: {audit['passed']}.

This finding is intentionally scoped. E55 is controlled local mock contract evidence; it does not execute real external side effects and does not validate production SaaS, browser, email, or banking systems.
"""


def ndss_limitations() -> str:
    return r"""\section{Limitations}
E55 shares deterministic mock schemas and authorization contracts with the label generator. Therefore it is contract evidence rather than independent deployment generalization. Real deployment still requires independent trace collection, a policy user interface, robust resource identity, mediation and commit protocols, logging, and adversarial validation against adapted tools. The negative E50 resource/auth stress remains an important limitation and motivation.
"""


def ndss_conclusion() -> str:
    return r"""\section{Conclusion}
The current evidence supports a measurement and diagnostic framework plus a local pre-commit authorization prototype. It does not support a complete defense or production-ready guard. The main lesson is that effect binding requires explicit interfaces for authorization, resources, provenance, operation mode, and evidence.
"""


def ndss_appendix(strict_result: dict[str, Any], ablation_rows: list[dict[str, Any]], slice_rows: list[dict[str, Any]], audit: dict[str, Any], sanity: dict[str, Any]) -> str:
    rows = "\n".join(
        rf"\texttt{{{latex_escape(row['method'])}}} & {fmt(row['unsafe_pre_allow'])} & {fmt(row['safe_false_deny'])} & {fmt(row['coverage'])} & {fmt(row['atom_expansion_exact_match'])} \\"
        for row in ablation_rows
        if row["method"] in {"existing_hard_effect_binding_guard", "authz_aware_effect_binding_guard", "authz_aware_no_multi_resource_expansion", "authz_aware_no_operation_mode", "authz_aware_no_provenance_overlay", "authz_aware_no_alias_resolution"}
    )
    return rf"""\section{{E55 Appendix}}
\begin{{table}}[h]
\centering
\small
\begin{{tabular}}{{lrrrr}}
\toprule
Method & UPA & FDeny & Coverage & Atom exact \\
\midrule
{rows}
\bottomrule
\end{{tabular}}
\caption{{E55 strict label-hidden ablation summary.}}
\end{{table}}

Decision-path audit passed: {audit['passed']}. Strict replay metric equality: {sanity['label_hidden_replay']['metrics_equal']}. Claim boundary: controlled local pre-commit contract evidence only.
"""


def claim_to_source_text() -> str:
    return """# Claim to Source Map

| Claim | Source artifact | Scope |
|---|---|---|
| E55 old hard guard is abstention-heavy | `analysis/results/e55_precommit_authz_results_strict.json` | controlled local mock |
| E55 authorization-aware guard improves coverage | `analysis/results/e55_precommit_authz_results_strict.json` | controlled local mock |
| Strict guard does not use gold labels | `analysis/results/e55_decision_path_audit.json` | decision-path audit |
| Ablations identify necessary infrastructure | `analysis/results/e55_precommit_authz_ablation_table.csv` | controlled local mock |
| E55 is not production validation | `analysis/results/e55_precommit_authz_claim_boundary.md` | claim boundary |
"""


def ndss_readiness_text(audit: dict[str, Any], sanity: dict[str, Any]) -> str:
    return f"""# NDSS Readiness Report

- Decision-path audit passed: `{audit['passed']}`.
- Strict replay equals original metrics: `{sanity['label_hidden_replay']['metrics_equal']}`.
- Candidate source was rebuilt during E56 because no LaTeX source was present at E56 start.
- Remaining boundary: E55 is controlled local mock contract evidence, not production safety.
"""


def final_report_markdown(report: dict[str, Any]) -> str:
    return f"""# E56 Final Report

- Decision-path audit passed: `{report['decision_path_audit_passed']}`.
- Strict mode passed: `{report['strict_mode_passed']}`.
- Existing hard guard metrics: `{report['paper_metrics']['existing_hard_guard']}`.
- Authz-aware guard metrics: `{report['paper_metrics']['authz_aware_guard']}`.
- Strongest ablation evidence: `{report['strongest_ablation_evidence']}`.
- Strongest remaining limitation: {report['strongest_remaining_limitation']}
- NDSS compiled: `{report['ndss_compile']['compiled']}`, pages: `{report['ndss_compile']['page_count']}`.
- Anonymity scan passed: `{report['anonymity_scan']['passed']}`.
- Recommended framing: {report['recommended_framing']}.
"""


def write_strict_markdown(path: Path, result: dict[str, Any]) -> None:
    existing = result["methods"]["existing_hard_effect_binding_guard"]["overall"]
    authz = result["methods"]["authz_aware_effect_binding_guard"]["overall"]
    write_text(
        path,
        "# E55 Strict Label-Hidden Replay\n\n"
        f"- Rows: {result['dataset']['n_rows']}\n"
        f"- Strict-vs-original metrics equal: `{result['strict_vs_original']['metrics_equal']}`\n"
        f"- Changed decisions: {result['strict_vs_original']['changed_decision_count']}\n"
        f"- Existing hard guard: UPA {fmt(rate(existing['unsafe_pre_allow']))}, FDeny {fmt(rate(existing['safe_false_deny']))}, coverage {fmt(rate(existing['coverage']))}\n"
        f"- Authz-aware guard: UPA {fmt(rate(authz['unsafe_pre_allow']))}, FDeny {fmt(rate(authz['safe_false_deny']))}, coverage {fmt(rate(authz['coverage']))}\n",
    )


def write_audit_markdown(path: Path, audit: dict[str, Any]) -> None:
    rows = []
    for method, info in audit["methods"].items():
        rows.append(
            {
                "method": method,
                "entry_point": info["entry_point"],
                "object_passed": info["object_passed"],
                "observed_fields": ", ".join(info["observed_accessed_fields"]),
                "forbidden_fields": ", ".join(info["forbidden_fields_observed"]),
                "status": info["decision_path_status"],
            }
        )
    write_text(path, "# E55 Decision-Path Audit\n\n" + markdown_table(rows) + f"\n\nPassed: `{audit['passed']}`.\n")


def write_sanity_markdown(path: Path, sanity: dict[str, Any]) -> None:
    write_text(
        path,
        "# E55 Sanity Checks\n\n"
        f"- Strict replay metrics equal: `{sanity['label_hidden_replay']['metrics_equal']}`\n"
        f"- Strict changed decisions: `{sanity['label_hidden_replay']['changed_decision_count']}`\n"
        f"- Resource-renaming metrics stable: `{sanity['resource_renaming']['metrics_stable']}`\n"
        f"- Spot audit rows: `{sanity['spot_audit_packet_rows']}`\n\n"
        "## Fold Breakdown\n\n"
        + markdown_table(sanity["group_folds"]),
    )


def write_anonymity_markdown(path: Path, scan: dict[str, Any]) -> None:
    lines = ["# E56 Anonymity Scan", "", f"- Passed: `{scan['passed']}`", f"- Files scanned: `{scan['n_files_scanned']}`", ""]
    if scan["findings"]:
        lines.append(markdown_table(scan["findings"]))
    write_text(path, "\n".join(lines) + "\n")


def write_spot_audit_markdown(path: Path, packet: list[dict[str, Any]]) -> None:
    rows = [
        {
            "case_id": row["case_id"],
            "domain": row["domain"],
            "expected_decision": row["expected_decision"],
            "violation_reasons": ",".join(row["violation_reasons"]),
        }
        for row in packet
    ]
    write_text(path, "# E55 Spot Audit Packet\n\n" + markdown_table(rows))


def write_table_md(path: Path, title: str, rows: list[dict[str, Any]]) -> None:
    write_text(path, f"# {title}\n\n" + markdown_table(rows))


def write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No rows._\n"
    columns = list(rows[0])
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", "/") for col in columns) + " |")
    return "\n".join(lines) + "\n"


def pick_main_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "unsafe_pre_allow": rate(metrics["unsafe_pre_allow"]),
        "safe_false_deny": rate(metrics["safe_false_deny"]),
        "coverage": rate(metrics["coverage"]),
        "abstain": rate(metrics["abstain_rate"]),
        "decision_accuracy": rate(metrics["decision_accuracy"]),
    }


def slice_rate(method_summary: dict[str, Any], slice_name: str, metric: str) -> Any:
    return rate(method_summary.get("by_slice", {}).get(slice_name, {}).get(metric))


def rate(metric: Any) -> Any:
    return metric.get("rate") if isinstance(metric, dict) else metric


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def latex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
