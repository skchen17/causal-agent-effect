#!/usr/bin/env python3
"""Validate an independently reviewed E84 authority packet and compile manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "evaluation/e84_authority_manifests/review_packet.template.jsonl"
DEFAULT_REVIEWED = ROOT / "evaluation/e84_authority_manifests/review_packet.reviewed.jsonl"
DEFAULT_OUTPUT = ROOT / "evaluation/e84_authority_manifests"
DEFAULT_RESOLVER_CATALOG = DEFAULT_OUTPUT / "resolver_catalog.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def immutable_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_packet_version": row.get("review_packet_version"),
        "suite": row.get("suite"),
        "user_task_id": row.get("user_task_id"),
        "original_task": row.get("original_task"),
        "original_task_sha256": row.get("original_task_sha256"),
        "pre_output_plan_available": row.get("pre_output_plan_available"),
        "candidate_task_goal": row.get("candidate_task_goal"),
        "candidate_bindings": [
            {key: value for key, value in binding.items() if key != "review"}
            for binding in row.get("candidate_bindings", [])
        ],
        "forbidden_hidden_evidence_present": row.get("forbidden_hidden_evidence_present"),
    }


def payload_hash(row: dict[str, Any]) -> str:
    encoded = json.dumps(immutable_payload(row), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def review_date_valid(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    return True


def validate_binding(
    binding: dict[str, Any], prefix: str, suite: str, resolver_catalog: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    mode = binding.get("mode")
    review = binding.get("review")
    if not isinstance(review, dict):
        return [f"{prefix}: missing review object"]
    decision = review.get("decision")
    if decision not in {"APPROVE", "REJECT"}:
        errors.append(f"{prefix}: decision must be APPROVE or REJECT")
        return errors
    if not str(review.get("rationale", "")).strip():
        errors.append(f"{prefix}: rationale is required")
    if decision == "REJECT":
        return errors
    if mode == "exact":
        spans = review.get("source_spans")
        transform = str(review.get("canonical_transform", "")).strip()
        if not isinstance(spans, list) or not all(isinstance(item, str) and item.strip() for item in spans):
            errors.append(f"{prefix}: source_spans must be a list of nonempty strings")
        if not spans and not transform:
            errors.append(f"{prefix}: approved exact binding requires a source span or canonical transform")
    elif mode == "resolve":
        resolver = review.get("resolver")
        if not isinstance(resolver, dict):
            errors.append(f"{prefix}: approved resolver requires a resolver object")
        else:
            read_tool = resolver.get("read_tool")
            tool_catalog = resolver_catalog.get("suites", {}).get(suite, {}).get(read_tool)
            if not isinstance(read_tool, str) or not read_tool.strip():
                errors.append(f"{prefix}: resolver.read_tool is required")
            elif not isinstance(tool_catalog, dict):
                errors.append(f"{prefix}: resolver.read_tool is not in the frozen suite catalog")
            elif tool_catalog.get("eligible_as_authorized_read") is not True:
                errors.append(f"{prefix}: resolver.read_tool is effectful or external")

            query = resolver.get("query_constraint")
            if not isinstance(query, dict) or set(query) != {"arguments", "allow_additional_arguments"}:
                errors.append(f"{prefix}: resolver.query_constraint must contain arguments and allow_additional_arguments")
            else:
                arguments = query.get("arguments")
                if not isinstance(arguments, dict):
                    errors.append(f"{prefix}: resolver.query_constraint.arguments must be an object")
                else:
                    permitted = set(tool_catalog.get("parameter_fields", [])) if isinstance(tool_catalog, dict) else set()
                    unknown = sorted(set(arguments) - permitted)
                    if unknown:
                        errors.append(f"{prefix}: resolver query uses unknown fields {unknown}")
                    required = set(tool_catalog.get("required_parameter_fields", [])) if isinstance(tool_catalog, dict) else set()
                    missing_required = sorted(required - set(arguments))
                    if missing_required:
                        errors.append(f"{prefix}: resolver query omits required fields {missing_required}")
                    for field_name, constraint in arguments.items():
                        if not isinstance(constraint, dict) or constraint.get("mode") not in {"exact", "forbidden"}:
                            errors.append(f"{prefix}: resolver query field {field_name} requires exact/forbidden mode")
                        elif constraint.get("mode") == "exact" and not isinstance(constraint.get("values"), list):
                            errors.append(f"{prefix}: resolver exact query field {field_name} requires values")
                if query.get("allow_additional_arguments") is not False:
                    errors.append(f"{prefix}: resolver queries must forbid additional arguments")

            projection = resolver.get("output_projection")
            kinds = set(resolver_catalog.get("projection_kinds", []))
            if not isinstance(projection, dict) or projection.get("kind") not in kinds:
                errors.append(f"{prefix}: resolver.output_projection.kind is unsupported")
            elif projection["kind"] in {
                "record_field",
                "record_list_field",
                "filtered_record_field",
                "parsed_text_field",
            } and not str(projection.get("field", "")).strip():
                errors.append(f"{prefix}: record or parsed projection requires a field")
            elif projection["kind"] == "filtered_record_field":
                selector = projection.get("selector")
                if not isinstance(selector, dict) or set(selector) != {"field", "operator", "value"}:
                    errors.append(f"{prefix}: filtered projection requires field/operator/value selector")
                elif (
                    not str(selector.get("field", "")).strip()
                    or selector.get("operator") not in {"exact", "casefold_contains"}
                    or selector.get("value") is None
                    or not isinstance(selector.get("value"), (str, int, float, bool))
                ):
                    errors.append(f"{prefix}: filtered projection selector is invalid")
            elif projection["kind"] == "parsed_text_field":
                parser_ids = set(resolver_catalog.get("parser_ids", []))
                if projection.get("parser_id") not in parser_ids:
                    errors.append(f"{prefix}: parsed projection parser_id is unsupported")
                elif projection.get("field") not in {"street", "city"}:
                    errors.append(f"{prefix}: postal parser exposes only street/city")
            cardinality = resolver.get("max_cardinality")
            if not isinstance(cardinality, int) or isinstance(cardinality, bool) or not 1 <= cardinality <= 100:
                errors.append(f"{prefix}: resolver.max_cardinality must be an integer from 1 to 100")
    elif mode != "forbidden":
        errors.append(f"{prefix}: unsupported binding mode {mode!r}")
    return errors


def validate(
    template_path: Path, reviewed_path: Path, resolver_catalog_path: Path = DEFAULT_RESOLVER_CATALOG
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    template = read_jsonl(template_path)
    reviewed = read_jsonl(reviewed_path)
    resolver_catalog = json.loads(resolver_catalog_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    exclusions: list[str] = []
    if len(template) != len(reviewed):
        errors.append(f"row count mismatch: template={len(template)} reviewed={len(reviewed)}")
    template_by_key = {(row.get("suite"), row.get("user_task_id")): row for row in template}
    reviewed_by_key = {(row.get("suite"), row.get("user_task_id")): row for row in reviewed}
    if len(template_by_key) != len(template) or len(reviewed_by_key) != len(reviewed):
        errors.append("duplicate suite/task key")
    if set(template_by_key) != set(reviewed_by_key):
        errors.append("reviewed task keys differ from template")

    compiled: list[dict[str, Any]] = []
    task_status = Counter()
    binding_status = Counter()
    reviewers = set()
    for key in sorted(set(template_by_key) & set(reviewed_by_key)):
        expected = template_by_key[key]
        row = reviewed_by_key[key]
        prefix = f"{key[0]}/{key[1]}"
        expected_hash = payload_hash(expected)
        if expected.get("candidate_payload_sha256") != expected_hash:
            errors.append(f"{prefix}: template candidate hash is invalid")
        if row.get("candidate_payload_sha256") != expected_hash or payload_hash(row) != expected_hash:
            errors.append(f"{prefix}: immutable candidate payload changed")
        if hashlib.sha256(str(row.get("original_task", "")).encode()).hexdigest() != row.get("original_task_sha256"):
            errors.append(f"{prefix}: original task hash mismatch")
        if row.get("forbidden_hidden_evidence_present") is not False:
            errors.append(f"{prefix}: hidden evidence marker is not false")

        human = row.get("human_review")
        task_errors: list[str] = []
        if not isinstance(human, dict):
            task_errors.append(f"{prefix}: missing human_review")
            human = {}
        reviewer_id = str(human.get("reviewer_anonymous_id", "")).strip()
        if not reviewer_id:
            task_errors.append(f"{prefix}: reviewer_anonymous_id is required")
        else:
            reviewers.add(reviewer_id)
        if not review_date_valid(human.get("review_date")):
            task_errors.append(f"{prefix}: review_date must be ISO YYYY-MM-DD")
        if human.get("original_task_only_confirmed") is not True:
            task_errors.append(f"{prefix}: original_task_only_confirmed must be true")

        binding_errors: list[str] = []
        approved_bindings: list[dict[str, Any]] = []
        for index, binding in enumerate(row.get("candidate_bindings", [])):
            current = validate_binding(binding, f"{prefix}/binding[{index}]", str(row.get("suite")), resolver_catalog)
            binding_errors.extend(current)
            decision = (binding.get("review") or {}).get("decision")
            binding_status[decision or "MISSING"] += 1
            if decision == "APPROVE" and not current:
                approved_bindings.append(binding)
        accepted = human.get("accepted") is True
        if accepted and (task_errors or binding_errors or len(approved_bindings) != len(row.get("candidate_bindings", []))):
            task_errors.append(f"{prefix}: accepted task contains incomplete or rejected bindings")
        if accepted:
            errors.extend(task_errors)
            errors.extend(binding_errors)
        else:
            review_incomplete = bool(task_errors) or any(
                (binding.get("review") or {}).get("decision") not in {"APPROVE", "REJECT"}
                or not str((binding.get("review") or {}).get("rationale", "")).strip()
                for binding in row.get("candidate_bindings", [])
            )
            if review_incomplete:
                errors.extend(task_errors)
                errors.extend(binding_errors)
            else:
                exclusions.append(f"{prefix}: task was independently rejected")
                exclusions.extend(binding_errors)
        task_status["accepted" if accepted and not task_errors and not binding_errors else "not_accepted"] += 1
        if accepted and not task_errors and not binding_errors:
            authority_tools: dict[str, dict[str, Any]] = {}
            resolver_specs: dict[str, dict[str, Any]] = {}
            for binding in approved_bindings:
                tool_name = binding["tool_name"]
                field_name = binding["field"]
                mode = binding["mode"]
                compiled_binding: dict[str, Any] = {"mode": mode}
                if mode == "exact":
                    compiled_binding.update({
                        "values": list(binding.get("proposed_values", [])),
                        "source_spans": list(binding["review"].get("source_spans", [])),
                        "canonical_transform": binding["review"].get("canonical_transform", ""),
                    })
                elif mode == "resolve":
                    resolver_id = binding["candidate_resolver_id"]
                    compiled_binding["resolver_id"] = resolver_id
                    resolver_specs[resolver_id] = dict(binding["review"]["resolver"])
                authority_tools.setdefault(tool_name, {})[field_name] = compiled_binding
            compiled.append({
                "suite": row["suite"],
                "user_task_id": row["user_task_id"],
                "original_task_sha256": row["original_task_sha256"],
                "task_goal": row.get("candidate_task_goal"),
                "authority_bindings": approved_bindings,
                "authority_tools": authority_tools,
                "resolver_specs": resolver_specs,
                "reviewer_anonymous_id": reviewer_id,
                "review_date": human["review_date"],
                "candidate_payload_sha256": expected_hash,
            })

    if errors:
        status = "blocked_by_incomplete_or_invalid_review"
    elif len(compiled) == len(template) == 97:
        status = "passed"
    elif compiled:
        status = "passed_with_rejections"
    else:
        status = "blocked_by_no_trusted_manifests"
    summary = {
        "experiment": "E84",
        "status": status,
        "template_rows": len(template),
        "reviewed_rows": len(reviewed),
        "compiled_trusted_manifests": len(compiled),
        "task_status_counts": dict(sorted(task_status.items())),
        "binding_decision_counts": dict(sorted(binding_status.items())),
        "reviewer_anonymous_ids": sorted(reviewers),
        "n_errors": len(errors),
        "errors": errors,
        "n_exclusions": len(exclusions),
        "exclusions": exclusions,
        "authority_coverage": len(compiled) / len(template) if template else 0.0,
        "claim_boundary": (
            "A passed validator establishes packet completeness, immutable candidate provenance, and recorded independent review; "
            "it does not establish production safety or correctness beyond the reviewed AgentDojo task set."
        ),
    }
    return summary, compiled


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--reviewed", type=Path, default=DEFAULT_REVIEWED)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resolver-catalog", type=Path, default=DEFAULT_RESOLVER_CATALOG)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    if not args.reviewed.exists():
        summary = {
            "experiment": "E84",
            "status": "blocked_by_missing_reviewed_packet",
            "template_rows": len(read_jsonl(args.template)),
            "reviewed_rows": 0,
            "compiled_trusted_manifests": 0,
            "n_errors": 1,
            "errors": ["No independently completed review packet was supplied."],
            "claim_boundary": "No trusted authority manifest is compiled without a complete independent review.",
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "validation_report.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if args.allow_incomplete else 2
    summary, compiled = validate(args.template, args.reviewed, args.resolver_catalog)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rendered_summary = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    (args.output_dir / "validation_report.json").write_text(rendered_summary, encoding="utf-8")
    # The packet builder writes summary.json before review. Refresh it here so
    # status readers cannot report a completed review as still awaiting input.
    (args.output_dir / "summary.json").write_text(rendered_summary, encoding="utf-8")
    if summary["status"] in {"passed", "passed_with_rejections"}:
        (args.output_dir / "trusted_manifests.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in compiled), encoding="utf-8"
        )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] in {"passed", "passed_with_rejections"} or args.allow_incomplete else 1


if __name__ == "__main__":
    raise SystemExit(main())
