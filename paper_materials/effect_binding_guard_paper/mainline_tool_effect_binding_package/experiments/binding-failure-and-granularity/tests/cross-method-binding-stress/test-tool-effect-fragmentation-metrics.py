from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiments.tool_effect_fragmentation.metrics import confusion, fnr_from_confusion, summarize_method  # noqa: E402
from src.experiments.tool_effect_fragmentation.schema import (  # noqa: E402
    AdapterStatus,
    Decision,
    GranularityLevel,
    PerturbationFamily,
    ToolEffectPrediction,
    ToolEffectStressCase,
)


def _case(case_id: str, expected: str, action: str = "a1") -> ToolEffectStressCase:
    return ToolEffectStressCase(
        case_id=case_id,
        semantic_group_id=action,
        source_system="unit",
        source_case_id=case_id,
        granularity=GranularityLevel.STEP_INVOCATION.value,
        perturbation_type=PerturbationFamily.ORIGINAL.value,
        user_task="Task.",
        tool_inventory=[{"name": "tool"}],
        tool_call_or_plan={"tool_name": "tool"},
        realized_effect="message_sent",
        resource="r",
        risk_label="unsafe" if expected == Decision.DENY.value else "safe",
        expected_decision=expected,
        surface_seen_status="seen",
        trace_view="full",
        adapter_status=AdapterStatus.PROXY_DIAGNOSTIC.value,
        paper_grade_eligible=False,
        action_id=action,
    )


def _pred(case_id: str, decision: str, action: str = "a1") -> ToolEffectPrediction:
    return ToolEffectPrediction(
        prediction_id=f"p_{case_id}",
        case_id=case_id,
        source_system="unit",
        method_name="m",
        predicted_decision=decision,
        predicted_effect="message_sent",
        predicted_risk_label="unsafe",
        action_id=action,
    )


def test_fnr_is_computed_from_confusion_matrix_not_f1() -> None:
    cases = [_case("c1", Decision.DENY.value), _case("c2", Decision.DENY.value), _case("c3", Decision.ALLOW.value)]
    preds = [_pred("c1", Decision.ALLOW.value), _pred("c2", Decision.DENY.value), _pred("c3", Decision.ALLOW.value)]

    conf = confusion(cases, preds)
    fnr = fnr_from_confusion(conf)

    assert conf["fn"] == 1
    assert conf["tp"] == 1
    assert fnr["rate"] == 0.5


def test_action_level_metrics_are_separate_from_row_fnr() -> None:
    cases = [
        _case("c1", Decision.DENY.value, action="a"),
        _case("c2", Decision.ALLOW.value, action="a"),
        _case("c3", Decision.ALLOW.value, action="a"),
    ]
    preds = [
        _pred("c1", Decision.DENY.value, action="a"),
        _pred("c2", Decision.ALLOW.value, action="a"),
        _pred("c3", Decision.ALLOW.value, action="a"),
    ]

    summary = summarize_method(cases, preds)

    assert summary["fnr"]["rate"] == 0.0
    assert summary["intra_action_decision_inconsistency"]["rate"] == 1.0
    assert summary["action_level_decision_error"]["rate"] == 0.0


def test_action_level_error_uses_deny_if_any_row_should_deny() -> None:
    cases = [
        _case("c1", Decision.DENY.value, action="a"),
        _case("c2", Decision.ALLOW.value, action="a"),
        _case("c3", Decision.ALLOW.value, action="b"),
    ]
    preds = [
        _pred("c1", Decision.ALLOW.value, action="a"),
        _pred("c2", Decision.ALLOW.value, action="a"),
        _pred("c3", Decision.DENY.value, action="b"),
    ]

    summary = summarize_method(cases, preds)

    assert summary["fnr"]["rate"] == 1.0
    assert summary["action_level_decision_error"]["successes"] == 2
    assert summary["action_level_decision_error"]["total"] == 2
