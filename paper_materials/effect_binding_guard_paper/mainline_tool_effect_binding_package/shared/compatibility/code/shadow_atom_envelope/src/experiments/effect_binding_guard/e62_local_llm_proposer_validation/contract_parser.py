from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contracts import (
    AtomFieldBinding,
    EffectTemplate,
    ToolEffectContract,
)


@dataclass(frozen=True)
class ParseResult:
    parse_valid: bool
    contract: ToolEffectContract | None
    error: str = ""
    extracted_json: dict[str, Any] | None = None


def parse_contract_from_text(text: str, *, tool_name: str, setting: str) -> ParseResult:
    try:
        obj = extract_json_object(text)
        contract_obj = obj.get("contract", obj)
        templates_obj = contract_obj.get("templates")
        if not isinstance(templates_obj, list) or not templates_obj:
            return ParseResult(False, None, "missing_or_empty_templates", obj)
        templates = tuple(parse_template(template) for template in templates_obj)
        non_security_fields = tuple(str(item) for item in contract_obj.get("non_security_fields", []) if str(item))
        requires_review = bool(contract_obj.get("requires_human_review", False))
        provenance = dict(contract_obj.get("provenance", {}))
        provenance.update({"parsed_from": setting, "parser": "e62_strict_json"})
        contract_tool_name = str(contract_obj.get("tool_name", tool_name))
        if contract_tool_name != tool_name:
            return ParseResult(False, None, f"tool_name_mismatch:{contract_tool_name}", obj)
        return ParseResult(
            True,
            ToolEffectContract(
                tool_name=tool_name,
                proposal_mode="local_llm",
                templates=templates,
                non_security_fields=non_security_fields,
                requires_human_review=requires_review,
                provenance=provenance,
            ),
            "",
            obj,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return ParseResult(False, None, f"{type(exc).__name__}:{exc}", None)


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = strip_markdown_fence(stripped)
    try:
        value = json.loads(stripped)
        if not isinstance(value, dict):
            raise ValueError("top_level_json_not_object")
        return value
    except json.JSONDecodeError:
        tagged = extract_tagged_final_json(stripped)
        if tagged is not None:
            return tagged
        filtered = strip_thinking_blocks(stripped)
        candidates = balanced_json_candidates(filtered)
        for candidate in reversed(candidates):
            try:
                value = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                if "templates" in value or ("contract" in value and isinstance(value["contract"], dict)):
                    return value
        for candidate in reversed(candidates):
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        raise


def extract_tagged_final_json(text: str) -> dict[str, Any] | None:
    matches = re.findall(r"<FINAL_JSON>\s*(.*?)\s*</FINAL_JSON>", text, flags=re.IGNORECASE | re.DOTALL)
    for body in reversed(matches):
        try:
            value = json.loads(strip_markdown_fence(body.strip()))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    marker = re.search(r"<FINAL_JSON>\s*(.*)$", text, flags=re.IGNORECASE | re.DOTALL)
    if marker:
        for candidate in reversed(balanced_json_candidates(marker.group(1))):
            try:
                value = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    return None


def strip_thinking_blocks(text: str) -> str:
    filtered = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    filtered = re.sub(r"<thought>.*?</thought>", "", filtered, flags=re.IGNORECASE | re.DOTALL)
    filtered = re.sub(r"<analysis>.*?</analysis>", "", filtered, flags=re.IGNORECASE | re.DOTALL)
    for tag in ("<FINAL_JSON>", "{"):
        index = filtered.find(tag)
        if index >= 0:
            return filtered[index:].strip()
    return filtered.strip()


def balanced_json_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
            continue
        if char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start : index + 1])
                start = None
    return candidates


def strip_markdown_fence(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_template(obj: dict[str, Any]) -> EffectTemplate:
    if not isinstance(obj, dict):
        raise TypeError("template_not_object")
    required = ("effect_type", "operation", "resource_field", "resource_type")
    for field in required:
        if field not in obj or obj[field] in (None, ""):
            raise KeyError(field)
    return EffectTemplate(
        effect_type=str(obj["effect_type"]),
        operation=str(obj["operation"]),
        resource_field=str(obj["resource_field"]),
        resource_type=str(obj["resource_type"]),
        field_bindings=tuple(parse_binding(item) for item in obj.get("field_bindings", []) if isinstance(item, dict)),
        target_principal_field=optional_str(obj.get("target_principal_field")),
        target_role=optional_str(obj.get("target_role")),
        target_as_resource=bool(obj.get("target_as_resource", False)),
        target_resource_type=str(obj.get("target_resource_type", "recipient")),
        visibility_field=optional_str(obj.get("visibility_field")),
        permission_delta_field=optional_str(obj.get("permission_delta_field")),
        commit_mode_field=optional_str(obj.get("commit_mode_field", "commit_mode")),
        default_commit_mode=str(obj.get("default_commit_mode", "commit")),
        control_source_field=str(obj.get("control_source_field", "control_source")),
        provenance_source_field=str(obj.get("provenance_source_field", "provenance_source")),
        evidence_ref_field=optional_str(obj.get("evidence_ref_field")),
        security_relevant_fields=tuple(str(item) for item in obj.get("security_relevant_fields", []) if str(item)),
        emit_if_field=optional_str(obj.get("emit_if_field")),
        emit_if_values=tuple(str(item) for item in obj.get("emit_if_values", []) if str(item)),
    )


def parse_binding(obj: dict[str, Any]) -> AtomFieldBinding:
    return AtomFieldBinding(
        source_field=str(obj["source_field"]),
        atom_field=str(obj["atom_field"]),
        required=bool(obj.get("required", True)),
        repeated=bool(obj.get("repeated", False)),
        canonicalize=bool(obj.get("canonicalize", True)),
    )


def optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
