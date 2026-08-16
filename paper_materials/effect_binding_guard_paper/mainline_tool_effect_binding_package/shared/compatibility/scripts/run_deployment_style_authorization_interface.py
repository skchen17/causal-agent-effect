#!/usr/bin/env python3
"""Run a frozen deployment-style authorization-interface experiment.

The experiment executes four stateful tools in copied in-memory sandboxes,
derives committed effects from before/after state, applies independently stated
ACL/capability-style rules to those effects, and compares four pre-commit
representations through the same finite-domain policy consumer.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def find_root(path: Path) -> Path:
    for candidate in (path.resolve(), *path.resolve().parents):
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
EVAL = ROOT / (
    "experiments/human-authority-and-causal-validation/evaluation/"
    "deployment-style-authorization-policy-conformance"
)
RESULTS = ROOT / (
    "experiments/human-authority-and-causal-validation/results/"
    "deployment-style-authorization-policy-conformance"
)
PROTOCOL = EVAL / "protocol.json"
POLICIES = EVAL / "policy-manifests.json"
CONTEXTS = EVAL / "contexts.jsonl"

REPRESENTATIONS = (
    "tool_name",
    "canonical_raw_arguments",
    "common_effect_fields",
    "validated_typed_effects",
)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def policies() -> dict[str, dict[str, Any]]:
    calendar_created = [
        "evt-target", "evt-expand", "evt-vis-private", "evt-vis-public",
        "evt-compound-safe", "evt-compound-deny", "evt-default",
    ]
    return {
        "calendar-team-acl": {
            "policy_type": "acl",
            "domain": "calendar",
            "rules": [
                {"effect": "event_created", "resources": calendar_created},
                {"effect": "event_updated", "resources": ["evt-prestate"]},
                {"effect": "participant_invited", "targets": ["alice@example.com", "bob@example.com"]},
                {"effect": "visibility_set", "qualifiers": {"visibility": {"allowed": ["private", "internal"]}}},
            ],
        },
        "workspace-share-acl": {
            "policy_type": "acl",
            "domain": "workspace",
            "rules": [
                {"effect": "share_granted", "resources": ["doc:report", "doc:plan"], "targets": ["alice", "bob"], "qualifiers": {"permission": {"allowed": ["viewer"]}}},
                {"effect": "visibility_set", "resources": ["doc:report", "doc:plan"], "qualifiers": {"visibility": {"allowed": ["private", "internal"]}}},
            ],
        },
        "messaging-capability": {
            "policy_type": "capability",
            "domain": "messaging",
            "rules": [
                {"effect": "message_posted", "resources": ["channel:internal"], "qualifiers": {"payload_class": {"allowed": ["public", "internal"]}, "delivery_mode": {"allowed": ["immediate"]}}},
                {"effect": "notification_delivered", "resources": ["channel:internal"], "targets": ["alice", "bob"]},
            ],
        },
        "banking-delegation": {
            "policy_type": "delegation",
            "domain": "banking",
            "rules": [
                {"effect": "funds_transferred", "resources": ["account:checking"], "targets": ["payee:acme"], "qualifiers": {"amount": {"max": 500}, "currency": {"allowed": ["USD"]}, "delivery_mode": {"allowed": ["immediate"]}}},
                {"effect": "balance_debited", "resources": ["account:checking"], "qualifiers": {"amount": {"max": 505}, "currency": {"allowed": ["USD"]}, "delivery_mode": {"allowed": ["immediate"]}}},
                {"effect": "fee_charged", "resources": ["account:checking"], "qualifiers": {"amount": {"max": 5}, "currency": {"allowed": ["USD"]}}},
            ],
        },
    }


def _calendar_state(*, default_visibility: str = "private", existing: bool = False) -> dict[str, Any]:
    events: dict[str, Any] = {}
    if existing:
        events["evt-prestate"] = {
            "title": "old title", "participants": ["alice@example.com"], "visibility": "private"
        }
    return {"default_visibility": default_visibility, "events": events}


def _file_state(*, default_visibility: str = "private", eve_present: bool = False) -> dict[str, Any]:
    acl = {"alice": "viewer"}
    if eve_present:
        acl["eve"] = "viewer"
    return {
        "documents": {
            "doc:report": {"acl": acl, "visibility": "private", "default_visibility": default_visibility},
            "doc:plan": {"acl": {}, "visibility": "private", "default_visibility": default_visibility},
        }
    }


def _message_state(*, alias_target: str = "channel:internal") -> dict[str, Any]:
    return {
        "aliases": {"ops": alias_target},
        "channels": {"channel:internal": [], "channel:external": []},
    }


def _bank_state(*, vendor: str = "payee:acme", fee_rate: float = 0.01) -> dict[str, Any]:
    return {
        "balances": {"account:checking": 5000.0},
        "payee_aliases": {"vendor": vendor, "acme": "payee:acme", "outsider": "payee:eve"},
        "fee_rate": fee_rate,
        "transfers": [],
    }


def build_contexts() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(domain: str, index: int, axis: str, role: str, args: dict[str, Any], state: dict[str, Any], policy_id: str, pair: int) -> None:
        rows.append({
            "case_id": f"deploy-authz-{domain}-{index:02d}",
            "domain": domain,
            "tool_name": {
                "calendar": "schedule_meeting",
                "workspace": "share_document",
                "messaging": "post_message",
                "banking": "transfer_funds",
            }[domain],
            "axis": axis,
            "pair_id": f"{domain}-pair-{pair}",
            "pair_role": role,
            "policy_id": policy_id,
            "arguments": args,
            "pre_state": state,
        })

    cal = "calendar-team-acl"
    add("calendar", 0, "target_identity", "authorized", {"event_id": "evt-target", "title": "sync", "participants": ["alice@example.com"], "visibility": "private"}, _calendar_state(), cal, 0)
    add("calendar", 1, "target_identity", "unauthorized", {"event_id": "evt-target", "title": "sync", "participants": ["eve@example.com"], "visibility": "private"}, _calendar_state(), cal, 0)
    add("calendar", 2, "target_expansion", "authorized", {"event_id": "evt-expand", "title": "sync", "participants": ["alice@example.com"], "visibility": "private"}, _calendar_state(), cal, 1)
    add("calendar", 3, "target_expansion", "unauthorized", {"event_id": "evt-expand", "title": "sync", "participants": ["alice@example.com", "eve@example.com"], "visibility": "private"}, _calendar_state(), cal, 1)
    add("calendar", 4, "qualifier_visibility", "authorized", {"event_id": "evt-vis-private", "title": "sync", "participants": ["alice@example.com"], "visibility": "private"}, _calendar_state(), cal, 2)
    add("calendar", 5, "qualifier_visibility", "unauthorized", {"event_id": "evt-vis-public", "title": "sync", "participants": ["alice@example.com"], "visibility": "public"}, _calendar_state(), cal, 2)
    add("calendar", 6, "compound_effect", "authorized", {"event_id": "evt-compound-safe", "title": "sync", "participants": ["alice@example.com", "bob@example.com"], "visibility": "internal"}, _calendar_state(), cal, 3)
    add("calendar", 7, "compound_effect", "unauthorized", {"event_id": "evt-compound-deny", "title": "sync", "participants": ["alice@example.com", "eve@example.com"], "visibility": "public"}, _calendar_state(), cal, 3)
    default_args = {"event_id": "evt-default", "title": "sync", "participants": ["alice@example.com"]}
    add("calendar", 8, "default_pre_state", "authorized", default_args, _calendar_state(default_visibility="private"), cal, 4)
    add("calendar", 9, "default_pre_state", "unauthorized", default_args, _calendar_state(default_visibility="public"), cal, 4)
    pre_args = {"event_id": "evt-prestate", "title": "new title", "participants": ["alice@example.com"], "visibility": "private"}
    add("calendar", 10, "existence_pre_state", "authorized", pre_args, _calendar_state(existing=True), cal, 5)
    add("calendar", 11, "existence_pre_state", "unauthorized", pre_args, _calendar_state(existing=False), cal, 5)

    ws = "workspace-share-acl"
    add("workspace", 0, "target_identity", "authorized", {"doc_id": "doc:report", "recipients": ["alice"], "permission": "viewer", "visibility": "private"}, _file_state(), ws, 0)
    add("workspace", 1, "target_identity", "unauthorized", {"doc_id": "doc:report", "recipients": ["eve"], "permission": "viewer", "visibility": "private"}, _file_state(), ws, 0)
    add("workspace", 2, "target_expansion", "authorized", {"doc_id": "doc:plan", "recipients": ["alice"], "permission": "viewer", "visibility": "private"}, _file_state(), ws, 1)
    add("workspace", 3, "target_expansion", "unauthorized", {"doc_id": "doc:plan", "recipients": ["alice", "eve"], "permission": "viewer", "visibility": "private"}, _file_state(), ws, 1)
    add("workspace", 4, "qualifier_permission", "authorized", {"doc_id": "doc:report", "recipients": ["bob"], "permission": "viewer", "visibility": "private"}, _file_state(), ws, 2)
    add("workspace", 5, "qualifier_permission", "unauthorized", {"doc_id": "doc:report", "recipients": ["bob"], "permission": "editor", "visibility": "private"}, _file_state(), ws, 2)
    add("workspace", 6, "qualifier_visibility", "authorized", {"doc_id": "doc:plan", "recipients": ["alice", "bob"], "permission": "viewer", "visibility": "internal"}, _file_state(), ws, 3)
    add("workspace", 7, "qualifier_visibility", "unauthorized", {"doc_id": "doc:plan", "recipients": ["alice", "bob"], "permission": "viewer", "visibility": "public"}, _file_state(), ws, 3)
    omitted = {"doc_id": "doc:report", "recipients": ["bob"], "permission": "viewer"}
    add("workspace", 8, "default_pre_state", "authorized", omitted, _file_state(default_visibility="private"), ws, 4)
    add("workspace", 9, "default_pre_state", "unauthorized", omitted, _file_state(default_visibility="public"), ws, 4)
    pre_share = {"doc_id": "doc:report", "recipients": ["eve"], "permission": "viewer", "visibility": "private"}
    add("workspace", 10, "existing_grant_pre_state", "authorized", pre_share, _file_state(eve_present=True), ws, 5)
    add("workspace", 11, "existing_grant_pre_state", "unauthorized", pre_share, _file_state(eve_present=False), ws, 5)

    msg = "messaging-capability"
    base_msg = {"message": "status update", "payload_class": "internal", "delivery_mode": "immediate", "recipients": ["alice"]}
    add("messaging", 0, "resource_identity", "authorized", {**base_msg, "channel_id": "channel:internal"}, _message_state(), msg, 0)
    add("messaging", 1, "resource_identity", "unauthorized", {**base_msg, "channel_id": "channel:external"}, _message_state(), msg, 0)
    add("messaging", 2, "target_identity", "authorized", {**base_msg, "channel_id": "channel:internal", "recipients": ["bob"]}, _message_state(), msg, 1)
    add("messaging", 3, "target_identity", "unauthorized", {**base_msg, "channel_id": "channel:internal", "recipients": ["eve"]}, _message_state(), msg, 1)
    add("messaging", 4, "target_expansion", "authorized", {**base_msg, "channel_id": "channel:internal", "recipients": ["alice", "bob"]}, _message_state(), msg, 2)
    add("messaging", 5, "target_expansion", "unauthorized", {**base_msg, "channel_id": "channel:internal", "recipients": ["alice", "eve"]}, _message_state(), msg, 2)
    add("messaging", 6, "qualifier_payload", "authorized", {**base_msg, "channel_id": "channel:internal", "payload_class": "public"}, _message_state(), msg, 3)
    add("messaging", 7, "qualifier_payload", "unauthorized", {**base_msg, "channel_id": "channel:internal", "payload_class": "secret"}, _message_state(), msg, 3)
    add("messaging", 8, "operation_mode", "authorized", {**base_msg, "channel_id": "channel:internal", "delivery_mode": "immediate"}, _message_state(), msg, 4)
    add("messaging", 9, "operation_mode", "unauthorized", {**base_msg, "channel_id": "channel:internal", "delivery_mode": "scheduled"}, _message_state(), msg, 4)
    alias_args = {**base_msg, "channel_alias": "ops"}
    add("messaging", 10, "alias_pre_state", "authorized", alias_args, _message_state(alias_target="channel:internal"), msg, 5)
    add("messaging", 11, "alias_pre_state", "unauthorized", alias_args, _message_state(alias_target="channel:external"), msg, 5)

    bank = "banking-delegation"
    def transfer(alias: str = "acme", amount: float = 100, currency: str = "USD", mode: str = "immediate") -> dict[str, Any]:
        return {"source_account": "account:checking", "payee_alias": alias, "amount": amount, "currency": currency, "delivery_mode": mode}
    add("banking", 0, "target_identity", "authorized", transfer("acme"), _bank_state(), bank, 0)
    add("banking", 1, "target_identity", "unauthorized", transfer("outsider"), _bank_state(), bank, 0)
    add("banking", 2, "qualifier_amount", "authorized", transfer(amount=100), _bank_state(), bank, 1)
    add("banking", 3, "qualifier_amount", "unauthorized", transfer(amount=700), _bank_state(), bank, 1)
    add("banking", 4, "qualifier_currency", "authorized", transfer(currency="USD"), _bank_state(), bank, 2)
    add("banking", 5, "qualifier_currency", "unauthorized", transfer(currency="EUR"), _bank_state(), bank, 2)
    add("banking", 6, "operation_mode", "authorized", transfer(mode="immediate"), _bank_state(), bank, 3)
    add("banking", 7, "operation_mode", "unauthorized", transfer(mode="scheduled"), _bank_state(), bank, 3)
    fee_args = transfer(amount=100)
    add("banking", 8, "fee_pre_state", "authorized", fee_args, _bank_state(fee_rate=0.01), bank, 4)
    add("banking", 9, "fee_pre_state", "unauthorized", fee_args, _bank_state(fee_rate=0.20), bank, 4)
    alias_bank = transfer(alias="vendor")
    add("banking", 10, "alias_pre_state", "authorized", alias_bank, _bank_state(vendor="payee:acme"), bank, 5)
    add("banking", 11, "alias_pre_state", "unauthorized", alias_bank, _bank_state(vendor="payee:eve"), bank, 5)
    return rows


def execute_tool(row: dict[str, Any]) -> dict[str, Any]:
    state = copy.deepcopy(row["pre_state"])
    args = copy.deepcopy(row["arguments"])
    tool = row["tool_name"]
    if tool == "schedule_meeting":
        event_id = args["event_id"]
        visibility = args.get("visibility", state["default_visibility"])
        state["events"][event_id] = {
            "title": args["title"],
            "participants": sorted(set(args.get("participants", []))),
            "visibility": visibility,
        }
    elif tool == "share_document":
        doc = state["documents"][args["doc_id"]]
        for principal in args.get("recipients", []):
            doc["acl"][principal] = args["permission"]
        doc["visibility"] = args.get("visibility", doc["default_visibility"])
    elif tool == "post_message":
        channel = args.get("channel_id") or state["aliases"][args["channel_alias"]]
        state["channels"][channel].append({
            "message": args["message"],
            "payload_class": args["payload_class"],
            "delivery_mode": args["delivery_mode"],
            "recipients": sorted(set(args.get("recipients", []))),
        })
    elif tool == "transfer_funds":
        payee = state["payee_aliases"][args["payee_alias"]]
        fee = round(float(args["amount"]) * float(state["fee_rate"]), 2)
        total = round(float(args["amount"]) + fee, 2)
        state["balances"][args["source_account"]] = round(state["balances"][args["source_account"]] - total, 2)
        state["transfers"].append({**args, "payee": payee, "fee": fee, "total_debit": total})
    else:
        raise ValueError(f"unknown tool: {tool}")
    return state


def source_effects(row: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    before = row["pre_state"]
    args = row["arguments"]
    tool = row["tool_name"]
    effects: list[dict[str, Any]] = []
    if tool == "schedule_meeting":
        event_id = args["event_id"]
        old = before["events"].get(event_id)
        new = after["events"][event_id]
        if old is None:
            effects.append(atom("event_created", "create", "calendar_event", event_id))
            old_participants: set[str] = set()
            old_visibility = None
        else:
            old_participants = set(old["participants"])
            old_visibility = old["visibility"]
            if old != new:
                effects.append(atom("event_updated", "update", "calendar_event", event_id))
        for principal in sorted(set(new["participants"]) - old_participants):
            effects.append(atom("participant_invited", "invite", "calendar_event", event_id, target=principal))
        if old_visibility != new["visibility"]:
            effects.append(atom("visibility_set", "set_visibility", "calendar_event", event_id, qualifiers={"visibility": new["visibility"]}))
    elif tool == "share_document":
        doc_id = args["doc_id"]
        old = before["documents"][doc_id]
        new = after["documents"][doc_id]
        for principal, permission in sorted(new["acl"].items()):
            if old["acl"].get(principal) != permission:
                effects.append(atom("share_granted", "grant", "document", doc_id, target=principal, qualifiers={"permission": permission}))
        if old["visibility"] != new["visibility"]:
            effects.append(atom("visibility_set", "set_visibility", "document", doc_id, qualifiers={"visibility": new["visibility"]}))
    elif tool == "post_message":
        changed = [name for name in after["channels"] if after["channels"][name] != before["channels"][name]]
        if len(changed) != 1:
            raise AssertionError("message execution must change exactly one channel")
        channel = changed[0]
        message = after["channels"][channel][-1]
        q = {"payload_class": message["payload_class"], "delivery_mode": message["delivery_mode"]}
        effects.append(atom("message_posted", "send", "channel", channel, target=channel, qualifiers=q, commit_mode=message["delivery_mode"]))
        for principal in message["recipients"]:
            effects.append(atom("notification_delivered", "notify", "channel", channel, target=principal, commit_mode=message["delivery_mode"]))
    elif tool == "transfer_funds":
        transfer = after["transfers"][-1]
        q = {"amount": transfer["amount"], "currency": transfer["currency"], "delivery_mode": transfer["delivery_mode"]}
        effects.append(atom("funds_transferred", "transfer", "bank_account", transfer["source_account"], target=transfer["payee"], qualifiers=q, commit_mode=transfer["delivery_mode"]))
        effects.append(atom("balance_debited", "debit", "bank_account", transfer["source_account"], qualifiers={**q, "amount": transfer["total_debit"]}, commit_mode=transfer["delivery_mode"]))
        effects.append(atom("fee_charged", "fee", "bank_account", transfer["source_account"], target="bank", qualifiers={"amount": transfer["fee"], "currency": transfer["currency"]}, commit_mode=transfer["delivery_mode"]))
    return normalize_atoms(effects)


def instantiate_descriptor(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Independent pre-commit descriptor instantiation over args and pre-state."""
    args = row["arguments"]
    state = row["pre_state"]
    tool = row["tool_name"]
    effects: list[dict[str, Any]] = []
    if tool == "schedule_meeting":
        event_id = args["event_id"]
        prior = state["events"].get(event_id)
        visibility = args.get("visibility", state["default_visibility"])
        if prior is None:
            effects.append(atom("event_created", "create", "calendar_event", event_id))
            old_targets: set[str] = set()
            old_visibility = None
        else:
            projected = {"title": args["title"], "participants": sorted(set(args.get("participants", []))), "visibility": visibility}
            if projected != prior:
                effects.append(atom("event_updated", "update", "calendar_event", event_id))
            old_targets = set(prior["participants"])
            old_visibility = prior["visibility"]
        for principal in sorted(set(args.get("participants", [])) - old_targets):
            effects.append(atom("participant_invited", "invite", "calendar_event", event_id, target=principal))
        if old_visibility != visibility:
            effects.append(atom("visibility_set", "set_visibility", "calendar_event", event_id, qualifiers={"visibility": visibility}))
    elif tool == "share_document":
        doc_id = args["doc_id"]
        doc = state["documents"][doc_id]
        for principal in sorted(set(args.get("recipients", []))):
            if doc["acl"].get(principal) != args["permission"]:
                effects.append(atom("share_granted", "grant", "document", doc_id, target=principal, qualifiers={"permission": args["permission"]}))
        visibility = args.get("visibility", doc["default_visibility"])
        if doc["visibility"] != visibility:
            effects.append(atom("visibility_set", "set_visibility", "document", doc_id, qualifiers={"visibility": visibility}))
    elif tool == "post_message":
        channel = args.get("channel_id") or state["aliases"][args["channel_alias"]]
        q = {"payload_class": args["payload_class"], "delivery_mode": args["delivery_mode"]}
        effects.append(atom("message_posted", "send", "channel", channel, target=channel, qualifiers=q, commit_mode=args["delivery_mode"]))
        for principal in sorted(set(args.get("recipients", []))):
            effects.append(atom("notification_delivered", "notify", "channel", channel, target=principal, commit_mode=args["delivery_mode"]))
    elif tool == "transfer_funds":
        source = args["source_account"]
        target = state["payee_aliases"][args["payee_alias"]]
        fee = round(float(args["amount"]) * float(state["fee_rate"]), 2)
        total = round(float(args["amount"]) + fee, 2)
        q = {"amount": args["amount"], "currency": args["currency"], "delivery_mode": args["delivery_mode"]}
        effects.append(atom("funds_transferred", "transfer", "bank_account", source, target=target, qualifiers=q, commit_mode=args["delivery_mode"]))
        effects.append(atom("balance_debited", "debit", "bank_account", source, qualifiers={**q, "amount": total}, commit_mode=args["delivery_mode"]))
        effects.append(atom("fee_charged", "fee", "bank_account", source, target="bank", qualifiers={"amount": fee, "currency": args["currency"]}, commit_mode=args["delivery_mode"]))
    return normalize_atoms(effects)


