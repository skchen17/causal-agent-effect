"""Effect-free state-aware observation view for pre-commit authorization.

This module deliberately exposes request text and trusted pre-state for only
the resources directly referenced by a call.  It does not derive committed
effects, authorization labels, or post-state facts.
"""

from __future__ import annotations

import copy
from typing import Any


def _resolve(value: str, mapping: dict[str, str]) -> str:
    return mapping.get(value, value)


def _resource(resource_id: str, resource_type: str, value: Any, **selected: Any) -> dict[str, Any]:
    return {
        "canonical_id": resource_id,
        "resource_type": resource_type,
        "exists": value is not None,
        "trusted_attributes": selected if value is not None else {},
    }


def build_view(row: dict[str, Any]) -> dict[str, Any]:
    """Return the frozen state-aware raw-call view for one benchmark row."""

    tool = row["tool_name"]
    args = copy.deepcopy(row["arguments"])
    state = row["pre_state"]
    resources: list[dict[str, Any]] = []
    defaults: dict[str, Any] = {}

    if tool == "schedule_meeting":
        calendar_id = _resolve(args["calendar_ref"], state["aliases"])
        calendar = state["calendars"].get(calendar_id)
        event = None if calendar is None else calendar["events"].get(args["event_id"])
        if calendar is not None:
            defaults = {
                "commit_mode": "commit",
                "visibility": calendar["default_visibility"],
                "recurrence": calendar["default_recurrence"],
            }
        args.setdefault("commit_mode", defaults.get("commit_mode", "commit"))
        if "visibility" not in args and "visibility" in defaults:
            args["visibility"] = defaults["visibility"]
        if "recurrence" not in args and "recurrence" in defaults:
            args["recurrence"] = defaults["recurrence"]
        resources.append(_resource(
            calendar_id, "calendar", calendar,
            default_visibility=None if calendar is None else calendar["default_visibility"],
            default_recurrence=None if calendar is None else calendar["default_recurrence"],
            referenced_event=copy.deepcopy(event),
        ))

    elif tool == "share_document":
        refs = args.get("doc_refs", [args["doc_ref"]])
        args.setdefault("operation", "grant")
        args.setdefault("commit_mode", "commit")
        resolved_defaults: dict[str, Any] = {}
        for ref in refs:
            doc_id = _resolve(ref, state["aliases"])
            doc = state["documents"].get(doc_id)
            recipients = args.get("recipients", [])
            referenced_acl = {} if doc is None else {
                principal: doc["acl"].get(principal) for principal in recipients
            }
            resources.append(_resource(
                doc_id, "document", doc,
                visibility=None if doc is None else doc["visibility"],
                default_visibility=None if doc is None else doc["default_visibility"],
                referenced_acl=referenced_acl,
            ))
            if doc is not None:
                resolved_defaults[doc_id] = {"visibility": doc["default_visibility"]}
        defaults = {"per_resource": resolved_defaults}

    elif tool == "post_message":
        refs = args.get("channel_refs", [args["channel_ref"]])
        args.setdefault("commit_mode", state["default_delivery_mode"])
        defaults = {"commit_mode": state["default_delivery_mode"]}
        for ref in refs:
            channel_id = _resolve(ref, state["aliases"])
            channel = state["channels"].get(channel_id)
            resources.append(_resource(
                channel_id, "channel", channel,
                external_bridge=None if channel is None else channel["external_bridge"],
            ))

    elif tool == "transfer_funds":
        account_id = _resolve(args["account_ref"], state["account_aliases"])
        payee_id = _resolve(args["payee_ref"], state["payee_aliases"])
        args.setdefault("commit_mode", "commit")
        defaults = {"commit_mode": "commit", "fee_rate": state["fee_rate"]}
        resources.append(_resource(
            account_id, "bank_account", state["balances"].get(account_id),
            balance=state["balances"].get(account_id),
            fee_rate=state["fee_rate"],
            compliance_hold=state["compliance_hold"],
        ))
        resources.append(_resource(payee_id, "payee", payee_id, canonical_payee=payee_id))
    else:
        raise ValueError(f"unsupported tool: {tool}")

    return {
        "schema_version": 1,
        "tool_name": tool,
        "totalized_arguments": args,
        "resolved_defaults": defaults,
        "referenced_resources": resources,
    }


def contract() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "state_aware_raw_call_view_v1",
        "allowed_inputs": ["tool_name", "arguments", "pre_state"],
        "exposes": [
            "totalized_arguments", "canonical resource identifiers",
            "referenced resource existence and type", "referenced pre-state attributes",
            "trusted defaults resolved at the pre-commit boundary",
        ],
        "forbidden": [
            "post_state", "source_transitions", "typed_effects", "effect_names",
            "ideal_decision", "source_oracle_labels", "global_database_serialization",
        ],
    }
