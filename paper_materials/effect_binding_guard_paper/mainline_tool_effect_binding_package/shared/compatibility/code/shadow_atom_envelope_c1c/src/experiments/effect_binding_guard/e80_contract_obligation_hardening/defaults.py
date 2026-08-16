"""Totalize structured tool calls before authorization and execution."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping


_MISSING = object()


@dataclass(frozen=True)
class FieldDefault:
    required: bool = False
    static_default: Any = _MISSING
    dynamic_default: bool = False


@dataclass(frozen=True)
class TotalizedCall:
    resolved: bool
    arguments: dict[str, Any] | None
    reasons: tuple[str, ...]
    instantiated_defaults: tuple[str, ...]


def totalize_call(
    arguments: Mapping[str, Any],
    field_semantics: Mapping[str, FieldDefault],
) -> TotalizedCall:
    """Produce the exact argument object that both guard and executor must use.

    Static defaults are instantiated before checking. Required, dynamic, hidden,
    or unknown fields fail closed instead of disappearing from the comparison.
    """

    unknown = sorted(set(arguments) - set(field_semantics))
    if unknown:
        return TotalizedCall(False, None, tuple(f"unknown_field:{field}" for field in unknown), ())

    output = copy.deepcopy(dict(arguments))
    reasons: list[str] = []
    instantiated: list[str] = []
    for field_name, semantics in field_semantics.items():
        if field_name in output:
            continue
        if semantics.required:
            reasons.append(f"required_field_missing:{field_name}")
        elif semantics.dynamic_default:
            reasons.append(f"dynamic_default_unresolved:{field_name}")
        elif semantics.static_default is _MISSING:
            reasons.append(f"default_semantics_unknown:{field_name}")
        else:
            output[field_name] = copy.deepcopy(semantics.static_default)
            instantiated.append(field_name)
    if reasons:
        return TotalizedCall(False, None, tuple(sorted(reasons)), tuple(sorted(instantiated)))
    return TotalizedCall(True, output, (), tuple(sorted(instantiated)))
