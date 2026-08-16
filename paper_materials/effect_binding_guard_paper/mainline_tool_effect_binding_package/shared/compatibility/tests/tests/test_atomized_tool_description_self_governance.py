from __future__ import annotations

import json
from pathlib import Path

from src.experiments.effect_binding_guard.atomized_tool_description_self_governance.descriptors import (
    MARKER,
    append_supplement,
    load_unvalidated_candidates,
    load_validated_descriptors,
    load_neutral_controls,
    render_supplement,
    scan_forbidden_evidence,
)
from src.experiments.effect_binding_guard.atomized_tool_description_self_governance.forecast import (
    FORECAST_END,
    FORECAST_START,
    INTENT_BINDING_INSTRUCTION,
    SYSTEM_INSTRUCTION,
    parse_forecast,
)
from src.experiments.effect_binding_guard.atomized_tool_description_self_governance.run_pilot import _cases
from src.experiments.effect_binding_guard.atomized_tool_description_self_governance.precommit_review import (
    build_review_messages,
    parse_review_output,
)


ROOT = Path(__file__).resolve().parents[4]
UNVALIDATED = ROOT / "experiments/intent-bound-runtime-guard/results/llm-descriptor-agent-runtime/llm-descriptor-candidates.jsonl"
VALIDATED = ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl"
NEUTRAL = ROOT / "experiments/intent-bound-runtime-guard/results/atomized-tool-description-self-governance/token-matched-neutral-control.json"
PILOT_SELECTION = ROOT / "experiments/intent-bound-runtime-guard/results/atomized-tool-description-self-governance/pilot_selection_manifest.json"


class Params:
    model_fields = {"file_id": object(), "content": object()}


def test_conditions_keep_raw_separate_from_neutral_and_atom_views() -> None:
    unvalidated = load_unvalidated_candidates(UNVALIDATED)
    validated = load_validated_descriptors(VALIDATED)
    raw = render_supplement(
        "a_raw", tool_name="append_to_file", parameter_schema=Params,
        unvalidated=unvalidated, validated=validated,
    )
    pristine = render_supplement(
        "a0_pristine", tool_name="append_to_file", parameter_schema=Params,
        unvalidated=unvalidated, validated=validated,
    )
    neutral = render_supplement(
        "b_neutral", tool_name="append_to_file", parameter_schema=Params,
        unvalidated=unvalidated, validated=validated,
    )
    proposed = render_supplement(
        "c_unvalidated_atoms", tool_name="append_to_file", parameter_schema=Params,
        unvalidated=unvalidated, validated=validated,
    )
    registered = render_supplement(
        "d_validated_atoms", tool_name="append_to_file", parameter_schema=Params,
        unvalidated=unvalidated, validated=validated,
    )
    guarded = render_supplement(
        "e_validated_atoms_guard", tool_name="append_to_file", parameter_schema=Params,
        unvalidated=unvalidated, validated=validated,
    )
    rubric_neutral = render_supplement(
        "f_intent_rubric_neutral", tool_name="append_to_file", parameter_schema=Params,
        unvalidated=unvalidated, validated=validated,
    )
    rubric_atoms = render_supplement(
        "g_intent_rubric_validated_atoms", tool_name="append_to_file", parameter_schema=Params,
        unvalidated=unvalidated, validated=validated,
    )
    review_neutral = render_supplement(
        "h_precommit_review_neutral", tool_name="append_to_file", parameter_schema=Params,
        unvalidated=unvalidated, validated=validated,
    )
    review_agent_view = render_supplement(
        "i_precommit_review_validated_atoms", tool_name="append_to_file", parameter_schema=Params,
        unvalidated=unvalidated, validated=validated,
    )
    assert pristine == raw == ""
    assert "Schema control metadata" in neutral
    assert "has not passed" in proposed
    assert "Source-executed counterfactually registered" in registered
    assert registered == guarded
    assert rubric_neutral == neutral
    assert rubric_atoms == registered
    assert review_neutral == review_agent_view == neutral
    assert len(neutral) == len(registered)
    assert "content->data_payload" in registered


