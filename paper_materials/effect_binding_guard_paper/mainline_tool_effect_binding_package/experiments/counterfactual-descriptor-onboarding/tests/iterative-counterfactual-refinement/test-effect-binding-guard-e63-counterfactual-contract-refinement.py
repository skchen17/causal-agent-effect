from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contract_validator import validate_contract
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.runtime import freeze_contract
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.contract_parser import parse_contract_from_text
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.heldout_tools import load_heldout_tools
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.local_llm_backend import StaticBackend, UnavailableBackend
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.reference_expectations import generate_reference_cases, reference_contract_for_tool, reference_templates
from src.experiments.effect_binding_guard.e63_counterfactual_contract_refinement.feedback import build_feedback_payload, feedback_leakage_scan
from src.experiments.effect_binding_guard.e63_counterfactual_contract_refinement.prompting import build_round_prompt, scan_round_prompt
from src.experiments.effect_binding_guard.e63_counterfactual_contract_refinement.run_e63 import (
    CANDIDATE_CONTRACTS,
    CLAIM_BOUNDARY,
    FAILURE_EXAMPLES,
    FEEDBACK_JSONL,
    FROZEN_CONTRACTS,
    PROMPTS_JSONL,
    REPORT_JSON,
    REPORT_MD,
    ROUND_METRICS_CSV,
    can_freeze,
    run_e63,
)
from src.experiments.effect_binding_guard.e63_counterfactual_contract_refinement.selection import select_best_candidate


def test_round_prompt_excludes_hidden_evidence_terms() -> None:
    tool = load_heldout_tools()[0]
    feedback = {"failure_categories": ["missed_side_effect"], "metrics": {"required_atom_coverage": 0.5}}
    prompt = build_round_prompt(tool=tool, round_index=1, previous_contract_json='{"tool_name":"forward_email"}', feedback_payload=feedback)
    scan = scan_round_prompt(prompt)
    assert scan["leakage_free"], scan["hits"]
    lowered = prompt.lower()
    for term in ("reference_contract", "expected_atoms", "expected_decision", "violation_reasons", "gold_atoms", "gold_labels"):
        assert term not in lowered


def test_feedback_is_sanitized_and_excludes_reference_atoms() -> None:
    tool = next(tool for tool in load_heldout_tools() if tool.name == "forward_email")
    incomplete = replace(reference_contract_for_tool(tool), templates=tuple(template for template in reference_templates(tool.name) if template.effect_type != "attachment_disclosed"))
    validation = validate_contract(incomplete, generate_reference_cases(tool))
    feedback = build_feedback_payload(validation=validation, round_index=0)
    scan = feedback_leakage_scan(feedback)
    assert scan["leakage_free"], scan["hits"]
    assert "failed_axes" in feedback
    text = repr(feedback).lower()
    assert "expected_base_atoms" not in text
    assert "expected_mutated_atoms" not in text
    assert "attachment_ids" not in text


def test_best_candidate_selection_prefers_first_freezeable() -> None:
    rows = [
        {"setting": "round_0_raw", "round_index": "0", "freezeable": "false", "parse_valid": "true", "unsafe_pre_allow_rate": "0.000", "required_atom_coverage": "0.900", "required_resource_binding_coverage": "1.000", "required_target_principal_coverage": "1.000", "decision_accuracy": "0.900", "false_deny_rate": "0.100"},
        {"setting": "round_1", "round_index": "1", "freezeable": "true", "parse_valid": "true", "unsafe_pre_allow_rate": "0.000", "required_atom_coverage": "1.000", "required_resource_binding_coverage": "1.000", "required_target_principal_coverage": "1.000", "decision_accuracy": "1.000", "false_deny_rate": "0.000"},
        {"setting": "round_2", "round_index": "2", "freezeable": "true", "parse_valid": "true", "unsafe_pre_allow_rate": "0.000", "required_atom_coverage": "1.000", "required_resource_binding_coverage": "1.000", "required_target_principal_coverage": "1.000", "decision_accuracy": "1.000", "false_deny_rate": "0.000"},
    ]
    assert select_best_candidate(rows)["setting"] == "round_1"


