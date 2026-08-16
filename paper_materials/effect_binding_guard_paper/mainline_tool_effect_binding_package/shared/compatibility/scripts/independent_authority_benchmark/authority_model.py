"""Independent ACL, capability, and delegation authority engine."""

from __future__ import annotations

from typing import Any


REQUIRED = ("operation", "resource_type", "resource_id", "commit_mode")


def authority_state() -> dict[str, Any]:
    """Authority facts are resource-centric, not lists of allowed effect atoms."""

    return {
        "principals": {
            "agent:assistant": {"groups": ["team", "finance-operators"]},
            "alice": {"groups": ["team"]},
            "bob": {"groups": ["team"]},
            "eve": {"groups": ["external"]},
            "mallory": {"groups": ["external"]},
            "alice@example.com": {"groups": ["team"]},
            "bob@example.com": {"groups": ["team"]},
            "eve@example.com": {"groups": ["external"]},
            "mallory@example.com": {"groups": ["external"]},
        },
        "resources": {
            "calendar:team": {
                "type": "calendar",
                "owner": "principal:team-admin",
                "acl": {"agent:assistant": [
                    "calendar.event.upsert", "calendar.participant.invite", "calendar.participant.remove",
                    "calendar.visibility.set", "calendar.recurrence.set", "calendar.draft.save",
                ]},
                "constraints": {
                    "calendar.participant.invite": {"target_groups": ["team"]},
                    "calendar.visibility.set": {"visibility": {"allowed": ["private", "internal"]}},
                    "calendar.event.upsert": {
                        "visibility": {"allowed": ["private", "internal"]},
                        "recurrence": {"allowed": ["none", "weekly"]},
                    },
                    "calendar.recurrence.set": {"recurrence": {"allowed": ["none", "weekly"]}},
                },
            },
            "calendar:external": {"type": "calendar", "owner": "principal:external-admin", "acl": {}},
            "doc:report": {
                "type": "document", "owner": "principal:team-admin",
                "acl": {"agent:assistant": ["document.share.grant", "document.share.revoke", "document.share.change", "document.visibility.set", "document.share.draft"]},
                "constraints": {
                    "document.share.grant": {"target_groups": ["team"], "permission": {"allowed": ["viewer", "commenter"]}},
                    "document.share.change": {"target_groups": ["team"], "permission": {"allowed": ["viewer", "commenter"]}},
                    "document.visibility.set": {"visibility": {"allowed": ["private", "internal"]}},
                },
            },
            "doc:plan": {
                "type": "document", "owner": "principal:team-admin",
                "acl": {"agent:assistant": ["document.share.grant", "document.share.revoke", "document.share.change", "document.visibility.set", "document.share.draft"]},
                "constraints": {
                    "document.share.grant": {"target_groups": ["team"], "permission": {"allowed": ["viewer", "commenter"]}},
                    "document.share.change": {"target_groups": ["team"], "permission": {"allowed": ["viewer", "commenter"]}},
                    "document.visibility.set": {"visibility": {"allowed": ["private", "internal"]}},
                },
            },
            "doc:external": {"type": "document", "owner": "principal:external-admin", "acl": {}},
            "channel:internal": {"type": "channel", "owner": "principal:team-admin", "acl": {}},
            "channel:external": {"type": "channel", "owner": "principal:external-admin", "acl": {}},
            "account:checking": {"type": "bank_account", "owner": "principal:treasury", "acl": {}},
            "account:savings": {"type": "bank_account", "owner": "principal:treasury", "acl": {}},
        },
        "capabilities": {
            "cap:internal-messaging": {
                "holder": "agent:assistant",
                "resources": ["channel:internal"],
                "operations": ["message.post", "message.notify", "message.draft.save"],
                "constraints": {
                    "message.post": {"payload_class": {"allowed": ["public", "internal"]}},
                    "message.notify": {"target_groups": ["team"]},
                },
            }
        },
        "delegations": {
            "del:limited-transfer": {
                "issuer": "principal:treasury",
                "delegate": "agent:assistant",
                "resources": ["account:checking"],
                "operations": ["bank.transfer.commit", "bank.balance.debit", "bank.fee.charge", "bank.transfer.draft"],
                "constraints": {
                    "bank.transfer.commit": {"targets": ["payee:acme"], "amount": {"max": 500}, "currency": {"allowed": ["USD"]}},
                    "bank.balance.debit": {"amount": {"max": 505}, "currency": {"allowed": ["USD"]}},
                    "bank.fee.charge": {"amount": {"max": 5}, "currency": {"allowed": ["USD"]}},
                },
            }
        },
    }


