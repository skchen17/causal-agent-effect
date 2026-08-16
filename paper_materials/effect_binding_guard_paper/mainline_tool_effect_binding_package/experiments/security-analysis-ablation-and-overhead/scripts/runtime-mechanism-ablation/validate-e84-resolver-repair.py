#!/usr/bin/env python3
"""Validate independently reviewed E84 resolver repairs by sandbox execution."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir()
)
sys.path.insert(0, str(ROOT / "code"))

from src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime import (  # noqa: E402
    ResolverSpec,
    build_typed_resolver_ledger_entry,
    compile_trusted_interface,
)


E84 = ROOT / "experiments/human-authority-and-causal-validation/evaluation/authority-manifest-human-review"
TEMPLATE = E84 / "runtime_repair_packet.template.jsonl"
TRUSTED = E84 / "trusted_manifests.jsonl"
CATALOG = E84 / "resolver_catalog.json"
RESULTS = ROOT / "experiments/security-analysis-ablation-and-overhead/results/runtime-mechanism-ablation"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed", type=Path, default=E84 / "runtime_repair_packet.reviewed.jsonl")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def payload_hash(row: dict[str, Any]) -> str:
    frozen = {key: value for key, value in row.items() if key not in {"human_review", "candidate_payload_sha256"}}
    return hashlib.sha256(
        json.dumps(frozen, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def build_spec(resolver_id: str, raw: dict[str, Any]) -> ResolverSpec:
    query = raw["query_constraint"]
    projection = raw["output_projection"]
    return ResolverSpec(
        resolver_id=resolver_id,
        read_tool=raw["read_tool"],
        query_arguments=query["arguments"],
        allow_additional_arguments=query["allow_additional_arguments"],
        projection_kind=projection["kind"],
        projection_field=projection.get("field", ""),
        max_cardinality=raw["max_cardinality"],
    )


def concrete_arguments(spec: ResolverSpec) -> tuple[dict[str, Any] | None, list[str]]:
    arguments: dict[str, Any] = {}
    errors: list[str] = []
    for field, constraint in spec.query_arguments.items():
        mode = constraint.get("mode")
        if mode == "forbidden":
            continue
        values = constraint.get("values")
        if mode != "exact" or not isinstance(values, list) or len(values) != 1:
            errors.append(f"query_not_singleton_exact:{field}")
        else:
            arguments[field] = values[0]
    return (arguments if not errors else None), errors


def main() -> int:
    args = parse_args()
    template = read_jsonl(TEMPLATE)
    templates = {(row["suite"], row["user_task_id"], row["resolver_id"]): row for row in template}
    reviewed = read_jsonl(args.reviewed) if args.reviewed.exists() else template
    trusted = read_jsonl(TRUSTED)
    resolver_catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    errors: list[str] = []
    decisions: dict[tuple[str, str, str], dict[str, Any]] = {}
    validated_approvals: dict[tuple[str, str, str], dict[str, Any]] = {}
    suite_cache: dict[str, tuple[Any, FunctionsRuntime]] = {}

    if len(reviewed) != len(template):
        errors.append(f"review_row_count_mismatch:{len(reviewed)}!={len(template)}")

    for row in reviewed:
        key = (row.get("suite"), row.get("user_task_id"), row.get("resolver_id"))
        original = templates.get(key)
        prefix = "/".join(str(item) for item in key)
        if original is None:
            errors.append(f"{prefix}:unknown_review_row")
            continue
        if row.get("candidate_payload_sha256") != original.get("candidate_payload_sha256"):
            errors.append(f"{prefix}:candidate_hash_changed")
            continue
        if payload_hash(row) != row.get("candidate_payload_sha256"):
            errors.append(f"{prefix}:immutable_candidate_payload_changed")
            continue
        review = row.get("human_review")
        if not isinstance(review, dict):
            errors.append(f"{prefix}:human_review_missing")
            continue
        decision = review.get("decision")
        if decision == "PENDING":
            errors.append(f"{prefix}:review_pending")
            continue
        if decision not in {"APPROVE", "REJECT"}:
            errors.append(f"{prefix}:invalid_decision")
            continue
        if not all(isinstance(review.get(field), str) and review.get(field).strip() for field in (
            "rationale", "reviewer_anonymous_id", "review_date"
        )):
            errors.append(f"{prefix}:review_metadata_incomplete")
            continue
        decisions[key] = review
        if decision == "REJECT":
            continue
        if review.get("original_task_only_and_schema_observation_confirmed") is not True:
            errors.append(f"{prefix}:review_scope_not_confirmed")
            continue
        raw = review.get("repaired_resolver")
        try:
            spec = build_spec(str(key[2]), raw)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{prefix}:resolver_schema_invalid:{exc}")
            continue
        suite_name = str(key[0])
        tool_catalog = resolver_catalog["suites"][suite_name].get(spec.read_tool)
        if not tool_catalog or tool_catalog.get("eligible_as_authorized_read") is not True:
            errors.append(f"{prefix}:read_tool_not_eligible")
            continue
        query_args, query_errors = concrete_arguments(spec)
        if query_errors:
            errors.extend(f"{prefix}:{error}" for error in query_errors)
            continue
        assert query_args is not None
        parameter_fields = set(tool_catalog["parameter_fields"])
        required_fields = set(tool_catalog["required_parameter_fields"])
        if set(query_args) - parameter_fields or required_fields - set(query_args):
            errors.append(f"{prefix}:query_arguments_do_not_match_tool_schema")
            continue
        if suite_name not in suite_cache:
            suite = get_suite("v1.1.2", suite_name)
            suite_cache[suite_name] = (suite, FunctionsRuntime(suite.tools))
        suite, runtime = suite_cache[suite_name]
        task = suite.user_tasks[str(key[1])]
        environment = task.init_environment(suite.load_and_inject_default_environment({}))
        value, runtime_error = runtime.run_function(copy.deepcopy(environment), spec.read_tool, query_args)
        if runtime_error is not None:
            errors.append(f"{prefix}:sandbox_query_failed:{runtime_error}")
            continue
        entry = build_typed_resolver_ledger_entry(
            spec,
            tool_name=spec.read_tool,
            arguments=query_args,
            result=value,
        )
        if entry is None:
            errors.append(f"{prefix}:typed_projection_failed")
            continue
        validated_approvals[key] = review

    compiled: list[dict[str, Any]] = []
    exact_only: list[dict[str, Any]] = []
    for manifest in trusted:
        key_prefix = (manifest["suite"], manifest["user_task_id"])
        transform_present = any(
            binding.get("canonical_transform")
            for fields in manifest.get("authority_tools", {}).values()
            for binding in fields.values()
        )
        resolver_ids = set(manifest.get("resolver_specs", {}))
        if transform_present:
            continue
        if resolver_ids:
            manifest_approvals = [validated_approvals.get((*key_prefix, resolver_id)) for resolver_id in resolver_ids]
            if not manifest_approvals or any(approval is None for approval in manifest_approvals):
                continue
            candidate = copy.deepcopy(manifest)
            candidate["resolver_specs"] = {
                resolver_id: validated_approvals[(*key_prefix, resolver_id)]["repaired_resolver"]
                for resolver_id in resolver_ids
            }
        else:
            candidate = manifest
        try:
            compile_trusted_interface(candidate)
        except ValueError as exc:
            errors.append(f"{key_prefix[0]}/{key_prefix[1]}:compiled_manifest_invalid:{exc}")
            continue
        compiled.append(candidate)
        if not resolver_ids:
            exact_only.append(candidate)

    pending = sum(error.endswith(":review_pending") for error in errors)
    non_pending_errors = len(errors) - pending
    reviewer_type_counts: dict[str, int] = {}
    for review in decisions.values():
        reviewer_type = str(review.get("reviewer_type", "unspecified"))
        reviewer_type_counts[reviewer_type] = reviewer_type_counts.get(reviewer_type, 0) + 1
    status = "blocked_by_pending_review" if pending else ("failed" if non_pending_errors else "passed_with_rejections")
    report = {
        "experiment": "E84-resolver-runtime-repair-validation",
        "status": status,
        "template_rows": len(template),
        "reviewed_rows": len(reviewed),
        "decision_counts": {
            decision: sum(review.get("decision") == decision for review in decisions.values())
            for decision in ("APPROVE", "REJECT")
        },
        "validated_approvals": len(validated_approvals),
        "reviewer_type_counts": reviewer_type_counts,
        "pending_rows": pending,
        "non_pending_errors": non_pending_errors,
        "errors": errors,
        "runtime_ready_trusted_manifests_after_full_review": len(compiled) if not errors else 0,
        "runtime_ready_exact_only_manifests": len(exact_only),
        "real_external_side_effects": False,
        "claim_boundary": (
            "A passing validator establishes immutable review provenance and executable typed projections in clean "
            "AgentDojo sandbox states. It does not establish attack robustness, production safety, or correctness "
            "outside the reviewed task and query contracts."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e84-resolver-repair-validation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output = E84 / "runtime_ready_trusted_manifests.jsonl"
    exact_only_output = E84 / "runtime_ready_exact_only_manifests.jsonl"
    exact_only_output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in exact_only), encoding="utf-8"
    )
    if status == "passed_with_rejections":
        output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in compiled), encoding="utf-8")
    elif output.exists():
        output.unlink()
    print(json.dumps({key: report[key] for key in (
        "status", "template_rows", "reviewed_rows", "decision_counts", "pending_rows",
        "non_pending_errors", "runtime_ready_trusted_manifests_after_full_review",
        "runtime_ready_exact_only_manifests"
    )}, indent=2))
    return 0 if status == "passed_with_rejections" else 1


if __name__ == "__main__":
    raise SystemExit(main())
