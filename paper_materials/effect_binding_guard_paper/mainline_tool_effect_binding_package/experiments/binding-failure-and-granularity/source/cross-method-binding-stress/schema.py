from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class PerturbationFamily(str, Enum):
    ORIGINAL = "original"
    SAME_EFFECT_TOOL_RENAME = "same_effect_tool_rename"
    SAME_EFFECT_ARG_SCHEMA_CHANGE = "same_effect_arg_schema_change"
    SAME_EFFECT_WRAPPER_TOOL = "same_effect_wrapper_tool"
    SAME_TOOL_DIFFERENT_EFFECT = "same_tool_different_effect"
    SAME_PLAN_DIFFERENT_PLANNER_FORMAT = "same_plan_different_planner_format"
    SAME_TRAJECTORY_DIFFERENT_TRACE_FORMAT = "same_trajectory_different_trace_format"
    HIDDEN_TRACE_LABELS = "hidden_trace_labels"
    TOOL_NAME_GRAPH_VS_EFFECT_RESOURCE_GRAPH = "tool_name_graph_vs_effect_resource_graph"
    AUTHORIZATION_CONTEXT_CHANGE = "authorization_context_change"
    AUTHORIZATION_RESOURCE_SHIFT = "authorization_resource_shift"
    RESOURCE_MISMATCH = "resource_mismatch"
    AUTHORIZED_NOOP_DRAFT = "authorized_noop_draft"
    TOOL_NAME_DEPENDENCY_GRAPH = "tool_name_dependency_graph"


class GranularityLevel(str, Enum):
    STATIC_INPUT = "static_input"
    PRE_EXECUTION_PLAN = "pre_execution_plan"
    STEP_INVOCATION = "step_invocation"
    MULTI_STEP_TRAJECTORY = "multi_step_trajectory"
    TOOL_DEPENDENCY_GRAPH = "tool_dependency_graph"
    PROVENANCE_EXECUTION_EVIDENCE = "provenance_execution_evidence"
    ACTION_LEVEL_POLICY = "action_level_policy"


class AdapterStatus(str, Enum):
    PAPER_GRADE = "paper_grade"
    PROXY_DIAGNOSTIC = "proxy_diagnostic"
    ADAPTER_FAILED = "adapter_failed"


class EffectLabelSource(str, Enum):
    ENV_DIFF = "env_diff"
    SANDBOX_GOLD = "sandbox_gold"
    PUBLISHED_LABEL = "published_label"
    RULE_PROXY = "rule_proxy"
    HUMAN_AUDIT = "human_audit"
    SEMANTIC_ORACLE = "semantic_oracle"
    EXECUTION_ORACLE = "execution_oracle"


class MethodInputView(str, Enum):
    TOOL_SURFACE_ONLY = "tool_surface_only"
    ARG_SCHEMA_ONLY = "arg_schema_only"
    STATIC_TEXT = "static_text"
    PLAN_TEXT = "plan_text"
    STEP_TEXT = "step_text"
    TRAJECTORY_TEXT = "trajectory_text"
    GRAPH_TOOL_NAME = "graph_tool_name"
    GRAPH_EFFECT_RESOURCE = "graph_effect_resource"
    EXECUTION_EVIDENCE = "execution_evidence"
    ORACLE_EFFECT_RESOURCE = "oracle_effect_resource"


class ClaimScope(str, Enum):
    ORIGINAL_METHOD = "original_method"
    ORIGINAL_METHOD_CUSTOM_STRESS = "original_method_custom_stress"
    ORIGINAL_PIPELINE_LOCAL_MODEL = "original_pipeline_local_model"
    ORIGINAL_PIPELINE_EXTERNAL_MODEL = "original_pipeline_external_model"
    ORIGINAL_COMPONENT_CUSTOM_STRESS = "original_component_custom_stress"
    PROXY_METHOD = "proxy_method"
    BASELINE = "baseline"
    UPPER_BOUND = "upper_bound"
    ADAPTER_FAILED = "adapter_failed"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"


REQUIRED_CASE_FIELDS = {
    "case_id",
    "semantic_group_id",
    "source_system",
    "source_case_id",
    "granularity",
    "perturbation_type",
    "user_task",
    "tool_inventory",
    "tool_call_or_plan",
    "realized_effect",
    "resource",
    "risk_label",
    "expected_decision",
    "surface_seen_status",
    "trace_view",
    "adapter_status",
    "paper_grade_eligible",
    "effect_label_source",
    "method_input_view",
    "source_repo_url",
    "source_commit_hash",
    "source_artifact_path",
    "official_method_reproduction",
    "custom_stress_protocol",
    "paper_grade_environment",
    "paper_grade_method",
    "claim_scope",
}


