from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiments.tool_effect_fragmentation.adapters import build_system_cases, run_baselines  # noqa: E402
from src.experiments.tool_effect_fragmentation.schema import AdapterStatus  # noqa: E402


def test_agentdojo_adapter_smoke_has_paper_grade_cases() -> None:
    cases, manifest = build_system_cases("agentdojo", ROOT, max_base_cases=4)

    assert manifest.adapter_status == AdapterStatus.PAPER_GRADE.value
    assert manifest.paper_grade_eligible is True
    assert len(cases) >= 20
    assert any(case.granularity == "step_invocation" for case in cases)


def test_toolsafe_proxy_adapter_marks_not_paper_grade() -> None:
    cases, manifest = build_system_cases("toolsafe", ROOT, max_base_cases=3)

    assert manifest.adapter_status == AdapterStatus.PROXY_DIAGNOSTIC.value
    assert manifest.paper_grade_eligible is False
    assert len(cases) >= 20
    assert all(case.paper_grade_eligible is False for case in cases)


def test_ipiguard_proxy_adapter_has_graph_cases() -> None:
    cases, manifest = build_system_cases("ipiguard", ROOT, max_base_cases=2)

    assert manifest.adapter_status == AdapterStatus.PROXY_DIAGNOSTIC.value
    assert len(cases) >= 10
    assert any(case.granularity == "tool_dependency_graph" for case in cases)


def test_safiron_proxy_adapter_has_plan_cases() -> None:
    cases, manifest = build_system_cases("safiron", ROOT, max_base_cases=2)

    assert manifest.adapter_status == AdapterStatus.PROXY_DIAGNOSTIC.value
    assert manifest.paper_grade_eligible is False
    assert len(cases) >= 10
    assert any(case.granularity == "pre_execution_plan" for case in cases)


def test_camel_adapter_failure_is_explicit() -> None:
    cases, manifest = build_system_cases("camel", ROOT, max_base_cases=2)

    assert cases == []
    assert manifest.adapter_status == AdapterStatus.ADAPTER_FAILED.value
    assert manifest.paper_grade_eligible is False
    assert manifest.source_repo_url


def test_baselines_produce_predictions_for_each_case() -> None:
    cases, _ = build_system_cases("toolsafe", ROOT, max_base_cases=2)
    preds = run_baselines(cases)
    methods = {pred.method_name for pred in preds}

    assert len(preds) == len(cases) * len(methods)
    assert "tool_name_classifier" in methods
    assert "execution_evidence_upper_bound" in methods
