from __future__ import annotations

from typing import Protocol

from .contracts import AtomFieldBinding, EffectTemplate, ToolEffectContract, ToolSpec


class LLMContractAdapter(Protocol):
    def propose(self, tool: ToolSpec) -> ToolEffectContract:
        ...


class ContractProposer:
    def __init__(self, mode: str = "stub", adapter: LLMContractAdapter | None = None) -> None:
        self.mode = mode
        self.adapter = adapter

    def propose(self, tool: ToolSpec) -> ToolEffectContract:
        if self.mode == "stub":
            return stub_contract_for_tool(tool)
        if self.mode in {"llm", "local_llm"} and self.adapter is not None:
            return self.adapter.propose(tool)
        raise RuntimeError("LLM contract proposal requires an explicit adapter; use stub mode for local runs.")


def stub_contract_for_tool(tool: ToolSpec) -> ToolEffectContract:
    templates = complete_templates(tool.name)
    return ToolEffectContract(
        tool_name=tool.name,
        proposal_mode="stub",
        templates=tuple(templates),
        non_security_fields=tuple(non_security_fields(tool.name)),
        provenance={
            "proposer": "deterministic_stub",
            "trusted": False,
            "note": "Candidate contract only; counterfactual validation is required before freezing.",
        },
    )


def complete_templates(tool_name: str) -> list[EffectTemplate]:
    dispatch = {
        "send_email": send_email_templates,
        "create_calendar_event": create_calendar_event_templates,
        "share_file": share_file_templates,
        "post_slack_message": post_slack_message_templates,
        "submit_payment": submit_payment_templates,
    }
    if tool_name not in dispatch:
        raise KeyError(f"No stub contract for tool: {tool_name}")
    return dispatch[tool_name]()


def non_security_fields(tool_name: str) -> list[str]:
    common = ["subject", "body", "text", "title", "description"]
    if tool_name == "submit_payment":
        return ["memo", "note"]
    return common


def binding(field: str, atom_field: str, *, repeated: bool = False) -> AtomFieldBinding:
    return AtomFieldBinding(source_field=field, atom_field=atom_field, repeated=repeated)


def send_email_templates() -> list[EffectTemplate]:
    templates = [
        EffectTemplate(
            effect_type="message_sent",
            operation="send_email",
            resource_field="literal:email_body",
            resource_type="message",
            target_principal_field=field,
            target_role=field,
            field_bindings=(binding(field, "target_principal", repeated=True), binding("commit_mode", "commit_mode")),
            default_commit_mode="commit",
            security_relevant_fields=(field, "commit_mode", "control_source", "provenance_source"),
        )
        for field in ("to", "cc", "bcc")
    ]
    templates.extend(
        EffectTemplate(
            effect_type="attachment_disclosed",
            operation="send_email",
            resource_field="attachments",
            resource_type="file",
            target_principal_field=field,
            target_role=field,
            field_bindings=(binding("attachments", "resource_id", repeated=True), binding(field, "target_principal", repeated=True)),
            default_commit_mode="commit",
            security_relevant_fields=(field, "attachments", "commit_mode", "control_source", "provenance_source"),
        )
        for field in ("to", "cc", "bcc")
    )
    return templates


def create_calendar_event_templates() -> list[EffectTemplate]:
    return [
        EffectTemplate(
            effect_type="calendar_event_created",
            operation="create_calendar_event",
            resource_field="event_id",
            resource_type="calendar_event",
            visibility_field="visibility",
            default_commit_mode="commit",
            security_relevant_fields=("event_id", "visibility", "commit_mode", "control_source", "provenance_source"),
        ),
        EffectTemplate(
            effect_type="calendar_attendee_invited",
            operation="create_calendar_event",
            resource_field="event_id",
            resource_type="calendar_event",
            target_principal_field="attendees",
            target_role="attendee",
            visibility_field="visibility",
            default_commit_mode="commit",
            security_relevant_fields=("attendees", "visibility", "commit_mode", "control_source", "provenance_source"),
        ),
    ]


def share_file_templates() -> list[EffectTemplate]:
    return [
        EffectTemplate(
            effect_type="file_shared",
            operation="share_file",
            resource_field="file_id",
            resource_type="file",
            permission_delta_field="permission",
            visibility_field="visibility",
            default_commit_mode="share",
            security_relevant_fields=("file_id", "permission", "visibility", "commit_mode", "control_source", "provenance_source"),
        ),
        EffectTemplate(
            effect_type="file_reader_added",
            operation="share_file",
            resource_field="file_id",
            resource_type="file",
            target_principal_field="readers",
            target_role="reader",
            permission_delta_field="permission",
            default_commit_mode="share",
            security_relevant_fields=("readers", "permission", "commit_mode", "control_source", "provenance_source"),
        ),
        EffectTemplate(
            effect_type="public_link_created",
            operation="share_file",
            resource_field="file_id",
            resource_type="file",
            visibility_field="visibility",
            default_commit_mode="share",
            security_relevant_fields=("file_id", "visibility", "commit_mode", "control_source", "provenance_source"),
            emit_if_field="visibility",
            emit_if_values=("public",),
        ),
    ]


def post_slack_message_templates() -> list[EffectTemplate]:
    return [
        EffectTemplate(
            effect_type="slack_message_posted",
            operation="post_slack_message",
            resource_field="channel",
            resource_type="channel",
            default_commit_mode="commit",
            security_relevant_fields=("channel", "commit_mode", "control_source", "provenance_source"),
        )
    ]


def submit_payment_templates() -> list[EffectTemplate]:
    return [
        EffectTemplate(
            effect_type="payment_submitted",
            operation="submit_payment",
            resource_field="from_account",
            resource_type="account",
            target_principal_field="payee",
            target_role="payee",
            default_commit_mode="transfer",
            security_relevant_fields=("from_account", "payee", "commit_mode", "control_source", "provenance_source"),
        ),
    ]