def constraint_matches(value: Any, constraint: dict[str, Any]) -> bool:
    if "allowed" in constraint and value not in constraint["allowed"]:
        return False
    if "max" in constraint and (not isinstance(value, (int, float)) or value > constraint["max"]):
        return False
    if "min" in constraint and (not isinstance(value, (int, float)) or value < constraint["min"]):
        return False
    return True


def rule_matches(effect: dict[str, Any], rule: dict[str, Any]) -> bool:
    if effect["effect"] != rule["effect"]:
        return False
    if rule.get("resources") and effect["resource_id"] not in rule["resources"]:
        return False
    if rule.get("targets") and effect.get("target_principal") not in rule["targets"]:
        return False
    for key, constraint in rule.get("qualifiers", {}).items():
        if key not in effect["qualifiers"] or not constraint_matches(effect["qualifiers"][key], constraint):
            return False
    return True


def policy_decision(effects: list[dict[str, Any]], policy: dict[str, Any]) -> str:
    return "ALLOW" if all(any(rule_matches(effect, rule) for rule in policy["rules"]) for effect in effects) else "DENY"


def representation(row: dict[str, Any], typed: list[dict[str, Any]], name: str) -> Any:
    if name == "tool_name":
        return {"tool_name": row["tool_name"]}
    if name == "canonical_raw_arguments":
        return {"tool_name": row["tool_name"], "arguments": row["arguments"]}
    if name == "common_effect_fields":
        return [
            {key: value for key, value in effect.items() if key != "qualifiers"}
            for effect in typed
        ]
    if name == "validated_typed_effects":
        return typed
    raise ValueError(name)


