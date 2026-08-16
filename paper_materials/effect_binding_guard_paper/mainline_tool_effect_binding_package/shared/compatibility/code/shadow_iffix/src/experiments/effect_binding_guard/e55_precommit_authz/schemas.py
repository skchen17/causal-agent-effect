from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Decision = Literal["ALLOW", "DENY", "ABSTAIN"]
Domain = Literal["email", "calendar", "file", "slack", "transaction"]
MultiResourcePolicy = Literal["all_resources_must_be_authorized", "any_resource_allowed", "domain_specific"]

DECISIONS = {"ALLOW", "DENY", "ABSTAIN"}


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthorizationContext:
    task_id: str
    allowed_effects: tuple[str, ...]
    allowed_operations: tuple[str, ...]
    allowed_resource_ids: tuple[str, ...]
    allowed_resource_aliases: dict[str, str]
    allowed_recipients: tuple[str, ...]
    allowed_accounts: tuple[str, ...]
    allowed_channels: tuple[str, ...]
    allowed_files: tuple[str, ...]
    allowed_visibility: tuple[str, ...]
    draft_allowed: bool
    commit_allowed: bool
    public_link_allowed: bool
    external_recipient_allowed: bool
    multi_resource_policy: MultiResourcePolicy
    trusted_control_sources: tuple[str, ...]
    untrusted_control_sources: tuple[str, ...]
    private_data_sources: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "AuthorizationContext":
        return cls(
            task_id=str(obj["task_id"]),
            allowed_effects=tuple(obj.get("allowed_effects", [])),
            allowed_operations=tuple(obj.get("allowed_operations", [])),
            allowed_resource_ids=tuple(obj.get("allowed_resource_ids", [])),
            allowed_resource_aliases=dict(obj.get("allowed_resource_aliases", {})),
            allowed_recipients=tuple(obj.get("allowed_recipients", [])),
            allowed_accounts=tuple(obj.get("allowed_accounts", [])),
            allowed_channels=tuple(obj.get("allowed_channels", [])),
            allowed_files=tuple(obj.get("allowed_files", [])),
            allowed_visibility=tuple(obj.get("allowed_visibility", [])),
            draft_allowed=bool(obj.get("draft_allowed", False)),
            commit_allowed=bool(obj.get("commit_allowed", False)),
            public_link_allowed=bool(obj.get("public_link_allowed", False)),
            external_recipient_allowed=bool(obj.get("external_recipient_allowed", False)),
            multi_resource_policy=obj.get("multi_resource_policy", "all_resources_must_be_authorized"),
            trusted_control_sources=tuple(obj.get("trusted_control_sources", [])),
            untrusted_control_sources=tuple(obj.get("untrusted_control_sources", [])),
            private_data_sources=tuple(obj.get("private_data_sources", [])),
        )


@dataclass(frozen=True)
class EffectAtom:
    effect: str
    operation: str
    resource_id: str
    resource_type: str
    resource_aliases: tuple[str, ...] = ()
    visibility: str | None = None
    recipient_role: str | None = None
    commit_mode: str = "commit"
    provenance_source: str = "user"
    control_source: str = "user"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "EffectAtom":
        return cls(
            effect=str(obj.get("effect", "unknown")),
            operation=str(obj.get("operation", "unknown")),
            resource_id=str(obj.get("resource_id", "unknown")),
            resource_type=str(obj.get("resource_type", "unknown")),
            resource_aliases=tuple(obj.get("resource_aliases", [])),
            visibility=obj.get("visibility"),
            recipient_role=obj.get("recipient_role"),
            commit_mode=str(obj.get("commit_mode", "commit")),
            provenance_source=str(obj.get("provenance_source", "user")),
            control_source=str(obj.get("control_source", "user")),
        )

    def signature(self) -> tuple[str, str, str, str, str | None, str | None, str]:
        return (
            self.effect,
            self.operation,
            self.resource_id,
            self.resource_type,
            self.visibility,
            self.recipient_role,
            self.commit_mode,
        )


