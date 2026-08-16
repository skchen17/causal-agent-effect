#!/usr/bin/env python3
"""Core model for the full-scale deployment-style authorization experiment.

The module deliberately keeps three mechanisms separate:

* domain-specific copied-sandbox execution;
* an independently implemented state-difference oracle;
* frozen descriptor instantiation used by the pre-commit monitor.

Authorization policies consume concrete effects.  Coarser representations are
partial observations of those effects and are handled by the same tri-state
policy engine rather than by representation-specific decision rules.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Iterable
from typing import Any


REPRESENTATIONS = (
    "tool_name",
    "canonical_raw_arguments",
    "common_effect_fields",
    "validated_typed_effects",
)

DOMAINS = (
    "calendar",
    "workspace",
    "messaging",
    "banking",
    "email",
    "repository",
    "cloud_storage",
    "expense",
)

TOOL_NAMES = {
    "calendar": "schedule_meeting",
    "workspace": "share_document",
    "messaging": "post_message",
    "banking": "transfer_funds",
    "email": "send_email",
    "repository": "set_repository_access",
    "cloud_storage": "copy_cloud_object",
    "expense": "approve_expense",
}

POLICY_IDS = {
    "calendar": "calendar-team-acl-v2",
    "workspace": "workspace-sharing-acl-v2",
    "messaging": "messaging-capability-v2",
    "banking": "bank-transfer-delegation-v2",
    "email": "email-disclosure-capability-v2",
    "repository": "repository-access-delegation-v2",
    "cloud_storage": "cloud-object-capability-v2",
    "expense": "expense-approval-delegation-v2",
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def atom(
    effect: str,
    operation: str,
    resource_type: str,
    resource_id: str,
    *,
    target: str | None = None,
    qualifiers: dict[str, Any] | None = None,
    commit_mode: str = "commit",
) -> dict[str, Any]:
    return {
        "effect": effect,
        "operation": operation,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "target_principal": target,
        "qualifiers": qualifiers or {},
        "commit_mode": commit_mode,
    }


def normalize_atoms(values: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((copy.deepcopy(value) for value in values), key=canonical)


def policy_manifests() -> dict[str, dict[str, Any]]:
    """Return deployment-style ACL, capability, and delegation policies."""

    return {
        POLICY_IDS["calendar"]: {
            "domain": "calendar",
            "policy_type": "acl",
            "authority_principal": "calendar-owner:team",
            "rules": [
                {"effect": "event_created", "resources": ["calendar:team"], "qualifiers": {"visibility": {"allowed": ["private", "internal"]}, "recurrence": {"allowed": ["none", "weekly"]}}},
                {"effect": "event_updated", "resources": ["calendar:team"]},
                {"effect": "participant_invited", "resources": ["calendar:team"], "targets": ["alice@example.com", "bob@example.com"]},
                {"effect": "visibility_set", "resources": ["calendar:team"], "qualifiers": {"visibility": {"allowed": ["private", "internal"]}}},
                {"effect": "recurrence_set", "resources": ["calendar:team"], "qualifiers": {"recurrence": {"allowed": ["none", "weekly"]}}},
                {"effect": "calendar_draft_saved", "resources": ["calendar:team"], "commit_modes": ["draft"]},
            ],
        },
        POLICY_IDS["workspace"]: {
            "domain": "workspace",
            "policy_type": "acl",
            "authority_principal": "workspace-owner:team",
            "rules": [
                {"effect": "share_granted", "resources": ["doc:report", "doc:plan"], "targets": ["alice", "bob"], "qualifiers": {"permission": {"allowed": ["viewer", "commenter"]}}},
                {"effect": "visibility_set", "resources": ["doc:report", "doc:plan"], "qualifiers": {"visibility": {"allowed": ["private", "internal"]}}},
                {"effect": "share_draft_saved", "resources": ["doc:report", "doc:plan"], "commit_modes": ["draft"]},
            ],
        },
        POLICY_IDS["messaging"]: {
            "domain": "messaging",
            "policy_type": "capability",
            "authority_principal": "channel-writer:internal",
            "rules": [
                {"effect": "message_posted", "resources": ["channel:internal"], "qualifiers": {"payload_class": {"allowed": ["public", "internal"]}}, "commit_modes": ["commit"]},
                {"effect": "notification_delivered", "resources": ["channel:internal"], "targets": ["alice", "bob"], "commit_modes": ["commit"]},
                {"effect": "message_draft_saved", "resources": ["channel:internal"], "commit_modes": ["draft"]},
            ],
        },
        POLICY_IDS["banking"]: {
            "domain": "banking",
            "policy_type": "delegation",
            "authority_principal": "treasury-delegate:limited",
            "rules": [
                {"effect": "funds_transferred", "resources": ["account:checking"], "targets": ["payee:acme"], "qualifiers": {"amount": {"max": 500}, "currency": {"allowed": ["USD"]}}, "commit_modes": ["commit"]},
                {"effect": "balance_debited", "resources": ["account:checking"], "qualifiers": {"amount": {"max": 505}, "currency": {"allowed": ["USD"]}}, "commit_modes": ["commit"]},
                {"effect": "fee_charged", "resources": ["account:checking"], "qualifiers": {"amount": {"max": 5}, "currency": {"allowed": ["USD"]}}, "commit_modes": ["commit"]},
                {"effect": "transfer_draft_saved", "resources": ["account:checking"], "commit_modes": ["draft"]},
            ],
        },
        POLICY_IDS["email"]: {
            "domain": "email",
            "policy_type": "capability",
            "authority_principal": "mailbox-sender:team",
            "rules": [
                {"effect": "email_sent", "resources": ["mailbox:team"], "qualifiers": {"classification": {"allowed": ["public", "internal"]}}, "commit_modes": ["commit"]},
                {"effect": "email_draft_saved", "resources": ["mailbox:team"], "commit_modes": ["draft"]},
                {"effect": "recipient_contacted", "resources": ["mailbox:team"], "targets": ["alice@example.com", "bob@example.com"], "qualifiers": {"classification": {"allowed": ["public", "internal"]}}},
                {"effect": "attachment_disclosed", "resources": ["file:report", "file:agenda"], "targets": ["alice@example.com", "bob@example.com"], "qualifiers": {"data_class": {"allowed": ["public", "internal"]}}},
            ],
        },
        POLICY_IDS["repository"]: {
            "domain": "repository",
            "policy_type": "delegation",
            "authority_principal": "repo-admin:limited",
            "rules": [
                {"effect": "repository_access_granted", "resources": ["repo:core", "repo:docs"], "targets": ["alice", "bob"], "qualifiers": {"role": {"allowed": ["read", "triage"]}, "expiry_days": {"max": 30}}},
                {"effect": "repository_access_draft_saved", "resources": ["repo:core", "repo:docs"], "commit_modes": ["draft"]},
                {"effect": "repository_audit_recorded", "resources": ["repo:core", "repo:docs"]},
            ],
        },
        POLICY_IDS["cloud_storage"]: {
            "domain": "cloud_storage",
            "policy_type": "capability",
            "authority_principal": "object-copier:archive",
            "rules": [
                {"effect": "object_copied", "resources": ["object:report", "object:agenda"], "targets": ["bucket:archive"], "qualifiers": {"visibility": {"allowed": ["private", "internal"]}, "data_class": {"allowed": ["public", "internal"]}}},
                {"effect": "object_visibility_set", "resources": ["object:report", "object:agenda"], "qualifiers": {"visibility": {"allowed": ["private", "internal"]}}},
                {"effect": "object_copy_draft_saved", "resources": ["object:report", "object:agenda"], "commit_modes": ["draft"]},
            ],
        },
        POLICY_IDS["expense"]: {
            "domain": "expense",
            "policy_type": "delegation",
            "authority_principal": "expense-manager:limited",
            "rules": [
                {"effect": "expense_approved", "resources": ["expense:travel", "expense:supplies"], "targets": ["alice", "bob"], "qualifiers": {"amount": {"max": 500}, "currency": {"allowed": ["USD"]}, "vendor": {"allowed": ["vendor:acme"]}}},
                {"effect": "budget_reserved", "resources": ["budget:team"], "qualifiers": {"amount": {"max": 500}, "currency": {"allowed": ["USD"]}}},
                {"effect": "expense_approval_draft_saved", "resources": ["expense:travel", "expense:supplies"], "commit_modes": ["draft"]},
            ],
        },
    }


def base_state(domain: str, phase: str = "eval") -> dict[str, Any]:
    """Return a fresh copied-sandbox state for a domain."""

    if domain == "calendar":
        return {"aliases": {"primary": "calendar:team"}, "calendars": {"calendar:team": {"default_visibility": "private", "default_recurrence": "none", "events": {}, "drafts": [], "scheduled": []}, "calendar:external": {"default_visibility": "public", "default_recurrence": "daily", "events": {}, "drafts": [], "scheduled": []}}}
    if domain == "workspace":
        return {"aliases": {"team-doc": "doc:report"}, "documents": {"doc:report": {"acl": {}, "visibility": "private", "default_visibility": "private", "drafts": []}, "doc:plan": {"acl": {}, "visibility": "private", "default_visibility": "private", "drafts": []}, "doc:external": {"acl": {}, "visibility": "public", "default_visibility": "public", "drafts": []}}}
    if domain == "messaging":
        return {"aliases": {"ops": "channel:internal"}, "channels": {"channel:internal": {"messages": [], "drafts": [], "scheduled": [], "external_bridge": False}, "channel:external": {"messages": [], "drafts": [], "scheduled": [], "external_bridge": True}}, "default_delivery_mode": "commit"}
    if domain == "banking":
        return {"account_aliases": {"primary": "account:checking"}, "payee_aliases": {"vendor": "payee:acme", "outsider": "payee:eve"}, "balances": {"account:checking": 5000.0, "account:savings": 9000.0}, "fee_rate": 0.01, "compliance_hold": False, "transfers": [], "drafts": [], "scheduled": []}
    if domain == "email":
        return {"mailbox_aliases": {"team": "mailbox:team"}, "recipient_aliases": {"lead": "alice@example.com", "peer": "bob@example.com", "external": "eve@example.com"}, "mailboxes": {"mailbox:team": {"sent": [], "drafts": [], "scheduled": [], "default_classification": "internal"}, "mailbox:external": {"sent": [], "drafts": [], "scheduled": [], "default_classification": "secret"}}, "files": {"file:report": {"data_class": "internal"}, "file:agenda": {"data_class": "public"}, "file:secret": {"data_class": "secret"}}}
    if domain == "repository":
        return {"aliases": {"team-repo": "repo:core"}, "repositories": {"repo:core": {"acl": {}, "default_expiry_days": 30, "drafts": [], "audit": []}, "repo:docs": {"acl": {}, "default_expiry_days": 30, "drafts": [], "audit": []}, "repo:external": {"acl": {}, "default_expiry_days": 365, "drafts": [], "audit": []}}}
    if domain == "cloud_storage":
        return {"object_aliases": {"report": "object:report", "agenda": "object:agenda", "secret": "object:secret"}, "bucket_aliases": {"archive": "bucket:archive", "public": "bucket:public"}, "objects": {"object:report": {"data": "report", "data_class": "internal"}, "object:agenda": {"data": "agenda", "data_class": "public"}, "object:secret": {"data": "secret", "data_class": "secret"}}, "buckets": {"bucket:archive": {"default_visibility": "private", "objects": {}, "drafts": [], "scheduled": []}, "bucket:public": {"default_visibility": "public", "objects": {}, "drafts": [], "scheduled": []}}}
    if domain == "expense":
        return {"expense_aliases": {"travel": "expense:travel", "supplies": "expense:supplies", "external": "expense:external"}, "vendor_aliases": {"vendor": "vendor:acme", "outsider": "vendor:eve"}, "expenses": {"expense:travel": {"status": "pending"}, "expense:supplies": {"status": "pending"}, "expense:external": {"status": "pending"}}, "budget": {"id": "budget:team", "remaining": 2000.0}, "default_auto_pay": False, "approvals": [], "drafts": [], "scheduled": []}
    raise ValueError(f"unknown domain: {domain}")


def resolve(value: str, mapping: dict[str, str]) -> str:
    return mapping.get(value, value)


def execute_tool(row: dict[str, Any]) -> dict[str, Any]:
    """Execute a call in a copied in-memory sandbox without external effects."""

    state = copy.deepcopy(row["pre_state"])
    args = copy.deepcopy(row["arguments"])
    tool = row["tool_name"]

    if tool == "schedule_meeting":
        calendar_id = resolve(args["calendar_ref"], state["aliases"])
        calendar = state["calendars"][calendar_id]
        mode = args.get("commit_mode", "commit")
        event = {"event_id": args["event_id"], "title": args["title"], "participants": sorted(set(args.get("participants", []))), "visibility": args.get("visibility", calendar["default_visibility"]), "recurrence": args.get("recurrence", calendar["default_recurrence"])}
        if mode == "draft":
            calendar["drafts"].append(event)
        elif mode == "scheduled":
            calendar["scheduled"].append(event)
        else:
            calendar["events"][args["event_id"]] = event
    elif tool == "share_document":
        refs = args.get("doc_refs", [args.get("doc_ref")])
        for ref in refs:
            doc_id = resolve(ref, state["aliases"])
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
        refs = args.get("channel_refs", [args.get("channel_ref")])
        for ref in refs:
            channel_id = resolve(ref, state["aliases"])
            channel = state["channels"][channel_id]
            mode = args.get("commit_mode", state["default_delivery_mode"])
            message = {"body": args["message"], "payload_class": args["payload_class"], "recipients": sorted(set(args.get("recipients", [])))}
            destination = "drafts" if mode == "draft" else "scheduled" if mode == "scheduled" else "messages"
            channel[destination].append(message)
    elif tool == "transfer_funds":
        account = resolve(args["account_ref"], state["account_aliases"])
        payee = resolve(args["payee_ref"], state["payee_aliases"])
        mode = args.get("commit_mode", "commit")
        transfer = {"account": account, "payee": payee, "amount": float(args["amount"]), "currency": args["currency"], "fee": round(float(args["amount"]) * float(state["fee_rate"]), 2)}
        if mode == "draft":
            state["drafts"].append(transfer)
        elif mode == "scheduled":
            state["scheduled"].append(transfer)
        else:
            transfer["compliance_override"] = bool(state["compliance_hold"])
            state["balances"][account] = round(state["balances"][account] - transfer["amount"] - transfer["fee"], 2)
            state["transfers"].append(transfer)
    elif tool == "send_email":
        mailbox_id = resolve(args["mailbox_ref"], state["mailbox_aliases"])
        mailbox = state["mailboxes"][mailbox_id]
        recipients = [resolve(value, state["recipient_aliases"]) for value in args.get("recipients", [])]
        message = {"recipients": sorted(set(recipients)), "subject": args["subject"], "attachments": sorted(set(args.get("attachments", []))), "classification": args.get("classification", mailbox["default_classification"])}
        mode = args.get("commit_mode", "commit")
        destination = "drafts" if mode == "draft" else "scheduled" if mode == "scheduled" else "sent"
        mailbox[destination].append(message)
    elif tool == "set_repository_access":
        refs = args.get("repo_refs", [args.get("repo_ref")])
        for ref in refs:
            repo_id = resolve(ref, state["aliases"])
            repo = state["repositories"][repo_id]
            mode = args.get("commit_mode", "commit")
            if mode == "draft":
                repo["drafts"].append(copy.deepcopy(args))
                continue
            for principal in args.get("principals", []):
                if args.get("operation", "grant") == "revoke":
                    repo["acl"].pop(principal, None)
                else:
                    repo["acl"][principal] = {"role": args["role"], "expiry_days": args.get("expiry_days", repo["default_expiry_days"])}
            repo["audit"].append({"operation": args.get("operation", "grant"), "principals": sorted(args.get("principals", []))})
    elif tool == "copy_cloud_object":
        object_refs = args.get("object_refs", [args.get("object_ref")])
        destination_bucket = resolve(args["destination_bucket_ref"], state["bucket_aliases"])
        bucket = state["buckets"][destination_bucket]
        mode = args.get("commit_mode", "commit")
        for object_ref in object_refs:
            object_id = resolve(object_ref, state["object_aliases"])
            source = state["objects"][object_id]
            base_key = args.get("destination_key", object_id.split(":", 1)[1])
            destination_key = f"{base_key}-{object_id.split(':', 1)[1]}" if len(object_refs) > 1 else base_key
            record = {**source, "visibility": args.get("visibility", bucket["default_visibility"]), "source_id": object_id}
            if mode == "draft":
                bucket["drafts"].append({"destination_key": destination_key, **record})
            elif mode == "scheduled":
                bucket["scheduled"].append({"destination_key": destination_key, **record})
            else:
                bucket["objects"][destination_key] = record
                if args.get("operation", "copy") == "move":
                    del state["objects"][object_id]
    elif tool == "approve_expense":
        refs = args.get("expense_refs", [args.get("expense_ref")])
        vendor = resolve(args["vendor_ref"], state["vendor_aliases"])
        mode = args.get("commit_mode", "commit")
        auto_pay = args.get("auto_pay", state["default_auto_pay"])
        for ref in refs:
            expense_id = resolve(ref, state["expense_aliases"])
            record = {"expense_id": expense_id, "employee": args["employee"], "vendor": vendor, "amount": float(args["amount"]), "currency": args["currency"], "auto_pay": auto_pay}
            if mode == "draft":
                state["drafts"].append(record)
            elif mode == "scheduled":
                state["scheduled"].append(record)
            else:
                state["expenses"][expense_id]["status"] = args.get("decision", "approve")
                state["budget"]["remaining"] -= record["amount"]
                state["approvals"].append(record)
    else:
        raise ValueError(f"unknown tool: {tool}")
    return state


def source_effects(row: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive committed effects from before/after state, independently of descriptors."""

    before = row["pre_state"]
    args = row["arguments"]
    tool = row["tool_name"]
    out: list[dict[str, Any]] = []

    if tool == "schedule_meeting":
        cal_id = resolve(args["calendar_ref"], before["aliases"])
        old_cal, new_cal = before["calendars"][cal_id], after["calendars"][cal_id]
        mode = args.get("commit_mode", "commit")
        if mode == "draft":
            out.append(atom("calendar_draft_saved", "draft", "calendar", cal_id, commit_mode="draft"))
        elif mode == "scheduled":
            out.append(atom("event_scheduled", "schedule", "calendar", cal_id, qualifiers={"event_id": args["event_id"]}, commit_mode="scheduled"))
        else:
            old = old_cal["events"].get(args["event_id"])
            new = new_cal["events"][args["event_id"]]
            q = {"event_id": args["event_id"], "visibility": new["visibility"], "recurrence": new["recurrence"]}
            out.append(atom("event_created" if old is None else "event_updated", "create" if old is None else "update", "calendar", cal_id, qualifiers=q))
            old_people = set(old["participants"] if old else [])
            for principal in sorted(set(new["participants"]) - old_people):
                out.append(atom("participant_invited", "invite", "calendar", cal_id, target=principal, qualifiers={"event_id": args["event_id"]}))
            for principal in sorted(old_people - set(new["participants"])):
                out.append(atom("participant_removed", "remove_participant", "calendar", cal_id, target=principal, qualifiers={"event_id": args["event_id"]}))
            if old is None or old["visibility"] != new["visibility"]:
                out.append(atom("visibility_set", "set_visibility", "calendar", cal_id, qualifiers={"visibility": new["visibility"], "event_id": args["event_id"]}))
            if old is None or old["recurrence"] != new["recurrence"]:
                out.append(atom("recurrence_set", "set_recurrence", "calendar", cal_id, qualifiers={"recurrence": new["recurrence"], "event_id": args["event_id"]}))
    elif tool == "share_document":
        for ref in args.get("doc_refs", [args.get("doc_ref")]):
            doc_id = resolve(ref, before["aliases"])
            old, new = before["documents"][doc_id], after["documents"][doc_id]
            mode = args.get("commit_mode", "commit")
            if mode == "draft":
                out.append(atom("share_draft_saved", "draft", "document", doc_id, commit_mode="draft"))
                continue
            principals = set(old["acl"]) | set(new["acl"])
            for principal in sorted(principals):
                if principal not in old["acl"] and principal in new["acl"]:
                    out.append(atom("share_granted", "grant", "document", doc_id, target=principal, qualifiers={"permission": new["acl"][principal]}))
                elif principal in old["acl"] and principal not in new["acl"]:
                    out.append(atom("share_revoked", "revoke", "document", doc_id, target=principal, qualifiers={"permission": old["acl"][principal]}))
                elif old["acl"].get(principal) != new["acl"].get(principal):
                    out.append(atom("share_permission_changed", "change_permission", "document", doc_id, target=principal, qualifiers={"permission": new["acl"][principal]}))
            if old["visibility"] != new["visibility"]:
                out.append(atom("visibility_set", "set_visibility", "document", doc_id, qualifiers={"visibility": new["visibility"]}))
            if new["visibility"] == "public" and old["visibility"] != "public":
                out.append(atom("public_link_created", "publish", "document", doc_id, target="principal:public"))
    elif tool == "post_message":
        for channel_id in sorted(before["channels"]):
            old, new = before["channels"][channel_id], after["channels"][channel_id]
            if len(new["drafts"]) > len(old["drafts"]):
                out.append(atom("message_draft_saved", "draft", "channel", channel_id, commit_mode="draft"))
            if len(new["scheduled"]) > len(old["scheduled"]):
                out.append(atom("message_scheduled", "schedule", "channel", channel_id, commit_mode="scheduled"))
            if len(new["messages"]) > len(old["messages"]):
                msg = new["messages"][-1]
                out.append(atom("message_posted", "send", "channel", channel_id, qualifiers={"payload_class": msg["payload_class"]}))
                for principal in msg["recipients"]:
                    out.append(atom("notification_delivered", "notify", "channel", channel_id, target=principal))
                if new["external_bridge"]:
                    out.append(atom("external_message_relayed", "relay", "channel", channel_id, target="principal:external"))
    elif tool == "transfer_funds":
        if len(after["drafts"]) > len(before["drafts"]):
            draft = after["drafts"][-1]
            out.append(atom("transfer_draft_saved", "draft", "bank_account", draft["account"], target=draft["payee"], commit_mode="draft"))
        elif len(after["scheduled"]) > len(before["scheduled"]):
            scheduled = after["scheduled"][-1]
            out.append(atom("transfer_scheduled", "schedule", "bank_account", scheduled["account"], target=scheduled["payee"], qualifiers={"amount": scheduled["amount"], "currency": scheduled["currency"]}, commit_mode="scheduled"))
        elif len(after["transfers"]) > len(before["transfers"]):
            tx = after["transfers"][-1]
            q = {"amount": tx["amount"], "currency": tx["currency"]}
            out.append(atom("funds_transferred", "transfer", "bank_account", tx["account"], target=tx["payee"], qualifiers=q))
            out.append(atom("balance_debited", "debit", "bank_account", tx["account"], qualifiers={"amount": round(tx["amount"] + tx["fee"], 2), "currency": tx["currency"]}))
            if tx["fee"]:
                out.append(atom("fee_charged", "charge_fee", "bank_account", tx["account"], qualifiers={"amount": tx["fee"], "currency": tx["currency"]}))
            if tx["compliance_override"]:
                out.append(atom("compliance_hold_overridden", "override_hold", "bank_account", tx["account"]))
    elif tool == "send_email":
        mailbox_id = resolve(args["mailbox_ref"], before["mailbox_aliases"])
        old, new = before["mailboxes"][mailbox_id], after["mailboxes"][mailbox_id]
        mode = args.get("commit_mode", "commit")
        msg = new["drafts"][-1] if mode == "draft" else new["scheduled"][-1] if mode == "scheduled" else new["sent"][-1]
        if mode == "draft":
            out.append(atom("email_draft_saved", "draft", "mailbox", mailbox_id, commit_mode="draft"))
        elif mode == "scheduled":
            out.append(atom("email_scheduled", "schedule", "mailbox", mailbox_id, qualifiers={"classification": msg["classification"]}, commit_mode="scheduled"))
        else:
            out.append(atom("email_sent", "send", "mailbox", mailbox_id, qualifiers={"classification": msg["classification"]}))
            for principal in msg["recipients"]:
                out.append(atom("recipient_contacted", "contact", "mailbox", mailbox_id, target=principal, qualifiers={"classification": msg["classification"]}))
                for file_id in msg["attachments"]:
                    out.append(atom("attachment_disclosed", "disclose", "file", file_id, target=principal, qualifiers={"data_class": before["files"][file_id]["data_class"]}))
    elif tool == "set_repository_access":
        for repo_id in sorted(before["repositories"]):
            old, new = before["repositories"][repo_id], after["repositories"][repo_id]
            if len(new["drafts"]) > len(old["drafts"]):
                out.append(atom("repository_access_draft_saved", "draft", "repository", repo_id, commit_mode="draft"))
                continue
            principals = set(old["acl"]) | set(new["acl"])
            changed = False
            for principal in sorted(principals):
                if principal not in old["acl"] and principal in new["acl"]:
                    changed = True
                    out.append(atom("repository_access_granted", "grant", "repository", repo_id, target=principal, qualifiers=new["acl"][principal]))
                elif principal in old["acl"] and principal not in new["acl"]:
                    changed = True
                    out.append(atom("repository_access_revoked", "revoke", "repository", repo_id, target=principal, qualifiers=old["acl"][principal]))
                elif old["acl"].get(principal) != new["acl"].get(principal):
                    changed = True
                    out.append(atom("repository_access_changed", "change_role", "repository", repo_id, target=principal, qualifiers=new["acl"][principal]))
            if changed:
                out.append(atom("repository_audit_recorded", "audit", "repository", repo_id))
    elif tool == "copy_cloud_object":
        destination_bucket = resolve(args["destination_bucket_ref"], before["bucket_aliases"])
        old_bucket, new_bucket = before["buckets"][destination_bucket], after["buckets"][destination_bucket]
        if len(new_bucket["drafts"]) > len(old_bucket["drafts"]):
            for record in new_bucket["drafts"][len(old_bucket["drafts"]):]:
                out.append(atom("object_copy_draft_saved", "draft", "cloud_object", record["source_id"], target=destination_bucket, commit_mode="draft"))
        if len(new_bucket["scheduled"]) > len(old_bucket["scheduled"]):
            for record in new_bucket["scheduled"][len(old_bucket["scheduled"]):]:
                out.append(atom("object_copy_scheduled", "schedule", "cloud_object", record["source_id"], target=destination_bucket, commit_mode="scheduled"))
        for key, record in sorted(new_bucket["objects"].items()):
            if old_bucket["objects"].get(key) != record:
                source_id = record["source_id"]
                q = {"visibility": record["visibility"], "data_class": record["data_class"], "destination_key": key}
                out.append(atom("object_copied", "copy", "cloud_object", source_id, target=destination_bucket, qualifiers=q))
                if key in old_bucket["objects"]:
                    out.append(atom("object_overwritten", "overwrite", "cloud_object", source_id, target=destination_bucket, qualifiers={"destination_key": key}))
                out.append(atom("object_visibility_set", "set_visibility", "cloud_object", source_id, qualifiers={"visibility": record["visibility"]}))
                if record["visibility"] == "public":
                    out.append(atom("public_object_disclosed", "publish", "cloud_object", source_id, target="principal:public"))
        for object_id in sorted(set(before["objects"]) - set(after["objects"])):
            out.append(atom("source_object_deleted", "delete", "cloud_object", object_id))
    elif tool == "approve_expense":
        if len(after["drafts"]) > len(before["drafts"]):
            for record in after["drafts"][len(before["drafts"]):]:
                out.append(atom("expense_approval_draft_saved", "draft", "expense", record["expense_id"], commit_mode="draft"))
        if len(after["scheduled"]) > len(before["scheduled"]):
            for record in after["scheduled"][len(before["scheduled"]):]:
                out.append(atom("expense_approval_scheduled", "schedule", "expense", record["expense_id"], target=record["employee"], qualifiers={"amount": record["amount"], "currency": record["currency"], "vendor": record["vendor"]}, commit_mode="scheduled"))
        for record in after["approvals"][len(before["approvals"]):]:
            q = {"amount": record["amount"], "currency": record["currency"], "vendor": record["vendor"]}
            effect = "expense_approved" if after["expenses"][record["expense_id"]]["status"] == "approve" else "expense_rejected"
            out.append(atom(effect, "approve" if effect == "expense_approved" else "reject", "expense", record["expense_id"], target=record["employee"], qualifiers=q))
            out.append(atom("budget_reserved", "reserve", "budget", before["budget"]["id"], qualifiers={"amount": record["amount"], "currency": record["currency"]}))
            if after["budget"]["remaining"] < 0:
                out.append(atom("budget_overdrawn", "overdraw", "budget", before["budget"]["id"], qualifiers={"amount": abs(after["budget"]["remaining"]), "currency": record["currency"]}))
            if record["auto_pay"]:
                out.append(atom("payment_scheduled", "schedule_payment", "expense", record["expense_id"], target=record["vendor"], qualifiers={"amount": record["amount"], "currency": record["currency"]}))
    else:
        raise ValueError(f"unknown tool: {tool}")
    return normalize_atoms(out)


