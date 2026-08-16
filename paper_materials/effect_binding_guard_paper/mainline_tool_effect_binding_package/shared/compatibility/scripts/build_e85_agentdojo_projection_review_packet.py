#!/usr/bin/env python3
"""Build an immutable AgentDojo security-effect projection review packet."""

from __future__ import annotations

import hashlib
import importlib.metadata
import inspect
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentdojo.task_suite.load_suites import get_suite


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evaluation/e85_security_effect_projections"
RESULTS = ROOT / "analysis/results"
DESCRIPTORS = RESULTS / "e77_registered_effect_diff_descriptors.jsonl"
FIELD_EVIDENCE = RESULTS / "e77_agentdojo_field_effect_diff.json"
SUITES = ("workspace", "slack", "travel", "banking")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return sha256_bytes(encoded)


def projection(
    projection_id: str,
    effect: str,
    operation: str,
    resource: str,
    target: str,
    dependencies: list[str],
    *,
    visibility: str = "literal:private",
    commit_mode: str = "literal:commit",
    expansion: str = "single",
    trigger: str = "always",
    note: str = "",
) -> dict[str, Any]:
    return {
        "projection_id": projection_id,
        "effect": effect,
        "operation": operation,
        "resource_binding": resource,
        "target_binding": target,
        "visibility_binding": visibility,
        "commit_mode_binding": commit_mode,
        "provenance_binding": "runtime:provenance",
        "control_source_binding": "runtime:control_source",
        "security_relevant_parameters": dependencies,
        "expansion": expansion,
        "trigger": trigger,
        "candidate_note": note,
    }


def candidate_projections() -> dict[str, list[dict[str, Any]]]:
    """Source-informed hypotheses for independent review, not trusted contracts."""
    return {
        "send_email": [
            projection(
                "message_delivery", "message_delivered", "send", "derived:message_payload",
                "each_union:param:recipients,param:cc,param:bcc",
                ["recipients", "subject", "body", "cc", "bcc"], expansion="per_target",
            ),
            projection(
                "attachment_disclosure", "attachment_disclosed", "disclose",
                "each:param:attachments", "each_union:param:recipients,param:cc,param:bcc",
                ["attachments", "recipients", "cc", "bcc"], expansion="cross_product",
                trigger="when_nonempty:param:attachments",
            ),
        ],
        "delete_email": [
            projection("email_delete", "email_deleted", "delete", "param:email_id", "literal:account_owner", ["email_id"]),
        ],
        "create_calendar_event": [
            projection(
                "event_create", "calendar_event_created", "create", "created:return:id",
                "literal:calendar_owner", ["title", "start_time", "end_time", "description", "participants", "location"],
            ),
            projection(
                "event_invitation", "calendar_invitation_sent", "notify", "created:return:id",
                "each:param:participants", ["title", "description", "participants"], expansion="per_target",
                trigger="when_nonempty:param:participants",
            ),
        ],
        "cancel_calendar_event": [
            projection("event_cancel", "calendar_event_cancelled", "cancel", "param:event_id", "literal:calendar_owner", ["event_id"]),
            projection(
                "cancel_notice", "calendar_cancellation_notice_sent", "notify", "param:event_id",
                "each:state:calendar.events[param:event_id].participants", ["event_id"], expansion="per_target",
            ),
        ],
        "reschedule_calendar_event": [
            projection(
                "event_reschedule", "calendar_event_rescheduled", "reschedule", "param:event_id",
                "literal:calendar_owner", ["event_id", "new_start_time", "new_end_time"],
            ),
            projection(
                "reschedule_notice", "calendar_reschedule_notice_sent", "notify", "param:event_id",
                "each:state:calendar.events[param:event_id].participants",
                ["event_id", "new_start_time", "new_end_time"], expansion="per_target",
            ),
        ],
        "add_calendar_event_participants": [
            projection(
                "participant_add", "calendar_participant_added", "add_participant", "param:event_id",
                "each:param:participants", ["event_id", "participants"], expansion="per_target",
                note="The v1.1.2 implementation mutates participants but does not itself send the email claimed by its docstring.",
            ),
        ],
        "append_to_file": [
            projection("file_append", "file_content_appended", "append", "param:file_id", "literal:file_owner", ["file_id", "content"]),
        ],
        "create_file": [
            projection("file_create", "file_created", "create", "created:return:id", "literal:drive_owner", ["filename", "content"]),
        ],
        "delete_file": [
            projection("file_delete", "file_deleted", "delete", "param:file_id", "literal:drive_owner", ["file_id"]),
        ],
        "share_file": [
            projection(
                "file_share", "file_permission_granted", "share", "param:file_id", "param:email",
                ["file_id", "email", "permission"], visibility="param:permission",
            ),
        ],
        "add_user_to_channel": [
            projection("channel_membership_add", "channel_membership_granted", "add_member", "param:channel", "param:user", ["channel", "user"], visibility="literal:channel_scoped"),
        ],
        "send_direct_message": [
            projection("direct_message", "direct_message_delivered", "send", "derived:message_payload", "param:recipient", ["recipient", "body"]),
        ],
        "send_channel_message": [
            projection("channel_message", "channel_message_posted", "post", "derived:message_payload", "param:channel", ["channel", "body"], visibility="literal:channel_scoped"),
        ],
        "invite_user_to_slack": [
            projection("workspace_invite", "workspace_user_created", "invite", "literal:slack_workspace", "param:user", ["user", "user_email"]),
        ],
        "remove_user_from_slack": [
            projection("workspace_remove", "workspace_user_removed", "remove", "literal:slack_workspace", "param:user", ["user"]),
        ],
        "get_webpage": [
            projection("network_read", "external_network_request", "read", "param:url", "derived:remote_endpoint", ["url"], visibility="literal:external"),
        ],
        "post_webpage": [
            projection("web_publish", "web_content_published", "publish", "param:url", "derived:remote_endpoint", ["url", "content"], visibility="literal:public"),
        ],
        "reserve_hotel": [
            projection("hotel_reservation", "hotel_reserved", "reserve", "param:hotel", "literal:account_user", ["hotel", "start_day", "end_day"]),
        ],
        "reserve_car_rental": [
            projection("car_reservation", "car_rental_reserved", "reserve", "param:company", "literal:account_user", ["company", "start_time", "end_time"]),
        ],
        "reserve_restaurant": [
            projection("restaurant_reservation", "restaurant_reserved", "reserve", "param:restaurant", "literal:account_user", ["restaurant", "start_time"]),
        ],
        "send_money": [
            projection("money_transfer", "funds_transferred", "transfer", "derived:account_funds[param:amount]", "param:recipient", ["recipient", "amount", "subject", "date"]),
        ],
        "schedule_transaction": [
            projection("scheduled_transfer", "funds_transfer_scheduled", "schedule", "derived:account_funds[param:amount]", "param:recipient", ["recipient", "amount", "subject", "date", "recurring"], commit_mode="literal:scheduled"),
        ],
        "update_scheduled_transaction": [
            projection("scheduled_transfer_update", "scheduled_transfer_modified", "modify", "param:id", "derived:scheduled_recipient", ["id", "recipient", "amount", "subject", "date", "recurring"], commit_mode="literal:scheduled"),
        ],
        "update_password": [
            projection("password_update", "account_credential_changed", "update", "literal:user_account", "literal:account_owner", ["password"]),
        ],
        "update_user_info": [
            projection("profile_update", "account_profile_changed", "update", "literal:user_account", "literal:account_owner", ["first_name", "last_name", "street", "city"]),
        ],
    }


