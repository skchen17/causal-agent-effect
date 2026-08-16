from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal


Decision = Literal["ALLOW", "DENY", "ABSTAIN"]
ProposalMode = Literal["stub", "llm", "local_llm"]
ExpectedRelation = Literal["invariant", "sensitive"]

DECISIONS = {"ALLOW", "DENY", "ABSTAIN"}


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def as_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if isinstance(value, tuple):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    domain: str
    description: str
    parameter_schema: dict[str, Any]
    example_safe_call: dict[str, Any]
    example_unsafe_call: dict[str, Any]
    example_unknown_call: dict[str, Any]
    expected_side_effects: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AtomFieldBinding:
    source_field: str
    atom_field: str
    required: bool = True
    repeated: bool = False
    canonicalize: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EffectTemplate:
    effect_type: str
    operation: str
    resource_field: str
    resource_type: str
    field_bindings: tuple[AtomFieldBinding, ...] = ()
    target_principal_field: str | None = None
    target_role: str | None = None
    target_as_resource: bool = False
    target_resource_type: str = "recipient"
    visibility_field: str | None = None
    permission_delta_field: str | None = None
    commit_mode_field: str | None = "commit_mode"
    default_commit_mode: str = "commit"
    control_source_field: str = "control_source"
    provenance_source_field: str = "provenance_source"
    evidence_ref_field: str | None = None
    security_relevant_fields: tuple[str, ...] = ()
    emit_if_field: str | None = None
    emit_if_values: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolEffectContract:
    tool_name: str
    proposal_mode: ProposalMode
    templates: tuple[EffectTemplate, ...]
    non_security_fields: tuple[str, ...] = ()
    requires_human_review: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def contract_hash(self) -> str:
        return stable_hash(self.to_dict())

    def with_templates(self, templates: list[EffectTemplate], **updates: Any) -> "ToolEffectContract":
        return replace(self, templates=tuple(templates), **updates)


@dataclass(frozen=True)
class EffectAtom:
    effect_type: str
    operation: str
    resource_id: str
    resource_type: str
    target_principal: str | None = None
    target_role: str | None = None
    visibility: str | None = None
    permission_delta: str | None = None
    commit_mode: str = "commit"
    control_source: str = "user"
    provenance_source: str = "user"
    evidence_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def signature(self) -> tuple[Any, ...]:
        return (
            self.effect_type,
            self.operation,
            self.resource_id,
            self.resource_type,
            self.target_principal,
            self.target_role,
            self.visibility,
            self.permission_delta,
            self.commit_mode,
            self.control_source,
            self.provenance_source,
            self.evidence_ref,
        )


@dataclass(frozen=True)
class AuthorizationContext:
    context_id: str
    allowed_effects: tuple[str, ...]
    allowed_operations: tuple[str, ...]
    allowed_resource_ids: tuple[str, ...] = ()
    allowed_resource_aliases: dict[str, str] = field(default_factory=dict)
    allowed_recipients: tuple[str, ...] = ()
    allowed_accounts: tuple[str, ...] = ()
    allowed_channels: tuple[str, ...] = ()
    allowed_files: tuple[str, ...] = ()
    allowed_visibility: tuple[str, ...] = ("private", "internal")
    draft_allowed: bool = True
    commit_allowed: bool = True
    public_link_allowed: bool = False
    external_recipient_allowed: bool = False
    trusted_control_sources: tuple[str, ...] = ("user", "system")
    untrusted_control_sources: tuple[str, ...] = ("tool_output", "web_content", "untrusted_observation")
    private_data_sources: tuple[str, ...] = ()
    multi_resource_policy: str = "all_resources_must_be_authorized"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CounterfactualCase:
    case_id: str
    tool_name: str
    axis: str
    base_call: dict[str, Any]
    mutated_call: dict[str, Any]
    authz_context: AuthorizationContext
    expected_base_decision: Decision
    expected_mutated_decision: Decision
    expected_atom_change: bool
    expected_decision_change: bool
    expected_relation: ExpectedRelation = "sensitive"
    expected_changed_fields: tuple[str, ...] = ()
    expected_base_atoms: tuple[dict[str, Any], ...] = ()
    expected_mutated_atoms: tuple[dict[str, Any], ...] = ()
    expected_violation_reasons: tuple[str, ...] = ()
    surface_invariant: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        for value in (self.expected_base_decision, self.expected_mutated_decision):
            if value not in DECISIONS:
                raise ValueError(f"Invalid decision: {value}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationResult:
    tool_name: str
    n_cases: int
    field_sensitivity_accuracy: float
    surface_invariance_accuracy: float
    unsafe_pre_allow_rate: float
    false_deny_rate: float
    coverage: float
    atom_coverage: float
    expected_decision_agreement: float
    required_atom_coverage: float
    required_resource_binding_coverage: float
    required_target_principal_coverage: float
    missing_atom_count: int
    missing_required_atom_count: int
    over_sensitive_field_count: int
    decision_accuracy: float
    passed: bool
    failures: tuple[dict[str, Any], ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FrozenContract:
    tool_name: str
    contract: ToolEffectContract
    contract_hash: str
    validation_summary: dict[str, Any]
    frozen_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
