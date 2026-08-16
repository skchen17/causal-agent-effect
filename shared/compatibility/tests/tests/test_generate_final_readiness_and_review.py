"""Tests for outcome-sensitive final readiness and review generation."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "paper/current-usenix/reproduction/generate_final_readiness_and_review.py"


def load_module():
    spec = importlib.util.spec_from_file_location("final_readiness", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def payloads(
    *,
    noninferior: bool = True,
    registered_asr: int = 1,
    atom_semantic_difference: bool = True,
    atom_semantic_benefit: bool = True,
):
    conditions = ("no_guard", "spotlighting", "c1f")
    qwen_methods = (
        "no_guard",
        "spotlighting",
        "prompt_sandwiching",
        "promptarmor_local",
        "c1f",
    )
    return {
        "deepseek": {
            "aggregates": [
                {"condition": name, "utility_successes": 300}
                for name in conditions
            ],
            "task_cluster_bootstrap": {
                "difference_c1f_minus_no_guard": -0.01,
                "one_sided_95_lower_bound": -0.04 if noninferior else -0.08,
                "noninferior": noninferior,
            },
        },
        "qwen": {
            "metrics": [
                {
                    "method": name,
                    "attack_successes": 8 if name == "no_guard" else (2 if name == "c1f" else 3),
                    "benign_utility_successes": 70,
                    "attack_utility_successes": 350,
                }
                for name in qwen_methods
            ]
        },
        "heldout": {
            "summaries": [
                {
                    "method": name,
                    "attack_successes": 12 if name == "no_guard" else 3,
                    "utility_successes": 200,
                }
                for name in conditions
            ]
        },
        "transfer": {
            "comparison_metrics": [
                {"condition": "no_guard", "attack_successes": 9, "utility_successes": 180},
                {"condition": "c1f", "attack_successes": 2, "utility_successes": 170},
            ]
        },
        "four_view": {
            "aggregates": [
                {
                    "variant": name,
                    "attack_successes": (
                        registered_asr
                        if name == "registered_field_c1f"
                        else {"no_guard": 10, "whole_call_provenance": 4, "effect_only": 5}[name]
                    ),
                }
                for name in (
                    "no_guard",
                    "whole_call_provenance",
                    "effect_only",
                    "registered_field_c1f",
                )
            ]
        },
        "bounded": {
            "search_metrics": [
                {
                    "method": "no_guard",
                    "attack_successes": 4,
                    "terminal_user_utility_successes": 18,
                },
                {
                    "method": "ours_e77_effect_diff_runtime",
                    "attack_successes": 1,
                    "terminal_user_utility_successes": 12,
                },
            ]
        },
        "raw_field": {
            "aggregates": [
                {
                    "variant": "raw_field_taint",
                    "attack_successes": 4,
                    "benign_utility_successes": 40,
                }
            ],
            "retrospective_same_call": {
                "decision_disagreements": 12,
                "n_effectful_call_checks": 100,
            },
            "attribution_assessment": {
                "atom_semantic_runtime_difference": atom_semantic_difference,
                "atom_semantic_runtime_benefit": atom_semantic_benefit,
            },
        },
        "concrete_authorizer": {
            "n_queries": 232,
            "metrics": [
                {
                    "method": "concrete_effect_atoms",
                    "unsafe_pre_allow": {"successes": 0},
                    "safe_false_deny": {"successes": 0},
                }
            ],
        },
    }


def test_assessment_allows_weak_accept_only_when_all_evidence_gates_support_it() -> None:
    module = load_module()
    result = module.assess(payloads())
    assert result["benign_utility_noninferior"] is True
    assert result["closed_loop_granularity_signal"] is True
    assert result["atom_semantic_runtime_difference"] is True
    assert result["atom_semantic_runtime_benefit"] is True
    assert result["security_not_worse_on_frozen_generalization_checks"] is True
    assert result["concrete_atom_authorizer_exact_on_finite_relation"] is True
    assert result["qwen_pareto_dominators"] == []
    assert result["simulated_recommendation"] == "Weak Accept"


def test_failed_noninferiority_is_retained_in_review_wording() -> None:
    module = load_module()
    result = module.assess(payloads(noninferior=False))
    review = module.render_review(result)
    assert result["simulated_recommendation"] == "Borderline / Weak Reject"
    assert "does not pass" in review
    assert "production safety" in review


def test_absent_raw_field_difference_blocks_weak_accept() -> None:
    module = load_module()
    result = module.assess(
        payloads(atom_semantic_difference=False, atom_semantic_benefit=False)
    )
    assert result["atom_semantic_runtime_difference"] is False
    assert result["atom_semantic_runtime_benefit"] is False
    assert result["simulated_recommendation"] == "Borderline / Weak Reject"
