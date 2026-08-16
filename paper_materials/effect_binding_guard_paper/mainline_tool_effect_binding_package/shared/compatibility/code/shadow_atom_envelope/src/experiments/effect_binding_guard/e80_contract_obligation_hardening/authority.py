"""Validate an LLM permission-plan proposal against independent authority.

The manifest is trusted benchmark/runtime input. The LLM may narrow it, but it
cannot introduce a tool, field, literal, or resolver obligation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class FieldAuthority:
    mode: str
    exact_values: tuple[Any, ...] = ()
    resolver_id: str | None = None
    source_spans: tuple[str, ...] = ()
    canonical_transform: str | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"exact", "resolve", "forbidden"}:
            raise ValueError(f"unsupported authority mode: {self.mode}")
        if self.mode == "exact" and not self.source_spans and not self.canonical_transform:
            raise ValueError("exact authority requires a source span or independently reviewed canonical transform")
        if self.mode == "resolve" and not self.resolver_id:
            raise ValueError("resolve authority requires a fixed resolver id")


@dataclass(frozen=True)
class AuthorityManifest:
    task_id: str
    tools: Mapping[str, Mapping[str, FieldAuthority]]
    resolver_catalog: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ManifestValidation:
    accepted: bool
    bounded_plan: dict[str, Any] | None
    violations: tuple[str, ...]


def _canonical(value: Any) -> tuple[str, str]:
    return type(value).__name__, repr(value)


def validate_plan_against_manifest(
    proposal: Mapping[str, Any] | None,
    manifest: AuthorityManifest,
) -> ManifestValidation:
    """Accept only proposals that are a semantic subset of ``manifest``."""

    if not isinstance(proposal, Mapping) or not isinstance(proposal.get("tools"), Mapping):
        return ManifestValidation(False, None, ("malformed_plan",))

    violations: list[str] = []
    bounded_tools: dict[str, Any] = {}
    for tool_name, tool_plan in proposal["tools"].items():
        if tool_name not in manifest.tools:
            violations.append(f"tool_not_authorized:{tool_name}")
            continue
        if not isinstance(tool_plan, Mapping) or not isinstance(tool_plan.get("fields"), Mapping):
            violations.append(f"malformed_tool_plan:{tool_name}")
            continue
        bounded_fields: dict[str, Any] = {}
        for field_name, binding in tool_plan["fields"].items():
            authority = manifest.tools[tool_name].get(field_name)
            if authority is None:
                violations.append(f"field_not_authorized:{tool_name}.{field_name}")
                continue
            if not isinstance(binding, Mapping):
                violations.append(f"malformed_binding:{tool_name}.{field_name}")
                continue
            mode = binding.get("mode")
            if mode == "forbidden":
                bounded_fields[field_name] = {"mode": "forbidden", "values": [], "resolver_id": None}
                continue
            if mode != authority.mode:
                violations.append(f"mode_expansion:{tool_name}.{field_name}")
                continue
            if mode == "exact":
                values = binding.get("values")
                if not isinstance(values, list):
                    violations.append(f"malformed_exact_values:{tool_name}.{field_name}")
                    continue
                allowed = {_canonical(value) for value in authority.exact_values}
                if any(_canonical(value) not in allowed for value in values):
                    violations.append(f"literal_not_grounded:{tool_name}.{field_name}")
                    continue
                bounded_fields[field_name] = {"mode": "exact", "values": list(values), "resolver_id": None}
            elif mode == "resolve":
                resolver_id = binding.get("resolver_id")
                if resolver_id != authority.resolver_id or resolver_id not in manifest.resolver_catalog:
                    violations.append(f"resolver_not_authorized:{tool_name}.{field_name}")
                    continue
                bounded_fields[field_name] = {"mode": "resolve", "values": [], "resolver_id": resolver_id}
            else:
                violations.append(f"unsupported_mode:{tool_name}.{field_name}")
        bounded_tools[tool_name] = {"fields": bounded_fields}

    if violations:
        return ManifestValidation(False, None, tuple(sorted(violations)))
    return ManifestValidation(
        True,
        {"task_id": manifest.task_id, "tools": bounded_tools, "authority_source": "independent_manifest"},
        (),
    )
