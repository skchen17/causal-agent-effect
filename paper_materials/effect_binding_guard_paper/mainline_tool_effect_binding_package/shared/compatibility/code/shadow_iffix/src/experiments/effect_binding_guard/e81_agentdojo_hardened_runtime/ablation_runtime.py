"""Single-switch E81 ablations over the reviewed AgentDojo runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.experiments.effect_binding_guard.e80_contract_obligation_hardening import (
    FieldDefault,
    mediate_hardened_call,
)

from .runtime import manifest_as_proposal
from .trusted_interface import (
    CompiledTrustedInterface,
    compile_tool_semantics,
)


@dataclass(frozen=True)
class RuntimeAblation:
    row_id: str
    label: str
    field_granularity: bool = True
    provenance_control_binding: bool = True
    counterfactual_registration: bool = True
    task_authority_envelope: bool = True
    authorized_read_grounding: bool = True
    omitted_fields_fail_closed: bool = True
    replan_recovery: bool = True


ABLATIONS = {
    "A1": RuntimeAblation("A1", "full_reviewed_effect_contract_guard"),
    "A2": RuntimeAblation(
        "A2", "tool_call_level_only", field_granularity=False
    ),
    "A7": RuntimeAblation(
        "A7", "no_provenance_control_binding", provenance_control_binding=False
    ),
    "A9": RuntimeAblation(
        "A9",
        "schema_description_only_registration",
        counterfactual_registration=False,
    ),
    "A11": RuntimeAblation(
        "A11", "no_task_authority_envelope", task_authority_envelope=False
    ),
    "A12": RuntimeAblation(
        "A12", "no_authorized_read_grounding", authorized_read_grounding=False
    ),
    "A13": RuntimeAblation(
        "A13", "omitted_fields_permissive", omitted_fields_fail_closed=False
    ),
    "A15": RuntimeAblation(
        "A15", "no_replan_recovery", replan_recovery=False
    ),
}


def _result(
    decision: str,
    reasons: list[str],
    *,
    row: RuntimeAblation,
    registry_hash: str,
    checks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "decision": decision,
        "reasons": reasons,
        "checks": checks or [],
        "runtime_called_llm": False,
        "runtime_executed_tool": False,
        "registry_hash": registry_hash,
        "ablation_row": row.row_id,
        "ablation_label": row.label,
        "replan_recovery": row.replan_recovery,
    }


def _permissive_dynamic_defaults(
    *,
    arguments: Mapping[str, Any],
    field_semantics: Mapping[str, FieldDefault],
    security_fields: tuple[str, ...],
) -> tuple[dict[str, FieldDefault], list[str], list[str]]:
    """Drop only omitted, unresolved dynamic security defaults.

    Required fields and known static defaults retain the A1 semantics. The
    returned list makes the omitted fields explicit in the audit record.
    """
    omitted = [
        field
        for field in security_fields
        if field not in arguments and field_semantics[field].dynamic_default
    ]
    semantics = {
        field: value for field, value in field_semantics.items() if field not in omitted
    }
    checked = [field for field in security_fields if field not in omitted]
    return semantics, checked, omitted


def _accept_untyped_resolver_evidence(
    entries: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Model removal of provenance/type checks while retaining resolver IDs."""
    accepted = []
    for entry in entries:
        resolver_id = entry.get("resolver_id")
        values = entry.get("values")
        if isinstance(resolver_id, str) and isinstance(values, list):
            accepted.append(
                {
                    "resolver_id": resolver_id,
                    "values": values,
                    "typed_projection": True,
                    "provenance": "authorized_read",
                    "ablation_original_provenance": entry.get("provenance"),
                    "ablation_original_typed_projection": entry.get(
                        "typed_projection"
                    ),
                }
            )
    return accepted


