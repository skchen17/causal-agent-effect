from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiments.tool_effect_fragmentation.schema import (  # noqa: E402
    AdapterStatus,
    Decision,
    GranularityLevel,
    PerturbationFamily,
    ToolEffectStressCase,
)


def _case() -> ToolEffectStressCase:
    return ToolEffectStressCase(
        case_id="c1",
        semantic_group_id="g1",
        source_system="unit",
        source_case_id="orig",
        granularity=GranularityLevel.STEP_INVOCATION.value,
        perturbation_type=PerturbationFamily.ORIGINAL.value,
        user_task="Send a message.",
        tool_inventory=[{"name": "send_email"}],
        tool_call_or_plan={"tool_name": "send_email", "arguments": {"recipient": "a@example.com"}},
        realized_effect="message_sent",
        resource="a@example.com",
        risk_label="unsafe",
        expected_decision=Decision.DENY.value,
        surface_seen_status="seen",
        trace_view="full_labels",
        adapter_status=AdapterStatus.PROXY_DIAGNOSTIC.value,
        paper_grade_eligible=False,
    )


def test_schema_roundtrip() -> None:
    row = _case().to_dict()
    parsed = ToolEffectStressCase.from_dict(row)

    assert parsed.case_id == "c1"
    assert parsed.realized_effect == "message_sent"


def test_schema_rejects_invalid_enum() -> None:
    row = _case().to_dict()
    row["granularity"] = "bad"

    with pytest.raises(ValueError):
        ToolEffectStressCase.from_dict(row)


def test_schema_requires_core_fields() -> None:
    row = _case().to_dict()
    del row["realized_effect"]

    with pytest.raises(ValueError):
        ToolEffectStressCase.from_dict(row)

