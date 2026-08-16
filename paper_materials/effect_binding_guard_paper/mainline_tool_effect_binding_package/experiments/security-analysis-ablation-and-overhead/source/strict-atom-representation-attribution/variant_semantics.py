"""Variant semantics for the strict atom representation attribution protocol.

Phase 0 CPU work. Implements protocol section 4 (V0--V4) as pure functions
with an explicit enum, forbidding positional boolean tuples (the Round 1--5
wiring defect). Also implements the V2 raw-schema-field registry builder and
the correct-vs-shuffled prompt-hash gate (protocol section 11.1).

Protocol v2 revision (2026-08-05): the V1 condition is redefined as a TRUE
whole-call representation -- the totalized call is serialized into an
indivisible canonical signature and exact-matched against a pre-registered
envelope signature set (a deterministic projection of the frozen common plan
cache; see ``whole_call_envelope.py``). No field decomposition, no per-field
repair, and no reuse of the V3/E77 field comparator. The signature functions
below are the single point of definition for the Phase-0 semantics half;
unit tests enforce byte-identical agreement with the runtime comparator half
(``agentdojo_representation_patch.py``) and with the offline projection half
(``whole_call_envelope.py``).

The comparator interface mirrors E77's field comparator; full E77 integration
happens in the runner phase and is deliberately not wired here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

Decision = str  # "ALLOW" | "DENY" | "ABSTAIN" | "NEEDS_REPLAN"


class Variant(str, Enum):
    """Four main conditions plus the optional shuffled-roles diagnostic."""

    TOOL_IDENTITY_ONLY = "tool_identity_only"  # V0
    OPAQUE_WHOLE_CALL = "opaque_whole_call"  # V1 (protocol v2: true whole call)
    RAW_SCHEMA_FIELDS = "raw_schema_fields"  # V2
    VALIDATED_ATOM_FIELDS = "validated_atom_fields"  # V3
    SHUFFLED_ROLES = "shuffled_roles"  # V4 (diagnostic)


@dataclass(frozen=True)
class Check:
    field: str
    role: str
    decision: Decision
    reason: str


@dataclass(frozen=True)
class Verdict:
    decision: Decision
    reasons: list[str]
    checks: list[Check] = field(default_factory=list)
    aggregate_call_level: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reasons": self.reasons,
            "checks": [c.__dict__ for c in self.checks],
            "aggregate_call_level": self.aggregate_call_level,
        }


# ---------------------------------------------------------------------------
# Whole-call canonical signatures (protocol v2). These functions are the ONLY
# serialization layer of the whole-call design; the runtime comparator and
# the offline envelope projection must produce byte-identical signatures
# (enforced by unit tests).
# ---------------------------------------------------------------------------


def whole_call_canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization used for all whole-call signatures."""
    return json.dumps(obj, sort_keys=True, default=str)


def whole_call_plan_signature(plan: Mapping[str, Any]) -> str:
    """Indivisible identity of a permission plan (key of the envelope registry)."""
    return hashlib.sha256(whole_call_canonical_json(plan).encode("utf-8")).hexdigest()


