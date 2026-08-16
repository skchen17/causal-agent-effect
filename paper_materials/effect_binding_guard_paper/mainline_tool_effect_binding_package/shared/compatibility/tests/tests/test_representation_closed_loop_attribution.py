from __future__ import annotations

import importlib.util
from pathlib import Path

from src.experiments.effect_binding_guard.representation_closed_loop_attribution.semantics import (
    tool_call_level_compare,
)


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/run_representation_closed_loop_attribution.py"


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "representation_closed_loop_attribution_runner", RUNNER
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_call_comparator_uses_only_tool_membership():
    descriptor = {"tool_name": "send_email", "side_effectful": True}
    plan = {
        "tools": {
            "send_email": {
                "fields": {
                    "recipients": {
                        "mode": "exact",
                        "values": ["authorized@example.com"],
                    }
                }
            }
        }
    }
    allowed = tool_call_level_compare(
        "email the authorized recipient",
        descriptor,
        plan,
        {"recipients": ["different@example.com"]},
        [],
    )
    denied = tool_call_level_compare(
        "email the authorized recipient",
        {"tool_name": "share_file", "side_effectful": True},
        plan,
        {"file_id": "1"},
        [],
    )

    assert allowed == {
        "decision": "ALLOW",
        "reasons": ["tool_identity_present_in_initial_permission_plan"],
        "checks": [],
    }
    assert denied["decision"] == "NEEDS_REPLAN"
    assert denied["reasons"] == ["tool_not_in_initial_permission_plan"]


def test_manifest_selects_exercised_cases_and_effectful_controls():
    runner = load_runner()
    source = runner.source_case_rows()
    assert len(source) == 726
    assert all(row["user_task_id"].startswith("user_task_") for row in source)
    assert any(row["field_mismatch_feedback"] for row in source)
    assert all(
        hit["statuses"]
        for row in source
        for hit in row["field_mismatch_feedback"]
    )


def test_batching_does_not_create_attack_cross_products():
    runner = load_runner()
    cases = [
        {
            "case_key": "workspace:user_task_1:important_instructions:injection_task_1",
            "suite": "workspace",
            "mode": "attack",
            "user_task_id": "user_task_1",
            "injection_task_id": "injection_task_1",
        },
        {
            "case_key": "workspace:user_task_2:important_instructions:injection_task_1",
            "suite": "workspace",
            "mode": "attack",
            "user_task_id": "user_task_2",
            "injection_task_id": "injection_task_1",
        },
        {
            "case_key": "workspace:user_task_1:important_instructions:injection_task_2",
            "suite": "workspace",
            "mode": "attack",
            "user_task_id": "user_task_1",
            "injection_task_id": "injection_task_2",
        },
    ]
    batches = runner.batch_rows(cases)
    assert len(batches) == 2
    assert {batch["injection_task_id"] for batch in batches} == {
        "injection_task_1",
        "injection_task_2",
    }
    assert sum(len(batch["case_keys"]) for batch in batches) == len(cases)


def test_manifest_build_is_deterministic(tmp_path, monkeypatch):
    runner = load_runner()
    monkeypatch.setattr(runner, "EVALUATION_DIR", tmp_path)
    monkeypatch.setattr(runner, "CASE_MANIFEST", tmp_path / "cases.jsonl")
    monkeypatch.setattr(runner, "MANIFEST_REPORT", tmp_path / "manifest.json")

    first = runner.build_case_manifest(controls_per_stratum=1)
    first_cases = runner.CASE_MANIFEST.read_text(encoding="utf-8")
    second = runner.build_case_manifest(controls_per_stratum=1)
    second_cases = runner.CASE_MANIFEST.read_text(encoding="utf-8")

    assert first == second
    assert first_cases == second_cases
    assert first["selection"]["field_mismatch_exercised"] > 0
    assert first["selection"]["effectful_no_mismatch_control"] > 0
