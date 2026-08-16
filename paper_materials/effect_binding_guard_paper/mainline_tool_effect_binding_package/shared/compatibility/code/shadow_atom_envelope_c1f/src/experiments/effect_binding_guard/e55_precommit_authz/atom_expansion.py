from __future__ import annotations

from typing import Any

from .schemas import EffectAtom


def as_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def atom(
    *,
    effect: str,
    operation: str,
    resource_id: str,
    resource_type: str,
    args: dict[str, Any],
    aliases: list[str] | None = None,
    visibility: str | None = None,
    recipient_role: str | None = None,
    commit_mode: str = "commit",
) -> EffectAtom:
    return EffectAtom(
        effect=effect,
        operation=operation,
        resource_id=str(resource_id),
        resource_type=resource_type,
        resource_aliases=tuple(aliases or []),
        visibility=visibility,
        recipient_role=recipient_role,
        commit_mode=commit_mode,
        provenance_source=str(args.get("provenance_source", "user")),
        control_source=str(args.get("control_source", "user")),
    )


def expand_tool_call(
    domain: str,
    tool_name: str,
    args: dict[str, Any],
    *,
    multi_resource: bool = True,
    corrected_v2: bool = False,
) -> list[EffectAtom]:
    if domain == "transaction":
        atoms = expand_transaction(tool_name, args, include_amount_atom=not corrected_v2)
    else:
        dispatch = {
            "email": expand_email,
            "calendar": expand_calendar,
            "file": expand_file,
            "slack": expand_slack,
        }
        atoms = dispatch[domain](tool_name, args)
    return atoms if multi_resource else atoms[:1]


def expand_email(tool_name: str, args: dict[str, Any]) -> list[EffectAtom]:
    commit_mode = str(args.get("commit_mode") or ("draft" if tool_name == "draft_email" else "commit"))
    effect = "email_draft_created" if commit_mode == "draft" else "message_sent"
    atoms: list[EffectAtom] = []
    for role in ("to", "cc", "bcc"):
        for recipient in as_list(args.get(role)):
            atoms.append(
                atom(
                    effect=effect,
                    operation=tool_name,
                    resource_id=recipient,
                    resource_type="recipient",
                    args=args,
                    recipient_role=role,
                    commit_mode=commit_mode,
                )
            )
    for file_id in as_list(args.get("attachments")) + as_list(args.get("file_id")):
        atoms.append(
            atom(
                effect="file_attached",
                operation=tool_name,
                resource_id=file_id,
                resource_type="file",
                args=args,
                commit_mode=commit_mode,
            )
        )
    for recipient in as_list(args.get("cc") if tool_name == "add_cc" else args.get("bcc") if tool_name == "add_bcc" else []):
        atoms.append(
            atom(
                effect="message_recipient_added",
                operation=tool_name,
                resource_id=recipient,
                resource_type="recipient",
                args=args,
                recipient_role="cc" if tool_name == "add_cc" else "bcc",
                commit_mode="commit",
            )
        )
    if not atoms:
        atoms.append(
            atom(
                effect=effect,
                operation=tool_name,
                resource_id=str(args.get("message_id", "email_thread")),
                resource_type="email_thread",
                args=args,
                commit_mode=commit_mode,
            )
        )
    return atoms


def expand_calendar(tool_name: str, args: dict[str, Any]) -> list[EffectAtom]:
    event = str(args.get("event_id", "unknown_event"))
    visibility = args.get("visibility")
    mode = str(args.get("commit_mode") or ("delete" if tool_name == "delete_event" else "commit"))
    if tool_name == "create_event":
        effect = "calendar_event_draft_created" if mode in {"draft", "dry_run"} else "calendar_event_created"
        atoms = [
            atom(
                effect=effect,
                operation=tool_name,
                resource_id=event,
                resource_type="calendar_event",
                args=args,
                visibility=visibility,
                commit_mode=mode,
            )
        ]
        for attendee in as_list(args.get("attendees")):
            atoms.append(
                atom(
                    effect="calendar_attendee_planned" if mode in {"draft", "dry_run"} else "calendar_attendee_invited",
                    operation=tool_name,
                    resource_id=attendee,
                    resource_type="attendee",
                    args=args,
                    visibility=visibility,
                    recipient_role="attendee",
                    commit_mode=mode,
                )
            )
        return atoms
    if tool_name == "invite_attendee":
        return [
            atom(
                effect="calendar_attendee_invited",
                operation=tool_name,
                resource_id=str(args.get("attendee", "unknown_attendee")),
                resource_type="attendee",
                args=args,
                recipient_role="attendee",
                commit_mode="commit",
            )
        ]
    if tool_name == "change_visibility":
        return [
            atom(
                effect="calendar_visibility_changed",
                operation=tool_name,
                resource_id=event,
                resource_type="calendar_event",
                args=args,
                visibility=str(visibility or "unknown"),
                commit_mode="commit",
            )
        ]
    if tool_name == "delete_event":
        return [
            atom(
                effect="calendar_event_deleted",
                operation=tool_name,
                resource_id=event,
                resource_type="calendar_event",
                args=args,
                commit_mode="delete",
            )
        ]
    return [
        atom(
            effect="calendar_event_updated",
            operation=tool_name,
            resource_id=event,
            resource_type="calendar_event",
            args=args,
            visibility=visibility,
            commit_mode="commit",
        )
    ]


