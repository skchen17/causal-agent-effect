"""Fail-closed pre-commit kernel over bounded plans and totalized calls."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .authority import AuthorityManifest, validate_plan_against_manifest
from .defaults import FieldDefault, totalize_call


def _canonical(value: Any) -> tuple[str, str]:
    return type(value).__name__, json.dumps(value, sort_keys=True, default=str)


def _flatten(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [child for item in value for child in _flatten(item)]
    if isinstance(value, Mapping):
        return [child for item in value.values() for child in _flatten(item)]
    return [value]


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def mediate_hardened_call(
    *,
    tool_name: str,
    arguments: Mapping[str, Any],
    field_semantics: Mapping[str, FieldDefault],
    security_fields: list[str],
    inactive_values: Mapping[str, list[Any]],
    proposal: Mapping[str, Any] | None,
    manifest: AuthorityManifest,
    resolver_ledger: list[Mapping[str, Any]],
    registry_hash: str,
) -> dict[str, Any]:
    """Return ALLOW, DENY, or ABSTAIN without invoking an LLM."""

    totalized = totalize_call(arguments, field_semantics)
    if not totalized.resolved:
        return {
            "decision": "ABSTAIN",
            "reasons": list(totalized.reasons),
            "checks": [],
            "runtime_called_llm": False,
            "registry_hash": registry_hash,
        }
    bounded = validate_plan_against_manifest(proposal, manifest)
    if not bounded.accepted:
        return {
            "decision": "ABSTAIN",
            "reasons": list(bounded.violations),
            "checks": [],
            "runtime_called_llm": False,
            "registry_hash": registry_hash,
            "totalized_call_hash": _hash({"tool_name": tool_name, "arguments": totalized.arguments}),
        }
    tool_plan = bounded.bounded_plan["tools"].get(tool_name)
    if tool_plan is None:
        return {
            "decision": "ABSTAIN",
            "reasons": ["tool_not_in_bounded_plan"],
            "checks": [],
            "runtime_called_llm": False,
            "registry_hash": registry_hash,
            "totalized_call_hash": _hash({"tool_name": tool_name, "arguments": totalized.arguments}),
        }

    ledger: dict[str, set[tuple[str, str]]] = {}
    for entry in resolver_ledger:
        resolver_id = entry.get("resolver_id")
        values = entry.get("values")
        if (
            isinstance(resolver_id, str)
            and isinstance(values, list)
            and entry.get("typed_projection") is True
            and entry.get("provenance") == "authorized_read"
        ):
            ledger.setdefault(resolver_id, set()).update(_canonical(value) for value in values)

    checks = []
    deny_reasons = []
    abstain_reasons = []
    for field in security_fields:
        if field not in totalized.arguments:
            abstain_reasons.append(f"security_field_not_totalized:{field}")
            continue
        value = totalized.arguments[field]
        inactive = {_canonical(item) for item in inactive_values.get(field, [])}
        if _canonical(value) in inactive:
            checks.append({"field": field, "value": value, "status": "declared_inactive"})
            continue
        binding = tool_plan["fields"].get(field)
        if binding is None:
            abstain_reasons.append(f"security_field_unbound:{field}")
            continue
        for concrete in _flatten(value):
            if binding["mode"] == "forbidden":
                status = "forbidden_value_used"
                deny_reasons.append(f"{field}={concrete!r}:forbidden")
            elif binding["mode"] == "exact":
                allowed = {_canonical(item) for item in binding["values"]}
                status = "matched_exact" if _canonical(concrete) in allowed else "outside_exact_authority"
                if status != "matched_exact":
                    deny_reasons.append(f"{field}={concrete!r}:outside_exact_authority")
            elif binding["mode"] == "resolve":
                allowed = ledger.get(binding["resolver_id"], set())
                status = "matched_typed_resolver" if _canonical(concrete) in allowed else "resolver_value_unproven"
                if status != "matched_typed_resolver":
                    abstain_reasons.append(f"{field}={concrete!r}:resolver_value_unproven")
            else:  # pragma: no cover - authority parser excludes this.
                status = "unsupported_binding"
                abstain_reasons.append(f"{field}:unsupported_binding")
            checks.append({
                "field": field,
                "value": concrete,
                "mode": binding["mode"],
                "resolver_id": binding.get("resolver_id"),
                "status": status,
            })

    if deny_reasons:
        decision, reasons = "DENY", deny_reasons
    elif abstain_reasons:
        decision, reasons = "ABSTAIN", abstain_reasons
    else:
        decision, reasons = "ALLOW", ["all_totalized_security_fields_authorized"]
    return {
        "decision": decision,
        "reasons": reasons,
        "checks": checks,
        "runtime_called_llm": False,
        "authority_source": "independent_manifest",
        "manifest_task_id": manifest.task_id,
        "registry_hash": registry_hash,
        "totalized_call_hash": _hash({"tool_name": tool_name, "arguments": totalized.arguments}),
        "instantiated_defaults": list(totalized.instantiated_defaults),
    }
