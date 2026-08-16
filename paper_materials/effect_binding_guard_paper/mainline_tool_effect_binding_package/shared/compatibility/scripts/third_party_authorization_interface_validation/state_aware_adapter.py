"""Tool-specific adapter from raw calls plus referenced pre-state.

This intentionally contains the semantic knowledge a downstream consumer must
provide when it receives a state-aware request instead of a typed interface.
It does not import or read frozen descriptors.
"""

from __future__ import annotations

import hashlib
import json
import copy
from typing import Any


def _payload_class(value: Any) -> str:
    return "restricted" if "secret-export" in json.dumps(value, sort_keys=True) else "routine"


def _request(operation: str, resource_type: str, resource_id: str, *, target: str | None = None,
             attributes: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "operation": operation,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "target_principal": target,
        "attributes": attributes or {},
        "commit_mode": "commit",
    }


def _matches(item: dict[str, Any], conditions: dict[str, Any]) -> bool:
    return all(item.get(key) == value for key, value in conditions.items())


def build_view(row: dict[str, Any]) -> dict[str, Any]:
    """Expose arguments and only the pre-state directly referenced by them."""

    args, source, before = row["arguments"], row["source"], row["before"]
    if source == "filesystem":
        names = [args[key] for key in ("path", "source", "destination") if key in args]
        referenced = {name: copy.deepcopy(before["entries"].get(name)) for name in names}
    elif source == "sqlite":
        table = args["table"]
        conditions = args.get("conditions", {})
        referenced = {
            "table": table,
            "table_exists": table in before["tables"],
            "matched_records": [
                copy.deepcopy(item) for item in before["tables"].get(table, [])
                if _matches(item, conditions)
            ],
        }
    else:
        names = set(args.get("entityNames", []))
        names.update(item.get("name") for item in args.get("entities", []))
        names.update(item.get("entityName") for item in args.get("observations", []))
        for relation in args.get("relations", []):
            names.update((relation.get("from"), relation.get("to")))
        referenced = {
            "entities": [copy.deepcopy(item) for item in before["entities"] if item["name"] in names],
            "relations": [copy.deepcopy(item) for item in before["relations"]
                          if item["from"] in names or item["to"] in names],
        }
    return {
        "schema_version": 1,
        "source": source,
        "tool_name": row["tool_name"],
        "totalized_arguments": copy.deepcopy(args),
        "referenced_state": referenced,
    }


def requests(view: dict[str, Any]) -> list[dict[str, Any]]:
    args, tool, source = view["totalized_arguments"], view["tool_name"], view["source"]
    referenced = view["referenced_state"]

    if source == "filesystem":
        entries = referenced
        if tool == "create_directory":
            return [] if entries.get(args["path"]) is not None else [
                _request("filesystem.directory.create", "directory", args["path"])
            ]
        if tool == "write_file":
            operation = "filesystem.file.overwrite" if entries.get(args["path"]) is not None else "filesystem.file.create"
            return [_request(operation, "file", args["path"], attributes={"payload_class": _payload_class(args["content"])})]
        if tool == "edit_file":
            if args.get("dryRun", False):
                return []
            text = entries.get(args["path"], {}).get("text", "")
            for edit in args["edits"]:
                if edit["oldText"] not in text:
                    return []
                text = text.replace(edit["oldText"], edit["newText"])
            return [_request("filesystem.file.edit", "file", args["path"], attributes={"payload_class": _payload_class(text)})]
        if entries.get(args["source"]) is None or entries.get(args["destination"]) is not None:
            return []
        return [_request("filesystem.entry.move", entries[args["source"]]["kind"], args["source"],
                         target=args["destination"], attributes={"destination": args["destination"]})]

    if source == "sqlite":
        table = args["table"]
        records = referenced["matched_records"]
        if tool == "create_record":
            next_id = max([item["id"] for item in records] or [0]) + 1
            value = args["data"]
            return [_request("sqlite.record.create", "sqlite_record", f"{table}:{next_id}",
                             target=value.get("owner"),
                             attributes={"table": table, "visibility": value.get("visibility")})]
        selected = [item for item in records if _matches(item, args["conditions"])]
        output = []
        for item in selected:
            value = {**item, **args["data"]} if tool == "update_records" else item
            operation = "sqlite.record.update" if tool == "update_records" else "sqlite.record.delete"
            output.append(_request(operation, "sqlite_record", f"{table}:{item['id']}",
                                   target=value.get("owner"),
                                   attributes={"table": table, "visibility": value.get("visibility")}))
        return output

    existing = {item["name"] for item in referenced["entities"]}
    output = []
    if tool == "create_entities":
        for item in args["entities"]:
            if item["name"] not in existing:
                output.append(_request("memory.entity.create", "memory_entity", f"entity:{item['name']}",
                                       target=item["name"],
                                       attributes={"payload_class": _payload_class(item["observations"])}))
    elif tool == "create_relations":
        for item in args["relations"]:
            output.append(_request("memory.relation.create", "memory_relation",
                                   f"relation:{item['from']}:{item['relationType']}:{item['to']}",
                                   target=item["to"], attributes={"source_entity": item["from"],
                                                                  "relation_type": item["relationType"]}))
    elif tool == "add_observations":
        for group in args["observations"]:
            for index, value in enumerate(group["contents"]):
                digest = hashlib.sha256(value.encode()).hexdigest()[:12]
                output.append(_request("memory.observation.add", "memory_entity",
                                       f"entity:{group['entityName']}", target=group["entityName"],
                                       attributes={"observation_id": f"{digest}:{index}",
                                                   "payload_class": _payload_class(value)}))
    else:
        for name in args["entityNames"]:
            if name in existing:
                output.append(_request("memory.entity.delete", "memory_entity", f"entity:{name}", target=name))
    return output
