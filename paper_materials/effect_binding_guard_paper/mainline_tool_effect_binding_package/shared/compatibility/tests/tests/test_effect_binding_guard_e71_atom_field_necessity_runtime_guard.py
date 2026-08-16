from __future__ import annotations

import json

from src.experiments.effect_binding_guard.e68_llm_counterfactual_atom_field_stress.run_e68 import load_external_cases
from src.experiments.effect_binding_guard.e69_counterfactually_selected_atomized_contracts.run_e69 import build_tool_views
from src.experiments.effect_binding_guard.e71_atom_field_necessity_runtime_guard.run_e71 import (
    ATOM_FIELDS,
    build_field_necessity_tasks,
    descriptor_from_fields,
    field_necessity_prompt,
    parse_pair_atom_output,
    prompt_text_leakage_scan,
    run_runtime_guard,
    score_field_outputs,
    selected_necessary_fields,
    split_heldout_cases,
)


def atom(resource_id: str = "r1") -> dict[str, str]:
    return {
        "effect": "file_modified",
        "operation": "delete_file",
        "resource_id": resource_id,
        "resource_type": "file",
        "recipient_role": "target",
        "visibility": "private",
        "commit_mode": "commit",
        "provenance_source": "user_request",
        "control_source": "user",
    }


def test_field_necessity_prompt_has_no_hidden_evidence() -> None:
    cases = load_external_cases(limit=5)
    view = build_tool_views(cases)[0]
    task = build_field_necessity_tasks(cases, [view], max_fields_per_tool=1)[0]
    messages = field_necessity_prompt(task, context_variant="clean")
    scan = prompt_text_leakage_scan(messages)
    assert scan["leakage_free"], scan["hits"]
    text = json.dumps(messages)
    assert "expected_decision" not in text
    assert "gold_atoms" not in text


def test_pair_parser_accepts_atom_only_and_rejects_decision() -> None:
    valid = {
        "full": {"atoms": [atom("r1")], "effect_summary": "deletes file", "missing_information": []},
        "field_removed": {"atoms": [atom("unknown")], "effect_summary": "file unknown", "missing_information": ["file_id"]},
    }
    full, removed, error = parse_pair_atom_output(json.dumps(valid))
    assert error == ""
    assert full.parse_valid
    assert removed.atoms[0]["resource_id"] == "unknown"

    invalid = {
        "full": {"atoms": [atom("r1")], "effect_summary": "x", "missing_information": [], "decision": "ALLOW"},
        "field_removed": {"atoms": [atom("unknown")], "effect_summary": "x", "missing_information": []},
    }
    full, _, _ = parse_pair_atom_output(json.dumps(invalid))
    assert not full.parse_valid


def test_missing_security_field_can_demonstrate_necessity() -> None:
    row = {
        "output_id": "o1",
        "task_id": "t1",
        "case_id": "c1",
        "tool_name": "delete_file",
        "domain": "docs",
        "field_under_test": "file_id",
        "context_variant": "clean",
        "expected_atom_fields": ["resource_id"],
        "expected_security_relevant": True,
        "prompt_leakage_free": True,
        "full": {"parse_valid": True, "atoms": [atom("file_1")], "missing_information": []},
        "field_removed": {"parse_valid": True, "atoms": [atom("unknown")], "missing_information": ["file_id"]},
    }
    score = score_field_outputs([row])[0]
    assert score["necessity_pass"] is True
    assert score["failure_category"] == "none"


def test_nonsecurity_field_should_not_change_atoms() -> None:
    row = {
        "output_id": "o1",
        "task_id": "t1",
        "case_id": "c1",
        "tool_name": "delete_file",
        "domain": "docs",
        "field_under_test": "description",
        "context_variant": "clean",
        "expected_atom_fields": [],
        "expected_security_relevant": False,
        "prompt_leakage_free": True,
        "full": {"parse_valid": True, "atoms": [atom("file_1")], "missing_information": []},
        "field_removed": {"parse_valid": True, "atoms": [atom("file_1")], "missing_information": []},
    }
    score = score_field_outputs([row])[0]
    assert score["invariant_pass"] is True


def test_runtime_abstains_without_registered_descriptor() -> None:
    case = load_external_cases(limit=1)[0]
    result = run_runtime_guard([case], [{"tool_name": case["visible"]["tool_call"]["tool"], "registered": False}])
    metrics = result["results"]["field_necessity_descriptor_guard"]
    assert metrics["abstain"]["successes"] == 1
    assert result["checks"][0]["check_result"] == "ABSTAIN"


