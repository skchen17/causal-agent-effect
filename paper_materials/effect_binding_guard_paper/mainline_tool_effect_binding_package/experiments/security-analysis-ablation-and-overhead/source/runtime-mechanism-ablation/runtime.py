"""AgentDojo-facing pure pre-commit adapter for reviewed authority manifests."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from src.experiments.effect_binding_guard.e80_contract_obligation_hardening import mediate_hardened_call

from .trusted_interface import CompiledTrustedInterface, compile_tool_semantics


def manifest_as_proposal(interface: CompiledTrustedInterface) -> dict[str, Any]:
    tools = {}
    for tool_name, fields in interface.manifest.tools.items():
        compiled_fields = {}
        for field_name, authority in fields.items():
            if authority.mode == "exact":
                compiled_fields[field_name] = {
                    "mode": "exact", "values": list(authority.exact_values), "resolver_id": None,
                }
            elif authority.mode == "resolve":
                compiled_fields[field_name] = {
                    "mode": "resolve", "values": [], "resolver_id": authority.resolver_id,
                }
            else:
                compiled_fields[field_name] = {"mode": "forbidden", "values": [], "resolver_id": None}
        tools[tool_name] = {"fields": compiled_fields}
    return {"tools": tools}


def mediate_reviewed_agentdojo_call(
    *,
    original_task: str,
    suite: str,
    tool_name: str,
    arguments: Mapping[str, Any],
    runtime_catalog: Mapping[str, Any],
    interface: CompiledTrustedInterface,
    resolver_ledger: list[Mapping[str, Any]],
    registry_hash: str,
    bounded_proposal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Mediate one totalized call; never invoke a model or execute the tool."""
    observed_task_hash = hashlib.sha256(original_task.encode()).hexdigest()
    if observed_task_hash != interface.original_task_sha256:
        return {
            "decision": "ABSTAIN",
            "reasons": ["authority_manifest_task_hash_mismatch"],
            "checks": [],
            "runtime_called_llm": False,
            "runtime_executed_tool": False,
            "registry_hash": registry_hash,
        }
    if interface.manifest.task_id != f"{suite}/{interface.manifest.task_id.rsplit('/', 1)[-1]}":
        return {
            "decision": "ABSTAIN",
            "reasons": ["authority_manifest_suite_mismatch"],
            "checks": [],
            "runtime_called_llm": False,
            "runtime_executed_tool": False,
            "registry_hash": registry_hash,
        }
    try:
        semantics = compile_tool_semantics(runtime_catalog, suite, tool_name)
    except ValueError as exc:
        return {
            "decision": "ABSTAIN", "reasons": [f"tool_semantics_unavailable:{exc}"], "checks": [],
            "runtime_called_llm": False, "runtime_executed_tool": False, "registry_hash": registry_hash,
        }
    result = mediate_hardened_call(
        tool_name=tool_name,
        arguments=arguments,
        field_semantics=semantics.field_semantics,
        security_fields=list(semantics.security_fields),
        inactive_values=semantics.inactive_values,
        proposal=bounded_proposal or manifest_as_proposal(interface),
        manifest=interface.manifest,
        resolver_ledger=resolver_ledger,
        registry_hash=registry_hash,
    )
    return {**result, "runtime_executed_tool": False}
