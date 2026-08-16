from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .perturbations import is_forbidden_trace_label_key, strip_trace_labels
from .schema import ClaimScope, MethodInputView, ToolEffectPrediction, ToolEffectStressCase


ORACLE_FIELDS = {
    "realized_effect",
    "risk_label",
    "expected_decision",
    "effect_label_source",
    "labels",
    "action_id",
}


ALLOWED_FIELDS_BY_VIEW = {
    MethodInputView.TOOL_SURFACE_ONLY.value: {"tool_inventory", "tool_call_or_plan"},
    MethodInputView.ARG_SCHEMA_ONLY.value: {"tool_inventory", "tool_call_or_plan"},
    MethodInputView.STATIC_TEXT.value: {"user_task", "tool_inventory", "tool_call_or_plan"},
    MethodInputView.PLAN_TEXT.value: {"user_task", "tool_inventory", "tool_call_or_plan"},
    MethodInputView.STEP_TEXT.value: {"user_task", "tool_inventory", "tool_call_or_plan"},
    MethodInputView.TRAJECTORY_TEXT.value: {"user_task", "tool_inventory", "tool_call_or_plan"},
    MethodInputView.GRAPH_TOOL_NAME.value: {"user_task", "tool_inventory", "tool_call_or_plan"},
    MethodInputView.GRAPH_EFFECT_RESOURCE.value: {"user_task", "tool_inventory", "tool_call_or_plan"},
    MethodInputView.EXECUTION_EVIDENCE.value: {"user_task", "tool_inventory", "tool_call_or_plan"},
    MethodInputView.ORACLE_EFFECT_RESOURCE.value: {"realized_effect", "resource", "risk_label", "expected_decision"},
}


@dataclass
class AccessAudit:
    allowed: bool
    violations: list[str]


def allowed_fields_for_view(view: str) -> list[str]:
    return sorted(ALLOWED_FIELDS_BY_VIEW.get(view, set()))


def build_method_input(case: ToolEffectStressCase, view: str) -> dict[str, Any]:
    allowed = ALLOWED_FIELDS_BY_VIEW[view]
    obj = case.to_dict()
    result = {field: obj[field] for field in allowed if field in obj}
    if view in {
        MethodInputView.STATIC_TEXT.value,
        MethodInputView.PLAN_TEXT.value,
        MethodInputView.STEP_TEXT.value,
        MethodInputView.TRAJECTORY_TEXT.value,
        MethodInputView.GRAPH_TOOL_NAME.value,
    }:
        result = strip_trace_labels(result)
    if view == MethodInputView.TOOL_SURFACE_ONLY.value:
        result = {"tool_names": [tool.get("name") for tool in case.tool_inventory]}
    if view == MethodInputView.ARG_SCHEMA_ONLY.value:
        result = {"arg_schema": _arg_schema(case.tool_call_or_plan)}
    return result


def audit_prediction_access(prediction: ToolEffectPrediction) -> AccessAudit:
    allowed = set(prediction.allowed_input_fields or allowed_fields_for_view(prediction.method_input_view))
    accessed = set(prediction.accessed_input_fields)
    violations = sorted(accessed - allowed)
    if prediction.method_input_view != MethodInputView.ORACLE_EFFECT_RESOURCE.value:
        violations.extend(sorted(accessed & ORACLE_FIELDS))
    if prediction.method_input_view not in {
        MethodInputView.EXECUTION_EVIDENCE.value,
        MethodInputView.ORACLE_EFFECT_RESOURCE.value,
    } and prediction.claim_scope == ClaimScope.UPPER_BOUND.value:
        violations.append("upper_bound_without_execution_or_oracle_view")
    if prediction.method_input_view == MethodInputView.ORACLE_EFFECT_RESOURCE.value and prediction.claim_scope != ClaimScope.UPPER_BOUND.value:
        violations.append("oracle_effect_resource_must_be_upper_bound")
    return AccessAudit(allowed=not violations, violations=sorted(set(violations)))


def contains_forbidden_label_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if is_forbidden_trace_label_key(key, child) or contains_forbidden_label_key(child):
                return True
    if isinstance(value, list):
        return any(contains_forbidden_label_key(child) for child in value)
    return False


def _arg_schema(payload: dict[str, Any]) -> list[str]:
    args = payload.get("arguments") or payload.get("args") or {}
    if not isinstance(args, dict):
        return []
    return sorted(args)
