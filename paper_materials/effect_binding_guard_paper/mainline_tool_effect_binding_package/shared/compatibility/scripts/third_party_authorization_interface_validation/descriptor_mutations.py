"""Systematic descriptor faults generated without evaluation outcomes."""

from __future__ import annotations

import copy
from typing import Any

from .descriptor_compiler import compile_descriptor


LIST_TOOLS = {"update_records", "delete_records", "create_entities", "create_relations",
              "add_observations", "delete_entities"}
QUALIFIER_TOOLS = {"write_file", "edit_file", "create_record", "update_records", "delete_records",
                   "create_entities", "add_observations"}
TARGET_TOOLS = {"move_file", "create_record", "update_records", "delete_records", "create_entities",
                "create_relations", "add_observations", "delete_entities"}
NOOP_TOOLS = {"create_directory", "edit_file", "move_file", "delete_records", "delete_entities"}


def mutation_manifest(descriptors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for descriptor in sorted(descriptors, key=lambda item: item["tool_name"]):
        tool = descriptor["tool_name"]
        operators = ["drop_effect_template"]
        if descriptor.get("trusted_state_dependencies"):
            operators.append("remove_pre_state")
        if tool in LIST_TOOLS:
            operators.append("disable_list_expansion")
        if tool in QUALIFIER_TOOLS:
            operators.append("drop_qualifiers")
        if tool in TARGET_TOOLS:
            operators.append("swap_resource_target")
        if len(descriptor["effect_templates"]) > 1:
            operators.append("collapse_operation")
        if tool in NOOP_TOOLS:
            operators.append("ignore_noop_or_default")
        for operator in operators:
            rows.append({
                "mutant_id": f"{tool}::{operator}",
                "tool_name": tool,
                "operator": operator,
                "generation_inputs": ["frozen_descriptor_schema", "tool_name"],
                "reads_evaluation_outcomes": False,
            })
    return rows


def _without_state(row: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(row)
    if row["source"] == "filesystem":
        value["before"] = {"entries": {}}
    elif row["source"] == "sqlite":
        value["before"] = {"tables": {row["arguments"]["table"]: []}}
    else:
        value["before"] = {"entities": [], "relations": []}
    return value


def _ignore_noop(row: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(row)
    tool, args = value["tool_name"], value["arguments"]
    if tool == "edit_file":
        args["dryRun"] = False
    elif tool == "create_directory":
        value["before"]["entries"].pop(args["path"], None)
    elif tool == "move_file":
        value["before"]["entries"].pop(args["destination"], None)
    elif tool == "delete_records":
        args["conditions"] = {}
    elif tool == "delete_entities" and not args.get("entityNames"):
        args["entityNames"] = ["team:synthetic"]
    return value


def compile_mutant(descriptor: dict[str, Any], row: dict[str, Any], operator: str) -> list[dict[str, Any]]:
    candidate, context = copy.deepcopy(descriptor), copy.deepcopy(row)
    if operator == "drop_effect_template":
        candidate["effect_templates"] = candidate["effect_templates"][:-1]
    elif operator == "remove_pre_state":
        candidate["trusted_state_dependencies"] = []
        context = _without_state(context)
    elif operator == "disable_list_expansion":
        candidate["features"]["list_expansion"] = False
    elif operator == "drop_qualifiers":
        candidate["features"]["qualifiers"] = False
    elif operator == "ignore_noop_or_default":
        context = _ignore_noop(context)
    effects = compile_descriptor(candidate, context)
    if operator == "disable_list_expansion":
        effects = effects[:1]
    elif operator == "swap_resource_target":
        for effect in effects:
            effect["resource_id"], effect["target_principal"] = (
                effect.get("target_principal"), effect.get("resource_id")
            )
    elif operator == "collapse_operation" and effects:
        replacement = candidate["effect_templates"][0]["operation"]
        for effect in effects:
            effect["operation"] = replacement
    return effects
