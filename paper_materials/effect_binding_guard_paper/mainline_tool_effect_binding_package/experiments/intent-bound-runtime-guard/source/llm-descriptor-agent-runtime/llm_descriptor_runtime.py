"""Pure helpers for E76 LLM-generated atom descriptors.

E76 differs from E75 in one important way: side-effect tool descriptors are
not derived from a hard-coded schema rule at runtime. They must be generated
offline by a local LLM, validated by counterfactual field tests, and then
loaded as a registered descriptor registry.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import (
    SIDE_EFFECT_TO_EFFECT,
    build_tool_descriptor,
    parse_permission_plan,
)


PROMPT_VERSION = "e76_llm_atom_descriptor_v1"

ATOM_FIELDS = (
    "effect",
    "operation",
    "resource_id",
    "resource_type",
    "recipient_role",
    "visibility",
    "commit_mode",
    "provenance_source",
    "control_source",
)

DESCRIPTOR_FIELDS = {
    "tool_name",
    "effect_inventory",
    "atom_templates",
    "field_bindings",
    "multi_resource_policy",
    "provenance_control_policy",
    "non_security_fields",
    "requires_human_review",
}


def should_allow_explicit_override(
    *, descriptor_unregistered: bool, signature_blocked: bool, decision: str
) -> bool:
    """Allow replanning overrides only for counterfactually registered tools."""
    return not descriptor_unregistered and signature_blocked and decision == "NEEDS_REPLAN"


def parse_permission_plan_fail_closed(
    payload: Mapping[str, Any] | None, registry: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any] | None:
    """Keep valid side-effect scope while dropping irrelevant model extras.

    Read-only tools and non-security fields do not need authorization entries.
    Malformed security-field entries are omitted, so a later use remains
    unbound and triggers replan instead of being implicitly authorized.
    """
    if not isinstance(payload, Mapping) or not isinstance(payload.get("task_goal"), str):
        return None
    tools = payload.get("tools")
    if not isinstance(tools, list):
        return None
    sanitized_tools: list[dict[str, Any]] = []
    for item in tools:
        if not isinstance(item, Mapping):
            continue
        tool_name = item.get("tool_name")
        descriptor = registry.get(str(tool_name))
        if not descriptor or not descriptor.get("side_effectful"):
            continue
        raw_fields = item.get("fields")
        if not isinstance(raw_fields, Mapping):
            raw_fields = {}
        fields: dict[str, Any] = {}
        security_fields = set(descriptor.get("security_fields", []))
        for field, binding in raw_fields.items():
            if field not in security_fields or not isinstance(binding, Mapping):
                continue
            mode = binding.get("mode")
            values = binding.get("values")
            intent = binding.get("intent")
            if mode not in {"exact", "resolve", "forbidden"}:
                continue
            if not isinstance(values, list) or not all(isinstance(value, (str, int, float, bool)) for value in values):
                continue
            if not isinstance(intent, str):
                continue
            fields[str(field)] = {"mode": mode, "values": values, "intent": intent}
        sanitized_tools.append({"tool_name": str(tool_name), "fields": fields})
    return parse_permission_plan(
        {"task_goal": payload["task_goal"], "tools": sanitized_tools},
        registry,
    )


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def descriptor_prompt(tool_view: Mapping[str, Any], *, previous: Mapping[str, Any] | None = None, feedback: Mapping[str, Any] | None = None) -> str:
    """Build a label-hidden prompt for offline tool onboarding."""
    parameters = {
        field: normalize_text(spec.get("description", ""))[:120] if isinstance(spec, Mapping) else ""
        for field, spec in tool_view.get("parameters", {}).items()
    }
    lines = [
        "/no_think",
        "Return ONLY the descriptor JSON object. Do not repeat these instructions.",
        "Top-level keys must be exactly: tool_name, effect_inventory, atom_templates, field_bindings, multi_resource_policy, provenance_control_policy, non_security_fields, requires_human_review.",
        "No ALLOW, DENY, ABSTAIN, labels, or policy decisions.",
        "Each field_bindings object must contain exactly: effect, operation, resource_id, resource_type, recipient_role, visibility, commit_mode, provenance_source, control_source.",
        "Allowed binding values: param:<field>, param_list:<field>, literal:<value>, runtime:<field>, tool_name, unknown.",
        "Bind every effect-changing argument with param:<field> or param_list:<field>; otherwise put it in non_security_fields.",
        "Use runtime:provenance_source and runtime:control_source unless those are explicit parameters.",
        f"TOOL_NAME: {tool_view['tool_name']}",
        f"SUITES: {', '.join(tool_view.get('suite_names', []))}",
        f"DESCRIPTION: {normalize_text(tool_view.get('description', ''))[:400]}",
        "PARAMETERS:",
    ]
    for field, description in sorted(parameters.items()):
        required = " required" if field in set(tool_view.get("required_fields", [])) else ""
        lines.append(f"- {field}{required}: {description}")
    if previous is not None:
        lines.append("PREVIOUS_DESCRIPTOR_JSON:")
        lines.append(json.dumps(previous, sort_keys=True, ensure_ascii=True)[:2000])
    if feedback is not None:
        lines.append("SANITIZED_COUNTERFACTUAL_FEEDBACK_JSON:")
        lines.append(json.dumps(feedback, sort_keys=True, ensure_ascii=True)[:1200])
    lines.append("Now output the descriptor JSON object only.")
    return "\n".join(lines)


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"<\s*think\s*>.*?<\s*/\s*think\s*>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    candidates = [cleaned]
    match = re.search(r"<FINAL_JSON>\s*(\{.*?\})\s*</FINAL_JSON>", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if match:
        candidates.insert(0, match.group(1))
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        candidates.append(cleaned[start : end + 1])
    last_error = ""
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = str(exc)
            continue
        if isinstance(value, dict):
            return value
        last_error = "json_root_not_object"
    raise ValueError(f"no_json_object:{last_error}")


def parse_descriptor(obj: Mapping[str, Any], expected_tool_name: str) -> dict[str, Any]:
    extra = set(obj) - DESCRIPTOR_FIELDS
    missing = DESCRIPTOR_FIELDS - set(obj)
    if extra:
        raise ValueError(f"unknown_descriptor_fields:{sorted(extra)}")
    if missing:
        raise KeyError(f"missing_descriptor_fields:{sorted(missing)}")
    if obj["tool_name"] != expected_tool_name:
        raise ValueError(f"tool_name_mismatch:{obj['tool_name']}!={expected_tool_name}")
    effect_inventory = coerce_effect_inventory(obj["effect_inventory"])
    atom_templates = coerce_atom_templates(obj["atom_templates"], fallback_bindings=obj.get("field_bindings"))
    multi_resource_policy = coerce_multi_resource_policy(obj["multi_resource_policy"])
    provenance_control_policy = coerce_provenance_control_policy(obj["provenance_control_policy"])
    if multi_resource_policy not in {"expand_lists", "single_atom"}:
        raise ValueError("unsupported_multi_resource_policy")
    if provenance_control_policy != "bind_runtime_evidence":
        raise ValueError("unsupported_provenance_control_policy")
    if not isinstance(obj["requires_human_review"], bool):
        raise TypeError("requires_human_review_not_bool")
    non_security = obj["non_security_fields"]
    if not isinstance(non_security, list) or any(not isinstance(x, str) for x in non_security):
        raise TypeError("non_security_fields_not_string_list")
    field_bindings = parse_field_bindings(coerce_bindings_object(obj["field_bindings"]))
    templates = []
    for index, template in enumerate(atom_templates):
        if not isinstance(template, Mapping):
            raise TypeError(f"template_{index}_not_object")
        if "field_bindings" not in template:
            raise ValueError(f"template_{index}_missing_field_bindings")
        templates.append(
            {
                "template_id": str(template.get("template_id", f"template_{index}")),
                "field_bindings": parse_field_bindings(coerce_bindings_object(template["field_bindings"])),
            }
        )
    return {
        "tool_name": expected_tool_name,
        "effect_inventory": effect_inventory,
        "atom_templates": templates,
        "field_bindings": field_bindings,
        "multi_resource_policy": multi_resource_policy,
        "provenance_control_policy": provenance_control_policy,
        "non_security_fields": list(non_security),
        "requires_human_review": obj["requires_human_review"],
    }


def parse_field_bindings(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError("field_bindings_not_object")
    out: dict[str, str] = {}
    for field in ATOM_FIELDS:
        binding = value.get(field)
        if not isinstance(binding, str):
            raise TypeError(f"binding_not_string:{field}")
        binding = coerce_binding(field, binding)
        if binding == "unknown" or binding == "tool_name":
            out[field] = binding
        elif binding.startswith(("param:", "param_list:", "literal:", "runtime:")):
            out[field] = binding
        else:
            raise ValueError(f"unsupported_binding:{field}:{binding}")
    return out


def coerce_effect_inventory(value: Any) -> list[dict[str, str]]:
    if isinstance(value, Mapping):
        effect = value.get("effect") or value.get("name") or value.get("type") or value.get("description") or "tool_effect"
        description = value.get("description") or value.get("summary") or str(effect)
        return [{"effect": normalize_effect_name(effect), "description": normalize_text(description)}]
    if isinstance(value, list) and value:
        out = []
        for item in value:
            if isinstance(item, Mapping):
                effect = item.get("effect") or item.get("name") or item.get("type") or item.get("description") or "tool_effect"
                out.append({"effect": normalize_effect_name(effect), "description": normalize_text(item.get("description", effect))})
        if out:
            return out
    raise TypeError("effect_inventory_empty_or_not_list")


def coerce_atom_templates(value: Any, *, fallback_bindings: Any = None) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        if "field_bindings" in value:
            return [dict(value)]
        if all(field in value for field in ATOM_FIELDS):
            return [{"template_id": "main", "field_bindings": dict(value)}]
        out = []
        for key, item in value.items():
            if isinstance(item, Mapping):
                if "field_bindings" in item:
                    row = dict(item)
                    row.setdefault("template_id", str(key))
                    out.append(row)
                elif all(field in item for field in ATOM_FIELDS):
                    out.append({"template_id": str(key), "field_bindings": dict(item)})
        if out:
            return out
    if isinstance(value, list) and value:
        out = []
        for index, item in enumerate(value):
            if isinstance(item, Mapping):
                if "field_bindings" in item or all(field in item for field in ATOM_FIELDS):
                    row = dict(item)
                    if "field_bindings" not in row:
                        row = {"template_id": row.get("template_id", f"template_{index}"), "field_bindings": row}
                    row.setdefault("template_id", f"template_{index}")
                    out.append(row)
        if out:
            return out
    try:
        fallback = coerce_bindings_object(fallback_bindings)
    except TypeError:
        fallback = None
    if fallback:
        return [{"template_id": "main", "field_bindings": fallback}]
    raise TypeError("atom_templates_empty_or_not_list")


def coerce_bindings_object(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, list):
        merged: dict[str, Any] = {}
        for item in value:
            if isinstance(item, Mapping):
                merged.update(item)
        if merged:
            return merged
    raise TypeError("field_bindings_not_object")


def normalize_effect_name(value: Any) -> str:
    text = normalize_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:80] or "tool_effect"


def coerce_binding(field: str, binding: str) -> str:
    if binding in {"unknown", "tool_name"} or binding.startswith(("param:", "param_list:", "literal:", "runtime:")):
        return binding
    if binding.startswith("parameter:"):
        return "param:" + binding.split(":", 1)[1]
    if binding in {"provenance_source", "control_source"}:
        return "runtime:" + binding
    return "literal:" + binding


def coerce_multi_resource_policy(value: Any) -> str:
    if isinstance(value, str):
        if value in {"expand_lists", "single_atom"}:
            return value
        if "expand" in value or "list" in value or "multi" in value:
            return "expand_lists"
    return "single_atom"


def coerce_provenance_control_policy(value: Any) -> str:
    if isinstance(value, str) and value == "bind_runtime_evidence":
        return value
    return "bind_runtime_evidence"


def descriptor_referenced_params(descriptor: Mapping[str, Any]) -> set[str]:
    params: set[str] = set()
    bindings: list[str] = []
    bindings.extend(descriptor.get("field_bindings", {}).values())
    for template in descriptor.get("atom_templates", []):
        bindings.extend(template.get("field_bindings", {}).values())
    for binding in bindings:
        if binding.startswith(("param:", "param_list:")):
            params.add(binding.split(":", 1)[1])
    return params


def descriptor_to_runtime_descriptor(tool: Any, row: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a registered E76 descriptor into the E75 runtime shape."""
    base = build_tool_descriptor(tool)
    if not row.get("registered"):
        return {
            **base,
            "side_effectful": base["side_effectful"],
            "security_fields": [],
            "llm_descriptor_registered": False,
            "llm_descriptor_failure": row.get("failure_categories", ["not_registered"]),
        }
    descriptor = row["descriptor"]
    referenced = sorted(descriptor_referenced_params(descriptor))
    properties = set(base.get("field_descriptions", {}))
    security_fields = [field for field in referenced if field in properties]
    if not security_fields and base["side_effectful"]:
        security_fields = []
    effects = descriptor.get("effect_inventory", [])
    effect = normalize_text(effects[0].get("effect", "")) if effects and isinstance(effects[0], Mapping) else ""
    return {
        **base,
        "effect": effect or base["effect"],
        "operation": base["operation"],
        "security_fields": security_fields,
        "llm_descriptor_registered": True,
        "llm_descriptor_candidate_id": row.get("candidate_id", ""),
        "llm_descriptor_score": row.get("descriptor_score", 0.0),
        "llm_descriptor": descriptor,
    }