def whole_call_signature(tool_name: str, args: Mapping[str, Any]) -> str:
    """Indivisible identity of a totalized whole call.

    Deliberately identical to ``full_atom_runtime.call_signature`` (the
    signature already recorded in every runtime audit row).
    """
    return hashlib.sha256(
        json.dumps(
            {"tool_name": tool_name, "args": dict(args)},
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------------------
# V0: tool identity only (reuses representation_closed_loop_attribution
# semantics; duplicated here as a pure function so the protocol is runnable
# without importing the E77 worker).
# ---------------------------------------------------------------------------


def decide_v0_tool_identity(
    tool_name: str,
    plan: Mapping[str, Any] | None,
) -> Verdict:
    tools = plan.get("tools") if isinstance(plan, Mapping) else None
    if not isinstance(tools, Mapping):
        return Verdict("NEEDS_REPLAN", ["task_permission_plan_unavailable"])
    if tool_name not in tools:
        return Verdict("NEEDS_REPLAN", ["tool_not_in_initial_permission_plan"])
    return Verdict("ALLOW", ["tool_identity_present_in_initial_permission_plan"])


# ---------------------------------------------------------------------------
# V1 (protocol v2): TRUE opaque whole call -- one indivisible signature
# exact-match against the pre-registered envelope set. No field-level
# comparison, no per-field repair; feedback is opaque (single aggregate
# check). Emits ALLOW or NEEDS_REPLAN only: match/mismatch is binary and
# DENY is reachable solely through the shared revision-DENY recovery path,
# which is identical across all four variants.
# ---------------------------------------------------------------------------


def decide_v1_opaque_whole_call(
    tool_name: str,
    plan: Mapping[str, Any] | None,
    totalized_call: Mapping[str, Any],
    envelope_signatures: set[str] | None,
) -> Verdict:
    """Authorize a totalized whole call by indivisible signature equality.

    ``envelope_signatures`` is the pre-registered set of whole-call
    signatures for the current plan and tool (``None`` or empty when no
    whole-call authority exists for the plan/tool, e.g. for runtime-revised
    plans that are not part of the frozen cache -- the pre-registered
    whole-call blindness characterization). The verdict exposes exactly one
    aggregate call-level check; no per-field or per-target detail leaks.
    """
    tools = plan.get("tools") if isinstance(plan, Mapping) else None
    if not isinstance(tools, Mapping):
        return Verdict("NEEDS_REPLAN", ["task_permission_plan_unavailable"])
    if tool_name not in tools:
        return Verdict("NEEDS_REPLAN", ["tool_not_in_initial_permission_plan"])
    if not envelope_signatures:
        return Verdict("NEEDS_REPLAN", ["whole_call_envelope_not_registered"])
    signature = whole_call_signature(tool_name, totalized_call)
    if signature in envelope_signatures:
        return Verdict(
            "ALLOW",
            ["whole_call_within_authorized_envelope"],
            checks=[Check(tool_name, "whole_call", "ALLOW", "signature_exact_match")],
            aggregate_call_level=True,
        )
    return Verdict(
        "NEEDS_REPLAN",
        ["whole_call_outside_authorized_envelope"],
        checks=[
            Check(tool_name, "whole_call", "NEEDS_REPLAN", "signature_outside_registry")
        ],
        aggregate_call_level=True,
    )


# ---------------------------------------------------------------------------
# V2: raw schema fields — all parameters are security fields with the fixed
# untyped_argument role; fail closed on anything unknown.
# ---------------------------------------------------------------------------


def build_v2_raw_schema_registry(
    runtime_catalog: Mapping[str, Any],
    tool_names: list[str],
) -> dict[str, dict[str, Any]]:
    """Mechanically generate a V2 registry from the official tool schema.

    Every schema parameter becomes a security_field with role
    `untyped_argument`; no LLM classification, no counterfactual evidence,
    no gold atoms, no human labels.
    """
    registry: dict[str, dict[str, Any]] = {}
    for suite_name, suite_tools in runtime_catalog.get("suites", {}).items():
        for tool_name in tool_names:
            if tool_name not in suite_tools:
                continue
            fields = sorted(suite_tools[tool_name].get("fields", {}))
            if tool_name in registry:
                existing = set(registry[tool_name]["security_fields"])
                if existing != set(fields):
                    raise ValueError(
                        f"{tool_name}: schema fields differ across suites "
                        f"({sorted(existing)} vs {fields})"
                    )
                continue
            registry[tool_name] = {
                "tool_name": tool_name,
                "security_fields": fields,
                "field_roles": {f: "untyped_argument" for f in fields},
                "non_security_fields": [],
                "effect_kind": "untyped_schema_argument",
                "source": "raw_schema_mechanical",
                "registration_policy": "fail_closed_unknown_parameters",
            }
    return registry


def decide_v2_raw_schema_fields(
    tool_name: str,
    plan: Mapping[str, Any] | None,
    descriptor: Mapping[str, Any],
    call_args: Mapping[str, Any],
    compare_field: Any = None,
) -> Verdict:
    """Per-field checks over every schema parameter; unknown args fail closed."""
    tools = plan.get("tools") if isinstance(plan, Mapping) else None
    if not isinstance(tools, Mapping):
        return Verdict("NEEDS_REPLAN", ["task_permission_plan_unavailable"])
    if tool_name not in tools:
        return Verdict("NEEDS_REPLAN", ["tool_not_in_initial_permission_plan"])
    fields = descriptor.get("security_fields") or []
    checks: list[Check] = []
    denied: list[str] = []
    for field_name in fields:
        role = descriptor.get("field_roles", {}).get(field_name, "untyped_argument")
        decision, reason = _field_decision(field_name, call_args, compare_field)
        checks.append(Check(field_name, role, decision, reason))
        if decision != "ALLOW":
            denied.append(f"{field_name}:{reason}")
    for arg_name in call_args:
        if arg_name not in fields:
            checks.append(Check(arg_name, "untyped_argument", "DENY", "unknown_parameter"))
            denied.append(f"{arg_name}:unknown_parameter")
    if denied:
        return Verdict("DENY", denied[:3], checks=checks)
    return Verdict("ALLOW", ["all_schema_fields_match"], checks=checks)


def _field_decision(
    field_name: str,
    call_args: Mapping[str, Any],
    compare_field: Any,
) -> tuple[Decision, str]:
    if call_args is None:
        return "DENY", "missing_call_arguments"
    if field_name not in call_args:
        return "DENY", "missing_required_argument"
    actual = call_args[field_name]
    if compare_field is None:
        return "ALLOW", "value_present"
    return compare_field(field_name, actual)


# ---------------------------------------------------------------------------
# V3: validated atom fields — counterfactually registered security fields
# only; non-security fields never block authority. V4 reuses V3 with shuffled
# roles. Both expose a representation text + hash for the §11.1 gate.
# ---------------------------------------------------------------------------


def render_v3_representation(
    tool_name: str,
    descriptor: Mapping[str, Any],
    *,
    shuffle_roles: bool = False,
) -> str:
    fields = [str(f) for f in descriptor.get("security_fields", [])]
    roles = dict(descriptor.get("field_roles", {}))
    if shuffle_roles:
        roles = _rotate_roles(roles, fields)
    role_text = ", ".join(
        f"{f}->{roles.get(f, 'security_relevant')}" for f in fields
    )
    return (
        f"[ATOMIZED_EFFECT_INTERFACE_V1] tool={tool_name} "
        f"effect_kind={descriptor.get('effect_kind', 'unspecified')} "
        f"security_fields={','.join(fields) or 'none'} roles={{{role_text}}}"
    )


def _rotate_roles(roles: Mapping[str, str], fields: list[str]) -> dict[str, str]:
    """Deterministic one-step rotation; never consults outcomes."""
    values = [roles.get(f, "security_relevant") for f in fields]
    if len(set(values)) <= 1:
        return dict(roles)
    return dict(zip(fields, values[1:] + values[:1]))


def representation_sha256(representation: str) -> str:
    return hashlib.sha256(representation.encode("utf-8")).hexdigest()


def decide_v3_validated_atom_fields(
    tool_name: str,
    plan: Mapping[str, Any] | None,
    descriptor: Mapping[str, Any],
    call_args: Mapping[str, Any],
    compare_field: Any = None,
    *,
    shuffle_roles: bool = False,
) -> Verdict:
    """Per-field checks over counterfactually validated security fields."""
    tools = plan.get("tools") if isinstance(plan, Mapping) else None
    if not isinstance(tools, Mapping):
        return Verdict("NEEDS_REPLAN", ["task_permission_plan_unavailable"])
    if tool_name not in tools:
        return Verdict("NEEDS_REPLAN", ["tool_not_in_initial_permission_plan"])
    fields = [str(f) for f in descriptor.get("security_fields", [])]
    roles = dict(descriptor.get("field_roles", {}))
    if shuffle_roles:
        roles = _rotate_roles(roles, fields)
    checks: list[Check] = []
    denied: list[str] = []
    for field_name in fields:
        role = roles.get(field_name, "security_relevant")
        decision, reason = _field_decision(field_name, call_args, compare_field)
        checks.append(Check(field_name, role, decision, reason))
        if decision != "ALLOW":
            denied.append(f"{field_name}:{reason}")
    if denied:
        return Verdict("DENY", denied[:3], checks=checks)
    return Verdict("ALLOW", ["all_validated_atom_fields_match"], checks=checks)


def validate_v2_v3_tool_set_alignment(
    v2_registry: Mapping[str, Any],
    v3_registry: Mapping[str, Any],
    expected_tools: list[str],
) -> list[str]:
    """Protocol section 11.1: V2 and V3 must cover exactly the same tools."""
    v2_tools = set(v2_registry)
    v3_tools = set(v3_registry)
    errors: list[str] = []
    if v2_tools != set(expected_tools):
        errors.append(f"V2 tool set mismatch: {sorted(v2_tools ^ set(expected_tools))}")
    if v3_tools != set(expected_tools):
        errors.append(f"V3 tool set mismatch: {sorted(v3_tools ^ set(expected_tools))}")
    if v2_tools != v3_tools:
        errors.append(f"V2/V3 sets differ: {sorted(v2_tools ^ v3_tools)}")
    return errors
