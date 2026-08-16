from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CandidateScore:
    freezeable: bool
    parse_valid: bool
    unsafe_pre_allow_zero: bool
    required_atom_coverage: float
    required_resource_binding_coverage: float
    required_target_principal_coverage: float
    decision_accuracy: float
    false_deny_inverse: float
    round_priority: int

    def as_tuple(self) -> tuple[Any, ...]:
        return (
            int(self.freezeable),
            int(self.parse_valid),
            int(self.unsafe_pre_allow_zero),
            self.required_atom_coverage,
            self.required_resource_binding_coverage,
            self.required_target_principal_coverage,
            self.decision_accuracy,
            self.false_deny_inverse,
            self.round_priority,
        )


def score_candidate(row: dict[str, Any]) -> CandidateScore:
    return CandidateScore(
        freezeable=str(row.get("freezeable")) == "true",
        parse_valid=str(row.get("parse_valid")) == "true",
        unsafe_pre_allow_zero=float(row.get("unsafe_pre_allow_rate", 1.0) or 1.0) == 0.0,
        required_atom_coverage=float(row.get("required_atom_coverage", 0.0) or 0.0),
        required_resource_binding_coverage=float(row.get("required_resource_binding_coverage", 0.0) or 0.0),
        required_target_principal_coverage=float(row.get("required_target_principal_coverage", 0.0) or 0.0),
        decision_accuracy=float(row.get("decision_accuracy", 0.0) or 0.0),
        false_deny_inverse=1.0 - float(row.get("false_deny_rate", 1.0) or 1.0),
        round_priority=-int(row.get("round_index", 0) or 0),
    )


def select_best_candidate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("No candidate rows to select from")
    freezeable = [row for row in rows if row.get("freezeable") == "true"]
    if freezeable:
        return sorted(freezeable, key=lambda row: int(row.get("round_index", 0)))[0]
    return max(rows, key=lambda row: score_candidate(row).as_tuple())

