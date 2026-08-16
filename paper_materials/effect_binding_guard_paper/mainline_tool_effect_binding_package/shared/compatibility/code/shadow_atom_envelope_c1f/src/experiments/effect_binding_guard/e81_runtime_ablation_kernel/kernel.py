"""Single-component E81 comparison variants.

This module is deliberately pure. It defines the runtime semantics to be wired
to a later common-protocol runner; importing it does not alter E77 or E78.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import (
    compare_call_to_plan,
    value_grounded,
)


@dataclass(frozen=True)
class AblationConfig:
    row_id: str
    field_granularity: bool = True
    provenance_control_binding: bool = True
    counterfactual_registration: bool = True
    task_envelope: bool = True
    authorized_read_grounding: bool = True
    omitted_fields_fail_closed: bool = True
    replan_enabled: bool = True


ABLATIONS = {
    "A1": AblationConfig("A1"),
    "A2": AblationConfig("A2", field_granularity=False),
    "A7": AblationConfig("A7", provenance_control_binding=False),
    "A9": AblationConfig("A9", counterfactual_registration=False),
    "A11": AblationConfig("A11", task_envelope=False),
    "A12": AblationConfig("A12", authorized_read_grounding=False),
    "A13": AblationConfig("A13", omitted_fields_fail_closed=False),
    "A15": AblationConfig("A15", replan_enabled=False),
}


def config_diff(row_id: str) -> dict[str, tuple[Any, Any]]:
    base = asdict(ABLATIONS["A1"])
    row = asdict(ABLATIONS[row_id])
    return {
        key: (base[key], row[key])
        for key in base
        if key != "row_id" and base[key] != row[key]
    }


def _terminal(decision: str, reasons: list[str], config: AblationConfig, checks: list[dict[str, Any]]) -> dict[str, Any]:
    if decision == "NEEDS_REPLAN" and not config.replan_enabled:
        return {"decision": "DENY", "reasons": ["replan_disabled", *reasons], "checks": checks}
    return {"decision": decision, "reasons": reasons, "checks": checks}


def compare_under_ablation(
    config: AblationConfig,
    user_task: str,
    descriptor: Mapping[str, Any],
    plan: Mapping[str, Any] | None,
    args: Mapping[str, Any],
    authorized_read_evidence: list[str],
    *,
    missing_fields: list[str] | None = None,
    raw_descriptor: Mapping[str, Any] | None = None,
    untrusted_read_evidence: list[str] | None = None,
) -> dict[str, Any]:
    if not config.counterfactual_registration:
        if raw_descriptor is None:
            return _terminal("NEEDS_REPLAN", ["raw_descriptor_missing"], config, [])
        descriptor = raw_descriptor
    if not descriptor.get("side_effectful"):
        return {"decision": "ALLOW", "reasons": ["read_only_tool"], "checks": []}
    if not config.task_envelope:
        return {"decision": "ALLOW", "reasons": ["ablation_no_task_envelope"], "checks": []}
    if plan is None or descriptor["tool_name"] not in plan.get("tools", {}):
        return _terminal("NEEDS_REPLAN", ["missing_task_envelope"], config, [])
    if missing_fields and config.omitted_fields_fail_closed:
        return _terminal(
            "NEEDS_REPLAN",
            [f"security_field_omitted:{field}" for field in sorted(missing_fields)],
            config,
            [],
        )
    if not config.field_granularity:
        return {"decision": "ALLOW", "reasons": ["ablation_tool_call_level_match"], "checks": []}

    effective_descriptor = dict(descriptor)
    if not config.provenance_control_binding:
        effective_descriptor["security_fields"] = [
            field for field in descriptor["security_fields"]
            if field not in {"provenance_source", "control_source"}
        ]
    comparison = compare_call_to_plan(user_task, effective_descriptor, plan, args)
    if (
        comparison["decision"] == "NEEDS_REPLAN"
        and config.authorized_read_grounding
        and comparison.get("checks")
    ):
        evidence = list(authorized_read_evidence)
        if not config.provenance_control_binding:
            evidence.extend(untrusted_read_evidence or [])
        allowed = {"matched_exact", "resolved_from_original_task", "resolved_from_authorized_read"}
        for check in comparison["checks"]:
            if check["status"] == "resolver_fill_requires_replan" and any(
                value_grounded(check["value"], item) for item in evidence
            ):
                check["status"] = "resolved_from_authorized_read"
        reasons = [
            f"{check['field']}={check['value']!r}: {check['status']}"
            for check in comparison["checks"] if check["status"] not in allowed
        ]
        comparison = {
            "decision": "ALLOW" if not reasons else "NEEDS_REPLAN",
            "reasons": reasons or ["all_fields_grounded"],
            "checks": comparison["checks"],
        }
    return _terminal(comparison["decision"], comparison["reasons"], config, comparison["checks"])
