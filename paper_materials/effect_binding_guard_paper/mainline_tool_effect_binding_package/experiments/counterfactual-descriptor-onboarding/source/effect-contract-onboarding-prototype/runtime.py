from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.experiments.effect_binding_guard.e55_precommit_authz.authz_model import (
    canonical_resource,
    operation_authorized,
    provenance_decision,
    resource_authorized,
    visibility_authorized,
)
from src.experiments.effect_binding_guard.e55_precommit_authz.schemas import (
    AuthorizationContext as E55AuthorizationContext,
)
from src.experiments.effect_binding_guard.e55_precommit_authz.schemas import EffectAtom as E55EffectAtom

from .contracts import (
    AuthorizationContext,
    EffectAtom,
    FrozenContract,
    ToolEffectContract,
    ValidationResult,
    as_list,
)


def atomize_tool_call(
    contract: ToolEffectContract | FrozenContract,
    tool_call: dict[str, Any],
    context: AuthorizationContext | None = None,
) -> list[EffectAtom]:
    active = contract.contract if isinstance(contract, FrozenContract) else contract
    atoms: list[EffectAtom] = []
    for template in active.templates:
        if template.emit_if_field and str(tool_call.get(template.emit_if_field, "")) not in set(template.emit_if_values):
            continue
        resource_values = as_list(tool_call.get(template.resource_field))
        if not resource_values and template.resource_field.startswith("literal:"):
            resource_values = [template.resource_field.split(":", 1)[1]]
        for resource_id in resource_values:
            evidence_values = as_list(tool_call.get(template.evidence_ref_field)) if template.evidence_ref_field else []
            evidence_ref = ",".join(evidence_values) if evidence_values else None
            target_values = as_list(tool_call.get(template.target_principal_field)) if template.target_principal_field else [None]
            if template.target_principal_field and not target_values:
                continue
            for target_value in target_values:
                atom_resource = canonical_resource(str(resource_id), to_e55_context(context), use_aliases=True) if context else resource_id
                resource_type = template.resource_type
                target_principal = target_value
                if template.target_as_resource and target_principal:
                    atom_resource = target_principal
                    resource_type = template.target_resource_type
                atoms.append(
                    EffectAtom(
                        effect_type=template.effect_type,
                        operation=template.operation,
                        resource_id=str(atom_resource),
                        resource_type=resource_type,
                        target_principal=str(target_principal) if target_principal is not None else None,
                        target_role=template.target_role,
                        visibility=_optional_str(tool_call.get(template.visibility_field)) if template.visibility_field else None,
                        permission_delta=_optional_str(tool_call.get(template.permission_delta_field)) if template.permission_delta_field else None,
                        commit_mode=str(tool_call.get(template.commit_mode_field or "", template.default_commit_mode) or template.default_commit_mode),
                        control_source=str(tool_call.get(template.control_source_field, "user")),
                        provenance_source=str(tool_call.get(template.provenance_source_field, "user")),
                        evidence_ref=evidence_ref,
                    )
                )
    return atoms


def authorize_tool_call(
    frozen_contract: FrozenContract,
    tool_call: dict[str, Any],
    context: AuthorizationContext,
) -> dict[str, Any]:
    atoms = atomize_tool_call(frozen_contract, tool_call, context)
    if not atoms:
        return {
            "decision": "ABSTAIN",
            "atoms": [],
            "atom_authorization": [],
            "reasons": ["no_atoms_generated"],
            "contract_hash": frozen_contract.contract_hash,
        }
    decision, atom_authorization, reasons = authorize_e60_atoms(atoms, context)
    return {
        "decision": decision,
        "atoms": [atom.to_dict() for atom in atoms],
        "atom_authorization": atom_authorization,
        "reasons": reasons,
        "contract_hash": frozen_contract.contract_hash,
    }


def freeze_contract(contract: ToolEffectContract, validation: ValidationResult) -> FrozenContract:
    if not validation.passed:
        raise ValueError(f"Cannot freeze failed contract for {contract.tool_name}")
    return FrozenContract(
        tool_name=contract.tool_name,
        contract=contract,
        contract_hash=contract.contract_hash(),
        validation_summary=validation.to_dict(),
        frozen_at=datetime.now(timezone.utc).isoformat(),
    )


def authorize_e60_atoms(atoms: list[EffectAtom], context: AuthorizationContext) -> tuple[str, list[dict[str, Any]], list[str]]:
    e55_context = to_e55_context(context)
    decisions = [authorize_e60_atom(atom, context, e55_context) for atom in atoms]
    reasons = sorted({reason for result in decisions for reason in result["reasons"]})
    if any(_is_unknown_reason(reason) for reason in reasons):
        return "ABSTAIN", decisions, reasons
    if any(result["decision"] == "DENY" for result in decisions):
        return "DENY", decisions, reasons
    if any(result["decision"] == "ABSTAIN" for result in decisions):
        return "ABSTAIN", decisions, reasons
    return "ALLOW", decisions, reasons