def test_best_candidate_selection_uses_ordered_score_without_freezeable() -> None:
    rows = [
        {"setting": "round_0_raw", "round_index": "0", "freezeable": "false", "parse_valid": "true", "unsafe_pre_allow_rate": "0.100", "required_atom_coverage": "1.000", "required_resource_binding_coverage": "1.000", "required_target_principal_coverage": "1.000", "decision_accuracy": "1.000", "false_deny_rate": "0.000"},
        {"setting": "round_1", "round_index": "1", "freezeable": "false", "parse_valid": "true", "unsafe_pre_allow_rate": "0.000", "required_atom_coverage": "0.800", "required_resource_binding_coverage": "1.000", "required_target_principal_coverage": "1.000", "decision_accuracy": "0.900", "false_deny_rate": "0.100"},
    ]
    assert select_best_candidate(rows)["setting"] == "round_1"


def test_freeze_gate_matches_e60_strict_validation() -> None:
    tool = load_heldout_tools()[0]
    contract = reference_contract_for_tool(tool)
    validation = validate_contract(contract, generate_reference_cases(tool))
    assert can_freeze(True, validation)
    freeze_contract(contract, validation)
    incomplete = replace(contract, templates=contract.templates[:1])
    failed = validate_contract(incomplete, generate_reference_cases(tool))
    assert not can_freeze(True, failed)


def test_parser_handles_think_and_final_json_fallback() -> None:
    tool = load_heldout_tools()[0]
    contract = reference_contract_for_tool(tool)
    raw = f"<think>reasoning</think>\n<FINAL_JSON>{json.dumps(contract.to_dict())}</FINAL_JSON>"
    parsed = parse_contract_from_text(raw, tool_name=tool.name, setting="round_1")
    assert parsed.parse_valid
    assert parsed.contract is not None


def test_backend_unavailable_writes_all_artifacts() -> None:
    report = run_e63(backend=UnavailableBackend("test unavailable"), max_rounds=1, tool_limit=2)
    assert report["local_llm_status"] == "not_executed"
    assert report["stub_harness"]["n"] == 2
    for path in (REPORT_JSON, REPORT_MD, ROUND_METRICS_CSV, CANDIDATE_CONTRACTS, PROMPTS_JSONL, FEEDBACK_JSONL, FAILURE_EXAMPLES, FROZEN_CONTRACTS, CLAIM_BOUNDARY):
        assert Path(path).exists()


def test_static_backend_records_multiple_rounds_and_human_review() -> None:
    bad = "{\"tool_name\":\"forward_email\",\"templates\":[]}"
    backend = StaticBackend({"forward_email": bad})
    report = run_e63(backend=backend, max_rounds=2, tool_limit=1)
    assert report["local_llm_status"] == "executed"
    assert report["n_candidate_records"] == 3
    assert report["local_llm_final_selection"]["human_review_required"] == 1
    assert report["prompt_leakage_violations"] == 0
    assert report["feedback_leakage_violations"] == 0
    assert "round_2" in ROUND_METRICS_CSV.read_text(encoding="utf-8")


def test_static_backend_can_freeze_after_refinement_without_runtime_llm_call(monkeypatch) -> None:
    tool = load_heldout_tools()[0]
    good = json.dumps(reference_contract_for_tool(tool).to_dict())
    backend = StaticBackend({"forward_email": good})
    report = run_e63(backend=backend, max_rounds=2, tool_limit=1)
    assert report["local_llm_final_selection"]["freezeable_tools"] == 1

    def fail_if_called(_prompt: str):
        raise AssertionError("frozen runtime called LLM backend")

    monkeypatch.setattr(backend, "complete", fail_if_called)
    assert report["local_llm_final_selection"]["human_review_required"] == 0

