"""Post-execution state-difference oracle.

This module deliberately does not import descriptor code or use effect atoms.
It derives transition facts solely from copied before/after states.
"""

from __future__ import annotations

from typing import Any


def _fact(operation: str, resource_type: str, resource_id: str, *, target: str | None = None,
          attributes: dict[str, Any] | None = None, commit_mode: str = "commit") -> dict[str, Any]:
    return {
        "operation": operation,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "target_principal": target,
        "attributes": attributes or {},
        "commit_mode": commit_mode,
    }


def _key(value: dict[str, Any]) -> tuple[Any, ...]:
    import json
    return (value["operation"], value["resource_type"], value["resource_id"],
            value.get("target_principal") or "", json.dumps(value.get("attributes", {}), sort_keys=True),
            value.get("commit_mode", "commit"))


def derive(before: dict[str, Any], after: dict[str, Any], tool_name: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if tool_name == "schedule_meeting":
        for calendar_id in sorted(before["calendars"]):
            old_cal, new_cal = before["calendars"][calendar_id], after["calendars"][calendar_id]
            for event in new_cal["drafts"][len(old_cal["drafts"]):]:
                out.append(_fact("calendar.draft.save", "calendar", calendar_id, attributes={"event_id": event["event_id"]}, commit_mode="draft"))
            for event in new_cal["scheduled"][len(old_cal["scheduled"]):]:
                out.append(_fact("calendar.event.schedule", "calendar", calendar_id, attributes={"event_id": event["event_id"]}, commit_mode="scheduled"))
            for event_id, new in sorted(new_cal["events"].items()):
                old = old_cal["events"].get(event_id)
                if old == new:
                    continue
                out.append(_fact("calendar.event.upsert", "calendar", calendar_id,
                                 attributes={"event_id": event_id, "visibility": new["visibility"], "recurrence": new["recurrence"]}))
                old_people = set(old["participants"] if old else [])
                for principal in sorted(set(new["participants"]) - old_people):
                    out.append(_fact("calendar.participant.invite", "calendar", calendar_id, target=principal,
                                     attributes={"event_id": event_id}))
                for principal in sorted(old_people - set(new["participants"])):
                    out.append(_fact("calendar.participant.remove", "calendar", calendar_id, target=principal,
                                     attributes={"event_id": event_id}))
                if old is None or old["visibility"] != new["visibility"]:
                    out.append(_fact("calendar.visibility.set", "calendar", calendar_id,
                                     attributes={"visibility": new["visibility"], "event_id": event_id}))
                if old is None or old["recurrence"] != new["recurrence"]:
                    out.append(_fact("calendar.recurrence.set", "calendar", calendar_id,
                                     attributes={"recurrence": new["recurrence"], "event_id": event_id}))
    elif tool_name == "share_document":
        for doc_id in sorted(before["documents"]):
            old, new = before["documents"][doc_id], after["documents"][doc_id]
            for _ in new["drafts"][len(old["drafts"]):]:
                out.append(_fact("document.share.draft", "document", doc_id, commit_mode="draft"))
            for principal in sorted(set(old["acl"]) | set(new["acl"])):
                if principal not in old["acl"] and principal in new["acl"]:
                    out.append(_fact("document.share.grant", "document", doc_id, target=principal,
                                     attributes={"permission": new["acl"][principal]}))
                elif principal in old["acl"] and principal not in new["acl"]:
                    out.append(_fact("document.share.revoke", "document", doc_id, target=principal,
                                     attributes={"permission": old["acl"][principal]}))
                elif old["acl"].get(principal) != new["acl"].get(principal):
                    out.append(_fact("document.share.change", "document", doc_id, target=principal,
                                     attributes={"permission": new["acl"][principal]}))
            if old["visibility"] != new["visibility"]:
                out.append(_fact("document.visibility.set", "document", doc_id,
                                 attributes={"visibility": new["visibility"]}))
                if new["visibility"] == "public":
                    out.append(_fact("document.public_link.create", "document", doc_id, target="principal:public"))
    elif tool_name == "post_message":
        for channel_id in sorted(before["channels"]):
            old, new = before["channels"][channel_id], after["channels"][channel_id]
            for _ in new["drafts"][len(old["drafts"]):]:
                out.append(_fact("message.draft.save", "channel", channel_id, commit_mode="draft"))
            for _ in new["scheduled"][len(old["scheduled"]):]:
                out.append(_fact("message.schedule", "channel", channel_id, commit_mode="scheduled"))
            for message in new["messages"][len(old["messages"]):]:
                out.append(_fact("message.post", "channel", channel_id, attributes={"payload_class": message["payload_class"]}))
                for principal in message["recipients"]:
                    out.append(_fact("message.notify", "channel", channel_id, target=principal))
                if new["external_bridge"]:
                    out.append(_fact("message.external_relay", "channel", channel_id, target="principal:external"))
    elif tool_name == "transfer_funds":
        for tx in after["drafts"][len(before["drafts"]):]:
            out.append(_fact("bank.transfer.draft", "bank_account", tx["account"], target=tx["payee"], commit_mode="draft"))
        for tx in after["scheduled"][len(before["scheduled"]):]:
            out.append(_fact("bank.transfer.schedule", "bank_account", tx["account"], target=tx["payee"],
                             attributes={"amount": tx["amount"], "currency": tx["currency"]}, commit_mode="scheduled"))
        for tx in after["transfers"][len(before["transfers"]):]:
            out.append(_fact("bank.transfer.commit", "bank_account", tx["account"], target=tx["payee"],
                             attributes={"amount": tx["amount"], "currency": tx["currency"]}))
            out.append(_fact("bank.balance.debit", "bank_account", tx["account"],
                             attributes={"amount": tx["amount"] + tx["fee"], "currency": tx["currency"]}))
            if tx["fee"]:
                out.append(_fact("bank.fee.charge", "bank_account", tx["account"],
                                 attributes={"amount": tx["fee"], "currency": tx["currency"]}))
            if tx["compliance_hold"]:
                out.append(_fact("bank.compliance.override", "bank_account", tx["account"]))
    else:
        raise ValueError(tool_name)
    return sorted(out, key=_key)