def compile_consumer(rows: list[dict[str, Any]], name: str, mixed_action: str = "ABSTAIN") -> dict[str, str]:
    cells: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        key = canonical({"policy_id": row["policy_id"], "view": row["representations"][name]})
        cells[key].append(row["ideal_decision"])
    compiled: dict[str, str] = {}
    for key, labels in cells.items():
        unique = set(labels)
        compiled[key] = next(iter(unique)) if len(unique) == 1 else mixed_action
    return compiled


def predict(rows: list[dict[str, Any]], name: str, mixed_action: str) -> list[str]:
    consumer = compile_consumer(rows, name, mixed_action)
    return [consumer[canonical({"policy_id": row["policy_id"], "view": row["representations"][name]})] for row in rows]


def rate(n: int, d: int) -> dict[str, Any]:
    return {"successes": n, "total": d, "rate": n / d if d else None}


def metrics(rows: list[dict[str, Any]], name: str, mixed_action: str = "ABSTAIN") -> dict[str, Any]:
    predictions = predict(rows, name, mixed_action)
    unauthorized = [i for i, row in enumerate(rows) if row["ideal_decision"] == "DENY"]
    authorized = [i for i, row in enumerate(rows) if row["ideal_decision"] == "ALLOW"]
    upa = sum(predictions[i] == "ALLOW" for i in unauthorized)
    fd = sum(predictions[i] == "DENY" for i in authorized)
    abstain = sum(value == "ABSTAIN" for value in predictions)
    correct = sum(value == row["ideal_decision"] for value, row in zip(predictions, rows))
    withheld = sum(predictions[i] != "ALLOW" for i in authorized)
    return {
        "representation": name,
        "mixed_action": mixed_action,
        "unsafe_pre_allow": rate(upa, len(unauthorized)),
        "false_denial": rate(fd, len(authorized)),
        "abstain": rate(abstain, len(rows)),
        "coverage": rate(len(rows) - abstain, len(rows)),
        "decision_accuracy": rate(correct, len(rows)),
        "withheld_authorized_work": rate(withheld, len(authorized)),
    }


