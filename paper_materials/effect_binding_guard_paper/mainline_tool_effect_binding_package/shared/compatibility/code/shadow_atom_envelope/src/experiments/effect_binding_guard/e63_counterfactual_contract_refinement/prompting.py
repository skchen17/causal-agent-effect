from __future__ import annotations

import json
import os
from typing import Any

from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contracts import ToolSpec
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.prompting import (
    contract_schema,
    deployable_tool_view,
    format_example_contract,
    prompt_hash,
    prompt_leakage_scan,
)


def build_round_prompt(
    *,
    tool: ToolSpec,
    round_index: int,
    previous_contract_json: str = "",
    feedback_payload: dict[str, Any] | None = None,
) -> str:
    compact = os.environ.get("E63_COMPACT_PROMPT", "0") == "1"
    task = (
        "Propose an effect contract for a side-effectful tool."
        if round_index == 0
        else "Revise the previous effect contract using only the sanitized counterfactual validation feedback."
    )
    dump_kwargs = {"sort_keys": True, "separators": (",", ":")} if compact else {"indent": 2, "sort_keys": True}
    sections = [
        "/no_think",
        "Return exactly one JSON object. Do not explain. Do not include markdown.",
        "The output object must have only these top-level keys: tool_name, templates, non_security_fields, requires_human_review, provenance.",
        "Do not echo prompt wrapper keys. Do not include hidden evaluation materials or validation answers.",
        "Separate operated resources from target principals. A recipient/payee/member/attendee is usually a target_principal, not the operated resource.",
        "Represent every security-relevant side effect as one or more templates, including attachment disclosure, public visibility, membership changes, payment/account changes, and execution triggers.",
        "Bind commit_mode, visibility/link scope, provenance_source, and control_source whenever those fields exist.",
        f"TASK:\n{task}",
        f"ROUND_INDEX:\n{round_index}",
        f"TOOL_VIEW_JSON:\n{json.dumps(deployable_tool_view(tool), **dump_kwargs)}",
    ]
    if compact:
        sections.append(
            "COMPACT_CONTRACT_SCHEMA:\n"
            "Top-level keys: tool_name, templates, non_security_fields, requires_human_review, provenance. "
            "Each template needs effect_type, operation, resource_field, resource_type. Add target_principal_field, "
            "visibility_field, commit_mode_field, provenance_source_field, control_source_field, and field_bindings "
            "only when needed. Omit null, false, empty-list, and parser-default fields."
        )
    else:
        sections.extend(
            [
                f"CONTRACT_FIELD_SCHEMA_JSON:\n{json.dumps(contract_schema(), **dump_kwargs)}",
                f"EXAMPLE_SHAPE_ONLY_DO_NOT_COPY_JSON:\n{json.dumps(format_example_contract(), **dump_kwargs)}",
            ]
        )
    if previous_contract_json:
        sections.append(f"PREVIOUS_CONTRACT_JSON_TRUNCATED:\n{previous_contract_json[:9000]}")
    if feedback_payload is not None:
        sections.append(f"SANITIZED_COUNTERFACTUAL_FEEDBACK_JSON:\n{json.dumps(feedback_payload, indent=2, sort_keys=True)}")
    sections.append(
        "OUTPUT_RULES:\n"
        "- Return the revised/proposed contract object itself as valid JSON.\n"
        "- If unresolved mappings remain, set requires_human_review to true instead of guessing.\n"
        "- Do not include hidden evaluation materials or validation answers."
    )
    return "\n\n".join(sections)


def scan_round_prompt(prompt: str) -> dict[str, Any]:
    return prompt_leakage_scan(prompt)


def round_prompt_hash(prompt: str) -> str:
    return prompt_hash(prompt)
