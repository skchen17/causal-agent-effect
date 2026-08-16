"""Copied in-memory tools used only to produce concrete state transitions."""

from __future__ import annotations

import copy
from typing import Any


TOOLS = ("schedule_meeting", "share_document", "post_message", "transfer_funds")


def base_state(domain: str) -> dict[str, Any]:
    if domain == "calendar":
        return {
            "aliases": {"primary": "calendar:team"},
            "calendars": {
                "calendar:team": {
                    "default_visibility": "private",
                    "default_recurrence": "none",
                    "events": {},
                    "drafts": [],
                    "scheduled": [],
                },
                "calendar:external": {
                    "default_visibility": "public",
                    "default_recurrence": "daily",
                    "events": {},
                    "drafts": [],
                    "scheduled": [],
                },
            },
        }
    if domain == "workspace":
        return {
            "aliases": {"team-doc": "doc:report"},
            "documents": {
                "doc:report": {"acl": {}, "visibility": "private", "default_visibility": "private", "drafts": []},
                "doc:plan": {"acl": {}, "visibility": "private", "default_visibility": "private", "drafts": []},
                "doc:external": {"acl": {}, "visibility": "public", "default_visibility": "public", "drafts": []},
            },
        }
    if domain == "messaging":
        return {
            "aliases": {"ops": "channel:internal"},
            "channels": {
                "channel:internal": {"messages": [], "drafts": [], "scheduled": [], "external_bridge": False},
                "channel:external": {"messages": [], "drafts": [], "scheduled": [], "external_bridge": True},
            },
            "default_delivery_mode": "commit",
        }
    if domain == "banking":
        return {
            "account_aliases": {"primary": "account:checking"},
            "payee_aliases": {"vendor": "payee:acme", "outsider": "payee:eve"},
            "balances": {"account:checking": 5000.0, "account:savings": 9000.0},
            "fee_rate": 0.01,
            "compliance_hold": False,
            "transfers": [],
            "drafts": [],
            "scheduled": [],
        }
    raise ValueError(domain)


def _resolve(value: str, aliases: dict[str, str]) -> str:
    return aliases.get(value, value)


def execute(row: dict[str, Any]) -> dict[str, Any]:
    """Execute exactly one call against a copied state; never performs I/O."""

    state = copy.deepcopy(row["pre_state"])
    args = copy.deepcopy(row["arguments"])
    tool = row["tool_name"]
    if tool == "schedule_meeting":
        calendar_id = _resolve(args["calendar_ref"], state["aliases"])
        calendar = state["calendars"][calendar_id]
        mode = args.get("commit_mode", "commit")
        event = {
            "event_id": args["event_id"],
            "title": args["title"],
            "participants": sorted(set(args.get("participants", []))),
            "visibility": args.get("visibility", calendar["default_visibility"]),
            "recurrence": args.get("recurrence", calendar["default_recurrence"]),
        }
        if mode == "draft":
            calendar["drafts"].append(event)
        elif mode == "scheduled":
            calendar["scheduled"].append(event)
        else:
            calendar["events"][args["event_id"]] = event
    elif tool == "share_document":
        refs = args.get("doc_refs", [args["doc_ref"]])
        for ref in refs:
            doc_id = _resolve(ref, state["aliases"])
            doc = state["documents"][doc_id]
            mode = args.get("commit_mode", "commit")
            if mode == "draft":
                doc["drafts"].append(copy.deepcopy(args))
                continue
            for principal in args.get("recipients", []):
                if args.get("operation", "grant") == "revoke":
                    doc["acl"].pop(principal, None)
                else:
                    doc["acl"][principal] = args["permission"]
            doc["visibility"] = args.get("visibility", doc["default_visibility"])
    elif tool == "post_message":
        refs = args.get("channel_refs", [args["channel_ref"]])
        for ref in refs:
            channel_id = _resolve(ref, state["aliases"])
            channel = state["channels"][channel_id]
            mode = args.get("commit_mode", state["default_delivery_mode"])
            message = {
                "body": args["message"],
                "payload_class": args["payload_class"],
                "recipients": sorted(set(args.get("recipients", []))),
            }
            destination = "drafts" if mode == "draft" else "scheduled" if mode == "scheduled" else "messages"
            channel[destination].append(message)
    elif tool == "transfer_funds":
        account = _resolve(args["account_ref"], state["account_aliases"])
        payee = _resolve(args["payee_ref"], state["payee_aliases"])
        mode = args.get("commit_mode", "commit")
        amount = float(args["amount"])
        record = {
            "account": account,
            "payee": payee,
            "amount": amount,
            "currency": args["currency"],
            "fee": round(amount * float(state["fee_rate"]), 2),
            "compliance_hold": bool(state["compliance_hold"]),
        }
        if mode == "draft":
            state["drafts"].append(record)
        elif mode == "scheduled":
            state["scheduled"].append(record)
        else:
            state["balances"][account] = round(state["balances"][account] - amount - record["fee"], 2)
            state["transfers"].append(record)
    else:
        raise ValueError(tool)
    return state
