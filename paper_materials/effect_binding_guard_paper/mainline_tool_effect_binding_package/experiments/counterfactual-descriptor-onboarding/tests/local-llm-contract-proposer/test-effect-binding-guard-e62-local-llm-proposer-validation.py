from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contract_validator import validate_contract
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.runtime import authorize_tool_call, freeze_contract
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.contract_parser import parse_contract_from_text
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.failure_analysis import classify_failure
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.heldout_tools import E60_TOOL_NAMES, authorization_context, load_heldout_tools
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.local_llm_backend import StaticBackend, UnavailableBackend
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.prompting import FORBIDDEN_PROMPT_TERMS, build_proposal_prompt, build_refinement_prompt, prompt_leakage_scan
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.reference_expectations import generate_reference_cases, reference_contract_for_tool, reference_templates
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.run_e62 import (
    CLAIM_BOUNDARY,
    FAILURE_EXAMPLES,
    PER_TOOL_CSV,
    PROMPTS_JSONL,
    REPORT_JSON,
    REPORT_MD,
    REUSE_INVENTORY,
    can_freeze,
    run_e62,
)


def test_heldout_tools_are_disjoint_from_e60_tools() -> None:
    tools = load_heldout_tools()
    names = {tool.name for tool in tools}
    assert len(tools) == 15
    assert not names & E60_TOOL_NAMES


def test_prompts_exclude_reference_and_gold_terms() -> None:
    for tool in load_heldout_tools():
        prompt = build_proposal_prompt(tool)
        scan = prompt_leakage_scan(prompt)
        assert scan["leakage_free"], (tool.name, scan["hits"])
        lowered = prompt.lower()
        assert "safe_style" not in lowered
        assert "unsafe_style" not in lowered
        for term in FORBIDDEN_PROMPT_TERMS:
            assert term not in lowered


def test_refinement_prompt_uses_summary_not_hidden_expectations() -> None:
    tool = load_heldout_tools()[0]
    prompt = build_refinement_prompt(
        tool,
        "{\"tool_name\":\"forward_email\",\"templates\":[]}",
        {
            "failure_categories": ["missed_side_effect"],
            "missing_required_atom_count": 2,
            "required_atom_coverage": 0.5,
            "expected_atoms": [{"effect_type": "forbidden"}],
            "violation_reasons": ["forbidden"],
        },
    )
    scan = prompt_leakage_scan(prompt)
    assert scan["leakage_free"], scan["hits"]
    assert "expected_atoms" not in prompt
    assert "violation_reasons" not in prompt


def test_valid_json_proposal_parses_to_e60_compatible_contract() -> None:
    tool = load_heldout_tools()[0]
    contract = reference_contract_for_tool(tool)
    parsed = parse_contract_from_text(json.dumps(contract.to_dict()), tool_name=tool.name, setting="raw_local_llm")
    assert parsed.parse_valid
    assert parsed.contract is not None
    assert parsed.contract.tool_name == tool.name
    assert parsed.contract.proposal_mode == "local_llm"


def test_parser_filters_chain_of_thought_and_final_json_tags() -> None:
    tool = load_heldout_tools()[0]
    contract = reference_contract_for_tool(tool)
    raw = (
        "<think>I will inspect the schema and reason about resources first.</think>\n"
        "Some explanatory text that should be ignored.\n"
        "<FINAL_JSON>\n"
        f"{json.dumps(contract.to_dict())}\n"
        "</FINAL_JSON>"
    )
    parsed = parse_contract_from_text(raw, tool_name=tool.name, setting="raw_local_llm")
    assert parsed.parse_valid
    assert parsed.contract is not None
    assert parsed.contract.tool_name == tool.name


def test_parser_uses_last_complete_json_object_when_tags_are_missing() -> None:
    tool = load_heldout_tools()[0]
    contract = reference_contract_for_tool(tool)
    raw = (
        "Reasoning with a small unrelated object {\"note\":\"ignore\"}.\n"
        "Final object follows:\n"
        f"{json.dumps(contract.to_dict())}"
    )
    parsed = parse_contract_from_text(raw, tool_name=tool.name, setting="raw_local_llm")
    assert parsed.parse_valid
    assert parsed.contract is not None
    assert parsed.contract.tool_name == tool.name


