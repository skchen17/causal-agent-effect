"""Source-executed adequacy audit for frozen AgentDojo effect descriptors.

The audit is intentionally separate from descriptor registration.  It never
changes a frozen descriptor; it records whether repeated field interventions
change committed sandbox state, only tool output, neither, or fail to execute.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any


MUTATION_KINDS = (
    "observed_alternative",
    "typed_alternative",
    "boundary_alternative",
    "expansion_alternative",
    "surface_alternative",
)


def jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): jsonable(child) for key, child in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [jsonable(child) for child in value]
    return value


def _path_join(prefix: str, key: Any) -> str:
    part = str(key)
    return f"{prefix}.{part}" if prefix else part


def changed_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    """Return deterministic leaf paths whose values differ."""
    before = jsonable(before)
    after = jsonable(after)
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        paths: list[str] = []
        for key in sorted(set(before) | set(after), key=str):
            child = _path_join(prefix, key)
            if key not in before or key not in after:
                paths.append(child)
            else:
                paths.extend(changed_paths(before[key], after[key], child))
        return paths
    if (
        isinstance(before, list)
        and isinstance(after, list)
    ):
        paths = []
        for index in range(max(len(before), len(after))):
            child = f"{prefix}[{index}]"
            if index >= len(before) or index >= len(after):
                paths.append(child)
            else:
                paths.extend(changed_paths(before[index], after[index], child))
        return paths
    return [] if before == after else [prefix or "$root"]


def effect_signature(before: Any, after: Any) -> tuple[str, ...]:
    return tuple(changed_paths(before, after))


def classify_pair(base: Mapping[str, Any], mutated: Mapping[str, Any]) -> str:
    if base.get("error") or mutated.get("error"):
        return "invalid_or_unresolved"
    base_state = effect_signature(base.get("before"), base.get("after"))
    mutated_state = effect_signature(mutated.get("before"), mutated.get("after"))
    if base_state != mutated_state or base.get("after") != mutated.get("after"):
        return "committed_effect_changed"
    if base.get("output") != mutated.get("output"):
        return "output_only_changed"
    return "effect_invariant"


def _unique(values: Sequence[Any], original: Any) -> list[Any]:
    seen = {json.dumps(jsonable(original), sort_keys=True, default=str)}
    rows = []
    for value in values:
        key = json.dumps(jsonable(value), sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        rows.append(copy.deepcopy(value))
    return rows


def mutation_candidates(
    value: Any,
    observed: Sequence[Any],
    field: str,
) -> list[tuple[str, Any]]:
    """Generate five deterministic mutation classes where the type permits."""
    observed_values = _unique(observed, value)
    candidates: list[tuple[str, Any]] = []
    if observed_values:
        candidates.append(("observed_alternative", observed_values[0]))

    lower = field.casefold()
    if isinstance(value, bool):
        candidates.extend(
            [
                ("typed_alternative", not value),
                ("boundary_alternative", bool(1 - int(value))),
            ]
        )
    elif isinstance(value, int) and not isinstance(value, bool):
        candidates.extend(
            [
                ("typed_alternative", value + 1),
                ("boundary_alternative", max(0, value - 1)),
                ("expansion_alternative", value + 10),
                ("surface_alternative", int(f"{value}")),
            ]
        )
    elif isinstance(value, float):
        candidates.extend(
            [
                ("typed_alternative", value + 1.0),
                ("boundary_alternative", max(0.0, value - 0.5)),
                ("expansion_alternative", value * 2.0 if value else 1.0),
                ("surface_alternative", float(f"{value:.6f}")),
            ]
        )
    elif isinstance(value, list):
        first = value[0] if value else "counterfactual-value"
        changed = list(value)
        if changed:
            changed[0] = f"{first}-counterfactual"
        else:
            changed = [first]
        candidates.extend(
            [
                ("typed_alternative", changed),
                ("boundary_alternative", []),
                ("expansion_alternative", list(value) + [f"{first}-additional"]),
                ("surface_alternative", list(value)),
            ]
        )
    elif isinstance(value, dict):
        changed = copy.deepcopy(value)
        changed["counterfactual_field"] = "changed"
        candidates.extend(
            [
                ("typed_alternative", changed),
                ("boundary_alternative", {}),
                ("expansion_alternative", {**value, "additional": True}),
                ("surface_alternative", dict(reversed(list(value.items())))),
            ]
        )
    else:
        text = "" if value is None else str(value)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            day = datetime.strptime(text, "%Y-%m-%d")
            typed = (day + timedelta(days=1)).strftime("%Y-%m-%d")
            boundary = (day + timedelta(days=7)).strftime("%Y-%m-%d")
        elif "@" in text or "email" in lower or "recipient" in lower:
            typed = "counterfactual-recipient@example.com"
            boundary = "alternate-recipient@example.net"
        elif "url" in lower or text.startswith(("http://", "https://", "www.")):
            typed = "https://counterfactual.example/path"
            boundary = "https://alternate.example/other"
        else:
            typed = f"{text}-counterfactual"
            boundary = f"alternate-{text}" if text else "alternate-value"
        candidates.extend(
            [
                ("typed_alternative", typed),
                ("boundary_alternative", boundary),
                ("expansion_alternative", f"{text} additional".strip()),
                ("surface_alternative", f" {text} " if text else " "),
            ]
        )

    for extra in observed_values[1:]:
        if len(candidates) >= len(MUTATION_KINDS):
            break
        missing = MUTATION_KINDS[len(candidates)]
        candidates.append((missing, extra))

    deduped: list[tuple[str, Any]] = []
    seen = {json.dumps(jsonable(value), sort_keys=True, default=str)}
    for kind, candidate in candidates:
        key = json.dumps(jsonable(candidate), sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((kind, candidate))
    return deduped[:5]


def aggregate_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    fields: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in rows:
        fields.setdefault((str(row["tool_name"]), str(row["field"])), []).append(row)
    field_rows = []
    for (tool, field), items in sorted(fields.items()):
        valid = [row for row in items if row["classification"] != "invalid_or_unresolved"]
        committed = [row for row in valid if row["classification"] == "committed_effect_changed"]
        output_only = [row for row in valid if row["classification"] == "output_only_changed"]
        invariant = [row for row in valid if row["classification"] == "effect_invariant"]
        field_rows.append(
            {
                "tool_name": tool,
                "field": field,
                "attempted": len(items),
                "valid": len(valid),
                "committed_effect_changed": len(committed),
                "output_only_changed": len(output_only),
                "effect_invariant": len(invariant),
                "five_valid_perturbations": len(valid) >= 5,
                "counterfactually_necessary_for_observed_effects": bool(committed),
            }
        )
    return {
        "n_fields": len(field_rows),
        "n_fields_with_five_valid_perturbations": sum(
            row["five_valid_perturbations"] for row in field_rows
        ),
        "n_fields_with_committed_effect_witness": sum(
            row["counterfactually_necessary_for_observed_effects"] for row in field_rows
        ),
        "n_attempts": len(rows),
        "n_valid": sum(row["valid"] for row in field_rows),
        "field_rows": field_rows,
    }
