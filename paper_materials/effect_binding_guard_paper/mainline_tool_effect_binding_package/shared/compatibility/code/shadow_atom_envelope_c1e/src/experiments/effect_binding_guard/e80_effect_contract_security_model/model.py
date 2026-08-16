"""A small executable model of the paper's conditional security argument."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


@dataclass(frozen=True, order=True)
class Atom:
    effect: str
    operation: str
    resource: str
    target: str
    commit_mode: str = "commit"


@dataclass(frozen=True)
class Envelope:
    allowed: tuple[Atom, ...]


@dataclass(frozen=True)
class Call:
    call_id: str
    actual_effects: tuple[Atom, ...]
    contracted_effects: tuple[Atom, ...] | None
    unresolved: bool = False


class Decision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class GuardResult:
    decision: Decision
    checked_call_id: str
    checked_effects: tuple[Atom, ...]
    committed_effects: tuple[Atom, ...]
    reason: str


def multiset_within(effects: Iterable[Atom], bound: Iterable[Atom]) -> bool:
    """Return whether every effect occurrence is covered by the bound."""
    return Counter(effects) <= Counter(bound)


def guard(call: Call, envelope: Envelope, *, executed_call_id: str | None = None) -> GuardResult:
    """Apply fail-closed pre-commit mediation to a finite call model."""
    if executed_call_id is not None and executed_call_id != call.call_id:
        return GuardResult(
            Decision.ABSTAIN,
            call.call_id,
            call.contracted_effects or (),
            (),
            "check_use_mismatch",
        )
    if call.contracted_effects is None:
        return GuardResult(Decision.ABSTAIN, call.call_id, (), (), "missing_contract")
    if call.unresolved:
        return GuardResult(
            Decision.ABSTAIN,
            call.call_id,
            call.contracted_effects,
            (),
            "unresolved_required_fact",
        )
    if not multiset_within(call.contracted_effects, envelope.allowed):
        return GuardResult(Decision.DENY, call.call_id, call.contracted_effects, (), "outside_envelope")
    return GuardResult(
        Decision.ALLOW,
        call.call_id,
        call.contracted_effects,
        call.actual_effects,
        "all_contracted_effects_authorized",
    )


def trajectory_prefixes(
    calls: Iterable[Call],
    envelope: Envelope,
    *,
    consume: bool = False,
) -> list[tuple[Atom, ...]]:
    """Return cumulative effects under reusable or consumable authority."""
    committed: list[Atom] = []
    residual = Counter(envelope.allowed)
    prefixes: list[tuple[Atom, ...]] = []
    for call in calls:
        current = Envelope(tuple(residual.elements())) if consume else envelope
        result = guard(call, current)
        committed.extend(result.committed_effects)
        if consume and result.decision == Decision.ALLOW:
            residual.subtract(Counter(result.committed_effects))
            residual = +residual
        prefixes.append(tuple(committed))
    return prefixes
