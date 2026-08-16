from __future__ import annotations

import json

from src.experiments.effect_binding_guard.e69_counterfactually_selected_atomized_contracts.run_e69 import (
    build_e69_tasks,
    build_tool_views,
    candidate_prompt,
    parse_candidate_response,
    prompt_text_leakage_scan,
    replay_from_outputs,
    score_candidates,
    select_topk,
)
from src.experiments.effect_binding_guard.e68_llm_counterfactual_atom_field_stress.run_e68 import (
    load_external_cases,
    make_counterfactual_tasks,
    pair_metrics,
    parse_pair_llm_output,
)


def valid_contract(tool_name: str = "create_calendar_event") -> dict:
    return {
        "tool_name": tool_name,
        "effect_inventory": [{"effect": "calendar_event_created", "description": "Creates a calendar event."}],
        "atom_templates": [
            {
                "effect": "calendar_event_created",
                "operation": "create_calendar_event",
                "resource_id": "source_field:title",
                "source_field": "title",
                "resource_type": "calendar_event",
                "recipient_role": "none",
                "target_principal": "none",
                "visibility": "unknown",
                "commit_mode": "literal:commit",
                "provenance_source": "runtime_evidence.provenance_source",
                "control_source": "runtime_evidence.control_source",
                "security_relevant_fields": ["title", "start_time", "end_time"],
            }
        ],
        "non_security_fields": ["description"],
        "requires_human_review": False,
        "provenance": {"proposer": "local_qwen"},
    }


def strict_pair_output(resource_id: str = "r1", decision: str = "ALLOW") -> dict:
    atom = {
        "effect": "calendar_event_created",
        "operation": "create_calendar_event",
        "resource_id": resource_id,
        "resource_type": "calendar_event",
        "recipient_role": "none",
        "visibility": "private",
        "commit_mode": "commit",
        "provenance_source": "user_request",
        "control_source": "user",
    }
    return {"atoms": [atom], "decision": decision, "reason": "ok", "field_dependencies": ["resource_id"]}


def test_candidate_prompt_does_not_leak_sidecar_terms() -> None:
    cases = load_external_cases(limit=3)
    tool_view = build_tool_views(cases)[0]
    prompt = candidate_prompt(tool_view, 1)
    scan = prompt_text_leakage_scan(prompt)
    assert scan["leakage_free"], scan["hits"]


def test_candidate_parser_accepts_valid_contract_and_fails_closed() -> None:
    parsed = parse_candidate_response(json.dumps(valid_contract()), expected_tool_name="create_calendar_event")
    assert parsed.parse_valid
    assert parsed.contracts[0]["atom_templates"][0]["resource_id"] == "source_field:title"

    missing = valid_contract()
    del missing["atom_templates"][0]["resource_id"]
    assert not parse_candidate_response(json.dumps(missing), expected_tool_name="create_calendar_event").parse_valid

    bad_type = valid_contract()
    bad_type["requires_human_review"] = "false"
    assert not parse_candidate_response(json.dumps(bad_type), expected_tool_name="create_calendar_event").parse_valid

    extra = valid_contract()
    extra["expected_decision"] = "ALLOW"
    assert not parse_candidate_response(json.dumps(extra), expected_tool_name="create_calendar_event").parse_valid


def test_all_supported_axes_are_materialized_for_external_cases() -> None:
    cases = load_external_cases(limit=5)
    tasks = make_counterfactual_tasks(cases, ["resource", "operation", "commit_mode", "visibility", "provenance", "control_source", "multi_resource", "surface_invariant"], 0)
    axes = {task["axis"] for task in tasks}
    assert {"resource", "operation", "provenance", "control_source", "surface_invariant"} <= axes


def test_build_e69_tasks_attaches_valid_candidate_contracts_only() -> None:
    cases = load_external_cases(limit=2)
    tool_name = cases[0]["visible"]["tool_call"]["tool"]
    candidates = [
        {"candidate_id": f"{tool_name}#0", "tool_name": tool_name, "parse_valid": True, "contract": valid_contract(tool_name)},
        {"candidate_id": f"{tool_name}#invalid", "tool_name": tool_name, "parse_valid": False, "contract": None},
    ]
    tasks = build_e69_tasks(cases, candidates)
    assert tasks
    assert all(task["candidate_id"] == f"{tool_name}#0" for task in tasks if task["tool_name"] == tool_name)


def test_pair_scoring_distinguishes_topk_from_strict_freeze() -> None:
    task = {
        "expected_changed_atom_fields": ["resource_id"],
        "expected_relation": "sensitive",
        "expected_base_decision": "ALLOW",
        "expected_mutated_decision": "DENY",
    }
    base, _, _ = parse_pair_llm_output(json.dumps({"base": strict_pair_output("r1", "ALLOW"), "mutated": strict_pair_output("r2", "ALLOW")}))
    _, mutated, _ = parse_pair_llm_output(json.dumps({"base": strict_pair_output("r1", "ALLOW"), "mutated": strict_pair_output("r2", "ALLOW")}))
    metrics = pair_metrics(task, base, mutated)
    rows = [
        {
            "candidate_id": "tool#0",
            "pair_id": "case:resource",
            "axis": "resource",
            "tool_name": "tool",
            "context_variant": "clean",
            "metrics": metrics,
            "base": {"parse_valid": True, "decision": "ALLOW", "atoms": base.atoms},
            "mutated": {"parse_valid": True, "decision": "ALLOW", "atoms": mutated.atoms},
        },
        {
            "candidate_id": "tool#0",
            "pair_id": "case:resource",
            "axis": "resource",
            "tool_name": "tool",
            "context_variant": "injected",
            "metrics": metrics,
            "base": {"parse_valid": True, "decision": "ALLOW", "atoms": base.atoms},
            "mutated": {"parse_valid": True, "decision": "ALLOW", "atoms": mutated.atoms},
        },
    ]
    candidates = [{"candidate_id": "tool#0", "tool_name": "tool", "parse_valid": True, "contract": valid_contract("tool")}]
    scores = score_candidates(candidates, rows)
    selected = select_topk(scores, candidates, top_k=1)
    assert selected[0]["selected_for_eval"] is True
    assert selected[0]["strictly_freezeable"] is False


def test_replay_metrics_use_selected_candidates_only() -> None:
    cases = load_external_cases(limit=1)
    case_id = cases[0]["case_id"]
    outputs = [
        {
            "candidate_id": "tool#0",
            "context_variant": "clean",
            "source_case_id": case_id,
            "base": {"parse_valid": True, "decision": cases[0]["base_label"], "atoms": []},
        },
        {
            "candidate_id": "tool#1",
            "context_variant": "clean",
            "source_case_id": case_id,
            "base": {"parse_valid": True, "decision": "ALLOW", "atoms": []},
        },
    ]
    selected = [{"candidate_id": "tool#0", "selected_for_eval": True}]
    replay = replay_from_outputs(cases, selected, outputs)
    assert replay["atomized_selected_topk"]["n_predictions_available"] == 1
    assert replay["atomized_selected_topk"]["accuracy"]["successes"] == 1