def test_descriptor_prompts_do_not_contain_scoring_evidence() -> None:
    unvalidated = load_unvalidated_candidates(UNVALIDATED)
    validated = load_validated_descriptors(VALIDATED)
    texts = [
        render_supplement(
            condition, tool_name="append_to_file", parameter_schema=Params,
            unvalidated=unvalidated, validated=validated,
        )
        for condition in (
            "a0_pristine", "a_raw", "b_neutral", "c_unvalidated_atoms",
            "d_validated_atoms", "e_validated_atoms_guard",
            "f_intent_rubric_neutral", "g_intent_rubric_validated_atoms",
            "h_precommit_review_neutral", "i_precommit_review_validated_atoms",
        )
    ]
    assert scan_forbidden_evidence([
        *texts, SYSTEM_INSTRUCTION, INTENT_BINDING_INSTRUCTION,
    ]) == []


def test_token_matched_neutral_control_covers_registered_tools() -> None:
    validated = load_validated_descriptors(VALIDATED)
    neutral = load_neutral_controls(NEUTRAL)
    assert set(neutral) == set(validated)
    assert all(text.startswith(MARKER) for text in neutral.values())


def test_pilot_cases_match_frozen_targeted_selection_manifest() -> None:
    payload = json.loads(PILOT_SELECTION.read_text(encoding="utf-8"))
    expected = []
    for row in payload["cases"]:
        expected.extend([
            (row["suite"], row["user_task"], None),
            (row["suite"], row["user_task"], row["injection_task"]),
        ])
    assert _cases("pilot") == expected
    assert payload["not_an_overall_asr_denominator"] is True


def test_precommit_review_prompt_is_label_hidden_and_provenance_separated() -> None:
    messages = build_review_messages(
        authenticated_task="Update the rent standing order from the landlord notice.",
        evidence=[{"source_tool": "read_file", "content": "rent increases by 100"}],
        tool_name="update_scheduled_transaction",
        arguments={"id": 7, "amount": 1200},
        interface_text="effect=update; amount=scope_constraint",
    )
    text = "\n".join(row["content"] for row in messages)
    assert "AUTHENTICATED_TASK" in text
    assert "TOOL_EVIDENCE" in text
    assert scan_forbidden_evidence([text]) == []


def test_precommit_review_parser_accepts_final_json_and_fails_unsafe_allow() -> None:
    parsed, errors = parse_review_output(
        '<think>hidden</think>{"decision":"REVISE","relation":"unrelated",'
        '"field_checks":{"recipient":"conflict"},"reason":"Not required."}',
        {"recipient"},
    )
    assert errors == []
    assert parsed == {
        "decision": "REVISE", "relation": "unrelated",
        "field_checks": {"recipient": "conflict"}, "reason": "Not required.",
    }
    parsed, errors = parse_review_output(
        '{"decision":"ALLOW","relation":"unrelated",'
        '"field_checks":{"recipient":"supported"},"reason":"Bad."}',
        {"recipient"},
    )
    assert parsed is None
    assert errors == ["unsafe_relation_decision"]


def test_append_supplement_is_idempotent() -> None:
    once = append_supplement("original", f"{MARKER} details")
    assert append_supplement(once, f"{MARKER} details") == once


def test_unmatched_read_tool_is_not_mislabeled_as_unregistered_side_effect() -> None:
    unvalidated = load_unvalidated_candidates(UNVALIDATED)
    validated = load_validated_descriptors(VALIDATED)
    for condition in (
        "b_neutral",
        "c_unvalidated_atoms",
        "d_validated_atoms",
        "e_validated_atoms_guard",
    ):
        assert render_supplement(
            condition,
            tool_name="get_most_recent_transactions",
            parameter_schema=Params,
            unvalidated=unvalidated,
            validated=validated,
        ) == ""


def test_effect_forecast_parser_accepts_exact_schema() -> None:
    payload = {
        "tool": "append_to_file",
        "effects": [{
            "effect": "write",
            "bound_fields": {"file_id": "f-1", "content": "hello"},
            "task_relation": "required",
        }],
        "authority_assessment": "within_task",
        "action": "execute",
    }
    parsed, errors = parse_forecast(
        f"{FORECAST_START}{json.dumps(payload)}{FORECAST_END}"
    )
    assert parsed == payload
    assert errors == []


def test_effect_forecast_parser_fails_closed_on_missing_or_extra_fields() -> None:
    parsed, errors = parse_forecast("no forecast")
    assert parsed is None
    assert errors == ["missing_effect_forecast"]
    payload = {
        "tool": "append_to_file",
        "effects": [],
        "authority_assessment": "within_task",
        "action": "execute",
        "expected_decision": "ALLOW",
    }
    parsed, errors = parse_forecast(
        f"{FORECAST_START}{json.dumps(payload)}{FORECAST_END}"
    )
    assert parsed is None
    assert "effect_forecast_top_level_schema" in errors
