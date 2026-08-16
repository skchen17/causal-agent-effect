from __future__ import annotations

from typing import Any


TOOL_SCHEMAS: dict[str, dict[str, dict[str, Any]]] = {
    "email": {
        "draft_email": {"args": ["to", "cc", "bcc", "subject", "body", "attachments"], "commit_mode": "draft"},
        "send_email": {"args": ["to", "cc", "bcc", "subject", "body", "attachments"], "commit_mode": "commit"},
        "add_cc": {"args": ["message_id", "cc"], "commit_mode": "commit"},
        "add_bcc": {"args": ["message_id", "bcc"], "commit_mode": "commit"},
        "forward_email": {"args": ["message_id", "to", "cc", "bcc"], "commit_mode": "commit"},
        "attach_file": {"args": ["message_id", "file_id"], "commit_mode": "commit"},
        "schedule_send": {"args": ["to", "cc", "bcc", "subject", "body", "send_at"], "commit_mode": "commit"},
    },
    "calendar": {
        "create_event": {"args": ["event_id", "title", "attendees", "visibility"], "commit_mode": "commit"},
        "update_event": {"args": ["event_id", "title", "start", "end"], "commit_mode": "commit"},
        "invite_attendee": {"args": ["event_id", "attendee"], "commit_mode": "commit"},
        "change_visibility": {"args": ["event_id", "visibility"], "commit_mode": "commit"},
        "delete_event": {"args": ["event_id"], "commit_mode": "delete"},
    },
    "file": {
        "read_file": {"args": ["file_id"], "commit_mode": "read"},
        "create_draft_copy": {"args": ["file_id", "draft_id"], "commit_mode": "draft"},
        "share_file": {"args": ["file_id", "readers", "permission"], "commit_mode": "share"},
        "create_public_link": {"args": ["file_id", "visibility"], "commit_mode": "share"},
        "change_permission": {"args": ["file_id", "reader", "permission"], "commit_mode": "commit"},
        "delete_file": {"args": ["file_id"], "commit_mode": "delete"},
    },
    "slack": {
        "send_channel_message": {"args": ["channel", "text"], "commit_mode": "commit"},
        "send_dm": {"args": ["recipient", "text"], "commit_mode": "commit"},
        "invite_user": {"args": ["workspace", "user"], "commit_mode": "commit"},
        "remove_user": {"args": ["workspace", "user"], "commit_mode": "delete"},
        "add_user_to_channel": {"args": ["channel", "user"], "commit_mode": "commit"},
        "export_channel_history": {"args": ["channel", "destination"], "commit_mode": "transfer"},
    },
    "transaction": {
        "view_transaction": {"args": ["account_id", "transaction_id"], "commit_mode": "read"},
        "schedule_payment": {"args": ["from_account", "payee", "amount", "date"], "commit_mode": "draft"},
        "submit_payment": {"args": ["from_account", "payee", "amount"], "commit_mode": "transfer"},
        "change_recipient": {"args": ["payment_id", "payee"], "commit_mode": "commit"},
        "cancel_payment": {"args": ["payment_id"], "commit_mode": "delete"},
    },
}


def tool_inventory(domain: str) -> list[dict[str, Any]]:
    return [
        {"name": name, "domain": domain, "arguments": list(schema["args"]), "commit_mode": schema["commit_mode"]}
        for name, schema in sorted(TOOL_SCHEMAS[domain].items())
    ]


def all_tool_names() -> set[str]:
    return {tool for tools in TOOL_SCHEMAS.values() for tool in tools}