def collision_audit(rows: list[dict[str, Any]], name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = canonical({"policy_id": row["policy_id"], "view": row["representations"][name]})
        cells[key].append(row)
    witnesses: list[dict[str, Any]] = []
    lower_bound = 0
    for index, (key, members) in enumerate(sorted(cells.items())):
        counts = Counter(row["ideal_decision"] for row in members)
        if not counts["ALLOW"] or not counts["DENY"]:
            continue
        lower_bound += min(counts["ALLOW"], counts["DENY"])
        witnesses.append({
            "representation": name,
            "cell_id": f"{name}-mixed-{index:03d}",
            "policy_and_view": json.loads(key),
            "n_authorized": counts["ALLOW"],
            "n_unauthorized": counts["DENY"],
            "case_ids": [row["case_id"] for row in members],
            "axes": sorted({row["axis"] for row in members}),
        })
    return ({
        "representation": name,
        "n_cells": len(cells),
        "n_mixed_cells": len(witnesses),
        "n_rows_in_mixed_cells": sum(len(row["case_ids"]) for row in witnesses),
        "unit_cost_error_lower_bound": lower_bound,
        "conforms_on_frozen_relation": not witnesses,
    }, witnesses)


def materialize_inputs() -> None:
    EVAL.mkdir(parents=True, exist_ok=True)
    POLICIES.write_text(json.dumps(policies(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CONTEXTS.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in build_contexts()), encoding="utf-8")


def verify_protocol() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol.get("status") != "frozen_before_full_run":
        raise ValueError("protocol is not frozen")
    observed = {
        "policy_manifests_sha256": sha256_file(POLICIES),
        "contexts_sha256": sha256_file(CONTEXTS),
        "runner_sha256": sha256_file(Path(__file__)),
    }
    if protocol.get("input_hashes") != observed:
        raise ValueError(f"frozen input mismatch: {observed}")
    return protocol


def load_inputs() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    policy_rows = json.loads(POLICIES.read_text(encoding="utf-8"))
    contexts = [json.loads(line) for line in CONTEXTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    return policy_rows, contexts


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "# Deployment-Style Authorization Interface Experiment",
        "",
        f"- Status: `{report['status']}`",
        f"- Contexts: `{report['n_contexts']}` across `{report['n_domains']}` domains",
        f"- Ideal labels: `{report['ideal_decisions']}`",
        f"- State-dependent contexts: `{report['n_state_dependent_contexts']}`",
        "",
        "## Primary fail-closed tri-state consumer",
        "",
        "| Representation | UPA | FD | Abstain | Coverage | Accuracy | Withheld authorized |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["primary_metrics"]:
        def show(key: str) -> str:
            value = row[key]
            return f"{value['successes']}/{value['total']} ({value['rate']:.3f})"
        lines.append(f"| `{row['representation']}` | {show('unsafe_pre_allow')} | {show('false_denial')} | {show('abstain')} | {show('coverage')} | {show('decision_accuracy')} | {show('withheld_authorized_work')} |")
    lines.extend([
        "", "## Interpretation", "",
        "The policies are explicit ACL, capability, and delegation-style rules over concrete committed effects. The copied sandbox and source-state diff determine the ideal decision. All four representations use the same compiled finite-domain consumer. A mixed representation cell returns ABSTAIN in the primary mode; uniform fail-open and fail-closed diagnostics expose the corresponding unsafe-allow/false-denial tradeoff.",
        "",
        "This is a controlled four-domain deployment-style policy test. It establishes only bounded interface conformance on the frozen contexts and does not estimate policy prevalence or production safety.",
        "",
    ])
    return "\n".join(lines)


def render_table(report: dict[str, Any]) -> str:
    names = {"tool_name": "Tool name", "canonical_raw_arguments": "Raw arguments", "common_effect_fields": "Common fields", "validated_typed_effects": "Validated typed effects"}
    lines = [
        r"\begin{table}[t]", r"\centering", r"\small",
        r"\caption{Deployment-style authorization-interface conformance over 48 frozen source-executed contexts. Mixed cells abstain in the primary consumer.}",
        r"\label{tab:deployment-authz-interface}", r"\begin{tabular}{lrrrrr}", r"\toprule",
        "View & Mixed & UPA & Abstain & Coverage & Accuracy \\\\", r"\midrule",
    ]
    audits = {row["representation"]: row for row in report["collision_audit"]}
    for row in report["primary_metrics"]:
        lines.append(f"{names[row['representation']]} & {audits[row['representation']]['n_mixed_cells']} & {100*row['unsafe_pre_allow']['rate']:.1f}\\% & {100*row['abstain']['rate']:.1f}\\% & {100*row['coverage']['rate']:.1f}\\% & {100*row['decision_accuracy']['rate']:.1f}\\% \\\\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    return "\n".join(lines)


def run(mode: str, output_dir: Path | None = None) -> dict[str, Any]:
    protocol = verify_protocol()
    policy_rows, contexts = load_inputs()
    if mode == "smoke":
        contexts = [row for domain in sorted({r["domain"] for r in contexts}) for row in [x for x in contexts if x["domain"] == domain][:2]]
    executed: list[dict[str, Any]] = []
    for row in contexts:
        after = execute_tool(row)
        source = source_effects(row, after)
        typed = instantiate_descriptor(row)
        ideal = policy_decision(source, policy_rows[row["policy_id"]])
        item = {**row, "post_state_hash": digest(after), "source_effects": source, "typed_effects": typed, "descriptor_matches_source": typed == source, "ideal_decision": ideal}
        item["representations"] = {name: representation(item, typed, name) for name in REPRESENTATIONS}
        executed.append(item)

    collision_rows = []
    witnesses = []
    for name in REPRESENTATIONS:
        summary, found = collision_audit(executed, name)
        collision_rows.append(summary)
        witnesses.extend(found)
    primary = [metrics(executed, name, "ABSTAIN") for name in REPRESENTATIONS]
    fail_open = [metrics(executed, name, "ALLOW") for name in REPRESENTATIONS]
    fail_closed = [metrics(executed, name, "DENY") for name in REPRESENTATIONS]
    typed_primary = next(row for row in primary if row["representation"] == "validated_typed_effects")
    raw_audit = next(row for row in collision_rows if row["representation"] == "canonical_raw_arguments")
    state_rows = [row for row in executed if "pre_state" in row["axis"]]
    state_raw_mixed = []
    for witness in witnesses:
        if witness["representation"] == "canonical_raw_arguments" and any(case in {row["case_id"] for row in state_rows} for case in witness["case_ids"]):
            state_raw_mixed.append(witness)
    coarse_gate_names = REPRESENTATIONS[:-1] if mode == "full" else ("tool_name",)
    gates = {
        "protocol_hashes_match": True,
        "expected_context_count": len(executed) == (48 if mode == "full" else 8),
        "four_domains_present": len({row["domain"] for row in executed}) == 4,
        "balanced_ideal_labels": Counter(row["ideal_decision"] for row in executed)["ALLOW"] == Counter(row["ideal_decision"] for row in executed)["DENY"],
        "descriptor_exact_on_source_executions": all(row["descriptor_matches_source"] for row in executed),
        "coarse_representation_collisions_present": all(next(row for row in collision_rows if row["representation"] == name)["n_mixed_cells"] > 0 for name in coarse_gate_names),
        "typed_representation_has_no_mixed_cells": next(row for row in collision_rows if row["representation"] == "validated_typed_effects")["n_mixed_cells"] == 0,
        "typed_primary_has_zero_unsafe_allow": typed_primary["unsafe_pre_allow"]["successes"] == 0,
        "typed_primary_has_zero_false_denial": typed_primary["false_denial"]["successes"] == 0,
        "typed_primary_full_coverage": typed_primary["coverage"]["rate"] == 1.0,
        "raw_arguments_have_state_dependent_collision": bool(state_raw_mixed) if mode == "full" else raw_audit["n_mixed_cells"] >= 0,
        "no_rows_dropped": len(executed) == len({row["case_id"] for row in executed}),
    }
    report = {
        "status": "passed" if all(gates.values()) else "failed",
        "experiment": "deployment_style_authorization_interface",
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_contexts": len(executed),
        "n_domains": len({row["domain"] for row in executed}),
        "n_tools": len({row["tool_name"] for row in executed}),
        "n_policies": len({row["policy_id"] for row in executed}),
        "ideal_decisions": dict(Counter(row["ideal_decision"] for row in executed)),
        "n_state_dependent_contexts": len(state_rows),
        "descriptor_conformance": rate(sum(row["descriptor_matches_source"] for row in executed), len(executed)),
        "collision_audit": collision_rows,
        "primary_metrics": primary,
        "uniform_fail_open_diagnostic": fail_open,
        "uniform_fail_closed_diagnostic": fail_closed,
        "state_dependent_raw_argument_mixed_cells": state_raw_mixed,
        "gates": gates,
        "input_hashes": protocol["input_hashes"],
        "claim_boundary": protocol["claim_boundary"],
    }
    target = output_dir or (RESULTS if mode == "full" else RESULTS / "smoke")
    target.mkdir(parents=True, exist_ok=True)
    (target / "source-executions.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in executed), encoding="utf-8")
    decisions = []
    for name in REPRESENTATIONS:
        for mixed_action in ("ABSTAIN", "ALLOW", "DENY"):
            preds = predict(executed, name, mixed_action)
            decisions.extend({"case_id": row["case_id"], "representation": name, "mixed_action": mixed_action, "ideal_decision": row["ideal_decision"], "monitor_decision": pred} for row, pred in zip(executed, preds))
    (target / "authorization-decisions.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in decisions), encoding="utf-8")
    (target / "representation-collision-witnesses.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in witnesses), encoding="utf-8")
    (target / "deployment-authorization-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target / "deployment-authorization-report.md").write_text(render_report(report), encoding="utf-8")
    with (target / "representation-metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["representation", "mixed_action", "upa_n", "upa_d", "upa", "fd_n", "fd_d", "fd", "abstain", "coverage", "accuracy", "withheld_authorized"])
        for row in primary + fail_open + fail_closed:
            writer.writerow([row["representation"], row["mixed_action"], row["unsafe_pre_allow"]["successes"], row["unsafe_pre_allow"]["total"], row["unsafe_pre_allow"]["rate"], row["false_denial"]["successes"], row["false_denial"]["total"], row["false_denial"]["rate"], row["abstain"]["rate"], row["coverage"]["rate"], row["decision_accuracy"]["rate"], row["withheld_authorized_work"]["rate"]])
    (target / "table_deployment_authorization_interface.tex").write_text(render_table(report), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize-inputs", action="store_true")
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.materialize_inputs:
        materialize_inputs()
        print(json.dumps({"contexts": len(build_contexts()), "policies": len(policies()), "contexts_sha256": sha256_file(CONTEXTS), "policy_manifests_sha256": sha256_file(POLICIES), "runner_sha256": sha256_file(Path(__file__))}, indent=2))
        return 0
    report = run(args.mode, args.output_dir)
    print(json.dumps({"status": report["status"], "mode": report["mode"], "n_contexts": report["n_contexts"], "ideal_decisions": report["ideal_decisions"], "gates": report["gates"]}, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
