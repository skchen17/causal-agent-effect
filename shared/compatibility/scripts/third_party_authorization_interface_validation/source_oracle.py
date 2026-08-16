"""Implementation-grounded transition oracle over before/after snapshots.

This module consumes only source execution rows. It deliberately does not import
the descriptor compiler or policy engine.
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


def _fs(row: dict[str, Any]) -> list[dict[str, Any]]:
    before, after, args = row["before"]["entries"], row["after"]["entries"], row["arguments"]
    tool = row["tool_name"]
    if tool == "move_file":
        source, destination = args["source"], args["destination"]
        if source in before and source not in after and destination in after:
            return [_effect("filesystem.entry.move", before[source]["kind"], source, target=destination,
                            attributes={"destination": destination})]
        return []
    added = sorted(set(after) - set(before))
    changed = sorted(name for name in set(before).intersection(after) if before[name] != after[name])
    effects: list[dict[str, Any]] = []
    for name in added:
        kind = after[name]["kind"]
        operation = "filesystem.directory.create" if kind == "directory" else "filesystem.file.create"
        attrs = {} if kind == "directory" else {"payload_class": _payload_class(after[name].get("text", ""))}
        effects.append(_effect(operation, kind, name, attributes=attrs))
    for name in changed:
        operation = "filesystem.file.edit" if tool == "edit_file" else "filesystem.file.overwrite"
        effects.append(_effect(operation, "file", name,
                               attributes={"payload_class": _payload_class(after[name].get("text", ""))}))
    return effects


def _sqlite(row: dict[str, Any]) -> list[dict[str, Any]]:
    tool, table = row["tool_name"], row["arguments"]["table"]
    before = {item["id"]: item for item in row["before"]["tables"][table]}
    after = {item["id"]: item for item in row["after"]["tables"][table]}
    ids = sorted(set(before) | set(after))
    effects = []
    for item_id in ids:
        old, new = before.get(item_id), after.get(item_id)
        if old == new:
            continue
        if old is None:
            operation, value = "sqlite.record.create", new
        elif new is None:
            operation, value = "sqlite.record.delete", old
        else:
            operation, value = "sqlite.record.update", new
        effects.append(_effect(operation, "sqlite_record", f"{table}:{item_id}", target=value.get("owner"),
                               attributes={"table": table, "visibility": value.get("visibility")}))
    return effects


def _memory(row: dict[str, Any]) -> list[dict[str, Any]]:
    before_entities = {item["name"]: item for item in row["before"]["entities"]}
    after_entities = {item["name"]: item for item in row["after"]["entities"]}
    effects: list[dict[str, Any]] = []
    for name in sorted(set(before_entities) | set(after_entities)):
        old, new = before_entities.get(name), after_entities.get(name)
        if old is None:
            effects.append(_effect("memory.entity.create", "memory_entity", f"entity:{name}", target=name,
                                   attributes={"payload_class": _payload_class(new.get("observations", []))}))
        elif new is None:
            effects.append(_effect("memory.entity.delete", "memory_entity", f"entity:{name}", target=name))
        elif old != new:
            additions = [item for item in new.get("observations", []) if item not in old.get("observations", [])]
            for index, value in enumerate(additions):
                digest = hashlib.sha256(value.encode()).hexdigest()[:12]
                effects.append(_effect("memory.observation.add", "memory_entity", f"entity:{name}", target=name,
                                       attributes={"observation_id": f"{digest}:{index}",
                                                   "payload_class": _payload_class(value)}))
    before_relations = {(item["from"], item["to"], item["relationType"]) for item in row["before"]["relations"]}
    after_relations = {(item["from"], item["to"], item["relationType"]) for item in row["after"]["relations"]}
    for source, target, relation_type in sorted(after_relations - before_relations):
        effects.append(_effect("memory.relation.create", "memory_relation",
                               f"relation:{source}:{relation_type}:{target}", target=target,
                               attributes={"source_entity": source, "relation_type": relation_type}))
    return effects


def source_effects(row: dict[str, Any]) -> list[dict[str, Any]]:
    if row.get("execution_error"):
        raise ValueError(f"source execution failed: {row['case_id']}: {row['execution_error']}")
    if row["source"] == "filesystem":
        effects = _fs(row)
    elif row["source"] == "sqlite":
        effects = _sqlite(row)
    elif row["source"] == "memory":
        effects = _memory(row)
    else:
        raise ValueError(row["source"])
    return sorted(effects, key=lambda item: json.dumps(item, sort_keys=True))

