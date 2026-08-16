"""Compiler for frozen typed-effect descriptors.

The compiler predicts concrete effects from call arguments and pre-state. It is
implemented independently from source_oracle.py and never reads post-state.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _payload_class(value: Any) -> str:
    return "restricted" if "secret-export" in json.dumps(value, sort_keys=True) else "routine"


def _effect(operation: str, resource_type: str, resource_id: str, *, target: str | None = None,
            attributes: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "operation": operation, "resource_type": resource_type, "resource_id": resource_id,
        "target_principal": target, "attributes": attributes or {}, "commit_mode": "commit",
    }


def initial_descriptors() -> list[dict[str, Any]]:
    specifications = {
        "create_directory": (["filesystem.directory.create"], {"resource_id": "arguments.path"}, ["pre_state.entries"]),
        "write_file": (["filesystem.file.create", "filesystem.file.overwrite"],
                       {"resource_id": "arguments.path", "payload_class": "arguments.content"}, ["pre_state.entries"]),
        "edit_file": (["filesystem.file.edit"],
                      {"resource_id": "arguments.path", "payload_class": "arguments.edits", "commit": "arguments.dryRun"},
                      ["pre_state.entries"]),
        "move_file": (["filesystem.entry.move"],
                      {"resource_id": "arguments.source", "target_principal": "arguments.destination"}, ["pre_state.entries"]),
        "create_record": (["sqlite.record.create"],
                          {"resource_id": "arguments.table + allocated id", "target_principal": "arguments.data.owner",
                           "visibility": "arguments.data.visibility"}, ["pre_state.tables"]),
        "update_records": (["sqlite.record.update"],
                           {"resources": "rows matching arguments.conditions", "target_principal": "post-update owner",
                            "visibility": "post-update visibility"}, ["pre_state.tables"]),
        "delete_records": (["sqlite.record.delete"],
                           {"resources": "rows matching arguments.conditions", "target_principal": "pre-state owner",
                            "visibility": "pre-state visibility"}, ["pre_state.tables"]),
        "create_entities": (["memory.entity.create"],
                            {"resources": "arguments.entities[*].name", "payload_class": "arguments.entities[*].observations"},
                            ["pre_state.entities"]),
        "create_relations": (["memory.relation.create"],
                             {"resources": "arguments.relations[*]", "target_principal": "arguments.relations[*].to"}, []),
        "add_observations": (["memory.observation.add"],
                             {"resources": "arguments.observations[*].entityName",
                              "payload_class": "arguments.observations[*].contents[*]"}, []),
        "delete_entities": (["memory.entity.delete"],
                            {"resources": "arguments.entityNames[*]"}, ["pre_state.entities"]),
    }
    return [{
        "tool_name": tool, "schema_version": 2, "provenance": "rule_generated",
        "features": {"pre_state": True, "list_expansion": True, "qualifiers": True},
        "effect_templates": [{"operation": operation, "commit_mode": "commit"} for operation in values[0]],
        "field_bindings": values[1], "trusted_state_dependencies": values[2],
        "evidence_scope": "registration-12-pairs-per-tool",
    } for tool, values in specifications.items()]


def _fs(descriptor: dict[str, Any], row: dict[str, Any]) -> list[dict[str, Any]]:
    args, entries, tool = row["arguments"], row["before"]["entries"], row["tool_name"]
    qualifiers = descriptor["features"].get("qualifiers", False)
    if tool == "create_directory":
        return [] if args["path"] in entries else [_effect("filesystem.directory.create", "directory", args["path"])]
    if tool == "write_file":
        operation = "filesystem.file.overwrite" if args["path"] in entries else "filesystem.file.create"
        attrs = {"payload_class": _payload_class(args["content"])} if qualifiers else {}
        return [_effect(operation, "file", args["path"], attributes=attrs)]
    if tool == "edit_file":
        if args.get("dryRun", False):
            return []
        text = entries.get(args["path"], {}).get("text", "")
        for edit in args["edits"]:
            if edit["oldText"] not in text:
                return []
            text = text.replace(edit["oldText"], edit["newText"])
        attrs = {"payload_class": _payload_class(text)} if qualifiers else {}
        return [_effect("filesystem.file.edit", "file", args["path"], attributes=attrs)]
    if args["source"] not in entries or args["destination"] in entries:
        return []
    return [_effect("filesystem.entry.move", entries[args["source"]]["kind"], args["source"],
                    target=args["destination"], attributes={"destination": args["destination"]})]


def _matches(item: dict[str, Any], conditions: dict[str, Any]) -> bool:
    return all(item.get(key) == value for key, value in conditions.items())


def _sqlite(descriptor: dict[str, Any], row: dict[str, Any]) -> list[dict[str, Any]]:
    args, table, tool = row["arguments"], row["arguments"]["table"], row["tool_name"]
    records = row["before"]["tables"].get(table, [])
    qualifiers = descriptor["features"].get("qualifiers", False)
    if tool == "create_record":
        next_id = max([item["id"] for item in records] or [0]) + 1
        values = args["data"]
        attrs = {"table": table, "visibility": values.get("visibility")} if qualifiers else {}
        return [_effect("sqlite.record.create", "sqlite_record", f"{table}:{next_id}",
                        target=values.get("owner"), attributes=attrs)]
    selected = [item for item in records if _matches(item, args["conditions"])]
    effects = []
    for item in selected:
        if tool == "update_records":
            values = {**item, **args["data"]}
            operation = "sqlite.record.update"
        else:
            values, operation = item, "sqlite.record.delete"
        attrs = {"table": table, "visibility": values.get("visibility")} if qualifiers else {}
        effects.append(_effect(operation, "sqlite_record", f"{table}:{item['id']}",
                               target=values.get("owner"), attributes=attrs))
    return effects


def _memory(descriptor: dict[str, Any], row: dict[str, Any]) -> list[dict[str, Any]]:
    args, tool = row["arguments"], row["tool_name"]
    existing = {item["name"] for item in row["before"]["entities"]}
    qualifiers = descriptor["features"].get("qualifiers", False)
    expand = descriptor["features"].get("list_expansion", False)
    effects = []
    if tool == "create_entities":
        values = args["entities"] if expand else args["entities"][:1]
        for item in values:
            if item["name"] in existing:
                continue
            attrs = {"payload_class": _payload_class(item["observations"])} if qualifiers else {}
            effects.append(_effect("memory.entity.create", "memory_entity", f"entity:{item['name']}",
                                   target=item["name"], attributes=attrs))
    elif tool == "create_relations":
        values = args["relations"] if expand else args["relations"][:1]
        for item in values:
            effects.append(_effect("memory.relation.create", "memory_relation",
                                   f"relation:{item['from']}:{item['relationType']}:{item['to']}",
                                   target=item["to"],
                                   attributes={"source_entity": item["from"], "relation_type": item["relationType"]}))
    elif tool == "add_observations":
        groups = args["observations"] if expand else args["observations"][:1]
        for group in groups:
            contents = group["contents"] if expand else group["contents"][:1]
            for index, value in enumerate(contents):
                digest = hashlib.sha256(value.encode()).hexdigest()[:12]
                attrs = {"observation_id": f"{digest}:{index}", "payload_class": _payload_class(value)} if qualifiers else {}
                effects.append(_effect("memory.observation.add", "memory_entity",
                                       f"entity:{group['entityName']}", target=group["entityName"], attributes=attrs))
    else:
        values = args["entityNames"] if expand else args["entityNames"][:1]
        for name in values:
            if name in existing:
                effects.append(_effect("memory.entity.delete", "memory_entity", f"entity:{name}", target=name))
    return effects


def compile_descriptor(descriptor: dict[str, Any], row: dict[str, Any]) -> list[dict[str, Any]]:
    if descriptor.get("tool_name") != row.get("tool_name") or descriptor.get("schema_version") != 2:
        raise ValueError("descriptor/tool/schema mismatch")
    if not isinstance(descriptor.get("field_bindings"), dict) or not descriptor.get("effect_templates"):
        raise ValueError("descriptor lacks executable interface declarations")
    if row["source"] == "filesystem":
        effects = _fs(descriptor, row)
    elif row["source"] == "sqlite":
        effects = _sqlite(descriptor, row)
    elif row["source"] == "memory":
        effects = _memory(descriptor, row)
    else:
        raise ValueError(row["source"])
    declared = {item["operation"] for item in descriptor["effect_templates"]}
    undeclared = {item["operation"] for item in effects} - declared
    if undeclared:
        raise ValueError(f"compiler emitted undeclared effects: {sorted(undeclared)}")
    return sorted(effects, key=lambda item: json.dumps(item, sort_keys=True))
