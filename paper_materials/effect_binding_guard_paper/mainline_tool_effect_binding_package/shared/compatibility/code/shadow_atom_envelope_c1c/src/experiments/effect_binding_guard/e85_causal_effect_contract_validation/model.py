"""Typed objects for counterfactual effect-contract validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True, order=True)
class ConcreteEffect:
    kind: str
    operation: str
    resource: str
    target: str
    visibility: str
    commit_mode: str
    provenance: str
    control_source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, order=True)
class EffectAtom:
    effect: str
    operation: str
    resource: str
    target: str
    visibility: str
    commit_mode: str
    provenance: str
    control_source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class InterventionCase:
    case_id: str
    axis: str
    base_args: Mapping[str, Any]
    mutated_args: Mapping[str, Any]
    intervention_fields: tuple[str, ...]
    negative_control: bool = False

