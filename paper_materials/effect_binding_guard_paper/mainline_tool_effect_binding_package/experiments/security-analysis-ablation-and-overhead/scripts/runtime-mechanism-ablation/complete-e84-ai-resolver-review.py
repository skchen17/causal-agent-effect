#!/usr/bin/env python3
"""Complete the E84 resolver packet as a label-hidden AI artifact review."""

from __future__ import annotations

import json
import collections
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir()
)
E84 = ROOT / "experiments/human-authority-and-causal-validation/evaluation/authority-manifest-human-review"
TEMPLATE = E84 / "runtime_repair_packet.template.jsonl"
OUTPUT = E84 / "runtime_repair_packet.reviewed.jsonl"
RESULTS = ROOT / "experiments/security-analysis-ablation-and-overhead/results/runtime-mechanism-ablation"


APPROVALS: dict[tuple[str, str, str], dict[str, Any]] = {
    (
        "workspace",
        "user_task_34",
        "resolve::append_to_file::file_id",
    ): {
        "rationale": (
            "The original task identifies the existing grocery list. The fixed query returns one structured "
            "CloudDriveFile, and id_ directly binds append_to_file.file_id without interpreting file content."
        ),
        "query_arguments": {"query": {"mode": "exact", "values": ["grocery list"]}},
        "projection_kind": "record_list_field",
        "projection_field": "id_",
    },
    (
        "workspace",
        "user_task_8",
        "resolve::add_calendar_event_participants::event_id",
    ): {
        "rationale": (
            "The original task gives the event title and date. The repaired exact query returns one structured "
            "CalendarEvent, and id_ directly binds add_calendar_event_participants.event_id."
        ),
        "query_arguments": {
            "date": {"mode": "exact", "values": ["2024-05-15"]},
            "query": {"mode": "exact", "values": ["Introductory meeting"]},
        },
        "projection_kind": "record_list_field",
        "projection_field": "id_",
    },
}


def rejection_rationale(row: dict[str, Any]) -> str:
    observation = row["runtime_observation"]
    target = row["target_bindings"][0]
    task_id = (row["suite"], row["user_task_id"])
    shape = observation.get("result_shape")
    if shape == "str":
        return (
            "The authorized read returns unstructured text. No independently reviewed deterministic parser maps "
            f"that text to {target['tool_name']}.{target['field']}; approving it would treat free text as authority."
        )
    if task_id == ("workspace", "user_task_13"):
        return (
            "The searched email is an unstructured delegated instruction. A record-field projection cannot derive "
            f"{target['tool_name']}.{target['field']} from its body without a separately reviewed parser and policy."
        )
    if row["suite"] == "banking" and shape == "list[Transaction]":
        return (
            "The query returns a broad transaction history. The resolver DSL has no independently justified row "
            f"selector linking one transaction to {target['tool_name']}.{target['field']}."
        )
    if shape == "list[Message]":
        return (
            "The query returns one or more messages, but the target requires selecting or interpreting message "
            f"content rather than directly projecting a uniquely identified field to {target['tool_name']}.{target['field']}."
        )
    if target["field"] in {"start_time", "end_time", "new_start_time"}:
        return (
            "The target time is computed from the requested schedule and availability; it is not a direct field of "
            "the read result, and the current resolver DSL has no reviewed computation for that derivation."
        )
    if target["field"] in {"content", "body", "subject", "filename", "recipients", "email", "permission"}:
        return (
            f"The target {target['tool_name']}.{target['field']} requires generation, interpretation, or a separate "
            "canonical binding; the observed read result does not provide a direct typed projection."
        )
    if target["field"] in {"participants", "attachments"}:
        return (
            f"The target {target['tool_name']}.{target['field']} is nested/list-valued. The current scalar projection "
            "contract cannot preserve its structure and cardinality, so the binding is not executable."
        )
    if observation.get("runtime_error"):
        return (
            "The reviewed query does not execute in the clean task state. No uniquely justified replacement query "
            "and direct typed projection can be established from the original task and schema alone."
        )
    return (
        f"The read result does not directly and uniquely bind {target['tool_name']}.{target['field']} under the "
        "current typed projection DSL; additional selection, parsing, or workflow state would be required."
    )