def expand_file(tool_name: str, args: dict[str, Any]) -> list[EffectAtom]:
    file_id = str(args.get("file_id", "unknown_file"))
    if tool_name == "read_file":
        return [atom(effect="file_read", operation=tool_name, resource_id=file_id, resource_type="file", args=args, commit_mode="read")]
    if tool_name == "create_draft_copy":
        return [atom(effect="file_draft_created", operation=tool_name, resource_id=file_id, resource_type="file", args=args, commit_mode="draft")]
    if tool_name == "share_file":
        atoms = [atom(effect="file_shared", operation=tool_name, resource_id=file_id, resource_type="file", args=args, commit_mode="share")]
        for reader in as_list(args.get("readers")):
            atoms.append(
                atom(
                    effect="file_reader_added",
                    operation=tool_name,
                    resource_id=reader,
                    resource_type="reader",
                    args=args,
                    recipient_role="reader",
                    commit_mode="share",
                )
            )
        return atoms
    if tool_name == "create_public_link":
        return [
            atom(
                effect="public_link_created",
                operation=tool_name,
                resource_id=file_id,
                resource_type="file",
                args=args,
                visibility=str(args.get("visibility", "public")),
                commit_mode="share",
            )
        ]
    if tool_name == "change_permission":
        return [
            atom(effect="file_permission_changed", operation=tool_name, resource_id=file_id, resource_type="file", args=args, commit_mode="commit"),
            atom(
                effect="file_reader_added",
                operation=tool_name,
                resource_id=str(args.get("reader", "unknown_reader")),
                resource_type="reader",
                args=args,
                recipient_role="reader",
                commit_mode="commit",
            ),
        ]
    return [atom(effect="file_deleted", operation=tool_name, resource_id=file_id, resource_type="file", args=args, commit_mode="delete")]


def expand_slack(tool_name: str, args: dict[str, Any]) -> list[EffectAtom]:
    channel = str(args.get("channel", args.get("workspace", "unknown_workspace")))
    mode = str(args.get("commit_mode") or ("transfer" if tool_name == "export_channel_history" else "commit"))
    if tool_name == "send_channel_message":
        return [atom(effect="message_sent", operation=tool_name, resource_id=channel, resource_type="channel", args=args, commit_mode=mode)]
    if tool_name == "send_dm":
        return [
            atom(
                effect="message_sent",
                operation=tool_name,
                resource_id=str(args.get("recipient", "unknown_recipient")),
                resource_type="recipient",
                args=args,
                recipient_role="to",
                commit_mode="commit",
            )
        ]
    if tool_name in {"invite_user", "remove_user"}:
        effect = "workspace_member_invited" if tool_name == "invite_user" else "workspace_member_removed"
        return [
            atom(effect=effect, operation=tool_name, resource_id=str(args.get("workspace", "workspace")), resource_type="workspace", args=args, commit_mode="commit" if tool_name == "invite_user" else "delete"),
            atom(effect=effect, operation=tool_name, resource_id=str(args.get("user", "unknown_user")), resource_type="member", args=args, recipient_role="member", commit_mode="commit" if tool_name == "invite_user" else "delete"),
        ]
    if tool_name == "add_user_to_channel":
        return [
            atom(effect="channel_member_added", operation=tool_name, resource_id=channel, resource_type="channel", args=args, commit_mode="commit"),
            atom(effect="channel_member_added", operation=tool_name, resource_id=str(args.get("user", "unknown_user")), resource_type="member", args=args, recipient_role="member", commit_mode="commit"),
        ]
    return [atom(effect="channel_history_exported", operation=tool_name, resource_id=channel, resource_type="channel", args=args, commit_mode="transfer")]


def expand_transaction(tool_name: str, args: dict[str, Any], *, include_amount_atom: bool = True) -> list[EffectAtom]:
    account = str(args.get("from_account", args.get("account_id", "unknown_account")))
    if tool_name == "view_transaction":
        return [
            atom(effect="transaction_viewed", operation=tool_name, resource_id=account, resource_type="account", args=args, commit_mode="read"),
            atom(effect="transaction_viewed", operation=tool_name, resource_id=str(args.get("transaction_id", "unknown_txn")), resource_type="transaction", args=args, commit_mode="read"),
        ]
    if tool_name in {"schedule_payment", "submit_payment"}:
        effect = "payment_scheduled" if tool_name == "schedule_payment" else "payment_submitted"
        mode = str(args.get("commit_mode") or ("draft" if tool_name == "schedule_payment" else "transfer"))
        atoms = [
            atom(effect=effect, operation=tool_name, resource_id=account, resource_type="account", args=args, commit_mode=mode),
            atom(effect=effect, operation=tool_name, resource_id=str(args.get("payee", "unknown_payee")), resource_type="payee", args=args, recipient_role="payee", commit_mode=mode),
        ]
        if include_amount_atom:
            atoms.append(atom(effect=effect, operation=tool_name, resource_id=str(args.get("amount", "0.00")), resource_type="amount", args=args, commit_mode=mode))
        return atoms
    if tool_name == "change_recipient":
        return [atom(effect="payment_recipient_changed", operation=tool_name, resource_id=str(args.get("payee", "unknown_payee")), resource_type="payee", args=args, recipient_role="payee", commit_mode="commit")]
    return [atom(effect="payment_cancelled", operation=tool_name, resource_id=str(args.get("payment_id", "unknown_payment")), resource_type="payment", args=args, commit_mode="delete")]
