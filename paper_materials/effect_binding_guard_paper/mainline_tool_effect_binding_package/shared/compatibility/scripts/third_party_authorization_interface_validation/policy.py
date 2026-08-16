"""Independent resource/subject/operation authority model for third-party tools.

Policies are written over resource namespaces and operation constraints. They
are not lists of effects selected from evaluation cases.
"""

from __future__ import annotations

from typing import Any


OPERATIONS = {
    "filesystem": {
        "filesystem.directory.create", "filesystem.file.create", "filesystem.file.overwrite",
        "filesystem.file.edit", "filesystem.entry.move",
    },
    "sqlite": {"sqlite.record.create", "sqlite.record.update", "sqlite.record.delete"},
    "memory": {"memory.entity.create", "memory.entity.delete", "memory.observation.add", "memory.relation.create"},
}


def authority_manifest() -> dict[str, Any]:
    return {
        "subject": "agent:validator",
        "filesystem": {
            "resource_prefixes": ["team/"], "destination_prefixes": ["team/"],
            # Overwrite is intentionally not delegated; create/edit are. This
            # makes existence in trusted pre-state authorization-relevant.
            "operations": sorted(OPERATIONS["filesystem"] - {"filesystem.file.overwrite"}),
            "payload_classes": ["routine"],
        },
        "sqlite": {
            "tables": ["records"], "principals": ["alice", "bob"],
            "visibilities": ["internal", "private"], "operations": sorted(OPERATIONS["sqlite"]),
        },
        "memory": {
            "entity_prefixes": ["team:"], "operations": sorted(OPERATIONS["memory"]),
            "payload_classes": ["routine"],
        },
    }


def _need(value: Any, reason: str, partial: bool) -> tuple[str, str] | None:
    if value is None:
        return ("ABSTAIN", reason) if partial else ("DENY", reason)
    return None


def authorize_effect(effect: dict[str, Any], manifest: dict[str, Any], *, partial: bool) -> tuple[str, str]:
    operation = effect.get("operation")
    resource = effect.get("resource_id")
    for value, reason in ((operation, "operation_unobservable"), (resource, "resource_unobservable")):
        missing = _need(value, reason, partial)
        if missing:
            return missing
    attributes = effect.get("attributes")
    if not isinstance(attributes, dict):
        return ("ABSTAIN", "attributes_unobservable") if partial else ("DENY", "malformed_attributes")

    if operation.startswith("filesystem."):
        policy = manifest["filesystem"]
        if operation not in policy["operations"]:
            return "DENY", "filesystem_operation_not_granted"
        if not any(resource.startswith(prefix) for prefix in policy["resource_prefixes"]):
            return "DENY", "filesystem_resource_out_of_scope"
        if operation == "filesystem.entry.move":
            destination = effect.get("target_principal") or attributes.get("destination")
            if destination is None:
                return ("ABSTAIN", "move_destination_unobservable") if partial else ("DENY", "missing_move_destination")
            if not any(destination.startswith(prefix) for prefix in policy["destination_prefixes"]):
                return "DENY", "move_destination_out_of_scope"
        if operation.startswith("filesystem.file"):
            payload = attributes.get("payload_class")
            if payload is None:
                return ("ABSTAIN", "payload_class_unobservable") if partial else ("DENY", "missing_payload_class")
            if payload not in policy["payload_classes"]:
                return "DENY", "restricted_payload"
        return "ALLOW", "filesystem_grant_satisfied"

    if operation.startswith("sqlite."):
        policy = manifest["sqlite"]
        if operation not in policy["operations"]:
            return "DENY", "sqlite_operation_not_granted"
        table = attributes.get("table")
        target = effect.get("target_principal")
        visibility = attributes.get("visibility")
        for value, reason in ((table, "table_unobservable"), (target, "owner_unobservable"),
                              (visibility, "visibility_unobservable")):
            missing = _need(value, reason, partial)
            if missing:
                return missing
        if table not in policy["tables"]:
            return "DENY", "table_out_of_scope"
        if target not in policy["principals"]:
            return "DENY", "principal_out_of_scope"
        if visibility not in policy["visibilities"]:
            return "DENY", "visibility_out_of_scope"
        return "ALLOW", "sqlite_grant_satisfied"

    if operation.startswith("memory."):
        policy = manifest["memory"]
        if operation not in policy["operations"]:
            return "DENY", "memory_operation_not_granted"
        names = [effect.get("target_principal")]
        if operation == "memory.relation.create":
            names.append(attributes.get("source_entity"))
        for name in names:
            missing = _need(name, "memory_principal_unobservable", partial)
            if missing:
                return missing
            if not any(name.startswith(prefix) for prefix in policy["entity_prefixes"]):
                return "DENY", "memory_principal_out_of_scope"
        if operation in {"memory.entity.create", "memory.observation.add"}:
            payload = attributes.get("payload_class")
            if payload is None:
                return ("ABSTAIN", "payload_class_unobservable") if partial else ("DENY", "missing_payload_class")
            if payload not in policy["payload_classes"]:
                return "DENY", "restricted_payload"
        return "ALLOW", "memory_grant_satisfied"
    return "DENY", "unknown_operation_family"


def authorize_all(effects: list[dict[str, Any]], manifest: dict[str, Any], *, partial: bool,
                  inventory_complete: bool = True) -> tuple[str, list[str]]:
    if not effects:
        return (("ALLOW", ["no_committed_effect"]) if inventory_complete
                else ("ABSTAIN", ["effect_inventory_unobservable"]))
    reasons: list[str] = []
    saw_abstain = False
    for effect in effects:
        decision, reason = authorize_effect(effect, manifest, partial=partial)
        reasons.append(reason)
        if decision == "DENY":
            return "DENY", reasons
        if decision == "ABSTAIN":
            saw_abstain = True
    return ("ABSTAIN", reasons) if saw_abstain else ("ALLOW", reasons)