@dataclass
class ToolEffectStressCase:
    case_id: str
    semantic_group_id: str
    source_system: str
    source_case_id: str
    granularity: str
    perturbation_type: str
    user_task: str
    tool_inventory: list[dict[str, Any]]
    tool_call_or_plan: dict[str, Any]
    realized_effect: str
    resource: str
    risk_label: str
    expected_decision: str
    surface_seen_status: str
    trace_view: str
    adapter_status: str
    paper_grade_eligible: bool
    effect_label_source: str = EffectLabelSource.RULE_PROXY.value
    method_input_view: str = MethodInputView.STEP_TEXT.value
    source_repo_url: str = ""
    source_commit_hash: str = ""
    source_artifact_path: str = ""
    official_method_reproduction: bool = False
    custom_stress_protocol: bool = True
    paper_grade_environment: bool = False
    paper_grade_method: bool = False
    claim_scope: str = ClaimScope.PROXY_METHOD.value
    action_id: str | None = None
    counterfactual_group_id: str = ""
    pair_id: str = ""
    pair_role: str = ""
    counterfactual_axis: str = ""
    authorized_effects: list[str] = field(default_factory=list)
    authorized_resources: list[str] = field(default_factory=list)
    answerable_input_views: list[str] = field(default_factory=list)
    evidence_origin: str = "no_execution_evidence"
    construction_source: str = ""
    audit_status: str = "not_audited"
    labels: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_enum(self.granularity, GranularityLevel, "granularity")
        _validate_enum(self.perturbation_type, PerturbationFamily, "perturbation_type")
        _validate_enum(self.adapter_status, AdapterStatus, "adapter_status")
        _validate_enum(self.expected_decision, Decision, "expected_decision")
        _validate_enum(self.effect_label_source, EffectLabelSource, "effect_label_source")
        _validate_enum(self.method_input_view, MethodInputView, "method_input_view")
        _validate_enum(self.claim_scope, ClaimScope, "claim_scope")
        if self.adapter_status != AdapterStatus.PAPER_GRADE.value and (
            self.official_method_reproduction or self.paper_grade_method or self.claim_scope == ClaimScope.ORIGINAL_METHOD.value
        ):
            raise ValueError("Proxy/failed adapters cannot be marked as original paper methods")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "ToolEffectStressCase":
        missing = REQUIRED_CASE_FIELDS - set(obj)
        if missing:
            raise ValueError(f"Missing ToolEffectStressCase fields: {sorted(missing)}")
        return cls(**{k: obj[k] for k in cls.__dataclass_fields__ if k in obj})


@dataclass
class ToolEffectPrediction:
    prediction_id: str
    case_id: str
    source_system: str
    method_name: str
    predicted_decision: str
    predicted_effect: str
    predicted_risk_label: str
    confidence: float = 1.0
    abstained: bool = False
    method_input_view: str = MethodInputView.STEP_TEXT.value
    claim_scope: str = ClaimScope.BASELINE.value
    allowed_input_fields: list[str] = field(default_factory=list)
    accessed_input_fields: list[str] = field(default_factory=list)
    action_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_enum(self.predicted_decision, Decision, "predicted_decision")
        _validate_enum(self.method_input_view, MethodInputView, "method_input_view")
        _validate_enum(self.claim_scope, ClaimScope, "claim_scope")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "ToolEffectPrediction":
        return cls(**{k: obj[k] for k in cls.__dataclass_fields__ if k in obj})


@dataclass
class AdapterManifest:
    system_name: str
    adapter_status: str
    paper_grade_eligible: bool
    source_path: str
    source_version: str
    source_repo_url: str = ""
    source_commit_hash: str = ""
    source_artifact_path: str = ""
    official_method_reproduction: bool = False
    custom_stress_protocol: bool = True
    paper_grade_environment: bool = False
    paper_grade_method: bool = False
    notes: list[str] = field(default_factory=list)
    n_cases: int = 0
    supported_granularities: list[str] = field(default_factory=list)
    supported_perturbations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_enum(self.adapter_status, AdapterStatus, "adapter_status")
        if self.adapter_status != AdapterStatus.PAPER_GRADE.value and (
            self.official_method_reproduction or self.paper_grade_method
        ):
            raise ValueError("Proxy/failed manifests cannot be marked as official paper-grade method reproductions")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_enum(value: str, enum_type: type[Enum], field_name: str) -> None:
    valid = {item.value for item in enum_type}
    if value not in valid:
        raise ValueError(f"Invalid {field_name}={value!r}; valid={sorted(valid)}")