def test_task_builder_marks_resource_like_fields() -> None:
    cases = load_external_cases(limit=5)
    views = build_tool_views(cases)
    tasks = build_field_necessity_tasks(cases, views, max_fields_per_tool=3)
    assert tasks
    assert all("full_visible" in task and "field_removed_visible" in task for task in tasks)
    assert any("resource_id" in task["expected_atom_fields"] for task in tasks)
    assert set(ATOM_FIELDS) == set(atom())


def _label_free_score(field: str, *, demonstrated: bool, gold_fields: str, gold_relevant: bool, necessity_pass: bool) -> dict:
    return {
        "output_id": f"{field}::clean",
        "task_id": f"delete_file:{field}:c1",
        "case_id": "c1",
        "tool_name": "delete_file",
        "domain": "docs",
        "field_under_test": field,
        "context_variant": "clean",
        "expected_atom_fields": gold_fields,
        "expected_security_relevant": gold_relevant,
        "full_parse_valid": True,
        "field_removed_parse_valid": True,
        "atom_signature_changed": demonstrated,
        "expected_field_degraded": False,
        "missing_mentions_field": demonstrated,
        "necessity_pass": necessity_pass,
        "invariant_pass": not gold_relevant,
        "label_free_necessity_demonstrated": demonstrated,
        "full_resource_nonunknown": True,
        "removed_resource_unknown": demonstrated,
        "prompt_leakage_free": True,
        "failure_category": "none",
    }


def test_descriptor_selection_ignores_gold_columns() -> None:
    # Label-free evidence is identical; gold-derived columns disagree between the two sets.
    scores_a = [
        _label_free_score("file_id", demonstrated=True, gold_fields="resource_id", gold_relevant=True, necessity_pass=True),
        _label_free_score("note", demonstrated=False, gold_fields="", gold_relevant=False, necessity_pass=False),
    ]
    scores_b = [
        _label_free_score("file_id", demonstrated=True, gold_fields="", gold_relevant=False, necessity_pass=False),
        _label_free_score("note", demonstrated=False, gold_fields="resource_id", gold_relevant=True, necessity_pass=True),
    ]
    selected_a = selected_necessary_fields(scores_a)
    selected_b = selected_necessary_fields(scores_b)
    assert selected_a == selected_b
    assert [row["field"] for row in selected_a] == ["file_id"]
    constants = {"effect": "file_modified", "resource_type": "file", "recipient_role": "target", "visibility": "private", "commit_mode": "commit"}
    descriptor_a = descriptor_from_fields("delete_file", selected_a, constants)
    descriptor_b = descriptor_from_fields("delete_file", selected_b, constants)
    assert descriptor_a == descriptor_b
    assert descriptor_a["field_bindings"]["resource_id"] == "param:file_id"


def test_signature_change_alone_is_not_directed_degradation() -> None:
    changed = atom("file_1")
    changed = {**changed, "effect": "file_disclosed"}
    row = {
        "output_id": "o1",
        "task_id": "t1",
        "case_id": "c1",
        "tool_name": "delete_file",
        "domain": "docs",
        "field_under_test": "file_id",
        "context_variant": "clean",
        "expected_atom_fields": ["visibility"],
        "expected_security_relevant": True,
        "prompt_leakage_free": True,
        "full": {"parse_valid": True, "atoms": [atom("file_1")], "missing_information": []},
        "field_removed": {"parse_valid": True, "atoms": [changed], "missing_information": []},
    }
    score = score_field_outputs([row])[0]
    assert score["atom_signature_changed"] is True
    assert score["expected_field_degraded"] is False
    assert score["necessity_pass"] is False
    assert score["failure_category"] == "necessary_field_not_demonstrated"


def test_heldout_split_is_deterministic_and_disjoint() -> None:
    cases = load_external_cases(limit=10)
    first = split_heldout_cases(cases)
    second = split_heldout_cases(list(reversed(cases)))
    assert {case["case_id"] for case in first[0]} == {case["case_id"] for case in second[0]}
    assert {case["case_id"] for case in first[1]} == {case["case_id"] for case in second[1]}
    assert not {case["case_id"] for case in first[0]} & {case["case_id"] for case in first[1]}
