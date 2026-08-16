from __future__ import annotations

from src.experiments.effect_binding_guard.e68_llm_counterfactual_atom_field_stress.run_e68 import load_external_cases
from src.experiments.effect_binding_guard.e69_counterfactually_selected_atomized_contracts.run_e69 import build_tool_views
from src.experiments.effect_binding_guard.e72_task_permission_envelope_runtime_guard.run_e72 import (
    build_fixed_tool_descriptors,
    extract_actual_permission_checks,
)
from src.experiments.effect_binding_guard.e73_intent_binding_replan_runtime.run_e73 import (
    apply_agent_decision_to_runtime,
    attach_registered_tools_to_cases,
    build_agentdojo_environment_tool_registry,
    build_planned_bindings,
    case_with_revised_tool_call,
    classify_planned_binding,
    compare_plan_to_actual,
    is_symbolic_intent_value,
    llm_agent_decision_prompt,
    load_e72_envelopes,
    parse_llm_agent_decision,
    prompt_text_leakage_scan,
    replan_behavior_audit,
    run_replan_runtime,
    side_effect_candidate_prediction,
)


def test_symbolic_placeholders_are_pending_bindings() -> None:
    assert is_symbolic_intent_value("Sarah Baker's email address (to be retrieved)")
    assert is_symbolic_intent_value("<extracted from Introductory meeting>")
    assert classify_planned_binding("participants", ["<extracted from Introductory meeting>"], []) == "pending_resolution"


def test_exact_values_remain_exact_bindings() -> None:
    assert classify_planned_binding("file_id", ["11"], []) == "exact_values"


def test_pending_actual_value_needs_replan_not_deny() -> None:
    cases = load_external_cases(limit=10)
    case = next(row for row in cases if row["case_id"] == "e61_external_ipiguard_workspace_001")
    descriptors = build_fixed_tool_descriptors([case], build_tool_views([case]))
    descriptor = descriptors[0]
    envelope = {
        case["case_id"]: {
            "case_id": case["case_id"],
            "task_goal": "Create lunch with Sarah Baker",
            "allowed_tool_envelopes": [
                {
                    "tool_name": "create_calendar_event",
                    "allowed_parameter_values": {"participants": ["Sarah Baker's email address (to be retrieved)"], "start_time": ["2024-05-19 12:00:00"], "end_time": ["2024-05-19 13:00:00"]},
                    "allowed_commit_modes": ["commit"],
                    "allowed_visibility": ["private"],
                    "trusted_control_sources": ["user"],
                    "notes": "test",
                }
            ],
            "missing_information": ["Sarah Baker's email address"],
        }
    }
    plan = build_planned_bindings([case], {(case["domain"], "create_calendar_event"): descriptor}, envelope)[0]
    decision, reasons, feedback = compare_plan_to_actual(case, descriptor, plan, extract_actual_permission_checks(case, descriptor))
    assert decision == "NEEDS_REPLAN"
    assert any("pending_binding_filled_by_actual_value:participants" in reason for reason in reasons)
    assert any(item["field"] == "participants" for item in feedback)


def test_exact_mismatch_needs_replan_for_agent_decision() -> None:
    cases = load_external_cases(limit=10)
    case = next(row for row in cases if row["visible"]["tool_call"]["tool"] == "delete_file")
    descriptors = build_fixed_tool_descriptors([case], build_tool_views([case]))
    descriptor = descriptors[0]
    envelope = {
        case["case_id"]: {
            "case_id": case["case_id"],
            "task_goal": "Delete a different file",
            "allowed_tool_envelopes": [
                {
                    "tool_name": "delete_file",
                    "allowed_parameter_values": {"file_id": ["different-file"]},
                    "allowed_commit_modes": ["commit"],
                    "allowed_visibility": ["private"],
                    "trusted_control_sources": ["user"],
                    "notes": "test",
                }
            ],
            "missing_information": [],
        }
    }
    plan = build_planned_bindings([case], {(case["domain"], "delete_file"): descriptor}, envelope)[0]
    decision, reasons, feedback = compare_plan_to_actual(case, descriptor, plan, extract_actual_permission_checks(case, descriptor))
    assert decision == "NEEDS_REPLAN"
    assert any(reason.startswith("actual_value_outside_exact_plan") for reason in reasons)
    assert feedback


