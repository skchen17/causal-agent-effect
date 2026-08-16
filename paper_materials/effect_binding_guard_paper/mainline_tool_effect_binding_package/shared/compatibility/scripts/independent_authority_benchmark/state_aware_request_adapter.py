"""Frozen diagnostic adapter from state-aware calls to authority requests.

Unlike :mod:`state_aware_view`, this module contains explicit, tool-specific
operation knowledge.  Its direct authorization metrics are therefore reported
separately from the representation-only collision audit.
"""

from __future__ import annotations

from typing import Any


def _atom(operation: str, kind: str, resource: str, *, target: str | None = None,
          qualifiers: dict[str, Any] | None = None, mode: str = "commit") -> dict[str, Any]:
    return {
        "effect": operation,
        "operation": operation,
        "resource_type": kind,
        "resource_id": resource,
        "target_principal": target,
        "qualifiers": qualifiers or {},
        "commit_mode": mode,
    }


def requests(view: dict[str, Any]) -> list[dict[str, Any]]:
    tool = view["tool_name"]
    args = view["totalized_arguments"]
    resources = view["referenced_resources"]
    mode = args.get("commit_mode", "commit")
    output: list[dict[str, Any]] = []

    if tool == "schedule_meeting":
        resource = resources[0]
        calendar_id = resource["canonical_id"]
        old = resource["trusted_attributes"].get("referenced_event") or {}
        q = {"event_id": args["event_id"]}
        if mode == "draft":
            return [_atom("calendar.draft.save", "calendar", calendar_id, qualifiers=q, mode="draft")]
        if mode == "scheduled":
            return [_atom("calendar.event.schedule", "calendar", calendar_id, qualifiers=q, mode="scheduled")]
        q.update({"visibility": args["visibility"], "recurrence": args["recurrence"]})
        output.append(_atom("calendar.event.upsert", "calendar", calendar_id, qualifiers=q))
        old_people, new_people = set(old.get("participants", [])), set(args.get("participants", []))
        for person in sorted(new_people - old_people):
            output.append(_atom("calendar.participant.invite", "calendar", calendar_id, target=person,
                                qualifiers={"event_id": args["event_id"]}))
        for person in sorted(old_people - new_people):
            output.append(_atom("calendar.participant.remove", "calendar", calendar_id, target=person,
                                qualifiers={"event_id": args["event_id"]}))
        if not old or old.get("visibility") != args["visibility"]:
            output.append(_atom("calendar.visibility.set", "calendar", calendar_id,
                                qualifiers={"visibility": args["visibility"], "event_id": args["event_id"]}))
        if not old or old.get("recurrence") != args["recurrence"]:
            output.append(_atom("calendar.recurrence.set", "calendar", calendar_id,
                                qualifiers={"recurrence": args["recurrence"], "event_id": args["event_id"]}))

    elif tool == "share_document":
        for resource in resources:
            doc_id = resource["canonical_id"]
            attrs = resource["trusted_attributes"]
            if mode == "draft":
                output.append(_atom("document.share.draft", "document", doc_id, mode="draft"))
                continue
            visibility = args.get("visibility", attrs.get("default_visibility"))
            if attrs.get("visibility") != visibility:
                output.append(_atom("document.visibility.set", "document", doc_id,
                                    qualifiers={"visibility": visibility}))
            if visibility == "public" and attrs.get("visibility") != "public":
                output.append(_atom("document.public_link.create", "document", doc_id,
                                    target="principal:public"))
            old_acl = attrs.get("referenced_acl", {})
            for person in args.get("recipients", []):
                old_permission = old_acl.get(person)
                if args.get("operation", "grant") == "revoke":
                    if old_permission is not None:
                        output.append(_atom("document.share.revoke", "document", doc_id, target=person,
                                            qualifiers={"permission": old_permission}))
                elif old_permission is None:
                    output.append(_atom("document.share.grant", "document", doc_id, target=person,
                                        qualifiers={"permission": args["permission"]}))
                elif old_permission != args["permission"]:
                    output.append(_atom("document.share.change", "document", doc_id, target=person,
                                        qualifiers={"permission": args["permission"]}))

    elif tool == "post_message":
        for resource in resources:
            channel_id = resource["canonical_id"]
            if mode == "draft":
                output.append(_atom("message.draft.save", "channel", channel_id, mode="draft"))
            elif mode == "scheduled":
                output.append(_atom("message.schedule", "channel", channel_id, mode="scheduled"))
            else:
                output.append(_atom("message.post", "channel", channel_id,
                                    qualifiers={"payload_class": args["payload_class"]}))
                for person in sorted(set(args.get("recipients", []))):
                    output.append(_atom("message.notify", "channel", channel_id, target=person))
                if resource["trusted_attributes"].get("external_bridge"):
                    output.append(_atom("message.external_relay", "channel", channel_id,
                                        target="principal:external"))

    elif tool == "transfer_funds":
        account, payee = resources[0], resources[1]
        q = {"amount": args["amount"], "currency": args["currency"]}
        if mode == "draft":
            output.append(_atom("bank.transfer.draft", "bank_account", account["canonical_id"],
                                target=payee["canonical_id"], mode="draft"))
        elif mode == "scheduled":
            output.append(_atom("bank.transfer.schedule", "bank_account", account["canonical_id"],
                                target=payee["canonical_id"], qualifiers=q, mode="scheduled"))
        else:
            fee = round(float(args["amount"]) * float(account["trusted_attributes"]["fee_rate"]), 2)
            output.append(_atom("bank.transfer.commit", "bank_account", account["canonical_id"],
                                target=payee["canonical_id"], qualifiers=q))
            output.append(_atom("bank.balance.debit", "bank_account", account["canonical_id"],
                                qualifiers={"amount": round(float(args["amount"]) + fee, 2), "currency": args["currency"]}))
            if fee > 0:
                output.append(_atom("bank.fee.charge", "bank_account", account["canonical_id"],
                                    qualifiers={"amount": fee, "currency": args["currency"]}))
            if account["trusted_attributes"].get("compliance_hold"):
                output.append(_atom("bank.compliance.override", "bank_account", account["canonical_id"]))
    else:
        raise ValueError(f"unsupported tool: {tool}")
    return output


def contract() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "state_aware_request_adapter_v1",
        "input": "state_aware_raw_call_view_v1",
        "disclosure": "Contains static per-tool operation and compound-request knowledge.",
        "forbidden_inputs": ["post_state", "source_transitions", "typed_effects", "ideal_decision"],
    }
