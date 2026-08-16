from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contracts import ToolSpec, stable_hash


FORBIDDEN_PROMPT_TERMS = (
    "reference_contract",
    "expected_atoms",
    "expected_decision",
    "violation_reasons",
    "gold_atoms",
    "gold_labels",
    "gold contract",
    "gold atom",
)


def build_proposal_prompt(tool: ToolSpec) -> str:
    payload = {
        "task": "Propose an effect contract for a side-effectful tool.",
        "tool": deployable_tool_view(tool),
        "contract_schema": contract_schema(),
        "output_protocol": output_protocol(),
        "format_example": format_example_contract(),
        "rules": [
            "Return the contract object itself as one valid JSON object with no markdown fence.",
            "If the runtime cannot produce raw JSON and forces free text, put only the final contract inside <FINAL_JSON> and </FINAL_JSON>.",
            "Every security-relevant side effect must be represented as one or more templates.",
            "Separate operated resources from target principals.",
            "Use literal:<value> for a stable synthetic resource when the tool has no explicit resource object.",
            "Bind commit mode, visibility, provenance source, and control source when the tool exposes them.",
            "Do not include labels, hidden evaluation data, or validation answers.",
            "Use the example only for JSON shape; do not copy its tool name, effects, or fields.",
        ],
    }
    return render_model_prompt(payload)


def build_refinement_prompt(tool: ToolSpec, previous_output: str, failure_summary: dict[str, Any]) -> str:
    payload = {
        "task": "Revise the previous effect contract JSON so it covers the validation feedback.",
        "tool": deployable_tool_view(tool),
        "previous_output": previous_output[:8000],
        "validation_feedback": sanitized_failure_summary(failure_summary),
        "contract_schema": contract_schema(),
        "output_protocol": output_protocol(),
        "format_example": format_example_contract(),
        "rules": [
            "Return the revised contract object itself as one valid JSON object with no markdown fence.",
            "If the runtime cannot produce raw JSON and forces free text, put only the final revised contract inside <FINAL_JSON> and </FINAL_JSON>.",
            "Add missing security-relevant templates and bindings.",
            "Preserve resource versus target-principal separation.",
            "Do not add labels, hidden evaluation data, or validation answers.",
            "Use the example only for JSON shape; do not copy its tool name, effects, or fields.",
        ],
    }
    return render_model_prompt(payload)


def render_model_prompt(payload: dict[str, Any]) -> str:
    sections = [
        "/no_think",
        "Return exactly one JSON object. Do not explain. Do not include markdown.",
        "The output object must have only these top-level keys: tool_name, templates, non_security_fields, requires_human_review, provenance.",
        (
            "Do not echo prompt wrapper keys such as task, tool, contract_schema, output_protocol, "
            "format_example, rules, prior model output, or validation feedback."
        ),
        "If a non-JSON runtime inserts reasoning, the parser will ignore it, but the final answer must still be the contract JSON object.",
        f"TASK:\n{payload['task']}",
        f"TOOL_VIEW_JSON:\n{json.dumps(payload['tool'], indent=2, sort_keys=True)}",
        f"CONTRACT_FIELD_SCHEMA_JSON:\n{json.dumps(payload['contract_schema'], indent=2, sort_keys=True)}",
        f"EXAMPLE_SHAPE_ONLY_DO_NOT_COPY_JSON:\n{json.dumps(payload['format_example'], indent=2, sort_keys=True)}",
        "RULES:\n- " + "\n- ".join(payload["rules"]),
    ]
    if "previous_output" in payload:
        sections.insert(6, f"PREVIOUS_MODEL_OUTPUT_TRUNCATED:\n{payload['previous_output']}")
    if "validation_feedback" in payload:
        sections.insert(7, f"VALIDATION_FEEDBACK_SUMMARY_JSON:\n{json.dumps(payload['validation_feedback'], indent=2, sort_keys=True)}")
    return "\n\n".join(sections)