def test_full_runtime_records_replan_feedback() -> None:
    cases = load_external_cases(limit=5)
    descriptors = build_fixed_tool_descriptors(cases, build_tool_views(cases))
    descriptor_map = {(row["domain"], row["tool_name"]): row for row in descriptors}
    envelopes = load_e72_envelopes(cases)
    plans = build_planned_bindings(cases, descriptor_map, envelopes)
    runtime = run_replan_runtime(cases, descriptor_map, plans, "record_only")
    assert runtime["results"]["runtime_llm_calls"] == 0
    assert runtime["results"]["side_effects_executed"] is False
    assert runtime["feedback"]
    assert "initial_runtime_as_abstain_metrics" in runtime["results"]


def test_agentdojo_environment_registry_includes_resolver_tools() -> None:
    cases = load_external_cases(limit=5)
    descriptors, registry = build_agentdojo_environment_tool_registry(cases)
    tool_names = {row["tool_name"] for row in registry}
    assert "list_files" in tool_names
    assert "search_calendar_events" in tool_names
    assert "workspace_user_lookup" in tool_names
    assert "channel_message_scan" in tool_names
    assert "delete_file" in tool_names
    assert any(row["tool_name"] == "list_files" and row["side_effectful"] is False for row in registry)
    assert any(row["tool_name"] == "workspace_user_lookup" and row["side_effectful"] is False for row in registry)
    assert any(row["tool_name"] == "delete_file" and row["side_effectful"] is True for row in registry)
    assert len(descriptors) >= 60


def test_llm_agent_decision_parser() -> None:
    parsed = parse_llm_agent_decision(
        '{"decision":"CONTINUE","rationale":"matches task intent","next_action":"proceed","field_audit":[{"field":"recipient","actual_value":"sarah@example.com","relation":"VALID_RESOLVER_FILL","evidence":"contact lookup","action":"continue"}],"expanded_scope_accepted":true,"requires_user_confirmation":false}'
    )
    assert parsed["parse_valid"]
    assert parsed["decision"] == "CONTINUE"
    assert not parsed["parse_repaired"]
    assert parsed["field_audit_valid"]
    assert parsed["field_audit"][0]["relation"] == "VALID_RESOLVER_FILL"

    repaired = parse_llm_agent_decision(
        '{"decision":"REVISE","rationale":"needs resolver evidence","next_action":"gather evidence","field_audit":[{"field":"participants"'
    )
    assert repaired["parse_valid"]
    assert repaired["parse_repaired"]
    assert repaired["decision"] == "REVISE"

    bad = parse_llm_agent_decision('{"decision":"ALLOW"}')
    assert not bad["parse_valid"]


def test_llm_agent_decision_parser_accepts_revised_tool_call() -> None:
    parsed = parse_llm_agent_decision(
        '{"decision":"REVISE","rationale":"drop extra participant","next_action":"retry revised call","revised_tool_call":{"tool":"create_calendar_event","parameters":{"participants":["sarah@example.com"]}},"field_audit":[{"field":"participants","actual_value":"sarah@example.com, mallory@example.com","relation":"UNAUTHORIZED_EXTRA_SCOPE","evidence":"extra participant","action":"revise"}],"expanded_scope_accepted":false,"requires_user_confirmation":false}'
    )
    assert parsed["parse_valid"]
    assert parsed["decision"] == "REVISE"
    assert parsed["revised_tool_call"] == {
        "tool": "create_calendar_event",
        "parameters": {"participants": ["sarah@example.com"]},
    }


