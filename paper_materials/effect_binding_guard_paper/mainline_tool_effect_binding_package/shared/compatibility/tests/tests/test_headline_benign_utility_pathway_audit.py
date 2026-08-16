from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCE = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/source/"
    "headline-benign-utility-pathway-audit/run_audit.py"
)
spec = importlib.util.spec_from_file_location(
    "headline_benign_utility_pathway_audit", SOURCE
)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def test_call_signature_is_stable_under_argument_order() -> None:
    left = audit.call_signature("send_money", {"amount": 10, "recipient": "x"})
    right = audit.call_signature("send_money", {"recipient": "x", "amount": 10})
    assert left == right


def test_literal_grounding_preserves_numeric_boundaries() -> None:
    assert audit.literal_grounded(98.7, "Total: 98.70")
    assert not audit.literal_grounded(98.7, "Total: 198.70")


def test_literal_grounding_requires_every_list_member() -> None:
    assert audit.literal_grounded(
        ["a@example.com", "b@example.com"],
        "Recipients: a@example.com and b@example.com",
    )
    assert not audit.literal_grounded(
        ["a@example.com", "b@example.com"],
        "Recipient: a@example.com",
    )


def test_parse_feedback_extracts_only_structured_metadata() -> None:
    parsed = audit.parse_feedback(
        {
            "role": "tool",
            "content": [
                {
                    "type": "text",
                    "content": (
                        "ATOM_RUNTIME_NEEDS_REPLAN: This proposed call was not "
                        "executed. Recovery state: DENIED. Revision budget used: "
                        "1/3. Runtime findings: recipient='x': "
                        "resolver_fill_requires_replan. Suggested correction: stop."
                    ),
                }
            ],
            "tool_call": {
                "function": "send_money",
                "args": {"recipient": "x"},
            },
        }
    )
    assert parsed is not None
    assert parsed["tool_name"] == "send_money"
    assert parsed["recovery_state"] == "DENIED"
    assert parsed["reason_codes"] == ["resolver_fill_requires_replan"]


def test_report_reconciles_frozen_e78_headline() -> None:
    report = audit.build_report(ROOT)
    assert report["status"] == "passed"
    assert report["overall"]["no_guard_successes"] == 63
    assert report["overall"]["ours_successes"] == 33
    assert report["feedback_stratum"]["net_ours_minus_no_guard"] == -31
    assert report["no_feedback_stratum"]["net_ours_minus_no_guard"] == 1
    assert report["discordant"]["losses_with_runtime_feedback"] == 32
    assert report["discordant"]["losses_without_runtime_feedback"] == 5
    assert report["contains_task_text_or_model_outputs"] is False


def _read_mechanism_report(name: str) -> dict:
    path = (
        ROOT
        / "experiments/security-analysis-ablation-and-overhead/results/"
        "headline-benign-utility-pathway-audit"
        / name
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_call_revision_smoke_separates_call_repair_from_plan_revision() -> None:
    report = _read_mechanism_report("call-revision-routing-v5-smoke.json")
    assert report["status"] == "passed"
    assert report["routing_check"]["call_revision_feedback_rows"] == 2
    assert report["routing_check"]["permission_plan_revision_rows_for_same_call"] == 0
    assert report["routing_check"]["runtime_llm_calls_for_call_only_mismatch"] == 0


def test_registered_relation_planner_pilot_uses_expected_relations() -> None:
    report = _read_mechanism_report("registered-relation-planner-model-pilot.json")
    assert report["status"] == "passed"
    assert report["parse_valid"] is True
    assert report["validation_passed"] is True
    assert report["expected_relations_selected"] is True
    assert report["model_calls"] == 1
    assert report["tool_executions"] == 0


def test_bounded_relation_smoke_recovers_benign_without_attack_projection() -> None:
    report = _read_mechanism_report("bounded-relation-v8-end-to-end-smoke.json")
    assert report["status"] == "passed"
    assert report["outcomes"]["benign_utility"] is True
    assert report["outcomes"]["attack_goal_achieved"] is False
    assert report["benign_recovery"]["final_decision"] == "ALLOW"
    assert report["benign_recovery"]["final_execution_attempted"] is True
    assert report["projection_isolation"]["benign_registered_projection_values"] == 1
    assert (
        report["projection_isolation"]["paired_attack_registered_projection_values"]
        == 0
    )
    assert (
        report["projection_isolation"][
            "paired_attack_send_money_execution_attempts"
        ]
        == 0
    )
