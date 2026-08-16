"""Typed resolver and authority compilation for a reviewed AgentDojo task."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from src.experiments.effect_binding_guard.e80_contract_obligation_hardening import (
    AuthorityManifest,
    FieldAuthority,
    FieldDefault,
)


Scalar = str | int | float | bool | None


@dataclass(frozen=True)
class ResolverSpec:
    resolver_id: str
    read_tool: str
    query_arguments: Mapping[str, Mapping[str, Any]]
    allow_additional_arguments: bool
    projection_kind: str
    projection_field: str
    max_cardinality: int
    selector_field: str = ""
    selector_operator: str = ""
    selector_value: Scalar = None
    parser_id: str = ""

    def __post_init__(self) -> None:
        if self.allow_additional_arguments:
            raise ValueError("authorized resolver cannot allow additional query arguments")
        if self.projection_kind not in {
            "scalar",
            "list_items",
            "record_field",
            "record_list_field",
            "filtered_record_field",
            "parsed_text_field",
        }:
            raise ValueError("unsupported resolver projection")
        if self.projection_kind in {
            "record_field",
            "record_list_field",
            "filtered_record_field",
            "parsed_text_field",
        } and not self.projection_field:
            raise ValueError("record projection requires a field")
        if self.projection_kind == "filtered_record_field":
            if not self.selector_field or self.selector_operator not in {"exact", "casefold_contains"}:
                raise ValueError("filtered record projection requires a supported selector")
            if self.selector_value is None or not isinstance(self.selector_value, (str, int, float, bool)):
                raise ValueError("filtered record selector requires a scalar value")
        if self.projection_kind == "parsed_text_field":
            if self.parser_id != "postal_address_block_v1":
                raise ValueError("parsed text projection requires a supported parser")
            if self.projection_field not in {"street", "city"}:
                raise ValueError("postal address parser exposes only street and city")
        if not 1 <= self.max_cardinality <= 100:
            raise ValueError("resolver cardinality must be in [1, 100]")


@dataclass(frozen=True)
class CompiledTrustedInterface:
    manifest: AuthorityManifest
    resolver_specs: Mapping[str, ResolverSpec]
    original_task_sha256: str
    reviewer_anonymous_id: str
    review_date: str


@dataclass(frozen=True)
class CompiledToolSemantics:
    field_semantics: Mapping[str, FieldDefault]
    security_fields: tuple[str, ...]
    inactive_values: Mapping[str, list[Any]]


def compile_tool_semantics(catalog: Mapping[str, Any], suite: str, tool_name: str) -> CompiledToolSemantics:
    try:
        tool = catalog["suites"][suite][tool_name]
    except KeyError as exc:
        raise ValueError(f"tool semantics missing for {suite}/{tool_name}") from exc
    fields = {}
    for field_name, raw in tool["fields"].items():
        kind = raw.get("kind")
        if kind == "required":
            fields[field_name] = FieldDefault(required=True)
        elif kind == "static":
            fields[field_name] = FieldDefault(static_default=raw.get("value"))
        elif kind == "dynamic_or_unknown":
            fields[field_name] = FieldDefault(dynamic_default=True)
        else:
            raise ValueError(f"unsupported field semantics for {tool_name}.{field_name}: {kind!r}")
    security_fields = tuple(tool.get("security_fields", []))
    if any(field not in fields for field in security_fields):
        raise ValueError("security field missing from totalization catalog")
    return CompiledToolSemantics(
        field_semantics=fields,
        security_fields=security_fields,
        inactive_values=tool.get("inactive_values", {}),
    )


def _canonical(value: Any) -> tuple[str, str]:
    return type(value).__name__, repr(value)


def _record_mapping(value: Any) -> Mapping[str, Any] | None:
    """Expose fields from mappings or structured AgentDojo/Pydantic records."""
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dumped
    return None


def compile_trusted_interface(row: Mapping[str, Any]) -> CompiledTrustedInterface:
    required = {
        "suite", "user_task_id", "original_task_sha256", "authority_tools", "resolver_specs",
        "reviewer_anonymous_id", "review_date",
    }
    missing = sorted(required - set(row))
    if missing:
        raise ValueError(f"compiled review row is missing {missing}")
    tools: dict[str, dict[str, FieldAuthority]] = {}
    resolver_ids = set()
    for tool_name, fields in row["authority_tools"].items():
        tools[tool_name] = {}
        for field_name, binding in fields.items():
            mode = binding.get("mode")
            if mode == "exact":
                tools[tool_name][field_name] = FieldAuthority(
                    mode="exact",
                    exact_values=tuple(binding.get("values", [])),
                    source_spans=tuple(binding.get("source_spans", [])),
                    canonical_transform=binding.get("canonical_transform") or None,
                )
            elif mode == "resolve":
                resolver_id = binding.get("resolver_id")
                if not isinstance(resolver_id, str) or not resolver_id:
                    raise ValueError(f"missing resolver id for {tool_name}.{field_name}")
                resolver_ids.add(resolver_id)
                tools[tool_name][field_name] = FieldAuthority(mode="resolve", resolver_id=resolver_id)
            elif mode == "forbidden":
                tools[tool_name][field_name] = FieldAuthority(mode="forbidden")
            else:
                raise ValueError(f"unsupported authority mode {mode!r}")

    specs = {}
    for resolver_id, raw in row["resolver_specs"].items():
        query = raw["query_constraint"]
        projection = raw["output_projection"]
        selector = projection.get("selector", {})
        specs[resolver_id] = ResolverSpec(
            resolver_id=resolver_id,
            read_tool=raw["read_tool"],
            query_arguments=query["arguments"],
            allow_additional_arguments=query["allow_additional_arguments"],
            projection_kind=projection["kind"],
            projection_field=projection.get("field", ""),
            max_cardinality=raw["max_cardinality"],
            selector_field=selector.get("field", ""),
            selector_operator=selector.get("operator", ""),
            selector_value=selector.get("value"),
            parser_id=projection.get("parser_id", ""),
        )
    if resolver_ids != set(specs):
        raise ValueError(f"resolver authority/spec mismatch: bindings={sorted(resolver_ids)} specs={sorted(specs)}")
    task_id = f"{row['suite']}/{row['user_task_id']}"
    return CompiledTrustedInterface(
        manifest=AuthorityManifest(task_id=task_id, tools=tools, resolver_catalog=frozenset(specs)),
        resolver_specs=specs,
        original_task_sha256=row["original_task_sha256"],
        reviewer_anonymous_id=row["reviewer_anonymous_id"],
        review_date=row["review_date"],
    )


def _query_matches(spec: ResolverSpec, arguments: Mapping[str, Any]) -> bool:
    if set(arguments) - set(spec.query_arguments):
        return False
    for field, constraint in spec.query_arguments.items():
        mode = constraint.get("mode")
        if mode == "forbidden":
            if field in arguments:
                return False
        elif mode == "exact":
            if field not in arguments:
                return False
            allowed = {_canonical(value) for value in constraint.get("values", [])}
            if _canonical(arguments[field]) not in allowed:
                return False
        else:
            return False
    return True


def _selector_matches(spec: ResolverSpec, record: Mapping[str, Any]) -> bool:
    if spec.selector_field not in record:
        return False
    observed = record[spec.selector_field]
    if spec.selector_operator == "exact":
        return _canonical(observed) == _canonical(spec.selector_value)
    if spec.selector_operator == "casefold_contains":
        return (
            isinstance(observed, str)
            and isinstance(spec.selector_value, str)
            and spec.selector_value.casefold() in observed.casefold()
        )
    return False


def _parse_postal_address_block(value: Any) -> Mapping[str, str] | None:
    """Parse one narrow address block without interpreting adjacent instructions."""
    if not isinstance(value, str):
        return None
    lines = [line.strip() for line in value.splitlines()]
    for index, line in enumerate(lines):
        if line.casefold() not in {"usa", "united states", "united states of america"} or index < 2:
            continue
        street = lines[index - 2]
        locality = lines[index - 1]
        if any(marker in street + locality for marker in ("<|", "|>", "[", "]", "{", "}")):
            continue
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .,'#/-]{2,100}", street):
            continue
        locality_match = re.fullmatch(
            r"(?P<city>[A-Za-z][A-Za-z .'-]{1,80})(?:,\s*[A-Za-z]{2}(?:\s+\d{5}(?:-\d{4})?)?)?",
            locality,
        )
        if locality_match:
            return {"street": street, "city": locality_match.group("city").strip()}
    return None


def _project(spec: ResolverSpec, value: Any) -> list[Scalar] | None:
    projected: list[Any]
    if spec.projection_kind == "scalar":
        projected = [value]
    elif spec.projection_kind == "list_items":
        if not isinstance(value, list):
            return None
        projected = value
    elif spec.projection_kind == "record_field":
        record = _record_mapping(value)
        if record is None or spec.projection_field not in record:
            return None
        projected = [record[spec.projection_field]]
    elif spec.projection_kind == "record_list_field":
        if not isinstance(value, list):
            return None
        records = [_record_mapping(item) for item in value]
        if any(record is None for record in records):
            return None
        if any(spec.projection_field not in record for record in records if record is not None):
            return None
        projected = [record[spec.projection_field] for record in records if record is not None]
    elif spec.projection_kind == "filtered_record_field":
        if not isinstance(value, list):
            return None
        records = [_record_mapping(item) for item in value]
        if any(record is None for record in records):
            return None
        selected = [
            record
            for record in records
            if record is not None and _selector_matches(spec, record)
        ]
        if any(spec.projection_field not in record for record in selected):
            return None
        projected = [record[spec.projection_field] for record in selected]
    else:
        parsed = _parse_postal_address_block(value)
        if parsed is None or spec.projection_field not in parsed:
            return None
        projected = [parsed[spec.projection_field]]
    if len(projected) > spec.max_cardinality:
        return None
    if any(item is not None and not isinstance(item, (str, int, float, bool)) for item in projected):
        return None
    return projected


def build_typed_resolver_ledger_entry(
    spec: ResolverSpec,
    *,
    tool_name: str,
    arguments: Mapping[str, Any],
    result: Any,
) -> dict[str, Any] | None:
    """Return trusted evidence only for the reviewed call and typed projection."""
    if tool_name != spec.read_tool or not _query_matches(spec, arguments):
        return None
    values = _project(spec, result)
    if values is None:
        return None
    return {
        "resolver_id": spec.resolver_id,
        "values": values,
        "typed_projection": True,
        "provenance": "authorized_read",
        "read_tool": tool_name,
    }
