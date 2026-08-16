from __future__ import annotations

from typing import Any

from src.experiments.effect_binding_guard.guards import (
    infer_authorization_match,
    infer_provenance_risk,
    infer_visible_effect,
    infer_visible_resource,
    tuple_decision,
)

from .atom_expansion import expand_tool_call
from .authz_model import authorize_atoms
from .schemas import AuthorizationContext, DeployableE55Input, E55Case, E55Prediction, EffectAtom, stable_hash


GuardInput = E55Case | DeployableE55Input


AUTHZ_METHODS = {
    "authz_aware_effect_binding_guard",
    "authz_aware_no_alias_resolution",
    "authz_aware_no_multi_resource_expansion",
    "authz_aware_no_operation_mode",
    "authz_aware_no_provenance_overlay",
    "authz_aware_no_evidence_fallback",
}


def prediction(
    case: GuardInput,
    *,
    method: str,
    decision: str,
    atoms: list[EffectAtom] | None = None,
    atom_auth: list[dict[str, Any]] | None = None,
    reasons: list[str] | tuple[str, ...] = (),
    accessed_fields: list[str] | tuple[str, ...] = (),
    confidence: float = 1.0,
    metadata: dict[str, Any] | None = None,
) -> E55Prediction:
    label_hidden_input = get_label_hidden_input(case)
    return E55Prediction(
        case_id=get_case_id(case),
        method=method,
        domain=get_domain(case),
        pair_group=get_pair_group(case),
        decision=decision,  # type: ignore[arg-type]
        predicted_atoms=tuple(atoms or []),
        atom_authorization=tuple(atom_auth or []),
        confidence=confidence,
        abstain_reason=";".join(reasons) if decision == "ABSTAIN" else "",
        violation_reasons=tuple(reasons),
        accessed_fields=tuple(sorted(set(accessed_fields))),
        decision_inputs_hash=stable_hash({field: label_hidden_input.get(field) for field in accessed_fields}),
        metadata=metadata or {},
    )


def get_label_hidden_input(case: GuardInput) -> dict[str, Any]:
    return case.label_hidden_input


def get_case_id(case: GuardInput) -> str:
    return case.case_id


def get_domain(case: GuardInput) -> str:
    return str(case.domain)


def get_pair_group(case: GuardInput) -> str:
    return case.pair_group


def strict_input(case: E55Case) -> DeployableE55Input:
    return DeployableE55Input.from_case(case)


def allow_all(case: GuardInput) -> E55Prediction:
    return prediction(case, method="allow_all", decision="ALLOW", accessed_fields=())


def deny_all(case: GuardInput) -> E55Prediction:
    return prediction(case, method="deny_all", decision="DENY", accessed_fields=())


def tool_name_proxy(case: GuardInput) -> E55Prediction:
    label_hidden_input = get_label_hidden_input(case)
    name = str(label_hidden_input["tool_name"])
    if any(token in name for token in ("delete", "remove", "public_link", "submit_payment", "export", "forward")):
        decision = "DENY"
        reason = "surface_high_risk_tool_name"
    elif any(token in name for token in ("draft", "read", "view", "schedule")):
        decision = "ALLOW"
        reason = "surface_low_risk_tool_name"
    else:
        decision = "ALLOW"
        reason = "surface_default_allow"
    return prediction(case, method="tool_name_proxy", decision=decision, reasons=[reason], accessed_fields=("tool_name",), metadata={"decision_reason": reason})


def text_rule_proxy(case: GuardInput) -> E55Prediction:
    label_hidden_input = get_label_hidden_input(case)
    text = (
        str(label_hidden_input.get("candidate_action_summary", ""))
        + " "
        + str(label_hidden_input.get("provenance_summary", ""))
    ).lower()
    if any(token in text for token in ("public", "partner.test", "untrusted_page", "private_tool_output", "third_party_message")):
        decision, reason = "DENY", "text_high_risk_marker"
    elif "unknown" in text:
        decision, reason = "ABSTAIN", "text_unknown_resource_or_control"
    else:
        decision, reason = "ALLOW", "text_default_allow"
    return prediction(
        case,
        method="text_rule_proxy",
        decision=decision,
        reasons=[reason],
        accessed_fields=("candidate_action_summary", "provenance_summary"),
        confidence=0.65,
        metadata={"decision_reason": reason},
    )


