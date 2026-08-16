#!/usr/bin/env python3
"""Validate E85 independent projection reviews and compile approved projections."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "evaluation/e85_security_effect_projections"
DEFAULT_TEMPLATE = DEFAULT_DIR / "review_packet.template.jsonl"
DEFAULT_REVIEWED = DEFAULT_DIR / "review_packet.reviewed.jsonl"
OUTPUT_NAME = "trusted_security_effect_projections.jsonl"

REQUIRED_CONFIRMATIONS = (
    "implementation_inspected",
    "state_mutation_paths_verified",
    "defaults_reviewed",
    "interactions_reviewed",
    "expansions_reviewed",
    "negative_controls_reviewed",
    "no_attack_outcomes_or_method_labels_used",
)
FIELD_DECISIONS = {"SECURITY_RELEVANT", "NON_SECURITY", "UNCERTAIN"}
FIELD_ROLES = {
    "resource", "target_principal", "operation", "payload", "amount_or_quantity",
    "visibility", "commit_mode", "provenance", "control_source", "temporal",
    "credential", "compound_trigger", "other_security_relevant",
}
PROJECTION_DECISIONS = {"APPROVE", "REJECT", "UNCERTAIN"}
OVERALL_DECISIONS = {"APPROVE", "REJECT", "UNCERTAIN"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def immutable_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"review", "candidate_payload_sha256"}}


def payload_hash(row: dict[str, Any]) -> str:
    encoded = json.dumps(
        immutable_payload(row), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def valid_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    return True


def validate_review(row: dict[str, Any]) -> tuple[list[str], str]:
    key = row.get("tool_instance_key", "<unknown>")
    review = row.get("review")
    errors: list[str] = []
    if not isinstance(review, dict):
        return [f"{key}: review must be an object"], "invalid"
    if not str(review.get("reviewer_anonymous_id", "")).strip():
        errors.append(f"{key}: reviewer_anonymous_id is required")
    if not valid_date(review.get("review_date")):
        errors.append(f"{key}: review_date must be ISO YYYY-MM-DD")
    for field in REQUIRED_CONFIRMATIONS:
        if review.get(field) is not True:
            errors.append(f"{key}: {field} must be confirmed true")
    overall = review.get("overall_decision")
    if overall not in OVERALL_DECISIONS:
        errors.append(f"{key}: overall_decision must be APPROVE, REJECT, or UNCERTAIN")
    if not str(review.get("rationale", "")).strip():
        errors.append(f"{key}: overall rationale is required")

    schema_names = [item.get("name") for item in row.get("schema_fields", [])]
    field_reviews = review.get("field_reviews")
    if not isinstance(field_reviews, list):
        errors.append(f"{key}: field_reviews must be a list")
        field_reviews = []
    reviewed_names = [item.get("field") for item in field_reviews if isinstance(item, dict)]
    if reviewed_names != schema_names:
        errors.append(f"{key}: field review keys/order differ from immutable schema")
    for item in field_reviews:
        if not isinstance(item, dict):
            errors.append(f"{key}: malformed field review")
            continue
        field_name = item.get("field")
        decision = item.get("decision")
        if decision not in FIELD_DECISIONS:
            errors.append(f"{key}/{field_name}: field decision is incomplete")
        if not str(item.get("rationale", "")).strip():
            errors.append(f"{key}/{field_name}: field rationale is required")
        role = str(item.get("role", "")).strip()
        if decision == "SECURITY_RELEVANT" and role not in FIELD_ROLES:
            errors.append(f"{key}/{field_name}: security-relevant field requires a supported role")
        if decision == "NON_SECURITY" and role:
            errors.append(f"{key}/{field_name}: non-security field role must be empty")

    projection_ids = [item.get("projection_id") for item in row.get("candidate_effect_projections", [])]
    projection_reviews = review.get("projection_reviews")
    if not isinstance(projection_reviews, list):
        errors.append(f"{key}: projection_reviews must be a list")
        projection_reviews = []
    reviewed_ids = [item.get("projection_id") for item in projection_reviews if isinstance(item, dict)]
    if reviewed_ids != projection_ids:
        errors.append(f"{key}: projection review keys/order differ from immutable candidates")
    projection_decisions: list[str] = []
    for item in projection_reviews:
        if not isinstance(item, dict):
            errors.append(f"{key}: malformed projection review")
            continue
        projection_id = item.get("projection_id")
        decision = item.get("decision")
        projection_decisions.append(str(decision))
        if decision not in PROJECTION_DECISIONS:
            errors.append(f"{key}/{projection_id}: projection decision is incomplete")
        if not str(item.get("rationale", "")).strip():
            errors.append(f"{key}/{projection_id}: projection rationale is required")

    if overall == "APPROVE":
        if any(decision != "APPROVE" for decision in projection_decisions):
            errors.append(f"{key}: overall APPROVE requires every candidate projection to be approved")
        if any(item.get("decision") == "UNCERTAIN" for item in field_reviews if isinstance(item, dict)):
            errors.append(f"{key}: overall APPROVE cannot contain uncertain fields")
        if review.get("no_missing_security_effects_confirmed") is not True:
            errors.append(f"{key}: overall APPROVE requires no_missing_security_effects_confirmed=true")
    return errors, str(overall).lower() if overall in OVERALL_DECISIONS else "invalid"


def validate(template_path: Path, reviewed_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    template = read_jsonl(template_path)
    reviewed = read_jsonl(reviewed_path)
    errors: list[str] = []
    template_by_key = {row.get("tool_instance_key"): row for row in template}
    reviewed_by_key = {row.get("tool_instance_key"): row for row in reviewed}
    if len(template_by_key) != len(template):
        errors.append("template contains duplicate tool_instance_key values")
    if len(reviewed_by_key) != len(reviewed):
        errors.append("reviewed packet contains duplicate tool_instance_key values")
    if set(template_by_key) != set(reviewed_by_key):
        errors.append("reviewed packet keys differ from immutable template")

    compiled: list[dict[str, Any]] = []
    decision_counts: Counter[str] = Counter()
    reviewers: set[str] = set()
    for template_row in template:
        key = template_row.get("tool_instance_key")
        expected_hash = payload_hash(template_row)
        if template_row.get("candidate_payload_sha256") != expected_hash:
            errors.append(f"{key}: template candidate hash is invalid")
        row = reviewed_by_key.get(key)
        if row is None:
            continue
        if row.get("candidate_payload_sha256") != expected_hash or payload_hash(row) != expected_hash:
            errors.append(f"{key}: immutable candidate content was changed")
            continue
        row_errors, decision = validate_review(row)
        errors.extend(row_errors)
        decision_counts[decision] += 1
        review = row.get("review") or {}
        reviewer_id = str(review.get("reviewer_anonymous_id", "")).strip()
        if reviewer_id:
            reviewers.add(reviewer_id)
        if not row_errors and decision == "approve":
            field_classification = {
                item["field"]: {"decision": item["decision"], "role": item["role"]}
                for item in review["field_reviews"]
            }
            compiled.append({
                "projection_version": "e85_agentdojo_trusted_projection_v1",
                "agentdojo_benchmark_version": row["agentdojo_benchmark_version"],
                "suite": row["suite"],
                "tool_name": row["tool_name"],
                "tool_instance_key": key,
                "source_evidence": {
                    name: row["source_evidence"][name]
                    for name in (
                        "module", "relative_path", "function_name", "start_line", "end_line",
                        "source_file_sha256", "function_source_sha256",
                    )
                },
                "security_effect_projections": row["candidate_effect_projections"],
                "field_classification": field_classification,
                "reviewer_anonymous_id": reviewer_id,
                "review_date": review["review_date"],
                "candidate_payload_sha256": expected_hash,
            })

    all_rows_complete = not errors and len(reviewed) == len(template)
    if not all_rows_complete:
        status = "blocked_by_incomplete_or_invalid_review"
        compiled_output: list[dict[str, Any]] = []
    elif decision_counts["approve"] == len(template):
        status = "passed"
        compiled_output = compiled
    else:
        status = "passed_with_rejections"
        compiled_output = compiled
    summary = {
        "experiment": "E85-AgentDojo-projection-review",
        "status": status,
        "template_rows": len(template),
        "reviewed_rows": len(reviewed),
        "compiled_trusted_projections": len(compiled_output),
        "review_decision_counts": dict(sorted(decision_counts.items())),
        "reviewer_anonymous_ids": sorted(reviewers),
        "n_errors": len(errors),
        "errors": errors,
        "claim_boundary": (
            "A passing review validates source-bound projection judgments for the approved AgentDojo tool instances only. "
            "Rejected or uncertain instances remain unavailable and must fail closed; this is not production certification."
        ),
    }
    return summary, compiled_output


def write_outputs(output_dir: Path, summary: dict[str, Any], compiled: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_summary = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    (output_dir / "validation_report.json").write_text(rendered_summary, encoding="utf-8")
    # Keep the human-facing status artifact synchronized with the validator.
    # The packet builder creates summary.json before review; leaving it stale
    # after validation makes completed review look pending to status tooling.
    (output_dir / "summary.json").write_text(rendered_summary, encoding="utf-8")
    trusted = output_dir / OUTPUT_NAME
    if summary["status"] in {"passed", "passed_with_rejections"}:
        trusted.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in compiled), encoding="utf-8"
        )
    elif trusted.exists():
        trusted.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--reviewed", type=Path, default=DEFAULT_REVIEWED)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    if not args.reviewed.exists():
        summary = {
            "experiment": "E85-AgentDojo-projection-review",
            "status": "awaiting_external_human_review",
            "template_rows": len(read_jsonl(args.template)),
            "reviewed_rows": 0,
            "compiled_trusted_projections": 0,
            "n_errors": 1,
            "errors": ["No independently completed review packet was supplied."],
            "claim_boundary": "No AgentDojo security-effect projection is trusted before independent review.",
        }
        write_outputs(args.output_dir, summary, [])
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if args.allow_incomplete else 2
    summary, compiled = validate(args.template, args.reviewed)
    write_outputs(args.output_dir, summary, compiled)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] in {"passed", "passed_with_rejections"} or args.allow_incomplete else 1


if __name__ == "__main__":
    raise SystemExit(main())