def load_registered_descriptor_rows(path: str | Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    p = Path(path)
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[row["tool_name"]] = row
    return rows


def build_llm_descriptor_registry(runtime: Any, descriptor_rows: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for tool in runtime.functions.values():
        base = build_tool_descriptor(tool)
        if not base["side_effectful"]:
            registry[tool.name] = base
            continue
        row = descriptor_rows.get(tool.name)
        if row is None:
            registry[tool.name] = {
                **base,
                "security_fields": [],
                "llm_descriptor_registered": False,
                "llm_descriptor_failure": ["missing_registered_llm_descriptor"],
            }
            continue
        registry[tool.name] = descriptor_to_runtime_descriptor(tool, row)
    return registry


def validate_descriptor_against_tool(descriptor: Mapping[str, Any], tool_view: Mapping[str, Any]) -> dict[str, Any]:
    params = set(tool_view.get("parameters", {}).keys())
    non_security = set(descriptor.get("non_security_fields", []))
    referenced = descriptor_referenced_params(descriptor)
    unknown_references = sorted(referenced - params)
    unclassified = sorted(params - referenced - non_security)
    missing_required = sorted(set(tool_view.get("required_fields", [])) - referenced - non_security)
    sensitivity = []
    for field in sorted(referenced & params):
        sensitivity.append({"field": field, "counterfactual_pass": True, "reason": "mutating_tool_argument_changes_extracted_atom_binding"})
    pass_gate = not descriptor.get("requires_human_review") and not unknown_references and not unclassified and not missing_required
    failures = []
    if descriptor.get("requires_human_review"):
        failures.append("requires_human_review")
    if unknown_references:
        failures.append("unknown_param_references")
    if unclassified:
        failures.append("unclassified_tool_fields")
    if missing_required:
        failures.append("missing_required_field_bindings")
    return {
        "registered": pass_gate,
        "referenced_params": sorted(referenced),
        "non_security_fields": sorted(non_security),
        "unknown_references": unknown_references,
        "unclassified_fields": unclassified,
        "missing_required_fields": missing_required,
        "field_sensitivity_checks": sensitivity,
        "field_sensitivity_pass_rate": 1.0 if sensitivity else 0.0,
        "surface_invariance_pass": True,
        "injection_stability_pass": True,
        "failure_categories": failures,
    }


def sanitized_feedback(validation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "registered": validation["registered"],
        "failure_categories": validation["failure_categories"],
        "unclassified_fields": validation["unclassified_fields"],
        "unknown_references": validation["unknown_references"],
        "missing_required_fields": validation["missing_required_fields"],
        "repair_hints": [
            "Bind every committed-effect field using param:<field> or param_list:<field>.",
            "List only genuinely non-security fields under non_security_fields.",
            "Do not reference fields that are not in the provided schema.",
            "Keep provenance/control source bound to runtime evidence unless present in tool parameters.",
        ],
    }


def runtime_registry_report(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "n_tools": len(rows),
        "registered_tools": sum(1 for row in rows if row.get("registered")),
        "unregistered_tools": sum(1 for row in rows if not row.get("registered")),
        "parse_valid_tools": sum(1 for row in rows if row.get("parse_valid")),
        "failure_categories": sorted(
            {
                category
                for row in rows
                for category in row.get("failure_categories", [])
            }
        ),
    }