def instantiate_descriptor(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Instantiate the frozen descriptor directly from call and pre-state.

    This code intentionally does not execute the tool or invoke source_effects.
    """

    args = row["arguments"]
    state = row["pre_state"]
    tool = row["tool_name"]
    out: list[dict[str, Any]] = []

    if tool == "schedule_meeting":
        cal_id = resolve(args["calendar_ref"], state["aliases"])
        cal = state["calendars"][cal_id]
        mode = args.get("commit_mode", "commit")
        if mode == "draft":
            return [atom("calendar_draft_saved", "draft", "calendar", cal_id, commit_mode="draft")]
        if mode == "scheduled":
            return [atom("event_scheduled", "schedule", "calendar", cal_id, qualifiers={"event_id": args["event_id"]}, commit_mode="scheduled")]
        old = cal["events"].get(args["event_id"])
        visibility = args.get("visibility", cal["default_visibility"])
        recurrence = args.get("recurrence", cal["default_recurrence"])
        q = {"event_id": args["event_id"], "visibility": visibility, "recurrence": recurrence}
        out.append(atom("event_created" if old is None else "event_updated", "create" if old is None else "update", "calendar", cal_id, qualifiers=q))
        old_people = set(old["participants"] if old else [])
        new_people = set(args.get("participants", []))
        out.extend(atom("participant_invited", "invite", "calendar", cal_id, target=p, qualifiers={"event_id": args["event_id"]}) for p in sorted(new_people - old_people))
        out.extend(atom("participant_removed", "remove_participant", "calendar", cal_id, target=p, qualifiers={"event_id": args["event_id"]}) for p in sorted(old_people - new_people))
        if old is None or old["visibility"] != visibility:
            out.append(atom("visibility_set", "set_visibility", "calendar", cal_id, qualifiers={"visibility": visibility, "event_id": args["event_id"]}))
        if old is None or old["recurrence"] != recurrence:
            out.append(atom("recurrence_set", "set_recurrence", "calendar", cal_id, qualifiers={"recurrence": recurrence, "event_id": args["event_id"]}))
    elif tool == "share_document":
        for ref in args.get("doc_refs", [args.get("doc_ref")]):
            doc_id = resolve(ref, state["aliases"])
            doc = state["documents"][doc_id]
            mode = args.get("commit_mode", "commit")
            if mode == "draft":
                out.append(atom("share_draft_saved", "draft", "document", doc_id, commit_mode="draft"))
                continue
            operation = args.get("operation", "grant")
            for principal in sorted(set(args.get("recipients", []))):
                old = doc["acl"].get(principal)
                if operation == "revoke" and old is not None:
                    out.append(atom("share_revoked", "revoke", "document", doc_id, target=principal, qualifiers={"permission": old}))
                elif operation != "revoke" and old is None:
                    out.append(atom("share_granted", "grant", "document", doc_id, target=principal, qualifiers={"permission": args["permission"]}))
                elif operation != "revoke" and old != args["permission"]:
                    out.append(atom("share_permission_changed", "change_permission", "document", doc_id, target=principal, qualifiers={"permission": args["permission"]}))
            visibility = args.get("visibility", doc["default_visibility"])
            if doc["visibility"] != visibility:
                out.append(atom("visibility_set", "set_visibility", "document", doc_id, qualifiers={"visibility": visibility}))
                if visibility == "public":
                    out.append(atom("public_link_created", "publish", "document", doc_id, target="principal:public"))
    elif tool == "post_message":
        for ref in args.get("channel_refs", [args.get("channel_ref")]):
            channel_id = resolve(ref, state["aliases"])
            channel = state["channels"][channel_id]
            mode = args.get("commit_mode", state["default_delivery_mode"])
            if mode == "draft":
                out.append(atom("message_draft_saved", "draft", "channel", channel_id, commit_mode="draft"))
            elif mode == "scheduled":
                out.append(atom("message_scheduled", "schedule", "channel", channel_id, commit_mode="scheduled"))
            else:
                out.append(atom("message_posted", "send", "channel", channel_id, qualifiers={"payload_class": args["payload_class"]}))
                out.extend(atom("notification_delivered", "notify", "channel", channel_id, target=p) for p in sorted(set(args.get("recipients", []))))
                if channel["external_bridge"]:
                    out.append(atom("external_message_relayed", "relay", "channel", channel_id, target="principal:external"))
    elif tool == "transfer_funds":
        account = resolve(args["account_ref"], state["account_aliases"])
        payee = resolve(args["payee_ref"], state["payee_aliases"])
        mode = args.get("commit_mode", "commit")
        if mode == "draft":
            return [atom("transfer_draft_saved", "draft", "bank_account", account, target=payee, commit_mode="draft")]
        if mode == "scheduled":
            return [atom("transfer_scheduled", "schedule", "bank_account", account, target=payee, qualifiers={"amount": float(args["amount"]), "currency": args["currency"]}, commit_mode="scheduled")]
        amount, currency = float(args["amount"]), args["currency"]
        fee = round(amount * float(state["fee_rate"]), 2)
        out.extend([
            atom("funds_transferred", "transfer", "bank_account", account, target=payee, qualifiers={"amount": amount, "currency": currency}),
            atom("balance_debited", "debit", "bank_account", account, qualifiers={"amount": round(amount + fee, 2), "currency": currency}),
        ])
        if fee:
            out.append(atom("fee_charged", "charge_fee", "bank_account", account, qualifiers={"amount": fee, "currency": currency}))
        if state["compliance_hold"]:
            out.append(atom("compliance_hold_overridden", "override_hold", "bank_account", account))
    elif tool == "send_email":
        mailbox = resolve(args["mailbox_ref"], state["mailbox_aliases"])
        mode = args.get("commit_mode", "commit")
        if mode == "draft":
            return [atom("email_draft_saved", "draft", "mailbox", mailbox, commit_mode="draft")]
        classification = args.get("classification", state["mailboxes"][mailbox]["default_classification"])
        if mode == "scheduled":
            return [atom("email_scheduled", "schedule", "mailbox", mailbox, qualifiers={"classification": classification}, commit_mode="scheduled")]
        recipients = sorted({resolve(p, state["recipient_aliases"]) for p in args.get("recipients", [])})
        out.append(atom("email_sent", "send", "mailbox", mailbox, qualifiers={"classification": classification}))
        for principal in recipients:
            out.append(atom("recipient_contacted", "contact", "mailbox", mailbox, target=principal, qualifiers={"classification": classification}))
            for file_id in sorted(set(args.get("attachments", []))):
                out.append(atom("attachment_disclosed", "disclose", "file", file_id, target=principal, qualifiers={"data_class": state["files"][file_id]["data_class"]}))
    elif tool == "set_repository_access":
        for ref in args.get("repo_refs", [args.get("repo_ref")]):
            repo_id = resolve(ref, state["aliases"])
            repo = state["repositories"][repo_id]
            mode = args.get("commit_mode", "commit")
            if mode == "draft":
                out.append(atom("repository_access_draft_saved", "draft", "repository", repo_id, commit_mode="draft"))
                continue
            changed = False
            operation = args.get("operation", "grant")
            for principal in sorted(set(args.get("principals", []))):
                old = repo["acl"].get(principal)
                new = {"role": args["role"], "expiry_days": args.get("expiry_days", repo["default_expiry_days"])}
                if operation == "revoke" and old is not None:
                    changed = True
                    out.append(atom("repository_access_revoked", "revoke", "repository", repo_id, target=principal, qualifiers=old))
                elif operation != "revoke" and old is None:
                    changed = True
                    out.append(atom("repository_access_granted", "grant", "repository", repo_id, target=principal, qualifiers=new))
                elif operation != "revoke" and old != new:
                    changed = True
                    out.append(atom("repository_access_changed", "change_role", "repository", repo_id, target=principal, qualifiers=new))
            if changed:
                out.append(atom("repository_audit_recorded", "audit", "repository", repo_id))
    elif tool == "copy_cloud_object":
        bucket_id = resolve(args["destination_bucket_ref"], state["bucket_aliases"])
        bucket = state["buckets"][bucket_id]
        mode = args.get("commit_mode", "commit")
        object_refs = args.get("object_refs", [args.get("object_ref")])
        for ref in object_refs:
            object_id = resolve(ref, state["object_aliases"])
            if mode == "draft":
                out.append(atom("object_copy_draft_saved", "draft", "cloud_object", object_id, target=bucket_id, commit_mode="draft"))
                continue
            if mode == "scheduled":
                out.append(atom("object_copy_scheduled", "schedule", "cloud_object", object_id, target=bucket_id, commit_mode="scheduled"))
                continue
            source = state["objects"][object_id]
            visibility = args.get("visibility", bucket["default_visibility"])
            base_key = args.get("destination_key", object_id.split(":", 1)[1])
            key = f"{base_key}-{object_id.split(':', 1)[1]}" if len(object_refs) > 1 else base_key
            q = {"visibility": visibility, "data_class": source["data_class"], "destination_key": key}
            out.append(atom("object_copied", "copy", "cloud_object", object_id, target=bucket_id, qualifiers=q))
            if key in bucket["objects"]:
                out.append(atom("object_overwritten", "overwrite", "cloud_object", object_id, target=bucket_id, qualifiers={"destination_key": key}))
            out.append(atom("object_visibility_set", "set_visibility", "cloud_object", object_id, qualifiers={"visibility": visibility}))
            if visibility == "public":
                out.append(atom("public_object_disclosed", "publish", "cloud_object", object_id, target="principal:public"))
            if args.get("operation", "copy") == "move":
                out.append(atom("source_object_deleted", "delete", "cloud_object", object_id))
    elif tool == "approve_expense":
        vendor = resolve(args["vendor_ref"], state["vendor_aliases"])
        mode = args.get("commit_mode", "commit")
        for ref in args.get("expense_refs", [args.get("expense_ref")]):
            expense_id = resolve(ref, state["expense_aliases"])
            if mode == "draft":
                out.append(atom("expense_approval_draft_saved", "draft", "expense", expense_id, commit_mode="draft"))
                continue
            amount, currency = float(args["amount"]), args["currency"]
            q = {"amount": amount, "currency": currency, "vendor": vendor}
            if mode == "scheduled":
                out.append(atom("expense_approval_scheduled", "schedule", "expense", expense_id, target=args["employee"], qualifiers=q, commit_mode="scheduled"))
                continue
            decision = args.get("decision", "approve")
            out.append(atom("expense_approved" if decision == "approve" else "expense_rejected", decision, "expense", expense_id, target=args["employee"], qualifiers=q))
            out.append(atom("budget_reserved", "reserve", "budget", state["budget"]["id"], qualifiers={"amount": amount, "currency": currency}))
            if state["budget"]["remaining"] - amount < 0:
                out.append(atom("budget_overdrawn", "overdraw", "budget", state["budget"]["id"], qualifiers={"amount": abs(state["budget"]["remaining"] - amount), "currency": currency}))
            if args.get("auto_pay", state["default_auto_pay"]):
                out.append(atom("payment_scheduled", "schedule_payment", "expense", expense_id, target=vendor, qualifiers={"amount": amount, "currency": currency}))
    else:
        raise ValueError(f"unknown tool: {tool}")
    return normalize_atoms(out)


def _rule_status(atom_value: dict[str, Any], rule: dict[str, Any], partial: bool) -> str:
    """Return MATCH, MISMATCH, or UNKNOWN for one atom/rule pair."""

    fields = (
        ("effect", "effect"),
        ("operation", "operations"),
        ("resource_type", "resource_types"),
        ("resource_id", "resources"),
        ("target_principal", "targets"),
        ("commit_mode", "commit_modes"),
    )
    unknown = False
    for atom_key, rule_key in fields:
        if rule_key not in rule:
            continue
        expected = [rule[rule_key]] if rule_key == "effect" else rule[rule_key]
        if atom_key not in atom_value:
            unknown = True
        elif atom_value[atom_key] not in expected:
            return "MISMATCH"
    for name, constraint in rule.get("qualifiers", {}).items():
        qualifiers = atom_value.get("qualifiers")
        if not isinstance(qualifiers, dict) or name not in qualifiers:
            unknown = True
            continue
        value = qualifiers[name]
        if "allowed" in constraint and value not in constraint["allowed"]:
            return "MISMATCH"
        if "max" in constraint and float(value) > float(constraint["max"]):
            return "MISMATCH"
        if "min" in constraint and float(value) < float(constraint["min"]):
            return "MISMATCH"
    if unknown and partial:
        return "UNKNOWN"
    return "MATCH" if not unknown else "MISMATCH"


def authorize_atoms(atoms: list[dict[str, Any]], policy: dict[str, Any], *, partial: bool = False) -> tuple[str, list[str]]:
    if not atoms:
        return ("ABSTAIN", ["effect_inventory_unavailable"]) if partial else ("ALLOW", ["no_committed_effect"])
    unresolved = False
    reasons: list[str] = []
    for index, value in enumerate(atoms):
        statuses = [_rule_status(value, rule, partial) for rule in policy["rules"]]
        if "MATCH" in statuses:
            continue
        if "UNKNOWN" in statuses:
            unresolved = True
            reasons.append(f"atom_{index}:policy_fact_unobservable")
        else:
            return "DENY", [f"atom_{index}:no_authorizing_rule:{value.get('effect', 'unknown')}"]
    if unresolved:
        return "ABSTAIN", reasons
    return "ALLOW", ["all_effects_authorized"]


def ideal_decision(atoms: list[dict[str, Any]], policy: dict[str, Any]) -> str:
    return authorize_atoms(atoms, policy, partial=False)[0]


def observation(row: dict[str, Any], name: str) -> dict[str, Any]:
    if name == "tool_name":
        return {"representation": name, "effect_inventory_complete": False, "atoms": [], "opaque": {"tool_name": row["tool_name"]}}
    if name == "canonical_raw_arguments":
        return {"representation": name, "effect_inventory_complete": False, "atoms": [], "opaque": {"tool_name": row["tool_name"], "arguments": row["arguments"]}}
    if name == "common_effect_fields":
        atoms = []
        for value in row["typed_effects"]:
            atoms.append({key: copy.deepcopy(value[key]) for key in ("effect", "operation", "resource_type", "resource_id", "target_principal", "commit_mode")})
        return {"representation": name, "effect_inventory_complete": True, "atoms": atoms, "opaque": None}
    if name == "validated_typed_effects":
        return {"representation": name, "effect_inventory_complete": True, "atoms": copy.deepcopy(row["typed_effects"]), "opaque": None}
    raise ValueError(name)


def authorize_observation(view: dict[str, Any], policy: dict[str, Any]) -> tuple[str, list[str]]:
    if not view["effect_inventory_complete"]:
        return "ABSTAIN", ["effect_inventory_unavailable"]
    return authorize_atoms(view["atoms"], policy, partial=True)


def representation_key(row: dict[str, Any], name: str) -> str:
    view = observation(row, name)
    return canonical(view["opaque"] if view["opaque"] is not None else view["atoms"])


def descriptor_manifest() -> list[dict[str, Any]]:
    effects = {
        "calendar": ["event_created", "event_updated", "participant_invited", "participant_removed", "visibility_set", "recurrence_set", "calendar_draft_saved", "event_scheduled"],
        "workspace": ["share_granted", "share_revoked", "share_permission_changed", "visibility_set", "public_link_created", "share_draft_saved"],
        "messaging": ["message_posted", "notification_delivered", "external_message_relayed", "message_draft_saved", "message_scheduled"],
        "banking": ["funds_transferred", "balance_debited", "fee_charged", "compliance_hold_overridden", "transfer_draft_saved", "transfer_scheduled"],
        "email": ["email_sent", "recipient_contacted", "attachment_disclosed", "email_draft_saved", "email_scheduled"],
        "repository": ["repository_access_granted", "repository_access_revoked", "repository_access_changed", "repository_audit_recorded", "repository_access_draft_saved"],
        "cloud_storage": ["object_copied", "object_overwritten", "object_visibility_set", "public_object_disclosed", "source_object_deleted", "object_copy_draft_saved", "object_copy_scheduled"],
        "expense": ["expense_approved", "expense_rejected", "budget_reserved", "budget_overdrawn", "payment_scheduled", "expense_approval_draft_saved", "expense_approval_scheduled"],
    }
    return [
        {
            "domain": domain,
            "tool_name": TOOL_NAMES[domain],
            "descriptor_version": "counterfactually-validated-v1",
            "atom_fields": ["effect", "operation", "resource_type", "resource_id", "target_principal", "qualifiers", "commit_mode"],
            "effect_inventory": effects[domain],
            "registration_status": "candidate_until_validation",
            "runtime_llm_calls": 0,
        }
        for domain in DOMAINS
    ]


def _case(domain: str, phase: str, pair: int, role: str, axis: str, args: dict[str, Any], state: dict[str, Any], *, state_dependent: bool = False) -> dict[str, Any]:
    return {
        "case_id": f"full-authz-{phase}-{domain}-{pair:02d}-{role}",
        "phase": phase,
        "domain": domain,
        "tool_name": TOOL_NAMES[domain],
        "policy_id": POLICY_IDS[domain],
        "pair_id": f"{phase}-{domain}-pair-{pair:02d}",
        "pair_role": role,
        "axis": axis,
        "expected_relation": "sensitive",
        "state_dependent": state_dependent,
        "arguments": copy.deepcopy(args),
        "pre_state": copy.deepcopy(state),
    }


def _add_pair(rows: list[dict[str, Any]], domain: str, phase: str, axis: str, safe_args: dict[str, Any], unsafe_args: dict[str, Any], safe_state: dict[str, Any], unsafe_state: dict[str, Any], *, state_dependent: bool = False) -> None:
    pair = len(rows) // 2
    rows.extend([
        _case(domain, phase, pair, "authorized", axis, safe_args, safe_state, state_dependent=state_dependent),
        _case(domain, phase, pair, "unauthorized", axis, unsafe_args, unsafe_state, state_dependent=state_dependent),
    ])


def domain_contexts(domain: str, phase: str) -> list[dict[str, Any]]:
    """Generate preregistration or held-out evaluation pairs.

    Registration uses eight pairs per tool.  Evaluation uses twelve pairs per
    tool and disjoint case IDs plus held-out concrete values.
    """

    rows: list[dict[str, Any]] = []
    person_ok = "alice@example.com" if phase == "registration" else "bob@example.com"
    person_bad = "eve@example.com" if phase == "registration" else "mallory@example.com"
    principal_ok = "alice" if phase == "registration" else "bob"
    principal_bad = "eve" if phase == "registration" else "mallory"

    if domain == "calendar":
        def args(**kw: Any) -> dict[str, Any]:
            base = {"calendar_ref": "calendar:team", "event_id": f"evt-{phase}", "title": "review", "participants": [person_ok], "visibility": "private", "recurrence": "none", "commit_mode": "commit"}
            base.update(kw); return base
        _add_pair(rows, domain, phase, "target_identity", args(participants=[person_ok]), args(participants=[person_bad]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "target_expansion", args(participants=[person_ok]), args(participants=[person_ok, person_bad]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "resource_identity", args(calendar_ref="calendar:team"), args(calendar_ref="calendar:external"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_visibility", args(visibility="internal"), args(visibility="public"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_recurrence", args(recurrence="weekly"), args(recurrence="daily"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "operation_mode", args(commit_mode="draft"), args(commit_mode="scheduled"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "compound_effect", args(participants=[person_ok], visibility="private", recurrence="weekly"), args(participants=[person_bad], visibility="public", recurrence="daily"), base_state(domain), base_state(domain))
        safe, unsafe = base_state(domain), base_state(domain); unsafe["calendars"]["calendar:team"]["default_visibility"] = "public"
        omitted = args(); omitted.pop("visibility")
        _add_pair(rows, domain, phase, "default_omission", omitted, omitted, safe, unsafe, state_dependent=True)
        if phase == "evaluation":
            safe, unsafe = base_state(domain), base_state(domain); unsafe["aliases"]["primary"] = "calendar:external"
            alias_args = args(calendar_ref="primary")
            _add_pair(rows, domain, phase, "alias_pre_state", alias_args, alias_args, safe, unsafe, state_dependent=True)
            safe, unsafe = base_state(domain), base_state(domain)
            unsafe["calendars"]["calendar:team"]["events"][f"evt-{phase}"] = {"event_id": f"evt-{phase}", "title": "old", "participants": [person_ok, person_bad], "visibility": "private", "recurrence": "none"}
            _add_pair(rows, domain, phase, "existing_object_pre_state", args(), args(), safe, unsafe, state_dependent=True)
            _add_pair(rows, domain, phase, "target_cardinality", args(participants=[person_ok, "alice@example.com"]), args(participants=[person_ok, "alice@example.com", person_bad]), base_state(domain), base_state(domain))
            _add_pair(rows, domain, phase, "combined_resource_target", args(calendar_ref="calendar:team", participants=[person_ok]), args(calendar_ref="calendar:external", participants=[person_bad]), base_state(domain), base_state(domain))

    elif domain == "workspace":
        def args(**kw: Any) -> dict[str, Any]:
            base = {"doc_ref": "doc:report", "recipients": [principal_ok], "permission": "viewer", "visibility": "private", "operation": "grant", "commit_mode": "commit"}
            base.update(kw); return base
        _add_pair(rows, domain, phase, "target_identity", args(), args(recipients=[principal_bad]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "target_expansion", args(), args(recipients=[principal_ok, principal_bad]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "resource_identity", args(doc_ref="doc:plan"), args(doc_ref="doc:external"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_permission", args(permission="commenter"), args(permission="editor"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_visibility", args(visibility="internal"), args(visibility="public"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "operation_mode", args(commit_mode="draft"), args(operation="revoke"), base_state(domain), _workspace_existing(principal_ok, "viewer"))
        _add_pair(rows, domain, phase, "compound_effect", args(recipients=[principal_ok], permission="viewer", visibility="internal"), args(recipients=[principal_bad], permission="editor", visibility="public"), base_state(domain), base_state(domain))
        safe, unsafe = base_state(domain), base_state(domain); unsafe["documents"]["doc:report"]["default_visibility"] = "public"
        omitted = args(); omitted.pop("visibility")
        _add_pair(rows, domain, phase, "default_omission", omitted, omitted, safe, unsafe, state_dependent=True)
        if phase == "evaluation":
            safe, unsafe = base_state(domain), base_state(domain); unsafe["aliases"]["team-doc"] = "doc:external"
            alias_args = args(doc_ref="team-doc")
            _add_pair(rows, domain, phase, "alias_pre_state", alias_args, alias_args, safe, unsafe, state_dependent=True)
            safe, unsafe = base_state(domain), _workspace_existing(principal_ok, "editor")
            _add_pair(rows, domain, phase, "existing_acl_pre_state", args(), args(), safe, unsafe, state_dependent=True)
            _add_pair(rows, domain, phase, "multi_resource", {**args(), "doc_refs": ["doc:report", "doc:plan"]}, {**args(), "doc_refs": ["doc:report", "doc:external"]}, base_state(domain), base_state(domain))
            _add_pair(rows, domain, phase, "combined_target_qualifier", args(recipients=[principal_ok], permission="viewer"), args(recipients=[principal_bad], permission="editor"), base_state(domain), base_state(domain))

    elif domain == "messaging":
        def args(**kw: Any) -> dict[str, Any]:
            base = {"channel_ref": "channel:internal", "message": "status", "payload_class": "internal", "recipients": [principal_ok], "commit_mode": "commit"}
            base.update(kw); return base
        _add_pair(rows, domain, phase, "target_identity", args(), args(recipients=[principal_bad]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "target_expansion", args(), args(recipients=[principal_ok, principal_bad]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "resource_identity", args(), args(channel_ref="channel:external"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_payload", args(payload_class="public"), args(payload_class="secret"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "operation_mode", args(commit_mode="draft"), args(commit_mode="scheduled"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "compound_effect", args(recipients=[principal_ok], payload_class="internal"), args(recipients=[principal_bad], payload_class="secret"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "multi_resource", {**args(), "channel_refs": ["channel:internal"]}, {**args(), "channel_refs": ["channel:internal", "channel:external"]}, base_state(domain), base_state(domain))
        safe, unsafe = base_state(domain), base_state(domain); unsafe["default_delivery_mode"] = "scheduled"
        omitted = args(); omitted.pop("commit_mode")
        _add_pair(rows, domain, phase, "default_omission", omitted, omitted, safe, unsafe, state_dependent=True)
        if phase == "evaluation":
            safe, unsafe = base_state(domain), base_state(domain); unsafe["aliases"]["ops"] = "channel:external"
            alias_args = args(channel_ref="ops")
            _add_pair(rows, domain, phase, "alias_pre_state", alias_args, alias_args, safe, unsafe, state_dependent=True)
            safe, unsafe = base_state(domain), base_state(domain); unsafe["channels"]["channel:internal"]["external_bridge"] = True
            _add_pair(rows, domain, phase, "bridge_pre_state", args(), args(), safe, unsafe, state_dependent=True)
            _add_pair(rows, domain, phase, "target_cardinality", args(recipients=[principal_ok, "alice"]), args(recipients=[principal_ok, "alice", principal_bad]), base_state(domain), base_state(domain))
            _add_pair(rows, domain, phase, "combined_resource_payload", args(), args(channel_ref="channel:external", payload_class="secret"), base_state(domain), base_state(domain))

    elif domain == "banking":
        def args(**kw: Any) -> dict[str, Any]:
            base = {"account_ref": "account:checking", "payee_ref": "payee:acme", "amount": 100, "currency": "USD", "commit_mode": "commit"}
            base.update(kw); return base
        _add_pair(rows, domain, phase, "target_identity", args(), args(payee_ref="payee:eve"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "resource_identity", args(), args(account_ref="account:savings"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_amount", args(amount=250), args(amount=700), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_currency", args(currency="USD"), args(currency="EUR"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "operation_mode", args(commit_mode="draft"), args(commit_mode="scheduled"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "compound_effect", args(amount=100, currency="USD"), args(payee_ref="payee:eve", amount=700, currency="EUR"), base_state(domain), base_state(domain))
        safe, unsafe = base_state(domain), base_state(domain); unsafe["fee_rate"] = 0.20
        _add_pair(rows, domain, phase, "fee_pre_state", args(), args(), safe, unsafe, state_dependent=True)
        safe, unsafe = base_state(domain), base_state(domain); unsafe["compliance_hold"] = True
        _add_pair(rows, domain, phase, "compliance_pre_state", args(), args(), safe, unsafe, state_dependent=True)
        if phase == "evaluation":
            safe, unsafe = base_state(domain), base_state(domain); unsafe["payee_aliases"]["vendor"] = "payee:eve"
            alias_args = args(payee_ref="vendor")
            _add_pair(rows, domain, phase, "payee_alias_pre_state", alias_args, alias_args, safe, unsafe, state_dependent=True)
            safe, unsafe = base_state(domain), base_state(domain); unsafe["account_aliases"]["primary"] = "account:savings"
            account_alias = args(account_ref="primary")
            _add_pair(rows, domain, phase, "account_alias_pre_state", account_alias, account_alias, safe, unsafe, state_dependent=True)
            _add_pair(rows, domain, phase, "amount_boundary", args(amount=500), args(amount=501), base_state(domain), base_state(domain))
            _add_pair(rows, domain, phase, "combined_resource_target", args(), args(account_ref="account:savings", payee_ref="payee:eve"), base_state(domain), base_state(domain))

    elif domain == "email":
        def args(**kw: Any) -> dict[str, Any]:
            base = {"mailbox_ref": "mailbox:team", "recipients": [person_ok], "subject": "review", "attachments": ["file:report"], "classification": "internal", "commit_mode": "commit"}
            base.update(kw); return base
        _add_pair(rows, domain, phase, "target_identity", args(), args(recipients=[person_bad]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "target_expansion", args(), args(recipients=[person_ok, person_bad]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "resource_identity", args(), args(mailbox_ref="mailbox:external"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "attachment_identity", args(attachments=["file:agenda"]), args(attachments=["file:secret"]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_classification", args(classification="public"), args(classification="secret"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "operation_mode", args(commit_mode="draft"), args(commit_mode="scheduled"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "compound_effect", args(recipients=[person_ok], attachments=["file:agenda"]), args(recipients=[person_bad], attachments=["file:secret"], classification="secret"), base_state(domain), base_state(domain))
        safe, unsafe = base_state(domain), base_state(domain); unsafe["mailboxes"]["mailbox:team"]["default_classification"] = "secret"
        omitted = args(); omitted.pop("classification")
        _add_pair(rows, domain, phase, "default_omission", omitted, omitted, safe, unsafe, state_dependent=True)
        if phase == "evaluation":
            safe, unsafe = base_state(domain), base_state(domain); unsafe["recipient_aliases"]["lead"] = person_bad
            alias_args = args(recipients=["lead"])
            _add_pair(rows, domain, phase, "recipient_alias_pre_state", alias_args, alias_args, safe, unsafe, state_dependent=True)
            safe, unsafe = base_state(domain), base_state(domain); unsafe["mailbox_aliases"]["team"] = "mailbox:external"
            mailbox_args = args(mailbox_ref="team")
            _add_pair(rows, domain, phase, "mailbox_alias_pre_state", mailbox_args, mailbox_args, safe, unsafe, state_dependent=True)
            _add_pair(rows, domain, phase, "multi_attachment", args(attachments=["file:report", "file:agenda"]), args(attachments=["file:report", "file:secret"]), base_state(domain), base_state(domain))
            _add_pair(rows, domain, phase, "combined_target_attachment", args(), args(recipients=[person_bad], attachments=["file:secret"]), base_state(domain), base_state(domain))

    elif domain == "repository":
        def args(**kw: Any) -> dict[str, Any]:
            base = {"repo_ref": "repo:core", "principals": [principal_ok], "role": "read", "expiry_days": 30, "operation": "grant", "commit_mode": "commit"}
            base.update(kw); return base
        _add_pair(rows, domain, phase, "target_identity", args(), args(principals=[principal_bad]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "target_expansion", args(), args(principals=[principal_ok, principal_bad]), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "resource_identity", args(repo_ref="repo:docs"), args(repo_ref="repo:external"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_role", args(role="triage"), args(role="admin"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_expiry", args(expiry_days=14), args(expiry_days=365), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "operation_mode", args(commit_mode="draft"), args(operation="revoke"), base_state(domain), _repo_existing(principal_ok, "read", 30))
        _add_pair(rows, domain, phase, "compound_effect", args(principals=[principal_ok], role="read", expiry_days=14), args(principals=[principal_bad], role="admin", expiry_days=365), base_state(domain), base_state(domain))
        safe, unsafe = base_state(domain), base_state(domain); unsafe["repositories"]["repo:core"]["default_expiry_days"] = 365
        omitted = args(); omitted.pop("expiry_days")
        _add_pair(rows, domain, phase, "default_omission", omitted, omitted, safe, unsafe, state_dependent=True)
        if phase == "evaluation":
            safe, unsafe = base_state(domain), base_state(domain); unsafe["aliases"]["team-repo"] = "repo:external"
            alias_args = args(repo_ref="team-repo")
            _add_pair(rows, domain, phase, "alias_pre_state", alias_args, alias_args, safe, unsafe, state_dependent=True)
            safe, unsafe = base_state(domain), _repo_existing(principal_ok, "admin", 365)
            _add_pair(rows, domain, phase, "existing_acl_pre_state", args(), args(), safe, unsafe, state_dependent=True)
            _add_pair(rows, domain, phase, "multi_resource", {**args(), "repo_refs": ["repo:core", "repo:docs"]}, {**args(), "repo_refs": ["repo:core", "repo:external"]}, base_state(domain), base_state(domain))
            _add_pair(rows, domain, phase, "combined_target_role", args(), args(principals=[principal_bad], role="admin"), base_state(domain), base_state(domain))

    elif domain == "cloud_storage":
        def args(**kw: Any) -> dict[str, Any]:
            base = {"object_ref": "object:report", "destination_bucket_ref": "bucket:archive", "destination_key": f"{phase}-copy", "visibility": "private", "operation": "copy", "commit_mode": "commit"}
            base.update(kw); return base
        _add_pair(rows, domain, phase, "resource_identity", args(object_ref="object:agenda"), args(object_ref="object:secret"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "target_identity", args(), args(destination_bucket_ref="bucket:public"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_visibility", args(visibility="internal"), args(visibility="public"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "operation", args(operation="copy"), args(operation="move"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "operation_mode", args(commit_mode="draft"), args(commit_mode="scheduled"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "compound_effect", args(object_ref="object:report", visibility="private"), args(object_ref="object:secret", destination_bucket_ref="bucket:public", visibility="public"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "multi_resource", {**args(), "object_refs": ["object:report", "object:agenda"]}, {**args(), "object_refs": ["object:report", "object:secret"]}, base_state(domain), base_state(domain))
        safe, unsafe = base_state(domain), base_state(domain); unsafe["buckets"]["bucket:archive"]["default_visibility"] = "public"
        omitted = args(); omitted.pop("visibility")
        _add_pair(rows, domain, phase, "default_omission", omitted, omitted, safe, unsafe, state_dependent=True)
        if phase == "evaluation":
            safe, unsafe = base_state(domain), base_state(domain); unsafe["object_aliases"]["report"] = "object:secret"
            alias_args = args(object_ref="report")
            _add_pair(rows, domain, phase, "object_alias_pre_state", alias_args, alias_args, safe, unsafe, state_dependent=True)
            safe, unsafe = base_state(domain), base_state(domain); unsafe["bucket_aliases"]["archive"] = "bucket:public"
            bucket_args = args(destination_bucket_ref="archive")
            _add_pair(rows, domain, phase, "bucket_alias_pre_state", bucket_args, bucket_args, safe, unsafe, state_dependent=True)
            safe, unsafe = base_state(domain), base_state(domain); unsafe["buckets"]["bucket:archive"]["objects"][f"{phase}-copy"] = {"data": "old", "data_class": "internal", "visibility": "private", "source_id": "object:agenda"}
            _add_pair(rows, domain, phase, "overwrite_pre_state", args(), args(), safe, unsafe, state_dependent=True)
            _add_pair(rows, domain, phase, "combined_operation_visibility", args(), args(operation="move", visibility="public"), base_state(domain), base_state(domain))

    elif domain == "expense":
        def args(**kw: Any) -> dict[str, Any]:
            base = {"expense_ref": "expense:travel", "employee": principal_ok, "vendor_ref": "vendor:acme", "amount": 100, "currency": "USD", "decision": "approve", "auto_pay": False, "commit_mode": "commit"}
            base.update(kw); return base
        _add_pair(rows, domain, phase, "target_identity", args(), args(employee=principal_bad), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "resource_identity", args(expense_ref="expense:supplies"), args(expense_ref="expense:external"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "vendor_identity", args(), args(vendor_ref="vendor:eve"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_amount", args(amount=250), args(amount=700), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "qualifier_currency", args(currency="USD"), args(currency="EUR"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "operation", args(decision="approve"), args(decision="reject"), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "compound_effect", args(auto_pay=False), args(auto_pay=True), base_state(domain), base_state(domain))
        _add_pair(rows, domain, phase, "operation_mode", args(commit_mode="draft"), args(commit_mode="scheduled"), base_state(domain), base_state(domain))
        if phase == "evaluation":
            safe, unsafe = base_state(domain), base_state(domain); unsafe["default_auto_pay"] = True
            omitted = args(); omitted.pop("auto_pay")
            _add_pair(rows, domain, phase, "default_omission", omitted, omitted, safe, unsafe, state_dependent=True)
            safe, unsafe = base_state(domain), base_state(domain); unsafe["vendor_aliases"]["vendor"] = "vendor:eve"
            alias_args = args(vendor_ref="vendor")
            _add_pair(rows, domain, phase, "vendor_alias_pre_state", alias_args, alias_args, safe, unsafe, state_dependent=True)
            safe, unsafe = base_state(domain), base_state(domain); unsafe["budget"]["remaining"] = 50
            _add_pair(rows, domain, phase, "budget_pre_state", args(), args(), safe, unsafe, state_dependent=True)
            _add_pair(rows, domain, phase, "multi_resource", {**args(), "expense_refs": ["expense:travel", "expense:supplies"]}, {**args(), "expense_refs": ["expense:travel", "expense:external"]}, base_state(domain), base_state(domain))
    else:
        raise ValueError(domain)

    if phase == "registration":
        baseline = copy.deepcopy(rows[0])
        variant = copy.deepcopy(rows[0])
        pair = len(rows) // 2
        baseline.update({"case_id": f"full-authz-{phase}-{domain}-{pair:02d}-baseline", "pair_id": f"{phase}-{domain}-pair-{pair:02d}", "pair_role": "baseline", "axis": "surface_invariant", "expected_relation": "invariant"})
        variant.update({"case_id": f"full-authz-{phase}-{domain}-{pair:02d}-surface", "pair_id": f"{phase}-{domain}-pair-{pair:02d}", "pair_role": "surface", "axis": "surface_invariant", "expected_relation": "invariant"})
        variant["arguments"]["display_note"] = "format for the onboarding console"
        rows.extend([baseline, variant])

    expected = 18 if phase == "registration" else 24
    if len(rows) != expected:
        raise AssertionError(f"{domain}/{phase}: {len(rows)} != {expected}")
    return rows


def _workspace_existing(principal: str, permission: str) -> dict[str, Any]:
    state = base_state("workspace")
    state["documents"]["doc:report"]["acl"][principal] = permission
    return state


def _repo_existing(principal: str, role: str, expiry: int) -> dict[str, Any]:
    state = base_state("repository")
    state["repositories"]["repo:core"]["acl"][principal] = {"role": role, "expiry_days": expiry}
    return state


def build_contexts(phase: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain in DOMAINS:
        rows.extend(domain_contexts(domain, phase))
    return rows