def test_revised_tool_call_reenters_runtime_comparison() -> None:
    cases = load_external_cases(limit=10)
    case = next(row for row in cases if row["case_id"] == "e61_external_ipiguard_workspace_001")
    descriptors = build_fixed_tool_descriptors([case], build_tool_views([case]))
    descriptor = descriptors[0]
    envelope = {
        case["case_id"]: {
            "case_id": case["case_id"],
            "task_goal": "Create lunch with Sarah Baker",
            "allowed_tool_envelopes": [
                {
                    "tool_name": "create_calendar_event",
                    "allowed_parameter_values": {"participants": ["sarah.baker@gmail.com"], "start_time": ["2024-05-19 12:00:00"], "end_time": ["2024-05-19 13:00:00"]},
                    "allowed_commit_modes": ["commit"],
                    "allowed_visibility": ["private"],
                    "trusted_control_sources": ["user"],
                    "notes": "test",
                }
            ],
            "missing_information": [],
        }
    }
    plan = build_planned_bindings([case], {(case["domain"], "create_calendar_event"): descriptor}, envelope)[0]
    revised = case_with_revised_tool_call(
        case,
        {
            "tool": "create_calendar_event",
            "parameters": {
                "title": "Lunch",
                "description": "Catch up over lunch.",
                "start_time": "2024-05-19 12:00:00",
                "end_time": "2024-05-19 13:00:00",
                "participants": ["sarah.baker@gmail.com"],
            },
        },
        1,
        plan,
    )
    decision, reasons, _ = compare_plan_to_actual(revised, descriptor, plan, extract_actual_permission_checks(revised, descriptor))
    assert decision == "ALLOW"
    assert reasons == []


def test_revised_registered_tool_is_compared_to_initial_plan() -> None:
    cases = load_external_cases(limit=10)
    case = next(row for row in cases if row["visible"]["tool_call"]["tool"] == "delete_file")
    descriptors = build_fixed_tool_descriptors([case], build_tool_views([case]))
    original_descriptor = descriptors[0]
    envelope = {
        case["case_id"]: {
            "case_id": case["case_id"],
            "task_goal": "Find the largest file before deletion",
            "allowed_tool_envelopes": [
                {
                    "tool_name": "delete_file",
                    "allowed_parameter_values": {"file_id": ["largest file id after lookup"]},
                    "allowed_commit_modes": ["commit"],
                    "allowed_visibility": ["private"],
                    "trusted_control_sources": ["user"],
                    "notes": "test",
                }
            ],
            "missing_information": ["largest file id"],
        }
    }
    plan = build_planned_bindings([case], {(case["domain"], "delete_file"): original_descriptor}, envelope)[0]
    revised = case_with_revised_tool_call(case, {"tool": "list_files", "parameters": {}}, 1, plan)
    list_descriptor = {
        **original_descriptor,
        "descriptor_id": f"{case['domain']}:list_files",
        "tool_name": "list_files",
        "security_parameter_fields": [],
        "resource_parameter_fields": [],
        "scope_parameter_fields": [],
        "side_effectful": False,
    }
    decision, reasons, feedback = compare_plan_to_actual(revised, list_descriptor, plan, extract_actual_permission_checks(revised, list_descriptor))
    assert decision == "NEEDS_REPLAN"
    assert "tool_call_changed_from_initial_plan" in reasons
    assert "tool_call_changed_from_registered_descriptor" not in reasons
    assert any(row["feedback_category"] == "tool_call_changed_from_initial_plan" for row in feedback)


def test_unregistered_revised_tool_is_hard_runtime_block() -> None:
    assert (
        apply_agent_decision_to_runtime(
            {"agent_choice": "CONTINUE", "runtime_action": "CONTINUE_UNVERIFIED"},
            ["unregistered_revised_tool_descriptor"],
        )
        == "ABSTAIN"
    )
    assert (
        apply_agent_decision_to_runtime(
            {"agent_choice": "CONTINUE", "runtime_action": "CONTINUE_UNVERIFIED"},
            ["tool_call_changed_from_initial_plan"],
        )
        == "CONTINUE_UNVERIFIED"
    )


