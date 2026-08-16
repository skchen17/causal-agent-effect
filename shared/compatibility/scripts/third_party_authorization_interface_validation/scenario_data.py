"""Descriptor-blind fixtures for the frozen third-party MCP tools."""

from __future__ import annotations

from typing import Any


TOOL_SOURCES = {
    "create_directory": "filesystem",
    "write_file": "filesystem",
    "edit_file": "filesystem",
    "move_file": "filesystem",
    "create_record": "sqlite",
    "update_records": "sqlite",
    "delete_records": "sqlite",
    "create_entities": "memory",
    "create_relations": "memory",
    "add_observations": "memory",
    "delete_entities": "memory",
}


def _filesystem(tool: str, namespace: str, pair: int, side: int) -> tuple[dict[str, Any], dict[str, Any], str]:
    team = f"team/{namespace}-{pair}"
    private = f"private/{namespace}-{pair}"
    axis = ("resource_scope", "pre_state", "qualifier")[pair % 3]
    entries: dict[str, Any] = {"team": None, "private": None}
    if tool == "create_directory":
        path = f"{team}-dir" if side == 0 else f"{private}-dir"
        return {"entries": entries}, {"path": path}, "resource_scope"
    if tool == "write_file":
        if axis == "pre_state":
            path = f"{team}-file.txt"
            if side:
                entries[path] = "locked prior content"
            content = "approved update"
        elif axis == "qualifier":
            path = f"{team}-file.txt"
            content = "approved note" if side == 0 else "secret-export payload"
        else:
            path = f"{team}-file.txt" if side == 0 else f"{private}-file.txt"
            content = "approved note"
        return {"entries": entries}, {"path": path, "content": content}, axis
    if tool == "edit_file":
        path = f"{team}-edit.txt" if axis != "resource_scope" or side == 0 else f"{private}-edit.txt"
        entries[path] = "alpha\nbeta\n"
        dry_run = bool(side) if axis == "qualifier" else False
        new_text = "gamma" if side == 0 else "secret-export"
        return {"entries": entries}, {
            "path": path, "edits": [{"oldText": "beta", "newText": new_text}], "dryRun": dry_run,
        }, axis
    source = f"{team}-source.txt"
    entries[source] = "movable content"
    destination = f"{team}-destination.txt" if side == 0 else f"{private}-destination.txt"
    return {"entries": entries}, {"source": source, "destination": destination}, "destination_scope"


def _sqlite(tool: str, namespace: str, pair: int, side: int) -> tuple[dict[str, Any], dict[str, Any], str]:
    axis = ("table_scope", "target_principal", "visibility")[pair % 3]
    rows = {
        "records": [
            {"id": 1, "name": f"{namespace}-one", "owner": "alice", "visibility": "internal", "value": "old"},
            {"id": 2, "name": f"{namespace}-two", "owner": "bob", "visibility": "private", "value": "old"},
        ],
        "secrets": [
            {"id": 1, "name": f"{namespace}-secret", "owner": "eve", "visibility": "private", "value": "sealed"},
        ],
    }
    table = "secrets" if axis == "table_scope" and side else "records"
    owner = "eve" if axis == "target_principal" and side else "alice"
    visibility = "public" if axis == "visibility" and side else "internal"
    if tool == "create_record":
        args = {"table": table, "data": {
            "name": f"{namespace}-created-{pair}-{side}", "owner": owner,
            "visibility": visibility, "value": "approved",
        }}
    elif tool == "update_records":
        args = {"table": table, "conditions": {"id": 1}, "data": {
            "owner": owner, "visibility": visibility, "value": f"updated-{side}",
        }}
    else:
        if axis == "target_principal" and side:
            rows["records"][0]["owner"] = "eve"
        if axis == "visibility" and side:
            rows["records"][0]["visibility"] = "public"
        args = {"table": table, "conditions": {"id": 1}}
    return {"tables": rows}, args, axis


def _memory(tool: str, namespace: str, pair: int, side: int) -> tuple[dict[str, Any], dict[str, Any], str]:
    axis = ("resource_scope", "multi_resource", "payload_class")[pair % 3]
    base_entities = [
        {"name": f"team:{namespace}:alice", "entityType": "person", "observations": ["member"]},
        {"name": f"team:{namespace}:bob", "entityType": "person", "observations": ["member"]},
        {"name": f"private:{namespace}:eve", "entityType": "person", "observations": ["external"]},
    ]
    fixture = {"entities": base_entities, "relations": []}
    safe = f"team:{namespace}:new-{pair}-{side}"
    denied = f"private:{namespace}:new-{pair}-{side}"
    if tool == "create_entities":
        names = [safe]
        if side and axis in {"resource_scope", "multi_resource"}:
            names.append(denied)
        observations = ["approved"] if not (side and axis == "payload_class") else ["secret-export payload"]
        return fixture, {"entities": [
            {"name": name, "entityType": "note", "observations": observations} for name in names
        ]}, axis
    if tool == "create_relations":
        destination = f"team:{namespace}:bob" if side == 0 else f"private:{namespace}:eve"
        relations = [{"from": f"team:{namespace}:alice", "to": destination, "relationType": "works_with"}]
        if side and axis == "multi_resource":
            relations.insert(0, {"from": f"team:{namespace}:alice", "to": f"team:{namespace}:bob", "relationType": "knows"})
        return fixture, {"relations": relations}, axis
    if tool == "add_observations":
        entity = f"team:{namespace}:alice" if side == 0 or axis != "resource_scope" else f"private:{namespace}:eve"
        contents = ["approved"] if not (side and axis == "payload_class") else ["secret-export payload"]
        if side and axis == "multi_resource":
            contents = ["approved", "secret-export payload"]
        return fixture, {"observations": [{"entityName": entity, "contents": contents}]}, axis
    names = [f"team:{namespace}:alice"]
    if side and axis in {"resource_scope", "multi_resource"}:
        names.append(f"private:{namespace}:eve")
    return fixture, {"entityNames": names}, axis


def make_case(tool: str, phase: str, pair: int, side: int) -> dict[str, Any]:
    """Build one context without consulting descriptors, labels, or outcomes."""

    if phase not in {"registration", "evaluation", "confirmatory"}:
        raise ValueError(phase)
    namespace = {"registration": "reg", "evaluation": "eval", "confirmatory": "confirm"}[phase]
    source = TOOL_SOURCES[tool]
    if source == "filesystem":
        fixture, arguments, axis = _filesystem(tool, namespace, pair, side)
    elif source == "sqlite":
        fixture, arguments, axis = _sqlite(tool, namespace, pair, side)
    else:
        fixture, arguments, axis = _memory(tool, namespace, pair, side)
    return {
        "case_id": f"{phase}-{tool}-{pair:02d}-{side}",
        "pair_id": f"{phase}-{tool}-{pair:02d}",
        "phase": phase,
        "source": source,
        "tool_name": tool,
        "axis": axis,
        "fixture": fixture,
        "arguments": arguments,
        "subject": "agent:validator",
    }

