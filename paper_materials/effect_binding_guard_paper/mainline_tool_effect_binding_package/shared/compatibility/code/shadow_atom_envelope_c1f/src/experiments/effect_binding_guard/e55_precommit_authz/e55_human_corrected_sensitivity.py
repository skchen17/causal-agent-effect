from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .schemas import E55Case, E55Prediction


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CASES = ROOT / "data/e55_precommit_authz_dataset.jsonl"
DEFAULT_PREDICTIONS = ROOT / "analysis/results/e55_precommit_authz_predictions_strict.jsonl"
DEFAULT_AUDIT = ROOT / "analysis/results/e57_spot_audit_packet_human_audited.jsonl"
DEFAULT_OUTPUT = ROOT / "analysis/results/e55_human_corrected_sensitivity.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute E55 metrics under E57 human-corrected labels without overwriting canonical results.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--predictions", default=str(DEFAULT_PREDICTIONS))
    parser.add_argument("--human-audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_cases(path: Path) -> list[E55Case]:
    return [E55Case.from_dict(row) for row in read_jsonl(path)]


def load_predictions(path: Path) -> list[E55Prediction]:
    return [E55Prediction.from_dict(row) for row in read_jsonl(path)]


def metric(successes: int, total: int) -> dict[str, Any]:
    return {"successes": successes, "total": total, "rate": None if total == 0 else successes / total}


def evaluate(case_ids: set[str], label_map: dict[str, str], predictions: list[E55Prediction], method: str) -> dict[str, Any]:
    rows = [prediction for prediction in predictions if prediction.method == method and prediction.case_id in case_ids]
    unsafe = [prediction for prediction in rows if label_map[prediction.case_id] == "DENY"]
    safe = [prediction for prediction in rows if label_map[prediction.case_id] == "ALLOW"]
    abstain_label = [prediction for prediction in rows if label_map[prediction.case_id] == "ABSTAIN"]
    covered = [prediction for prediction in rows if prediction.decision != "ABSTAIN"]
    correct = [prediction for prediction in rows if prediction.decision == label_map[prediction.case_id]]
    return {
        "n_rows": len(rows),
        "label_counts": dict(Counter(label_map[prediction.case_id] for prediction in rows)),
        "unsafe_pre_allow": metric(sum(prediction.decision == "ALLOW" for prediction in unsafe), len(unsafe)),
        "safe_false_deny": metric(sum(prediction.decision == "DENY" for prediction in safe), len(safe)),
        "abstain_label_recall": metric(sum(prediction.decision == "ABSTAIN" for prediction in abstain_label), len(abstain_label)),
        "coverage": metric(len(covered), len(rows)),
        "abstain_rate": metric(len(rows) - len(covered), len(rows)),
        "decision_accuracy": metric(len(correct), len(rows)),
    }


def delta(corrected: dict[str, Any], original: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("unsafe_pre_allow", "safe_false_deny", "coverage", "abstain_rate", "decision_accuracy"):
        c_rate = corrected[key]["rate"]
        o_rate = original[key]["rate"]
        out[key] = None if c_rate is None or o_rate is None else c_rate - o_rate
    return out


def main() -> None:
    args = parse_args()
    cases_path = Path(args.cases)
    predictions_path = Path(args.predictions)
    audit_path = Path(args.human_audit)
    output_path = Path(args.output)
    if not cases_path.is_absolute():
        cases_path = (ROOT / cases_path).resolve()
    if not predictions_path.is_absolute():
        predictions_path = (ROOT / predictions_path).resolve()
    if not audit_path.is_absolute():
        audit_path = (ROOT / audit_path).resolve()
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()

    cases = load_cases(cases_path)
    predictions = load_predictions(predictions_path)
    audited_rows = read_jsonl(audit_path)
    original_labels = {case.case_id: case.expected_decision for case in cases}
    audited_labels = {row["case_id"]: row["human_expected_decision"] for row in audited_rows}
    decision_corrections = {
        row["case_id"]: row["human_expected_decision"]
        for row in audited_rows
        if row["human_expected_decision"] != row["expected_decision"]
    }
    corrected_full_labels = dict(original_labels)
    corrected_full_labels.update(decision_corrections)
    methods = sorted({prediction.method for prediction in predictions})
    all_case_ids = set(original_labels)
    audit_case_ids = set(audited_labels)

    audit_subset_original = {method: evaluate(audit_case_ids, original_labels, predictions, method) for method in methods}
    audit_subset_human = {method: evaluate(audit_case_ids, audited_labels, predictions, method) for method in methods}
    full_original = {method: evaluate(all_case_ids, original_labels, predictions, method) for method in methods}
    full_minimal_corrected = {method: evaluate(all_case_ids, corrected_full_labels, predictions, method) for method in methods}
    result = {
        "experiment": "E55 human-corrected sensitivity analysis",
        "claim_scope": "sensitivity analysis over controlled local mock labels; does not overwrite canonical E55",
        "inputs": {
            "cases": str(cases_path),
            "predictions": str(predictions_path),
            "human_audit": str(audit_path),
        },
        "row_counts": {
            "full_cases": len(cases),
            "predictions": len(predictions),
            "audit_rows": len(audited_rows),
        },
        "decision_corrections": [
            {
                "case_id": row["case_id"],
                "domain": row.get("domain"),
                "counterfactual_axis": row.get("counterfactual_axis"),
                "original_expected_decision": row["expected_decision"],
                "human_expected_decision": row["human_expected_decision"],
                "human_notes": row.get("human_notes", ""),
            }
            for row in audited_rows
            if row["case_id"] in decision_corrections
        ],
        "audit_subset": {
            "original_labels": audit_subset_original,
            "human_labels": audit_subset_human,
            "human_minus_original_delta": {method: delta(audit_subset_human[method], audit_subset_original[method]) for method in methods},
        },
        "full_600_minimal_correction": {
            "original_labels": full_original,
            "minimal_human_corrected_labels": full_minimal_corrected,
            "corrected_minus_original_delta": {method: delta(full_minimal_corrected[method], full_original[method]) for method in methods},
        },
        "writing_interpretation": {
            "main_guard": "authz_aware_effect_binding_guard",
            "recommendation": "Report E55 as human-audited-with-corrections. The corrected sensitivity preserves zero unsafe pre-allow for the full authz-aware guard but introduces a small false-denial rate.",
            "do_not_claim": "Do not claim the E57 spot audit fully confirmed E55 labels or atom construction.",
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(output_path.with_suffix(".csv"), result, methods)
    write_md(output_path.with_suffix(".md"), result, methods)
    print(json.dumps({"output": str(output_path), "audit_rows": len(audited_rows), "decision_corrections": len(decision_corrections)}, indent=2))


def fmt(metric_obj: dict[str, Any]) -> str:
    rate = metric_obj["rate"]
    if rate is None:
        return "NA"
    return f"{metric_obj['successes']}/{metric_obj['total']} ({rate:.3f})"


def write_csv(path: Path, result: dict[str, Any], methods: list[str]) -> None:
    rows: list[dict[str, Any]] = []
    scopes = (
        ("audit_subset_original", result["audit_subset"]["original_labels"]),
        ("audit_subset_human", result["audit_subset"]["human_labels"]),
        ("full_600_original", result["full_600_minimal_correction"]["original_labels"]),
        ("full_600_minimal_human_corrected", result["full_600_minimal_correction"]["minimal_human_corrected_labels"]),
    )
    for scope, table in scopes:
        for method in methods:
            metrics = table[method]
            row = {"scope": scope, "method": method, "n_rows": metrics["n_rows"], "label_counts": json.dumps(metrics["label_counts"], sort_keys=True)}
            for key in ("unsafe_pre_allow", "safe_false_deny", "abstain_label_recall", "coverage", "abstain_rate", "decision_accuracy"):
                row[f"{key}_successes"] = metrics[key]["successes"]
                row[f"{key}_total"] = metrics[key]["total"]
                row[f"{key}_rate"] = metrics[key]["rate"]
            rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, result: dict[str, Any], methods: list[str]) -> None:
    selected = [
        "existing_hard_effect_binding_guard",
        "authz_aware_effect_binding_guard",
        "authz_aware_no_alias_resolution",
        "authz_aware_no_multi_resource_expansion",
        "authz_aware_no_operation_mode",
        "authz_aware_no_provenance_overlay",
        "authz_aware_no_evidence_fallback",
    ]
    lines = [
        "# E55 Human-Corrected Sensitivity Analysis",
        "",
        "This analysis applies the E57 human spot-audit decision corrections without overwriting canonical E55/E56/E57 artifacts.",
        "",
        f"- Full E55 cases: {result['row_counts']['full_cases']}",
        f"- Human-audited rows: {result['row_counts']['audit_rows']}",
        f"- Decision corrections: {len(result['decision_corrections'])}",
        "",
        "## Decision Corrections",
        "",
        "| Case | Domain | Original | Human | Note |",
        "|---|---|---:|---:|---|",
    ]
    for item in result["decision_corrections"]:
        note = str(item["human_notes"]).replace("\n", " ")
        lines.append(f"| `{item['case_id']}` | {item['domain']} | {item['original_expected_decision']} | {item['human_expected_decision']} | {note} |")
    lines.extend(
        [
            "",
            "## Full 600-Row Minimal Correction",
            "",
            "| Method | Original UPA | Corrected UPA | Original FDeny | Corrected FDeny | Original Coverage | Corrected Coverage |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    original = result["full_600_minimal_correction"]["original_labels"]
    corrected = result["full_600_minimal_correction"]["minimal_human_corrected_labels"]
    for method in selected:
        if method not in methods:
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    method,
                    fmt(original[method]["unsafe_pre_allow"]),
                    fmt(corrected[method]["unsafe_pre_allow"]),
                    fmt(original[method]["safe_false_deny"]),
                    fmt(corrected[method]["safe_false_deny"]),
                    fmt(original[method]["coverage"]),
                    fmt(corrected[method]["coverage"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Writing Implication",
            "",
            "The corrected sensitivity preserves zero unsafe pre-allow for the full authorization-aware guard, but it introduces a small false-denial rate after correcting transaction/resource semantics. The paper should report this as a caveat and avoid claiming perfect human label confirmation.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
