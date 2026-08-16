"""Schema-native before/after differences with no typed-effect vocabulary."""

from __future__ import annotations

from typing import Any


def _filesystem(row: dict[str, Any]) -> list[dict[str, Any]]:
    before, after = row["before"]["entries"], row["after"]["entries"]
    output = []
    for path in sorted(set(before) | set(after)):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        if old is None:
            output.append({"kind": "entry_added", "path": path, "value": new})
        elif new is None:
            output.append({"kind": "entry_removed", "path": path, "value": old})
        else:
            output.append({"kind": "entry_changed", "path": path, "before": old, "after": new})
    return output


def _sqlite(row: dict[str, Any]) -> list[dict[str, Any]]:
    table = row["arguments"]["table"]
    before = {item["id"]: item for item in row["before"]["tables"].get(table, [])}
    after = {item["id"]: item for item in row["after"]["tables"].get(table, [])}
    output = []
    for item_id in sorted(set(before) | set(after)):
        old, new = before.get(item_id), after.get(item_id)
        if old == new:
            continue
        if old is None:
            output.append({"kind": "row_added", "table": table, "row_id": item_id, "value": new})
        elif new is None:
            output.append({"kind": "row_removed", "table": table, "row_id": item_id, "value": old})
        else:
            output.append({"kind": "row_changed", "table": table, "row_id": item_id,
                           "before": old, "after": new})
    return output


def _memory(row: dict[str, Any]) -> list[dict[str, Any]]:
    before_entities = {item["name"]: item for item in row["before"]["entities"]}
    after_entities = {item["name"]: item for item in row["after"]["entities"]}
    output = []
    for name in sorted(set(before_entities) | set(after_entities)):
        old, new = before_entities.get(name), after_entities.get(name)
        if old == new:
            continue
        if old is None:
            output.append({"kind": "entity_added", "name": name, "value": new})
        elif new is None:
            output.append({"kind": "entity_removed", "name": name, "value": old})
        else:
            output.append({"kind": "entity_changed", "name": name, "before": old, "after": new})
    before_relations = {(item["from"], item["to"], item["relationType"]) for item in row["before"]["relations"]}
    after_relations = {(item["from"], item["to"], item["relationType"]) for item in row["after"]["relations"]}
    for source, target, relation in sorted(after_relations - before_relations):
        output.append({"kind": "relation_added", "from": source, "to": target, "relation": relation})
    for source, target, relation in sorted(before_relations - after_relations):
        output.append({"kind": "relation_removed", "from": source, "to": target, "relation": relation})
    return output


def native_deltas(row: dict[str, Any]) -> list[dict[str, Any]]:
    if row.get("execution_error"):
        raise ValueError(f"source execution failed: {row['case_id']}")
    if row["source"] == "filesystem":
        return _filesystem(row)
    if row["source"] == "sqlite":
        return _sqlite(row)
    if row["source"] == "memory":
        return _memory(row)
    raise ValueError(row["source"])

