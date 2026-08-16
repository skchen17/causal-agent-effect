from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


DECISIONS = {"ALLOW", "DENY", "ABSTAIN"}
AUTHORIZATION_MATCHES = {"allowed", "denied", "uncertain", "missing"}
PROVENANCE_RISKS = {
    "trusted",
    "untrusted_data_control",
    "private_control",
    "unknown",
    "missing",
}

FORBIDDEN_DEPLOYABLE_KEYS = {
    "expected_decision",
    "gold_effect",
    "gold_resource",
    "gold_authorization_match",
    "gold_provenance_risk",
    "realized_effect",
    "authorized_effects",
    "authorized_resources",
    "risk_label",
    "counterfactual_axis",
    "pair_role",
    "semantic_pair_role",
    "same_effect_as_original",
    "effect_change_visible",
    "normalized_effect_label_visible",
    "effect_signature",
}


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def split_name(group: str) -> str:
    value = int(stable_hash(group)[:8], 16) % 10
    return "train" if value < 6 else "validation" if value < 8 else "test"


def contains_forbidden_key(value: Any) -> list[str]:
    found: set[str] = set()

    def visit(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, child in obj.items():
                if str(key) in FORBIDDEN_DEPLOYABLE_KEYS:
                    found.add(str(key))
                visit(child)
        elif isinstance(obj, list):
            for child in obj:
                visit(child)

    visit(value)
    return sorted(found)


@dataclass
class EffectBindingRow:
    case_id: str
    split_group_id: str
    counterfactual_group_id: str
    pair_role: str
    counterfactual_axis: str
    source_scope: str
    claim_scope: str
    audit_status: str
    deployable_input: dict[str, Any]
    labels: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        violations = contains_forbidden_key(self.deployable_input)
        if violations:
            raise ValueError(f"Forbidden deployable-input fields: {violations}")
        if self.labels.get("expected_decision") not in {"ALLOW", "DENY"}:
            raise ValueError(f"Invalid expected decision for {self.case_id}")
        if self.labels.get("gold_authorization_match") not in AUTHORIZATION_MATCHES:
            raise ValueError(f"Invalid authorization label for {self.case_id}")
        if self.labels.get("gold_provenance_risk") not in PROVENANCE_RISKS:
            raise ValueError(f"Invalid provenance label for {self.case_id}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "EffectBindingRow":
        return cls(**obj)


@dataclass
class TuplePrediction:
    case_id: str
    method: str
    source_scope: str
    split_group_id: str
    predicted_effect: str
    predicted_resource: str
    authorization_match: str
    provenance_risk: str
    decision: str
    confidence: float
    uncertainty: float
    abstain_reason: str
    accessed_fields: list[str]
    decision_inputs_hash: str
    claim_scope: str = "diagnostic"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.decision not in DECISIONS:
            raise ValueError(f"Invalid decision: {self.decision}")
        if self.authorization_match not in AUTHORIZATION_MATCHES:
            raise ValueError(f"Invalid authorization match: {self.authorization_match}")
        if self.provenance_risk not in PROVENANCE_RISKS:
            raise ValueError(f"Invalid provenance risk: {self.provenance_risk}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "TuplePrediction":
        return cls(**obj)
