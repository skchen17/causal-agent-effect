"""Deterministic pre-commit path; this module has no LLM dependency."""

from __future__ import annotations

import copy
import json
from typing import Any

from shared.compatibility.scripts.independent_authority_benchmark.authority_model import (
    atom_request, authority_state, authorize_all, default_context,
)
from shared.compatibility.scripts.independent_authority_benchmark.descriptor_runtime import compile_descriptor
from shared.compatibility.scripts.independent_authority_benchmark.sandbox import execute
from shared.compatibility.scripts.independent_authority_benchmark.transition_oracle import derive

from .cases import SCHEMAS


DOMAINS = {"schedule_meeting": "calendar", "share_document": "workspace", "transfer_funds": "banking"}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def totalize(tool: str, arguments: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(arguments)
    result.setdefault("commit_mode", "commit")
    if tool == "schedule_meeting":
        calendar = state["aliases"].get(result["calendar_ref"], result["calendar_ref"])
        if calendar in state["calendars"]:
            result.setdefault("visibility", state["calendars"][calendar]["default_visibility"])
            result.setdefault("recurrence", state["calendars"][calendar]["default_recurrence"])
        result.setdefault("participants", [])
    elif tool == "share_document":
        result.setdefault("operation", "grant")
        result.setdefault("recipients", [])
        doc = state["aliases"].get(result["doc_ref"], result["doc_ref"])
        if doc in state["documents"]:
            result.setdefault("visibility", state["documents"][doc]["default_visibility"])
    return result


def evaluate(case: dict[str, Any], proposed: dict[str, Any] | None, descriptor: dict[str, Any],
             *, parse_error: str | None = None) -> dict[str, Any]:
    base = {
        "case_id": case["case_id"], "scenario": case["scenario"], "task": case["task"],
        "trusted_observations": case["trusted_observations"], "untrusted_observations": case["untrusted_observations"],
        "pre_state": case["pre_state"], "proposed_call": proposed, "parse_error": parse_error,
    }
    if parse_error or proposed is None:
        return {**base, "decision": "ABSTAIN", "decision_reasons": ["model_call_parse_failure"],
                "checked_call": None, "executed_call": None, "atoms": [], "reconciliation_passed": None,
                "post_state": case["pre_state"]}
    tool = proposed["tool_name"]
    if tool != case["tool_name"] or tool not in SCHEMAS:
        return {**base, "decision": "ABSTAIN", "decision_reasons": ["unexpected_tool"],
                "checked_call": proposed, "executed_call": None, "atoms": [], "reconciliation_passed": None,
                "post_state": case["pre_state"]}
    missing = [name for name in SCHEMAS[tool]["required"] if name not in proposed["arguments"]]
    if missing:
        return {**base, "decision": "ABSTAIN", "decision_reasons": ["missing_required_arguments:" + ",".join(missing)],
                "checked_call": proposed, "executed_call": None, "atoms": [], "reconciliation_passed": None,
                "post_state": case["pre_state"]}
    try:
        arguments = totalize(tool, proposed["arguments"], case["pre_state"])
        checked = {"tool_name": tool, "arguments": arguments}
        runtime_row = {"tool_name": tool, "arguments": arguments, "pre_state": case["pre_state"]}
        atoms = compile_descriptor(descriptor, runtime_row)
        requests = [atom_request(atom, default_context(DOMAINS[tool])) for atom in atoms]
        decision, reasons = authorize_all(requests, authority_state(), default_context(DOMAINS[tool]),
                                          partial=True, inventory_complete=True)
    except Exception as exc:
        return {**base, "decision": "ABSTAIN", "decision_reasons": [f"runtime_binding_failure:{type(exc).__name__}"],
                "checked_call": proposed, "executed_call": None, "atoms": [], "reconciliation_passed": None,
                "post_state": case["pre_state"]}
    executed_call = None
    post_state = case["pre_state"]
    observed: list[dict[str, Any]] = []
    reconciliation = None
    if decision == "ALLOW":
        executed_call = copy.deepcopy(checked)
        post_state = execute(runtime_row)
        observed = derive(case["pre_state"], post_state, tool)
        normalized_atoms = [atom_request(atom, default_context(DOMAINS[tool])) for atom in atoms]
        normalized_observed = [{"subject": default_context(DOMAINS[tool])["subject"], **item} for item in observed]
        # Python structural equality intentionally treats integral JSON numbers
        # such as 100 and 100.0 as the same semantic value.
        reconciliation = normalized_atoms == normalized_observed
    return {
        **base, "totalized_arguments": arguments, "atoms": atoms, "authority_requests": requests,
        "decision": decision, "decision_reasons": reasons, "checked_call": checked,
        "executed_call": executed_call, "post_state": post_state, "observed_transitions": observed,
        "check_use_equal": executed_call is None or canonical(executed_call) == canonical(checked),
        "reconciliation_passed": reconciliation,
    }