def mediate_reviewed_agentdojo_call_ablation(
    *,
    row_id: str,
    suite: str,
    tool_name: str,
    arguments: Mapping[str, Any],
    runtime_catalog: Mapping[str, Any],
    interface: CompiledTrustedInterface,
    resolver_ledger: list[Mapping[str, Any]],
    registry_hash: str,
    raw_descriptor: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply exactly one E81 runtime switch before tool execution."""
    try:
        row = ABLATIONS[row_id]
    except KeyError as exc:
        raise ValueError(f"unsupported E81 ablation row: {row_id}") from exc

    try:
        semantics = compile_tool_semantics(runtime_catalog, suite, tool_name)
    except ValueError as exc:
        return _result(
            "ABSTAIN",
            [f"tool_semantics_unavailable:{exc}"],
            row=row,
            registry_hash=registry_hash,
        )

    if not row.task_authority_envelope:
        return {
            **_result(
                "ALLOW",
                ["ablation_no_task_authority_envelope"],
                row=row,
                registry_hash=registry_hash,
            ),
            "switch_applicable": True,
        }

    if tool_name not in interface.manifest.tools:
        return _result(
            "ABSTAIN",
            ["tool_not_in_reviewed_task_authority"],
            row=row,
            registry_hash=registry_hash,
        )

    if not row.field_granularity:
        return {
            **_result(
                "ALLOW",
                ["ablation_tool_call_level_match"],
                row=row,
                registry_hash=registry_hash,
            ),
            "switch_applicable": True,
        }

    security_fields = list(semantics.security_fields)
    round0_descriptor_used = False
    if not row.counterfactual_registration:
        if not raw_descriptor:
            return _result(
                "ABSTAIN",
                ["round0_descriptor_unavailable"],
                row=row,
                registry_hash=registry_hash,
            )
        if raw_descriptor.get("registered") is not True:
            return _result(
                "ABSTAIN",
                ["round0_descriptor_not_registered"],
                row=row,
                registry_hash=registry_hash,
            )
        raw_fields = raw_descriptor.get("security_fields")
        if not isinstance(raw_fields, list) or any(
            not isinstance(field, str) for field in raw_fields
        ):
            return _result(
                "ABSTAIN",
                ["round0_descriptor_security_fields_malformed"],
                row=row,
                registry_hash=registry_hash,
            )
        unknown = sorted(set(raw_fields) - set(semantics.field_semantics))
        if unknown:
            return _result(
                "ABSTAIN",
                [f"round0_descriptor_unknown_field:{field}" for field in unknown],
                row=row,
                registry_hash=registry_hash,
            )
        security_fields = list(raw_fields)
        round0_descriptor_used = True

    field_semantics = dict(semantics.field_semantics)
    omitted_permissive: list[str] = []
    if not row.omitted_fields_fail_closed:
        field_semantics, security_fields, omitted_permissive = (
            _permissive_dynamic_defaults(
                arguments=arguments,
                field_semantics=field_semantics,
                security_fields=tuple(security_fields),
            )
        )

    ledger: list[Mapping[str, Any]]
    untyped_evidence_entries = 0
    if not row.authorized_read_grounding:
        ledger = []
    elif not row.provenance_control_binding:
        ledger = _accept_untyped_resolver_evidence(resolver_ledger)
        untyped_evidence_entries = sum(
            entry.get("typed_projection") is not True
            or entry.get("provenance") != "authorized_read"
            for entry in resolver_ledger
        )
    else:
        ledger = list(resolver_ledger)

    mediated = mediate_hardened_call(
        tool_name=tool_name,
        arguments=arguments,
        field_semantics=field_semantics,
        security_fields=security_fields,
        inactive_values=semantics.inactive_values,
        proposal=manifest_as_proposal(interface),
        manifest=interface.manifest,
        resolver_ledger=ledger,
        registry_hash=registry_hash,
    )
    reasons = list(mediated["reasons"])
    if omitted_permissive:
        reasons.append(
            "ablation_permissive_omitted_dynamic_fields:"
            + ",".join(sorted(omitted_permissive))
        )
    untyped_resolver_matches = sum(
        check.get("status") == "matched_typed_resolver"
        for check in mediated.get("checks", [])
    ) if not row.provenance_control_binding else 0
    return {
        **mediated,
        "reasons": reasons,
        "runtime_executed_tool": False,
        "ablation_row": row.row_id,
        "ablation_label": row.label,
        "replan_recovery": row.replan_recovery,
        "omitted_dynamic_security_fields": omitted_permissive,
        "round0_descriptor_used": round0_descriptor_used,
        "untyped_evidence_entries_accepted": untyped_evidence_entries,
        "untyped_resolver_matches": untyped_resolver_matches,
        "authorized_read_grounding_disabled_with_resolvers": (
            not row.authorized_read_grounding and bool(interface.resolver_specs)
        ),
        "switch_applicable": bool(
            round0_descriptor_used
            or omitted_permissive
            or untyped_evidence_entries
            or (
                not row.authorized_read_grounding
                and interface.resolver_specs
            )
        ),
    }
