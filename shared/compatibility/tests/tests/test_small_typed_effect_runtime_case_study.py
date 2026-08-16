from __future__ import annotations

import ast
from pathlib import Path

from shared.compatibility.scripts.independent_authority_benchmark.specs import descriptor_candidates
from shared.compatibility.scripts.small_typed_effect_runtime_case_study.cases import generate_cases
from shared.compatibility.scripts.small_typed_effect_runtime_case_study.local_llm import build_prompt, parse_call
from shared.compatibility.scripts.small_typed_effect_runtime_case_study.runtime_engine import evaluate


ROOT = Path(__file__).resolve().parents[4]


def descriptors():
    return {item["tool_name"]: item for item in descriptor_candidates()["descriptors"]}


def test_case_manifest_has_six_scenarios_and_thirty_rows():
    cases = generate_cases()
    assert len(cases) == 30
    assert len({item["case_id"] for item in cases}) == 30
    assert len({item["scenario"] for item in cases}) == 6


def test_runtime_engine_has_no_llm_dependency():
    path = ROOT / "shared/compatibility/scripts/small_typed_effect_runtime_case_study/runtime_engine.py"
    tree = ast.parse(path.read_text())
    imported = " ".join((node.module or "") for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
    assert "local_llm" not in imported


def test_strict_parser_accepts_only_call_schema():
    assert parse_call('<think>discard</think>{"tool_name":"x","arguments":{}}')["tool_name"] == "x"
    try:
        parse_call('{"tool_name":"x","arguments":{},"decision":"ALLOW"}')
    except ValueError:
        pass
    else:
        raise AssertionError("extra decision field must fail")


def test_authorized_call_is_checked_executed_and_reconciled():
    case = generate_cases()[0]
    proposed = {"tool_name": "schedule_meeting", "arguments": {
        "calendar_ref": "calendar:team", "event_id": "evt-a", "title": "Review",
        "participants": ["alice@example.com"], "visibility": "private", "recurrence": "none",
    }}
    row = evaluate(case, proposed, descriptors()["schedule_meeting"])
    assert row["decision"] == "ALLOW"
    assert row["checked_call"] == row["executed_call"]
    assert row["reconciliation_passed"] is True


def test_unauthorized_call_does_not_execute():
    case = generate_cases()[5]
    proposed = {"tool_name": "schedule_meeting", "arguments": {
        "calendar_ref": "calendar:team", "event_id": "evt-c", "title": "External",
        "participants": ["eve@example.com"], "visibility": "private", "recurrence": "none",
    }}
    row = evaluate(case, proposed, descriptors()["schedule_meeting"])
    assert row["decision"] == "DENY"
    assert row["executed_call"] is None
    assert row["post_state"] == row["pre_state"]


def test_integral_amount_reconciles_with_float_source_value():
    case = generate_cases()[21]
    proposed = {"tool_name": "transfer_funds", "arguments": {
        "account_ref": "primary", "payee_ref": "vendor", "amount": 100, "currency": "USD",
    }}
    row = evaluate(case, proposed, descriptors()["transfer_funds"])
    assert row["decision"] == "ALLOW"
    assert row["reconciliation_passed"] is True


def test_prompt_does_not_request_authority_decision():
    case = generate_cases()[0]
    prompt = build_prompt(case, {"required": ["calendar_ref"], "optional": [], "constraints": "calendar_ref is calendar:team"})
    assert "decision" not in prompt.lower()
    assert "gold" not in prompt.lower()