def rejection_category(row: dict[str, Any]) -> str:
    observation = row["runtime_observation"]
    target = row["target_bindings"][0]
    task_id = (row["suite"], row["user_task_id"])
    shape = observation.get("result_shape")
    if shape == "str":
        return "unstructured_text_without_reviewed_parser"
    if task_id == ("workspace", "user_task_13"):
        return "delegated_unstructured_instruction"
    if row["suite"] == "banking" and shape == "list[Transaction]":
        return "broad_history_without_row_selector"
    if shape == "list[Message]":
        return "message_selection_or_interpretation_required"
    if target["field"] in {"start_time", "end_time", "new_start_time"}:
        return "derived_value_without_reviewed_computation"
    if target["field"] in {"content", "body", "subject", "filename", "recipients", "email", "permission"}:
        return "generation_interpretation_or_canonical_binding_required"
    if target["field"] in {"participants", "attachments"}:
        return "nested_value_not_supported_by_scalar_projection"
    if observation.get("runtime_error"):
        return "query_not_executable_in_clean_task_state"
    return "no_direct_unique_typed_binding"


def main() -> int:
    rows = [json.loads(line) for line in TEMPLATE.read_text(encoding="utf-8").splitlines() if line.strip()]
    counts = {"APPROVE": 0, "REJECT": 0}
    categories: collections.Counter[str] = collections.Counter()
    suite_decisions: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for row in rows:
        key = (row["suite"], row["user_task_id"], row["resolver_id"])
        approval = APPROVALS.get(key)
        review = row["human_review"]
        review.update(
            {
                "decision": "APPROVE" if approval else "REJECT",
                "rationale": approval["rationale"] if approval else rejection_rationale(row),
                "original_task_only_and_schema_observation_confirmed": True,
                "reviewer_anonymous_id": "AI_ARTIFACT_REVIEW_01",
                "reviewer_type": "ai_artifact_reviewer",
                "review_method": (
                    "original task, public tool schema, result type/field names, and runtime error only; "
                    "no result values or benchmark outcome labels"
                ),
                "review_date": "2026-07-23",
            }
        )
        if approval:
            original = row["approved_resolver_before_runtime_audit"]
            review["repaired_resolver"] = {
                "read_tool": original["read_tool"],
                "query_constraint": {
                    "arguments": approval["query_arguments"],
                    "allow_additional_arguments": False,
                },
                "output_projection": {
                    "kind": approval["projection_kind"],
                    "field": approval["projection_field"],
                },
                "max_cardinality": 1,
            }
        counts[review["decision"]] += 1
        suite_decisions[row["suite"]][review["decision"]] += 1
        categories["approved_direct_typed_binding" if approval else rejection_category(row)] += 1
    OUTPUT.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    report = {
        "experiment": "E84-label-hidden-AI-resolver-artifact-review",
        "status": "completed",
        "reviewer_anonymous_id": "AI_ARTIFACT_REVIEW_01",
        "reviewer_type": "ai_artifact_reviewer",
        "review_date": "2026-07-23",
        "rows": len(rows),
        "decision_counts": counts,
        "category_counts": dict(sorted(categories.items())),
        "suite_decision_counts": {
            suite: dict(counter) for suite, counter in sorted(suite_decisions.items())
        },
        "evidence_available_to_reviewer": [
            "original_task",
            "target_binding",
            "approved_resolver_before_runtime_audit",
            "public_tool_schema",
            "runtime_result_type_and_field_names",
            "runtime_error_without_result_values",
        ],
        "evidence_not_used": [
            "runtime_result_values",
            "benchmark_utility",
            "attack_success",
            "gold_atoms",
            "gold_labels",
            "expected_decisions",
        ],
        "claim_boundary": (
            "This is a label-hidden AI artifact review, not an independent human review. Approval means only that "
            "the resolver has a direct typed binding justified by the original task and public schema; sandbox "
            "execution and projection validity are checked separately by the validator."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e84-ai-resolver-review-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E84 Label-Hidden AI Resolver Artifact Review",
        "",
        f"- Reviewer type: `{report['reviewer_type']}`",
        f"- Rows: `{len(rows)}`",
        f"- APPROVE: `{counts['APPROVE']}`",
        f"- REJECT: `{counts['REJECT']}`",
        "- Runtime result values used: `false`",
        "- Benchmark outcome labels used: `false`",
        "",
        "## Decision Categories",
        "",
    ]
    lines.extend(f"- `{category}`: `{count}`" for category, count in report["category_counts"].items())
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    (RESULTS / "e84-ai-resolver-review-report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "completed_ai_artifact_review", "rows": len(rows), **counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
