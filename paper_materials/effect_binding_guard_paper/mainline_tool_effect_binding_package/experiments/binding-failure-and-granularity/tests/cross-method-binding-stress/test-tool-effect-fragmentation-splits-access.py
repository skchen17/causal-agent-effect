from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiments.tool_effect_fragmentation.access_guards import (  # noqa: E402
    audit_prediction_access,
    build_method_input,
    contains_forbidden_label_key,
)
from src.experiments.tool_effect_fragmentation.schema import (  # noqa: E402
    AdapterStatus,
    ClaimScope,
    Decision,
    GranularityLevel,
    MethodInputView,
    PerturbationFamily,
    ToolEffectPrediction,
    ToolEffectStressCase,
)
from src.experiments.tool_effect_fragmentation.splits import make_split  # noqa: E402


def _case(
    case_id: str,
    tool_name: str,
    expected: str = Decision.DENY.value,
    semantic_group_id: str = "g1",
    perturbation: str = PerturbationFamily.ORIGINAL.value,
) -> ToolEffectStressCase:
    return ToolEffectStressCase(
        case_id=case_id,
        semantic_group_id=semantic_group_id,
        source_system="unit",
        source_case_id=case_id,
        granularity=GranularityLevel.STEP_INVOCATION.value,
        perturbation_type=perturbation,
        user_task="Send a message.",
        tool_inventory=[{"name": tool_name, "description": "tool"}],
        tool_call_or_plan={
            "tool_name": tool_name,
            "arguments": {"recipient": "a@example.com"},
            "verified_effects": ["message_sent"],
            "nested": {"gold_label": "unsafe"},
        },
        realized_effect="message_sent",
        resource="a@example.com",
        risk_label="unsafe" if expected == Decision.DENY.value else "safe",
        expected_decision=expected,
        surface_seen_status="seen",
        trace_view="full",
        adapter_status=AdapterStatus.PROXY_DIAGNOSTIC.value,
        paper_grade_eligible=False,
    )


def _pred(view: str, claim_scope: str, accessed: list[str]) -> ToolEffectPrediction:
    return ToolEffectPrediction(
        prediction_id="p1",
        case_id="c1",
        source_system="unit",
        method_name="m",
        predicted_decision=Decision.DENY.value,
        predicted_effect="message_sent",
        predicted_risk_label="unsafe",
        method_input_view=view,
        claim_scope=claim_scope,
        accessed_input_fields=accessed,
    )


def test_held_out_tool_split_marks_surface_and_blocks_leakage() -> None:
    cases = [
        _case("c1", "send_email", semantic_group_id="g1"),
        _case("c2", "surface_alias_send_email", semantic_group_id="g1"),
        _case("c3", "write_file", semantic_group_id="g2"),
    ]

    split = make_split(cases, "held_out_tool", heldout_values=["surface_alias_send_email"])

    assert split.test_indices == [1]
    assert split.cases_with_status[1].surface_seen_status == "held_out_tool"
    assert split.leakage_report["heldout_tool_in_train"] == []


def test_held_out_semantic_group_reports_no_group_overlap() -> None:
    cases = [
        _case("c1", "send_email", semantic_group_id="g1"),
        _case("c2", "write_file", semantic_group_id="g2"),
        _case("c3", "delete_file", semantic_group_id="g3"),
    ]

    split = make_split(cases, "held_out_semantic_group", heldout_values=["g2"])

    assert split.test_indices == [1]
    assert split.leakage_report["semantic_group_overlap"] == []
    assert split.leakage_report["semantic_group_leakage"] is False


def test_method_input_strips_oracle_labels_recursively() -> None:
    method_input = build_method_input(_case("c1", "send_email"), MethodInputView.STEP_TEXT.value)

    assert not contains_forbidden_label_key(method_input)
    assert "verified_effects" not in method_input["tool_call_or_plan"]
    assert "gold_label" not in method_input["tool_call_or_plan"]["nested"]


def test_access_guard_rejects_oracle_fields_for_baseline() -> None:
    pred = _pred(
        MethodInputView.STEP_TEXT.value,
        ClaimScope.BASELINE.value,
        ["user_task", "tool_inventory", "realized_effect", "expected_decision"],
    )

    audit = audit_prediction_access(pred)

    assert not audit.allowed
    assert "realized_effect" in audit.violations
    assert "expected_decision" in audit.violations


def test_access_guard_allows_oracle_effect_resource_only_for_upper_bound() -> None:
    pred = _pred(
        MethodInputView.ORACLE_EFFECT_RESOURCE.value,
        ClaimScope.UPPER_BOUND.value,
        ["realized_effect", "resource", "risk_label", "expected_decision"],
    )

    audit = audit_prediction_access(pred)

    assert audit.allowed
    assert audit.violations == []