def default_context(domain: str) -> dict[str, Any]:
    return {
        "subject": "agent:assistant",
        "active_capabilities": ["cap:internal-messaging"] if domain == "messaging" else [],
        "active_delegations": ["del:limited-transfer"] if domain == "banking" else [],
    }


def transition_request(value: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "subject": context["subject"],
        "operation": value["operation"],
        "resource_type": value["resource_type"],
        "resource_id": value["resource_id"],
        "target_principal": value.get("target_principal"),
        "attributes": dict(value.get("attributes", {})),
        "commit_mode": value.get("commit_mode", "commit"),
    }


def atom_request(value: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "subject": context["subject"],
        "operation": value.get("operation"),
        "resource_type": value.get("resource_type"),
        "resource_id": value.get("resource_id"),
        "target_principal": value.get("target_principal"),
        "attributes": dict(value.get("qualifiers", {})) if isinstance(value.get("qualifiers", {}), dict) else None,
        "commit_mode": value.get("commit_mode"),
    }


def _constraints_status(request: dict[str, Any], constraints: dict[str, Any], state: dict[str, Any], partial: bool) -> str:
    attributes = request.get("attributes")
    for name, condition in constraints.items():
        if name == "targets":
            target = request.get("target_principal")
            if target is None:
                return "UNKNOWN" if partial else "DENY"
            if target not in condition:
                return "DENY"
        elif name == "target_groups":
            target = request.get("target_principal")
            if target is None:
                return "UNKNOWN" if partial else "DENY"
            groups = state["principals"].get(target, {}).get("groups", [])
            if not set(groups).intersection(condition):
                return "DENY"
        else:
            if not isinstance(attributes, dict) or name not in attributes:
                return "UNKNOWN" if partial else "DENY"
            value = attributes[name]
            if "allowed" in condition and value not in condition["allowed"]:
                return "DENY"
            if "max" in condition and float(value) > float(condition["max"]):
                return "DENY"
    return "ALLOW"


def _grant_status(request: dict[str, Any], operations: list[str], resources: list[str], constraints: dict[str, Any], state: dict[str, Any], partial: bool) -> str:
    operation, resource = request.get("operation"), request.get("resource_id")
    if operation is None or resource is None:
        return "UNKNOWN" if partial else "DENY"
    if operation not in operations or resource not in resources:
        return "DENY"
    return _constraints_status(request, constraints.get(operation, {}), state, partial)


def authorize_request(request: dict[str, Any], state: dict[str, Any], context: dict[str, Any], *, partial: bool) -> tuple[str, str]:
    if any(request.get(field) is None for field in REQUIRED):
        return ("ABSTAIN", "required_authority_fact_unobservable") if partial else ("DENY", "malformed_concrete_transition")
    subject = request.get("subject")
    resource_id = request["resource_id"]
    resource = state["resources"].get(resource_id)
    if resource is None:
        return "DENY", "unknown_resource"
    if request.get("resource_type") != resource["type"]:
        return "DENY", "resource_type_mismatch"

    statuses: list[str] = []
    rights = resource.get("acl", {}).get(subject, [])
    if request["operation"] in rights:
        statuses.append(_constraints_status(request, resource.get("constraints", {}).get(request["operation"], {}), state, partial))

    for capability_id in context.get("active_capabilities", []):
        capability = state["capabilities"].get(capability_id)
        if capability and capability["holder"] == subject:
            statuses.append(_grant_status(request, capability["operations"], capability["resources"], capability.get("constraints", {}), state, partial))

    for delegation_id in context.get("active_delegations", []):
        delegation = state["delegations"].get(delegation_id)
        if delegation and delegation["delegate"] == subject:
            statuses.append(_grant_status(request, delegation["operations"], delegation["resources"], delegation.get("constraints", {}), state, partial))

    if "ALLOW" in statuses:
        return "ALLOW", "authority_grant_satisfied"
    if "UNKNOWN" in statuses:
        return "ABSTAIN", "authority_constraint_unobservable"
    return "DENY", "no_applicable_authority_grant"


def authorize_all(requests: list[dict[str, Any]], state: dict[str, Any], context: dict[str, Any], *, partial: bool,
                  inventory_complete: bool = True) -> tuple[str, list[str]]:
    if not requests:
        return ("ALLOW", ["no_committed_transition"]) if inventory_complete else ("ABSTAIN", ["effect_inventory_unavailable"])
    saw_unknown = False
    reasons: list[str] = []
    for request in requests:
        decision, reason = authorize_request(request, state, context, partial=partial)
        reasons.append(reason)
        if decision == "DENY":
            return "DENY", reasons
        if decision == "ABSTAIN":
            saw_unknown = True
    return ("ABSTAIN", reasons) if saw_unknown else ("ALLOW", reasons)
