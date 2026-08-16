from __future__ import annotations

import json

from src.experiments.effect_binding_guard.e68_llm_counterfactual_atom_field_stress.run_e68 import load_external_cases
from src.experiments.effect_binding_guard.e69_counterfactually_selected_atomized_contracts.run_e69 import build_tool_views
from src.experiments.effect_binding_guard.e72_task_permission_envelope_runtime_guard.run_e72 import (
    build_fixed_tool_descriptors,
    compare_actual_to_envelope,
    extract_actual_permission_checks,
    norm,
    parse_task_envelope,
    prompt_text_leakage_scan,
    run_runtime_guard,
    task_permission_prompt,
)


def valid_envelope(tool_name: str = "delete_file", field: str = "file_id", value: str = "11") -> dict:
    return {
        "parse_valid": True,
        "allowed_tool_envelopes": [
            {
                "tool_name": tool_name,
                "allowed_parameter_values": {field: [value]},
                "allowed_commit_modes": ["commit", "schedule"],
                "allowed_visibility": ["private", "team"],
                "trusted_control_sources": ["user", "system_policy"],
                "notes": "needed by task",
            }
        ],
        "missing_information": [],
    }


def test_task_permission_prompt_has_no_hidden_evidence() -> None:
    cases = load_external_cases(limit=5)
    descriptors = build_fixed_tool_descriptors(cases, build_tool_views(cases))
    descriptor = descriptors[0]
    case = next(case for case in cases if case["domain"] == descriptor["domain"] and case["visible"]["tool_call"]["tool"] == descriptor["tool_name"])
    messages = task_permission_prompt(case, descriptor)
    scan = prompt_text_leakage_scan(messages)
    assert scan["leakage_free"], scan["hits"]
    text = json.dumps(messages)
    assert "gold_atoms" not in text
    assert "expected_decision" not in text
    assert "violation_reasons" not in text


def test_parser_accepts_envelope_and_rejects_decision() -> None:
    raw = {
        "task_goal": "delete requested file",
        "allowed_tool_envelopes": [
            {
                "tool_name": "delete_file",
                "allowed_parameter_values": {"file_id": ["11"]},
                "allowed_commit_modes": ["commit"],
                "allowed_visibility": ["private"],
                "trusted_control_sources": ["user"],
                "notes": "user requested it",
            }
        ],
        "missing_information": [],
    }
    parsed = parse_task_envelope(json.dumps(raw))
    assert parsed.parse_valid
    assert parsed.allowed_tool_envelopes[0]["allowed_parameter_values"]["file_id"] == ["11"]

    raw["decision"] = "ALLOW"
    parsed = parse_task_envelope(json.dumps(raw))
    assert not parsed.parse_valid


def test_fixed_descriptors_use_canonical_policy_effects() -> None:
    cases = load_external_cases(limit=20)
    descriptors = build_fixed_tool_descriptors(cases, build_tool_views(cases))
    effects = {row["canonical_effect"] for row in descriptors}
    assert "calendar_event_modified" in effects
    assert "create" not in effects
    assert all("security_parameter_fields" in row for row in descriptors)


def test_actual_tool_call_inside_envelope_allows() -> None:
    case = next(case for case in load_external_cases(limit=20) if case["visible"]["tool_call"]["tool"] == "delete_file")
    descriptors = build_fixed_tool_descriptors([case], build_tool_views([case]))
    descriptor = descriptors[0]
    checks = extract_actual_permission_checks(case, descriptor)
    assert checks
    decision, reasons = compare_actual_to_envelope(checks, descriptor, valid_envelope("delete_file", "file_id", checks[0]["value"]), case["visible"]["runtime_evidence"])
    assert decision == "ALLOW", reasons


def test_actual_tool_call_outside_envelope_denies() -> None:
    case = next(case for case in load_external_cases(limit=20) if case["visible"]["tool_call"]["tool"] == "delete_file")
    descriptors = build_fixed_tool_descriptors([case], build_tool_views([case]))
    descriptor = descriptors[0]
    checks = extract_actual_permission_checks(case, descriptor)
    decision, reasons = compare_actual_to_envelope(checks, descriptor, valid_envelope("delete_file", "file_id", "different-file"), case["visible"]["runtime_evidence"])
    assert decision == "DENY"
    assert any(reason.startswith("field_value_outside_task_envelope") for reason in reasons)


def test_iso_time_normalization_and_symbolic_permissions() -> None:
    assert norm("2024-05-19T17:00:00Z") == norm("2024-05-19 17:00:00")
    descriptor = {
        "tool_name": "delete_file",
        "default_commit_mode": "commit",
        "default_visibility": "private",
    }
    checks = [{"field": "file_id", "kind": "resource", "value": "11", "canonical_value": norm("11")}]
    envelope = valid_envelope("delete_file", "file_id", "any valid file ID from the drive")
    decision, reasons = compare_actual_to_envelope(checks, descriptor, envelope, {"control_source": "user"})
    assert decision == "ABSTAIN"
    assert "symbolic_permission_unresolved:file_id" in reasons


def test_missing_envelope_abstains() -> None:
    case = load_external_cases(limit=1)[0]
    descriptors = build_fixed_tool_descriptors([case], build_tool_views([case]))
    descriptor_map = {(row["domain"], row["tool_name"]): row for row in descriptors}
    runtime = run_runtime_guard([case], descriptor_map, [])
    metric = runtime["results"]["task_envelope_guard"]
    assert metric["abstain"]["successes"] == 1
    assert runtime["checks"][0]["check_result"] == "ABSTAIN"
