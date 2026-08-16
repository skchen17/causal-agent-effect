"""Authority decisions directly over schema-native state deltas."""

from __future__ import annotations

import json
from typing import Any


def _payload_class(value: Any) -> str:
    return "restricted" if "secret-export" in json.dumps(value, sort_keys=True) else "routine"


def _allowed_prefix(value: str, prefixes: list[str]) -> bool:
    return any(value.startswith(prefix) for prefix in prefixes)


def _filesystem(row: dict[str, Any], deltas: list[dict[str, Any]], policy: dict[str, Any]) -> tuple[str, list[str]]:
    if not deltas:
        return "ALLOW", ["no_native_change"]
    reasons = []
    removed = [item for item in deltas if item["kind"] == "entry_removed"]
    added = [item for item in deltas if item["kind"] == "entry_added"]
    is_move = row["tool_name"] == "move_file" and len(removed) == 1 and len(added) == 1
    for delta in deltas:
        path = delta["path"]
        if not _allowed_prefix(path, policy["resource_prefixes"]):
            return "DENY", ["filesystem_resource_out_of_scope"]
        if is_move:
            if delta["kind"] == "entry_added" and not _allowed_prefix(path, policy["destination_prefixes"]):
                return "DENY", ["move_destination_out_of_scope"]
            semantic = "filesystem.entry.move"
        elif delta["kind"] == "entry_added":
            semantic = "filesystem.directory.create" if delta["value"]["kind"] == "directory" else "filesystem.file.create"
        elif delta["kind"] == "entry_changed":
            semantic = "filesystem.file.edit" if row["tool_name"] == "edit_file" else "filesystem.file.overwrite"
        else:
            return "DENY", ["native_removal_not_granted"]
        if semantic not in policy["operations"]:
            return "DENY", ["filesystem_operation_not_granted"]
        value = delta.get("after", delta.get("value", {}))
        if value.get("kind") == "file" and _payload_class(value.get("text", "")) not in policy["payload_classes"]:
            return "DENY", ["restricted_payload"]
        reasons.append("filesystem_grant_satisfied")
    return "ALLOW", reasons


def _sqlite(deltas: list[dict[str, Any]], policy: dict[str, Any]) -> tuple[str, list[str]]:
    if not deltas:
        return "ALLOW", ["no_native_change"]
    operation = {"row_added": "sqlite.record.create", "row_changed": "sqlite.record.update",
                 "row_removed": "sqlite.record.delete"}
    reasons = []
    for delta in deltas:
        if delta["table"] not in policy["tables"] or operation[delta["kind"]] not in policy["operations"]:
            return "DENY", ["sqlite_scope_or_operation_not_granted"]
        value = delta.get("after", delta.get("value", {}))
        if value.get("owner") not in policy["principals"]:
            return "DENY", ["principal_out_of_scope"]
        if value.get("visibility") not in policy["visibilities"]:
            return "DENY", ["visibility_out_of_scope"]
        reasons.append("sqlite_grant_satisfied")
    return "ALLOW", reasons


def _memory(deltas: list[dict[str, Any]], policy: dict[str, Any]) -> tuple[str, list[str]]:
    if not deltas:
        return "ALLOW", ["no_native_change"]
    operation = {"entity_added": "memory.entity.create", "entity_removed": "memory.entity.delete",
                 "entity_changed": "memory.observation.add", "relation_added": "memory.relation.create",
                 "relation_removed": "memory.relation.delete"}
    reasons = []
    for delta in deltas:
        semantic = operation[delta["kind"]]
        if semantic not in policy["operations"]:
            return "DENY", ["memory_operation_not_granted"]
        names = [delta.get("name")] if delta["kind"].startswith("entity_") else [delta["from"], delta["to"]]
        if not all(name is not None and _allowed_prefix(name, policy["entity_prefixes"]) for name in names):
            return "DENY", ["memory_principal_out_of_scope"]
        if delta["kind"] in {"entity_added", "entity_changed"}:
            value = delta.get("after", delta.get("value", {}))
            observations = value.get("observations", [])
            if _payload_class(observations) not in policy["payload_classes"]:
                return "DENY", ["restricted_payload"]
        reasons.append("memory_grant_satisfied")
    return "ALLOW", reasons


def authorize_native(row: dict[str, Any], deltas: list[dict[str, Any]], manifest: dict[str, Any]) -> tuple[str, list[str]]:
    if row["source"] == "filesystem":
        return _filesystem(row, deltas, manifest["filesystem"])
    if row["source"] == "sqlite":
        return _sqlite(deltas, manifest["sqlite"])
    if row["source"] == "memory":
        return _memory(deltas, manifest["memory"])
    raise ValueError(row["source"])