def authorize_e60_atom(atom: EffectAtom, context: AuthorizationContext, e55_context: E55AuthorizationContext) -> dict[str, Any]:
    e55_atom = to_e55_atom(atom)
    reasons: list[str] = []
    resource_ok = resource_authorized(e55_atom, e55_context, use_aliases=True)
    operation_ok = operation_authorized(e55_atom, e55_context, check_operation_mode=True)
    visibility_ok = visibility_authorized(e55_atom, e55_context)
    target_ok = target_authorized(atom, context)
    provenance_status, provenance_reason = provenance_decision(e55_atom, e55_context, use_provenance=True)
    for name, value in (
        ("resource_authorization", resource_ok),
        ("operation_authorization", operation_ok),
        ("visibility_authorization", visibility_ok),
        ("target_principal_authorization", target_ok),
    ):
        if value is False:
            reasons.append(name)
        elif value is None:
            reasons.append(f"{name}_unknown")
    if provenance_status == "DENY":
        reasons.append(provenance_reason)
    elif provenance_status == "ABSTAIN":
        reasons.append(provenance_reason)
    if any(_is_unknown_reason(reason) for reason in reasons):
        decision = "ABSTAIN"
    elif reasons:
        decision = "DENY"
    else:
        decision = "ALLOW"
    return {
        "decision": decision,
        "reasons": reasons,
        "resource_authorized": resource_ok,
        "target_principal_authorized": target_ok,
        "operation_authorized": operation_ok,
        "visibility_authorized": visibility_ok,
        "provenance_status": provenance_status,
        "canonical_resource_id": canonical_resource(atom.resource_id, e55_context, use_aliases=True),
        "atom": atom.to_dict(),
    }


def target_authorized(atom: EffectAtom, context: AuthorizationContext) -> bool | None:
    if atom.target_principal in (None, ""):
        return True
    target = canonical_target(str(atom.target_principal), context)
    if target.startswith("unknown") or target in {"none", ""}:
        return None
    if atom.target_role in {"to", "cc", "bcc", "attendee", "reader", "payee"}:
        if target in set(context.allowed_recipients):
            return True
        return bool(context.external_recipient_allowed)
    if atom.target_role in {"member", "user"}:
        return target in set(context.allowed_recipients) or target in set(context.allowed_resource_ids)
    return target in set(context.allowed_recipients) or target in set(context.allowed_resource_ids)


def canonical_target(target: str, context: AuthorizationContext) -> str:
    return context.allowed_resource_aliases.get(target, target)


def _is_unknown_reason(reason: str) -> bool:
    return reason.endswith("_unknown") or reason in {"unknown_control_source", "control_source_not_in_authorization_context"}


def to_e55_atom(atom: EffectAtom) -> E55EffectAtom:
    return E55EffectAtom(
        effect=atom.effect_type,
        operation=atom.operation,
        resource_id=atom.resource_id,
        resource_type=atom.resource_type,
        resource_aliases=(),
        visibility=atom.visibility,
        recipient_role=atom.target_role,
        commit_mode=atom.commit_mode,
        provenance_source=atom.provenance_source,
        control_source=atom.control_source,
    )


def to_e55_context(context: AuthorizationContext) -> E55AuthorizationContext:
    return E55AuthorizationContext(
        task_id=context.context_id,
        allowed_effects=context.allowed_effects,
        allowed_operations=context.allowed_operations,
        allowed_resource_ids=context.allowed_resource_ids,
        allowed_resource_aliases=context.allowed_resource_aliases,
        allowed_recipients=context.allowed_recipients,
        allowed_accounts=context.allowed_accounts,
        allowed_channels=context.allowed_channels,
        allowed_files=context.allowed_files,
        allowed_visibility=context.allowed_visibility,
        draft_allowed=context.draft_allowed,
        commit_allowed=context.commit_allowed,
        public_link_allowed=context.public_link_allowed,
        external_recipient_allowed=context.external_recipient_allowed,
        multi_resource_policy=context.multi_resource_policy,
        trusted_control_sources=context.trusted_control_sources,
        untrusted_control_sources=context.untrusted_control_sources,
        private_data_sources=context.private_data_sources,
    )


def atom_signature_set(atoms: list[EffectAtom]) -> set[tuple[Any, ...]]:
    return {atom.signature() for atom in atoms}


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