def immutable_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"review", "candidate_payload_sha256"}}


def candidate_payload_hash(row: dict[str, Any]) -> str:
    return json_hash(immutable_payload(row))


def safe_default(field: Any) -> Any:
    if field.is_required():
        return None
    value = field.default
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return {"non_json_default_type": type(value).__name__}
    return value


def relative_agentdojo_path(path: Path, package_root: Path) -> str:
    return str(Path("agentdojo") / path.resolve().relative_to(package_root.resolve()))


def build() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    descriptors = {row["tool_name"]: row for row in read_jsonl(DESCRIPTORS)}
    findings = json.loads(FIELD_EVIDENCE.read_text(encoding="utf-8"))["findings"]
    finding_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for finding in findings:
        finding_index.setdefault((finding["suite"], finding["tool_name"]), []).append(finding)
    hypotheses = candidate_projections()
    if set(hypotheses) != set(descriptors):
        raise RuntimeError(
            f"projection/tool mismatch: missing={sorted(set(descriptors)-set(hypotheses))}, "
            f"extra={sorted(set(hypotheses)-set(descriptors))}"
        )

    import agentdojo

    package_root = Path(agentdojo.__file__).resolve().parent
    rows: list[dict[str, Any]] = []
    source_files: dict[str, dict[str, Any]] = {}
    for suite_name in SUITES:
        suite = get_suite("v1.1.2", suite_name)
        for tool in suite.tools:
            if tool.name not in descriptors:
                continue
            source_path = Path(inspect.getsourcefile(tool.run) or "")
            source_lines, start_line = inspect.getsourcelines(tool.run)
            source_text = "".join(source_lines)
            source_relative = relative_agentdojo_path(source_path, package_root)
            source_files[source_relative] = {
                "sha256": sha256_bytes(source_path.read_bytes()),
                "size_bytes": source_path.stat().st_size,
            }
            descriptor = descriptors[tool.name]
            schema_fields = []
            for name, field in tool.parameters.model_fields.items():
                schema_fields.append({
                    "name": name,
                    "required": field.is_required(),
                    "default": safe_default(field),
                    "annotation": str(field.annotation),
                    "description": field.description or "",
                    "candidate_security_role": descriptor.get("field_roles", {}).get(name, "unclassified"),
                })
            evidence = []
            for finding in finding_index.get((suite_name, tool.name), []):
                evidence.append({key: finding.get(key) for key in (
                    "field", "required", "status", "evidence", "base_error", "mutated_error"
                )})
            candidate_templates = hypotheses[tool.name]
            review = {
                "reviewer_anonymous_id": "",
                "review_date": "",
                "implementation_inspected": False,
                "state_mutation_paths_verified": False,
                "defaults_reviewed": False,
                "interactions_reviewed": False,
                "expansions_reviewed": False,
                "negative_controls_reviewed": False,
                "no_attack_outcomes_or_method_labels_used": False,
                "no_missing_security_effects_confirmed": False,
                "overall_decision": "PENDING",
                "rationale": "",
                "field_reviews": [
                    {"field": item["name"], "decision": "PENDING", "role": "", "rationale": ""}
                    for item in schema_fields
                ],
                "projection_reviews": [
                    {"projection_id": item["projection_id"], "decision": "PENDING", "rationale": ""}
                    for item in candidate_templates
                ],
                "notes": "",
            }
            row = {
                "review_packet_version": "e85_agentdojo_security_effect_projection_v1",
                "agentdojo_benchmark_version": "v1.1.2",
                "installed_agentdojo_distribution_version": importlib.metadata.version("agentdojo"),
                "suite": suite_name,
                "tool_name": tool.name,
                "tool_instance_key": f"{suite_name}/{tool.name}",
                "tool_description": tool.description,
                "schema_fields": schema_fields,
                "source_evidence": {
                    "module": tool.run.__module__,
                    "relative_path": source_relative,
                    "function_name": tool.run.__name__,
                    "start_line": start_line,
                    "end_line": start_line + len(source_lines) - 1,
                    "source_file_sha256": source_files[source_relative]["sha256"],
                    "function_source_sha256": sha256_bytes(source_text.encode()),
                    "function_source": source_text,
                },
                "candidate_effect_projections": candidate_templates,
                "candidate_field_counterfactual_evidence": evidence,
                "candidate_descriptor_source_sha256": json_hash(descriptor),
                "forbidden_hidden_evidence_present": False,
                "review": review,
            }
            row["candidate_payload_sha256"] = candidate_payload_hash(row)
            rows.append(row)

    rows.sort(key=lambda item: (SUITES.index(item["suite"]), item["tool_name"]))
    freeze_manifest = {
        "artifact_type": "e85_agentdojo_source_freeze",
        "agentdojo_benchmark_version": "v1.1.2",
        "installed_agentdojo_distribution_version": importlib.metadata.version("agentdojo"),
        "source_files": dict(sorted(source_files.items())),
        "descriptor_artifact": {
            "relative_path": str(DESCRIPTORS.relative_to(ROOT)),
            "sha256": sha256_bytes(DESCRIPTORS.read_bytes()),
        },
        "field_evidence_artifact": {
            "relative_path": str(FIELD_EVIDENCE.relative_to(ROOT)),
            "sha256": sha256_bytes(FIELD_EVIDENCE.read_bytes()),
        },
        "tool_instance_keys": [row["tool_instance_key"] for row in rows],
        "packet_payload_sha256": json_hash([immutable_payload(row) for row in rows]),
    }
    summary = {
        "experiment": "E85-AgentDojo-projection-review",
        "status": "awaiting_external_human_review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agentdojo_benchmark_version": "v1.1.2",
        "n_tool_instances": len(rows),
        "n_unique_tools": len({row["tool_name"] for row in rows}),
        "n_candidate_projections": sum(len(row["candidate_effect_projections"]) for row in rows),
        "n_schema_fields": sum(len(row["schema_fields"]) for row in rows),
        "suite_counts": dict(sorted(Counter(row["suite"] for row in rows).items())),
        "reviewed_tool_instances": 0,
        "approved_tool_instances": 0,
        "source_freeze_sha256": json_hash(freeze_manifest),
        "claim_boundary": (
            "The packet freezes source-informed candidate projections for independent review. "
            "It contains no attack outcomes or method decisions and does not certify any projection before review."
        ),
    }
    return rows, summary, freeze_manifest


def main() -> int:
    rows, summary, freeze_manifest = build()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    rendered = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    (OUTPUT / "review_packet.template.jsonl").write_text(rendered, encoding="utf-8")
    (OUTPUT / "projection_catalog.jsonl").write_text(rendered, encoding="utf-8")
    (OUTPUT / "source_freeze_manifest.json").write_text(
        json.dumps(freeze_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (RESULTS / "e85_agentdojo_projection_review_status.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E85 AgentDojo Projection Review Status", "",
        f"Status: `{summary['status']}`.", "",
        f"- Tool instances: `{summary['n_tool_instances']}` across `{summary['n_unique_tools']}` unique tools.",
        f"- Candidate projections: `{summary['n_candidate_projections']}`.",
        f"- Schema fields requiring classification: `{summary['n_schema_fields']}`.",
        f"- Source freeze SHA-256: `{summary['source_freeze_sha256']}`.",
        f"- Reviewed instances: `0/{summary['n_tool_instances']}`; approved instances: `0`.",
        "", "## Claim Boundary", "", summary["claim_boundary"], "",
    ]
    (RESULTS / "e85_agentdojo_projection_review_status.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