@dataclass(frozen=True)
class E55Case:
    case_id: str
    domain: Domain
    task: str
    authorization_context: AuthorizationContext
    tool_name: str
    tool_args: dict[str, Any]
    candidate_action_summary: str
    non_oracle_views: dict[str, Any]
    provenance_summary: dict[str, Any]
    expanded_atoms: tuple[EffectAtom, ...]
    expected_decision: Decision
    violation_reasons: tuple[str, ...]
    pair_group: str
    counterfactual_axis: str
    label_hidden_input: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.expected_decision not in DECISIONS:
            raise ValueError(f"Invalid expected decision: {self.expected_decision}")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["authorization_context"] = self.authorization_context.to_dict()
        payload["expanded_atoms"] = [atom.to_dict() for atom in self.expanded_atoms]
        return payload

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "E55Case":
        return cls(
            case_id=str(obj["case_id"]),
            domain=obj["domain"],
            task=str(obj["task"]),
            authorization_context=AuthorizationContext.from_dict(obj["authorization_context"]),
            tool_name=str(obj["tool_name"]),
            tool_args=dict(obj.get("tool_args", {})),
            candidate_action_summary=str(obj.get("candidate_action_summary", "")),
            non_oracle_views=dict(obj.get("non_oracle_views", {})),
            provenance_summary=dict(obj.get("provenance_summary", {})),
            expanded_atoms=tuple(EffectAtom.from_dict(atom) for atom in obj.get("expanded_atoms", [])),
            expected_decision=obj["expected_decision"],
            violation_reasons=tuple(obj.get("violation_reasons", [])),
            pair_group=str(obj["pair_group"]),
            counterfactual_axis=str(obj["counterfactual_axis"]),
            label_hidden_input=dict(obj["label_hidden_input"]),
            metadata=dict(obj.get("metadata", {})),
        )


@dataclass(frozen=True)
class DeployableE55Input:
    case_id: str
    domain: Domain
    pair_group: str
    label_hidden_input: dict[str, Any]

    @classmethod
    def from_case(cls, case: E55Case) -> "DeployableE55Input":
        return cls(
            case_id=case.case_id,
            domain=case.domain,
            pair_group=case.pair_group,
            label_hidden_input=json.loads(json.dumps(case.label_hidden_input, ensure_ascii=False)),
        )


@dataclass(frozen=True)
class E55Prediction:
    case_id: str
    method: str
    domain: str
    pair_group: str
    decision: Decision
    predicted_atoms: tuple[EffectAtom, ...]
    atom_authorization: tuple[dict[str, Any], ...]
    confidence: float
    abstain_reason: str
    violation_reasons: tuple[str, ...]
    accessed_fields: tuple[str, ...]
    decision_inputs_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.decision not in DECISIONS:
            raise ValueError(f"Invalid decision: {self.decision}")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["predicted_atoms"] = [atom.to_dict() for atom in self.predicted_atoms]
        return payload

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "E55Prediction":
        return cls(
            case_id=str(obj["case_id"]),
            method=str(obj["method"]),
            domain=str(obj["domain"]),
            pair_group=str(obj["pair_group"]),
            decision=obj["decision"],
            predicted_atoms=tuple(EffectAtom.from_dict(atom) for atom in obj.get("predicted_atoms", [])),
            atom_authorization=tuple(dict(item) for item in obj.get("atom_authorization", [])),
            confidence=float(obj.get("confidence", 0.0)),
            abstain_reason=str(obj.get("abstain_reason", "")),
            violation_reasons=tuple(obj.get("violation_reasons", [])),
            accessed_fields=tuple(obj.get("accessed_fields", [])),
            decision_inputs_hash=str(obj.get("decision_inputs_hash", "")),
            metadata=dict(obj.get("metadata", {})),
        )