def test_malformed_schema_fails_closed() -> None:
    tool = load_heldout_tools()[0]
    parsed = parse_contract_from_text("{\"tool_name\":\"forward_email\",\"templates\":[]}", tool_name=tool.name, setting="raw_local_llm")
    assert not parsed.parse_valid
    assert parsed.contract is None


def test_reference_stub_contracts_pass_strict_freeze_gate() -> None:
    for tool in load_heldout_tools():
        contract = reference_contract_for_tool(tool)
        validation = validate_contract(contract, generate_reference_cases(tool))
        assert validation.passed, (tool.name, validation.failures)
        assert can_freeze(True, validation), tool.name
        freeze_contract(contract, validation)


def test_contract_failing_freeze_criteria_cannot_be_frozen() -> None:
    tool = next(tool for tool in load_heldout_tools() if tool.name == "forward_email")
    contract = reference_contract_for_tool(tool)
    incomplete = replace(contract, templates=tuple(template for template in contract.templates if template.effect_type != "attachment_disclosed"))
    validation = validate_contract(incomplete, generate_reference_cases(tool))
    assert not validation.passed
    assert not can_freeze(True, validation)


def test_failure_classifier_covers_required_categories() -> None:
    tool = next(tool for tool in load_heldout_tools() if tool.name == "forward_email")
    incomplete = replace(reference_contract_for_tool(tool), templates=tuple(template for template in reference_templates(tool.name) if template.effect_type != "attachment_disclosed"))
    validation = validate_contract(incomplete, generate_reference_cases(tool))
    categories = set(classify_failure(validation=validation))
    assert "missed_side_effect" in categories
    assert "ignored_attachment_disclosure" in categories
    assert "parse_failure" in classify_failure(parse_error="missing_or_empty_templates")


def test_frozen_runtime_does_not_call_backend_after_freeze(monkeypatch) -> None:
    tool = next(tool for tool in load_heldout_tools() if tool.name == "forward_email")
    contract = reference_contract_for_tool(tool)
    validation = validate_contract(contract, generate_reference_cases(tool))
    frozen = freeze_contract(contract, validation)
    backend = StaticBackend({"forward_email": json.dumps(contract.to_dict())})

    def fail_if_called(_prompt: str):
        raise AssertionError("runtime called local LLM backend")

    monkeypatch.setattr(backend, "complete", fail_if_called)
    result = authorize_tool_call(frozen, tool.example_safe_call, authorization_context("draft_only"))
    assert result["decision"] == "ALLOW"


def test_backend_unavailable_mode_emits_conservative_reports() -> None:
    report = run_e62(backend=UnavailableBackend("test unavailable"))
    assert report["local_llm_status"] == "not_executed"
    assert report["stub_harness"]["n"] == 15
    assert report["raw_local_llm"]["n"] == 0
    for path in (REPORT_JSON, REPORT_MD, PER_TOOL_CSV, FAILURE_EXAMPLES, PROMPTS_JSONL, CLAIM_BOUNDARY, REUSE_INVENTORY):
        assert Path(path).exists()
        assert Path(path).stat().st_size >= 0


def test_static_backend_scores_raw_and_refined_separately() -> None:
    valid_contract = reference_contract_for_tool(load_heldout_tools()[0])
    backend = StaticBackend(
        {
            "previous_output": json.dumps(valid_contract.to_dict()),
            "forward_email": "{\"tool_name\":\"forward_email\",\"templates\":[]}",
        }
    )
    report = run_e62(backend=backend)
    assert report["local_llm_status"] == "executed"
    assert report["raw_local_llm"]["n"] == 15
    assert report["refined_local_llm"]["n"] == 15
    assert report["raw_local_llm"]["freezeable"] == 0
    rows = PER_TOOL_CSV.read_text(encoding="utf-8")
    assert "raw_local_llm" in rows
    assert "refined_local_llm" in rows
