from __future__ import annotations

from typing import Any

from .schemas import AuthorizationContext, EffectAtom


READ_MODES = {"read", "dry_run"}
DRAFT_MODES = {"draft"}
COMMIT_MODES = {"commit", "delete", "share", "transfer"}


def canonical_resource(resource_id: str, context: AuthorizationContext, *, use_aliases: bool = True) -> str:
    value = str(resource_id)
    if use_aliases and value in context.allowed_resource_aliases:
        return context.allowed_resource_aliases[value]
    return value


def resource_universe(context: AuthorizationContext) -> set[str]:
    return {
        *context.allowed_resource_ids,
        *context.allowed_recipients,
        *context.allowed_accounts,
        *context.allowed_channels,
        *context.allowed_files,
    }


def resource_authorized(atom: EffectAtom, context: AuthorizationContext, *, use_aliases: bool = True) -> bool | None:
    resource_id = canonical_resource(atom.resource_id, context, use_aliases=use_aliases)
    if resource_id.startswith("unknown") or resource_id in {"", "none"}:
        return None
    if atom.resource_type in {"recipient", "attendee", "reader"}:
        return resource_id in set(context.allowed_recipients)
    if atom.resource_type == "payee":
        return resource_id in set(context.allowed_recipients)
    if atom.resource_type == "account":
        return resource_id in set(context.allowed_accounts)
    if atom.resource_type == "channel":
        return resource_id in set(context.allowed_channels)
    if atom.resource_type == "file":
        return resource_id in set(context.allowed_files) or resource_id in set(context.allowed_resource_ids)
    if atom.resource_type in {"calendar_event", "workspace", "member", "payment", "transaction", "email_thread", "amount"}:
        return resource_id in resource_universe(context) or resource_id in set(context.allowed_resource_ids)
    return resource_id in resource_universe(context)


def operation_authorized(atom: EffectAtom, context: AuthorizationContext, *, check_operation_mode: bool = True) -> bool | None:
    if atom.operation not in set(context.allowed_operations):
        return False
    if atom.effect not in set(context.allowed_effects):
        return False
    if not check_operation_mode:
        return True
    if atom.commit_mode in READ_MODES:
        return True
    if atom.commit_mode in DRAFT_MODES:
        return context.draft_allowed
    if atom.commit_mode in COMMIT_MODES:
        return context.commit_allowed
    return None


def visibility_authorized(atom: EffectAtom, context: AuthorizationContext) -> bool | None:
    if atom.visibility is None:
        return True
    visibility = str(atom.visibility)
    if visibility in {"unknown", ""}:
        return None
    if visibility == "public" and not context.public_link_allowed:
        return False
    return visibility in set(context.allowed_visibility)


def external_recipient_authorized(atom: EffectAtom, context: AuthorizationContext, *, use_aliases: bool = True) -> bool:
    if atom.resource_type not in {"recipient", "attendee", "reader", "payee"}:
        return True
    resource = canonical_resource(atom.resource_id, context, use_aliases=use_aliases)
    if resource in set(context.allowed_recipients):
        return True
    if "@" in resource and resource.endswith("@example.com"):
        return True
    return context.external_recipient_allowed


def provenance_decision(atom: EffectAtom, context: AuthorizationContext, *, use_provenance: bool = True) -> tuple[str, str]:
    if not use_provenance:
        return "ALLOW", "provenance_not_checked"
    control = atom.control_source
    source = atom.provenance_source
    if control in set(context.trusted_control_sources):
        return "ALLOW", "trusted_control_source"
    if control in set(context.untrusted_control_sources):
        return "DENY", "untrusted_control_source"
    if control in set(context.private_data_sources) or source in set(context.private_data_sources):
        return "DENY", "private_data_control_source"
    if control in {"", "unknown", "unknown_non_user"}:
        return "ABSTAIN", "unknown_control_source"
    return "ABSTAIN", "control_source_not_in_authorization_context"


def authorize_atom(
    atom: EffectAtom,
    context: AuthorizationContext,
    *,
    use_aliases: bool = True,
    check_operation_mode: bool = True,
    use_provenance: bool = True,
) -> dict[str, Any]:
    reasons: list[str] = []
    resource_ok = resource_authorized(atom, context, use_aliases=use_aliases)
    operation_ok = operation_authorized(atom, context, check_operation_mode=check_operation_mode)
    visibility_ok = visibility_authorized(atom, context)
    external_ok = external_recipient_authorized(atom, context, use_aliases=use_aliases)
    provenance_status, provenance_reason = provenance_decision(atom, context, use_provenance=use_provenance)
    for name, value in (
        ("resource_authorization", resource_ok),
        ("operation_authorization", operation_ok),
        ("visibility_authorization", visibility_ok),
        ("external_recipient_authorization", external_ok),
    ):
        if value is False:
            reasons.append(name)
        elif value is None:
            reasons.append(f"{name}_unknown")
    if provenance_status == "DENY":
        reasons.append(provenance_reason)
    elif provenance_status == "ABSTAIN":
        reasons.append(provenance_reason)
    if any(reason.endswith("_unknown") or reason in {"unknown_control_source", "control_source_not_in_authorization_context"} for reason in reasons):
        decision = "ABSTAIN"
    elif reasons:
        decision = "DENY"
    else:
        decision = "ALLOW"
    return {
        "decision": decision,
        "reasons": reasons,
        "resource_authorized": resource_ok,
        "operation_authorized": operation_ok,
        "visibility_authorized": visibility_ok,
        "external_recipient_authorized": external_ok,
        "provenance_status": provenance_status,
        "canonical_resource_id": canonical_resource(atom.resource_id, context, use_aliases=use_aliases),
        "atom": atom.to_dict(),
    }


def authorize_atoms(
    atoms: list[EffectAtom],
    context: AuthorizationContext,
    *,
    use_aliases: bool = True,
    check_operation_mode: bool = True,
    use_provenance: bool = True,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    decisions = [
        authorize_atom(
            atom,
            context,
            use_aliases=use_aliases,
            check_operation_mode=check_operation_mode,
            use_provenance=use_provenance,
        )
        for atom in atoms
    ]
    reasons = sorted({reason for result in decisions for reason in result["reasons"]})
    if any(result["decision"] == "DENY" for result in decisions):
        return "DENY", decisions, reasons
    if any(result["decision"] == "ABSTAIN" for result in decisions):
        return "ABSTAIN", decisions, reasons
    return "ALLOW", decisions, reasons

