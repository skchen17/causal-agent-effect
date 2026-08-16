from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/scripts/"
    "utility-causal-diagnostics/run_deepseek_atom_cegar_probe.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("utility_causal_diagnostics", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_probe_dataset_and_prompts_hide_scoring_labels() -> None:
    module = load_module()
    cases = module.build_cases()
    assert len(cases) == 35
    assert {case.suite for case in cases} == {"workspace", "slack", "travel", "banking"}
    for case in cases:
        for condition in module.CONDITIONS:
            system, user = module.build_prompt(case, condition)
            prompt = system + "\n" + user
            assert "expected_decision" not in prompt
            assert case.case_type not in prompt
            assert case.case_id not in prompt


def test_counterexample_guided_rules_reduce_false_denial_without_unsafe_allow() -> None:
    module = load_module()
    cases = module.build_cases()
    trace = module.run_deterministic_cegar(cases)
    assert trace
    assert all(row["accepted"] for row in trace)
    assert all(row["validation_unsafe_allow"] == 0 for row in trace)
    accepted = set(trace[-1]["accepted_rules_after_round"])

    strict_safe = sum(
        module.strict_literal_decision(case) == "ALLOW"
        for case in cases
        if case.expected_decision == "ALLOW"
    )
    refined_safe = sum(
        module.cegar_decision(case, accepted) == "ALLOW"
        for case in cases
        if case.expected_decision == "ALLOW"
    )
    assert refined_safe > strict_safe
    assert not any(
        module.cegar_decision(case, accepted) == "ALLOW"
        for case in cases
        if case.expected_decision == "DENY"
    )


def test_policy_success_keeps_utility_and_safety_distinct() -> None:
    module = load_module()
    assert module.policy_success("DENY", "REVISE")
    assert module.policy_success("ABSTAIN", "REVISE")
    assert not module.policy_success("ALLOW", "REVISE")
    assert not module.policy_success("DENY", "ALLOW")