def existing_hard_effect_binding_guard(case: GuardInput) -> E55Prediction:
    label_hidden_input = get_label_hidden_input(case)
    visible = {
        "tool_name": label_hidden_input["tool_name"],
        "arguments": label_hidden_input["tool_args"],
    }
    e48_like_input = {
        "user_task": label_hidden_input["task"],
        "candidate_action": visible,
        "provenance_summary": label_hidden_input.get("provenance_summary"),
    }
    effect = infer_visible_effect(visible)
    resource = infer_visible_resource(visible)
    provenance = infer_provenance_risk(e48_like_input)
    authorization = infer_authorization_match(label_hidden_input["task"], effect, resource, e48_like_input)
    decision, reason = tuple_decision(effect, resource, authorization, provenance, e48_like_input)
    atom = EffectAtom(
        effect=effect,
        operation=str(label_hidden_input["tool_name"]),
        resource_id=resource,
        resource_type="unknown",
        commit_mode=str(label_hidden_input["tool_args"].get("commit_mode", "commit")),
        provenance_source=str(label_hidden_input.get("provenance_summary", {}).get("provenance_source", "user")),
        control_source=str(label_hidden_input.get("provenance_summary", {}).get("control_source", "user")),
    )
    return prediction(
        case,
        method="existing_hard_effect_binding_guard",
        decision=decision,
        atoms=[atom],
        reasons=[reason],
        accessed_fields=("task", "tool_name", "tool_args", "provenance_summary"),
        confidence=0.55 if decision == "ABSTAIN" else 0.75,
        metadata={
            "decision_reason": reason,
            "predicted_effect": effect,
            "predicted_resource": resource,
            "authorization_match": authorization,
            "provenance_risk": provenance,
            "minimal_e48_adaptation": True,
        },
    )


def authz_aware_guard(case: GuardInput, *, method: str = "authz_aware_effect_binding_guard", corrected_v2: bool = False) -> E55Prediction:
    if method not in AUTHZ_METHODS:
        raise ValueError(f"Unknown authz-aware method: {method}")
    label_hidden_input = get_label_hidden_input(case)
    use_aliases = method != "authz_aware_no_alias_resolution"
    multi_resource = method != "authz_aware_no_multi_resource_expansion"
    check_operation_mode = method != "authz_aware_no_operation_mode"
    use_provenance = method != "authz_aware_no_provenance_overlay"
    use_evidence = method != "authz_aware_no_evidence_fallback"
    context = AuthorizationContext.from_dict(label_hidden_input["authorization_context"])
    args = dict(label_hidden_input["tool_args"])
    if use_evidence:
        args = apply_evidence_fallback(args, label_hidden_input.get("evidence_summary"), allow_unknown_resource_fallback=not corrected_v2)
    atoms = expand_tool_call(get_domain(case), label_hidden_input["tool_name"], args, multi_resource=multi_resource, corrected_v2=corrected_v2)
    decision, auth, reasons = authorize_atoms(
        atoms,
        context,
        use_aliases=use_aliases,
        check_operation_mode=check_operation_mode,
        use_provenance=use_provenance,
    )
    accessed = ["authorization_context", "tool_name", "tool_args", "tool_inventory", "provenance_summary"]
    if use_evidence:
        accessed.append("evidence_summary")
    return prediction(
        case,
        method=method,
        decision=decision,
        atoms=atoms,
        atom_auth=auth,
        reasons=reasons,
        accessed_fields=accessed,
        confidence=0.9 if decision != "ABSTAIN" else 0.45,
        metadata={
            "use_aliases": use_aliases,
            "multi_resource": multi_resource,
            "check_operation_mode": check_operation_mode,
            "use_provenance": use_provenance,
            "use_evidence_fallback": use_evidence,
            "corrected_v2": corrected_v2,
            "all_atoms_authorized": decision == "ALLOW",
            "decision_reason": "all_atoms_authorized" if decision == "ALLOW" else ",".join(reasons),
        },
    )


def apply_evidence_fallback(args: dict[str, Any], evidence: Any, *, allow_unknown_resource_fallback: bool = True) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        return args
    out = dict(args)
    if not allow_unknown_resource_fallback:
        return out
    for key in ("to", "event_id", "file_id", "channel", "from_account", "recipient", "payee"):
        if key not in evidence:
            continue
        current = out.get(key)
        if current in (None, "", "unknown", "unknown_recipient", "unknown_event", "unknown_file", "unknown_channel", "unknown_account"):
            out[key] = [evidence[key]] if key == "to" else evidence[key]
        elif isinstance(current, list) and any(str(item).startswith("unknown") for item in current):
            out[key] = [evidence[key]]
    return out


def run_methods(
    case: E55Case,
    *,
    include_optional_local_qwen: bool = False,
    strict_label_hidden: bool = False,
    corrected_v2: bool = False,
) -> list[E55Prediction]:
    del include_optional_local_qwen
    guard_input: GuardInput = strict_input(case) if strict_label_hidden else case
    out = [
        allow_all(guard_input),
        deny_all(guard_input),
        tool_name_proxy(guard_input),
        text_rule_proxy(guard_input),
        existing_hard_effect_binding_guard(guard_input),
    ]
    for method in (
        "authz_aware_effect_binding_guard",
        "authz_aware_no_alias_resolution",
        "authz_aware_no_multi_resource_expansion",
        "authz_aware_no_operation_mode",
        "authz_aware_no_provenance_overlay",
        "authz_aware_no_evidence_fallback",
    ):
        out.append(authz_aware_guard(guard_input, method=method, corrected_v2=corrected_v2))
    return out