def deployable_tool_view(tool: ToolSpec) -> dict[str, Any]:
    return {
        "name": tool.name,
        "domain": tool.domain,
        "description": tool.description,
        "parameter_schema": tool.parameter_schema,
        "example_calls": {
            "example_a": tool.example_safe_call,
            "example_b": tool.example_unsafe_call,
            "example_c": tool.example_unknown_call,
        },
    }


def contract_schema() -> dict[str, Any]:
    return {
        "tool_name": "string",
        "templates": [
            {
                "effect_type": "string",
                "operation": "string",
                "resource_field": "string or literal:<resource>",
                "resource_type": "message|file|channel|calendar_event|workspace|account|transaction|recipient",
                "target_principal_field": "optional string",
                "target_role": "optional string",
                "visibility_field": "optional string",
                "permission_delta_field": "optional string",
                "commit_mode_field": "commit_mode",
                "default_commit_mode": "draft|commit|share|transfer",
                "control_source_field": "control_source",
                "provenance_source_field": "provenance_source",
                "security_relevant_fields": ["field names"],
                "emit_if_field": "optional string",
                "emit_if_values": ["optional triggering values"],
            }
        ],
        "non_security_fields": ["field names that do not alter pre-commit authorization"],
        "requires_human_review": False,
        "provenance": {"proposer": "local_llm"},
    }


def output_protocol() -> dict[str, Any]:
    return {
        "primary": "raw_json_object",
        "fallback_final_answer_start": "<FINAL_JSON>",
        "fallback_final_answer_end": "</FINAL_JSON>",
        "parser_behavior": "A raw JSON object is preferred. If free text is emitted, only the final tagged or balanced JSON object is evaluated.",
    }


def format_example_contract() -> dict[str, Any]:
    return {
        "tool_name": "grant_project_viewer",
        "templates": [
            {
                "effect_type": "project_viewer_added",
                "operation": "grant_project_viewer",
                "resource_field": "project_id",
                "resource_type": "workspace",
                "target_principal_field": "viewer_id",
                "target_role": "viewer",
                "visibility_field": None,
                "permission_delta_field": "role",
                "commit_mode_field": "commit_mode",
                "default_commit_mode": "commit",
                "control_source_field": "control_source",
                "provenance_source_field": "provenance_source",
                "security_relevant_fields": [
                    "project_id",
                    "viewer_id",
                    "role",
                    "commit_mode",
                    "control_source",
                    "provenance_source",
                ],
                "emit_if_field": None,
                "emit_if_values": [],
            }
        ],
        "non_security_fields": ["message", "comment"],
        "requires_human_review": False,
        "provenance": {"proposer": "local_llm"},
    }


def sanitized_failure_summary(summary: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "parse_error",
        "failure_categories",
        "missing_required_atom_count",
        "required_atom_coverage",
        "required_resource_binding_coverage",
        "required_target_principal_coverage",
        "unsafe_pre_allow_rate",
        "false_deny_rate",
        "coverage",
        "decision_accuracy",
        "n_failures_shown",
        "hints",
    }
    return {key: value for key, value in summary.items() if key in allowed_keys}


def prompt_hash(prompt: str) -> str:
    return stable_hash({"prompt": prompt})


def prompt_leakage_scan(prompt: str) -> dict[str, Any]:
    lowered = prompt.lower()
    hits = [term for term in FORBIDDEN_PROMPT_TERMS if term in lowered]
    return {"leakage_free": not hits, "hits": hits, "prompt_hash": prompt_hash(prompt)}


def prompt_record(
    *,
    prompt_id: str,
    tool_name: str,
    setting: str,
    prompt: str,
    backend: str,
    model: str,
    raw_output: str = "",
    status: str = "created",
) -> dict[str, Any]:
    scan = prompt_leakage_scan(prompt)
    return {
        "prompt_id": prompt_id,
        "tool_name": tool_name,
        "setting": setting,
        "backend": backend,
        "model": model,
        "prompt_hash": scan["prompt_hash"],
        "leakage_free": scan["leakage_free"],
        "leakage_hits": scan["hits"],
        "prompt": prompt,
        "raw_output": raw_output,
        "status": status,
    }


def tool_prompt_fingerprint(tool: ToolSpec) -> str:
    return stable_hash(asdict(tool))
