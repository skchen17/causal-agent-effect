"""Pure representation keys and explicit diagnostic adapters."""

from __future__ import annotations

import json
from typing import Any

from .descriptor_compiler import compile_descriptor
from .sources import referenced_state


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def representation_keys(row: dict[str, Any], typed: list[dict[str, Any]], source: list[dict[str, Any]]) -> dict[str, str]:
    common = [{
        "operation": item.get("operation"), "resource_type": item.get("resource_type"),
        "resource_id": item.get("resource_id"), "target_principal": item.get("target_principal"),
        "commit_mode": item.get("commit_mode"),
    } for item in typed]
    return {
        "tool_name": canonical({"tool_name": row["tool_name"]}),
        "raw_call": canonical({"tool_name": row["tool_name"], "arguments": row["arguments"]}),
        "state_aware_raw_call": canonical({
            "tool_name": row["tool_name"], "arguments": row["arguments"],
            "referenced_state": referenced_state(row, row["before"]),
        }),
        "common_field": canonical(common),
        "typed_effect": canonical(typed),
        "source_effect_oracle": canonical(source),
    }


def diagnostic_effects(name: str, row: dict[str, Any], descriptor: dict[str, Any],
                       typed: list[dict[str, Any]], source: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    if name == "tool_name":
        return [], False
    if name == "raw_call":
        stripped = {**descriptor, "features": {**descriptor["features"], "pre_state": False}}
        # Calls whose operation depends on state cannot be safely totalized from arguments alone.
        if row["tool_name"] in {"write_file", "create_directory", "edit_file", "move_file",
                               "update_records", "delete_records", "delete_entities"}:
            return [], False
        return compile_descriptor(stripped, row), True
    if name == "state_aware_raw_call":
        return compile_descriptor(descriptor, row), True
    if name == "common_field":
        return [{**item, "attributes": {}} for item in typed], True
    if name == "typed_effect":
        return typed, True
    if name == "source_effect_oracle":
        return source, True
    raise ValueError(name)

