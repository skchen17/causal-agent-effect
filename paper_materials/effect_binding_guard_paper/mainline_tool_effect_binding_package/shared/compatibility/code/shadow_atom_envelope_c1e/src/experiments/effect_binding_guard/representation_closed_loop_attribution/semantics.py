"""Decision semantics for the tool-call-level representation ablation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def tool_call_level_compare(
    user_task: str,
    descriptor: Mapping[str, Any],
    plan: Mapping[str, Any] | None,
    args: Mapping[str, Any],
    authorized_read_evidence: list[Any],
) -> dict[str, Any]:
    """Authorize by planned tool identity without inspecting effect fields.

    Unused parameters intentionally match E77's atom-level comparator. Call
    totalization, descriptor registration, planning, and execution remain in
    the surrounding E77 runtime.
    """
    del user_task, args, authorized_read_evidence
    tools = plan.get("tools") if isinstance(plan, Mapping) else None
    if not isinstance(tools, Mapping):
        return {
            "decision": "NEEDS_REPLAN",
            "reasons": ["task_permission_plan_unavailable"],
            "checks": [],
        }
    tool_name = str(descriptor.get("tool_name", ""))
    if tool_name not in tools:
        return {
            "decision": "NEEDS_REPLAN",
            "reasons": ["tool_not_in_initial_permission_plan"],
            "checks": [],
        }
    return {
        "decision": "ALLOW",
        "reasons": ["tool_identity_present_in_initial_permission_plan"],
        "checks": [],
    }