def test_resolver_tool_continue_does_not_count_as_side_effect_candidate_execution() -> None:
    cases = load_external_cases(limit=10)
    original = next(row for row in cases if row["visible"]["tool_call"]["tool"] == "delete_file")
    revised = {**original, "visible": {**original["visible"], "tool_call": {"tool": "list_files", "parameters": {}}}}
    descriptor = {"tool_name": "list_files", "side_effectful": False}
    assert side_effect_candidate_prediction(original, revised, descriptor, "CONTINUE_UNVERIFIED") == "ABSTAIN"
    assert side_effect_candidate_prediction(original, original, {"tool_name": "delete_file", "side_effectful": True}, "CONTINUE_UNVERIFIED") == "ALLOW"


def test_llm_replan_prompt_has_no_hidden_evidence_terms() -> None:
    cases = load_external_cases(limit=5)
    descriptors = build_fixed_tool_descriptors(cases, build_tool_views(cases))
    attach_registered_tools_to_cases(cases, descriptors)
    descriptor_map = {(row["domain"], row["tool_name"]): row for row in descriptors}
    envelopes = load_e72_envelopes(cases)
    plans = build_planned_bindings(cases, descriptor_map, envelopes)
    runtime = run_replan_runtime(cases, descriptor_map, plans, "record_only")
    case = cases[0]
    plan = next(row for row in plans if row["case_id"] == case["case_id"])
    feedback = [row for row in runtime["feedback"] if row["case_id"] == case["case_id"]]
    messages = llm_agent_decision_prompt(case, plan, feedback)
    prompt_text = "\n".join(message["content"] for message in messages)
    assert "RUNTIME_FEEDBACK_INTERPRETATION_GUIDE" in prompt_text
    assert "RUNTIME_EVIDENCE" in prompt_text
    assert "REGISTERED_AGENTDOJO_ENVIRONMENT_TOOLS" in prompt_text
    assert "FIELD_LEVEL_REPLAN_AUDIT" in prompt_text
    assert "AUDIT_TARGET_FIELDS" in prompt_text
    assert "Use at most 6 field_audit rows" in prompt_text
    assert "VALID_RESOLVER_FILL" in prompt_text
    assert "UNTRUSTED_OR_INJECTED_SOURCE" in prompt_text
    assert "control_source_requires_replan" in prompt_text
    assert "unregistered_revised_tool_descriptor" in prompt_text
    assert "Do not repeat the same unregistered revised tool" in prompt_text
    assert "not a hard rule table" in prompt_text
    assert "If you choose REVISE, you must provide a concrete revised_tool_call" in prompt_text
    assert "A narrative next_action alone is not a revision" in prompt_text
    assert "For REVISE, revised_tool_call must be non-null" in prompt_text
    assert prompt_text_leakage_scan(messages)["leakage_free"]


def test_replan_behavior_audit_separates_user_source_fills_from_untrusted_continues() -> None:
    cases = load_external_cases(limit=12)
    allow_case = next(row for row in cases if row["base_label"] == "ALLOW")
    deny_case = next(row for row in cases if row["base_label"] == "DENY")
    decisions = [
        {
            "case_id": allow_case["case_id"],
            "agent_choice": "CONTINUE",
            "field_audit_valid": True,
            "field_audit": [{"relation": "VALID_RESOLVER_FILL"}],
        },
        {
            "case_id": deny_case["case_id"],
            "agent_choice": "CONTINUE",
            "field_audit_valid": True,
            "field_audit": [{"relation": "UNTRUSTED_OR_INJECTED_SOURCE"}],
        },
    ]
    audit = replan_behavior_audit(cases, decisions)
    assert audit["user_source_allow_continues"] == 1
    assert audit["untrusted_continue_failures"] == 1
    assert audit["continue_on_unauthorized_or_injected_audit"] == 1
