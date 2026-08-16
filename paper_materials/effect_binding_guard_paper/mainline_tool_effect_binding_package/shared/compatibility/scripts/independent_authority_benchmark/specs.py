"""Freeze-time benchmark specifications; runtime consumes only emitted JSON."""

from __future__ import annotations

from typing import Any


L = lambda value: {"literal": value}
A = lambda path, default=None: {"arg": path, **({"default": default} if default is not None else {})}
S = lambda path, default=None: {"state": path, **({"default": default} if default is not None else {})}
V = lambda name: {"var": name}


def _emit(operation: str, resource_type: str, resource_id: dict[str, Any], *, target: dict[str, Any] | None = None,
          qualifiers: dict[str, Any] | None = None, mode: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "effect": operation,
        "operation": operation,
        "resource_type": L(resource_type),
        "resource_id": resource_id,
        "target_principal": target or L(None),
        "qualifiers": qualifiers or {},
        "commit_mode": mode or L("commit"),
    }


def descriptor_candidates() -> dict[str, Any]:
    commit = {"eq": [V("mode"), L("commit")]}
    descriptors: list[dict[str, Any]] = []

    calendar = {
        "schema_version": 1,
        "tool_name": "schedule_meeting",
        "lets": {
            "calendar_id": {"resolve": {"value": A("calendar_ref"), "mapping": S("aliases")}},
            "event_id": A("event_id"),
            "mode": A("commit_mode", L("commit")),
            "visibility": {"coalesce": [A("visibility"), S("calendars.{calendar_id}.default_visibility")]},
            "recurrence": {"coalesce": [A("recurrence"), S("calendars.{calendar_id}.default_recurrence")]},
            "old_visibility": S("calendars.{calendar_id}.events.{event_id}.visibility"),
            "old_recurrence": S("calendars.{calendar_id}.events.{event_id}.recurrence"),
            "old_participants": S("calendars.{calendar_id}.events.{event_id}.participants", L([])),
        },
        "rules": [
            {"rule_id": "calendar-draft", "when": {"eq": [V("mode"), L("draft")]},
             "emit": _emit("calendar.draft.save", "calendar", V("calendar_id"), qualifiers={"event_id": V("event_id")}, mode=L("draft"))},
            {"rule_id": "calendar-schedule", "when": {"eq": [V("mode"), L("scheduled")]},
             "emit": _emit("calendar.event.schedule", "calendar", V("calendar_id"), qualifiers={"event_id": V("event_id")}, mode=L("scheduled"))},
            {"rule_id": "calendar-upsert", "when": commit,
             "emit": _emit("calendar.event.upsert", "calendar", V("calendar_id"), qualifiers={"event_id": V("event_id"), "visibility": V("visibility"), "recurrence": V("recurrence")})},
            {"rule_id": "calendar-invite", "bindings": [{"name": "person", "from": A("participants", L([]))}],
             "when": {"all": [commit, {"not": {"contains": [V("old_participants"), V("person")]}}]},
             "emit": _emit("calendar.participant.invite", "calendar", V("calendar_id"), target=V("person"), qualifiers={"event_id": V("event_id")})},
            {"rule_id": "calendar-remove", "bindings": [{"name": "person", "from": V("old_participants")}],
             "when": {"all": [commit, {"not": {"contains": [A("participants", L([])), V("person")]}}]},
             "emit": _emit("calendar.participant.remove", "calendar", V("calendar_id"), target=V("person"), qualifiers={"event_id": V("event_id")})},
            {"rule_id": "calendar-visibility", "when": {"all": [commit, {"any": [{"missing": V("old_visibility")}, {"ne": [V("old_visibility"), V("visibility")]}]}]},
             "emit": _emit("calendar.visibility.set", "calendar", V("calendar_id"), qualifiers={"visibility": V("visibility"), "event_id": V("event_id")})},
            {"rule_id": "calendar-recurrence", "when": {"all": [commit, {"any": [{"missing": V("old_recurrence")}, {"ne": [V("old_recurrence"), V("recurrence")]}]}]},
             "emit": _emit("calendar.recurrence.set", "calendar", V("calendar_id"), qualifiers={"recurrence": V("recurrence"), "event_id": V("event_id")})},
        ],
    }
    descriptors.append(calendar)

    doc_refs = {"coalesce": [A("doc_refs"), {"wrap": A("doc_ref")}]} 
    doc_binding = [{"name": "doc_ref", "from": doc_refs}]
    doc_lets = {
        "doc_id": {"resolve": {"value": V("doc_ref"), "mapping": S("aliases")}},
        "mode": A("commit_mode", L("commit")),
        "operation": A("operation", L("grant")),
        "visibility": {"coalesce": [A("visibility"), S("documents.{doc_id}.default_visibility")]},
        "old_visibility": S("documents.{doc_id}.visibility"),
    }
    workspace_rules: list[dict[str, Any]] = [
        {"rule_id": "doc-draft", "bindings": doc_binding, "lets": doc_lets,
         "when": {"eq": [V("mode"), L("draft")]}, "emit": _emit("document.share.draft", "document", V("doc_id"), mode=L("draft"))},
        {"rule_id": "doc-visibility", "bindings": doc_binding, "lets": doc_lets,
         "when": {"all": [{"eq": [V("mode"), L("commit")]}, {"ne": [V("old_visibility"), V("visibility")]}]},
         "emit": _emit("document.visibility.set", "document", V("doc_id"), qualifiers={"visibility": V("visibility")})},
        {"rule_id": "doc-public", "bindings": doc_binding, "lets": doc_lets,
         "when": {"all": [{"eq": [V("mode"), L("commit")]}, {"eq": [V("visibility"), L("public")]}, {"ne": [V("old_visibility"), L("public")]}]},
         "emit": _emit("document.public_link.create", "document", V("doc_id"), target=L("principal:public"))},
    ]
    for suffix, operation, condition_spec in (
        ("grant", "document.share.grant", {"all": [{"eq": [V("mode"), L("commit")]}, {"ne": [V("operation"), L("revoke")]}, {"missing": V("old_permission")}] }),
        ("change", "document.share.change", {"all": [{"eq": [V("mode"), L("commit")]}, {"ne": [V("operation"), L("revoke")]}, {"exists": V("old_permission")}, {"ne": [V("old_permission"), A("permission")]}]}),
        ("revoke", "document.share.revoke", {"all": [{"eq": [V("mode"), L("commit")]}, {"eq": [V("operation"), L("revoke")]}, {"exists": V("old_permission")}]}),
    ):
        permission = V("old_permission") if suffix == "revoke" else A("permission")
        workspace_rules.append({
            "rule_id": f"doc-{suffix}",
            "bindings": doc_binding + [{"name": "person", "from": A("recipients", L([]))}],
            "lets": {**doc_lets, "old_permission": S("documents.{doc_id}.acl.{person}")},
            "when": condition_spec,
            "emit": _emit(operation, "document", V("doc_id"), target=V("person"), qualifiers={"permission": permission}),
        })
    descriptors.append({"schema_version": 1, "tool_name": "share_document", "rules": workspace_rules})

    channel_refs = {"coalesce": [A("channel_refs"), {"wrap": A("channel_ref")}]} 
    channel_binding = [{"name": "channel_ref", "from": channel_refs}]
    channel_lets = {
        "channel_id": {"resolve": {"value": V("channel_ref"), "mapping": S("aliases")}},
        "mode": {"coalesce": [A("commit_mode"), S("default_delivery_mode")]},
    }
    descriptors.append({
        "schema_version": 1,
        "tool_name": "post_message",
        "rules": [
            {"rule_id": "message-draft", "bindings": channel_binding, "lets": channel_lets,
             "when": {"eq": [V("mode"), L("draft")]}, "emit": _emit("message.draft.save", "channel", V("channel_id"), mode=L("draft"))},
            {"rule_id": "message-schedule", "bindings": channel_binding, "lets": channel_lets,
             "when": {"eq": [V("mode"), L("scheduled")]}, "emit": _emit("message.schedule", "channel", V("channel_id"), mode=L("scheduled"))},
            {"rule_id": "message-post", "bindings": channel_binding, "lets": channel_lets,
             "when": {"eq": [V("mode"), L("commit")]}, "emit": _emit("message.post", "channel", V("channel_id"), qualifiers={"payload_class": A("payload_class")})},
            {"rule_id": "message-notify", "bindings": channel_binding + [{"name": "person", "from": A("recipients", L([]))}], "lets": channel_lets,
             "when": {"eq": [V("mode"), L("commit")]}, "emit": _emit("message.notify", "channel", V("channel_id"), target=V("person"))},
            {"rule_id": "message-relay", "bindings": channel_binding, "lets": {**channel_lets, "bridged": S("channels.{channel_id}.external_bridge")},
             "when": {"all": [{"eq": [V("mode"), L("commit")]}, {"eq": [V("bridged"), L(True)]}]},
             "emit": _emit("message.external_relay", "channel", V("channel_id"), target=L("principal:external"))},
        ],
    })

    bank_lets = {
        "account": {"resolve": {"value": A("account_ref"), "mapping": S("account_aliases")}},
        "payee": {"resolve": {"value": A("payee_ref"), "mapping": S("payee_aliases")}},
        "mode": A("commit_mode", L("commit")),
        "amount": A("amount"),
        "currency": A("currency"),
        "fee": {"calc": {"op": "mul", "values": [A("amount"), S("fee_rate")], "round": 2}},
    }
    descriptors.append({
        "schema_version": 1,
        "tool_name": "transfer_funds",
        "lets": bank_lets,
        "rules": [
            {"rule_id": "bank-draft", "when": {"eq": [V("mode"), L("draft")]},
             "emit": _emit("bank.transfer.draft", "bank_account", V("account"), target=V("payee"), mode=L("draft"))},
            {"rule_id": "bank-schedule", "when": {"eq": [V("mode"), L("scheduled")]},
             "emit": _emit("bank.transfer.schedule", "bank_account", V("account"), target=V("payee"), qualifiers={"amount": V("amount"), "currency": V("currency")}, mode=L("scheduled"))},
            {"rule_id": "bank-transfer", "when": {"eq": [V("mode"), L("commit")]},
             "emit": _emit("bank.transfer.commit", "bank_account", V("account"), target=V("payee"), qualifiers={"amount": V("amount"), "currency": V("currency")})},
            {"rule_id": "bank-debit", "when": {"eq": [V("mode"), L("commit")]},
             "emit": _emit("bank.balance.debit", "bank_account", V("account"), qualifiers={"amount": {"calc": {"op": "add", "values": [V("amount"), V("fee")], "round": 2}}, "currency": V("currency")})},
            {"rule_id": "bank-fee", "when": {"all": [{"eq": [V("mode"), L("commit")]}, {"gt": [V("fee"), L(0)]}]},
             "emit": _emit("bank.fee.charge", "bank_account", V("account"), qualifiers={"amount": V("fee"), "currency": V("currency")})},
            {"rule_id": "bank-hold", "when": {"all": [{"eq": [V("mode"), L("commit")]}, {"eq": [S("compliance_hold"), L(True)]}]},
             "emit": _emit("bank.compliance.override", "bank_account", V("account"))},
        ],
    })
    return {"schema_version": 1, "descriptors": descriptors}
