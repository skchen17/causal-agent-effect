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


def payloads(*, noninferior: bool = True, registered_asr: int = 1):
    conditions = ("no_guard", "spotlighting", "c1f")
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
                    "condition": name,
                    "attack_successes": 8 if name == "no_guard" else 2,
                    "benign_utility_successes": 70,
                }
                for name in conditions
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
    }


def test_assessment_allows_weak_accept_only_when_all_evidence_gates_support_it() -> None:
    module = load_module()
    result = module.assess(payloads())
    assert result["benign_utility_noninferior"] is True
    assert result["closed_loop_granularity_signal"] is True
    assert result["security_not_worse_on_frozen_generalization_checks"] is True
    assert result["simulated_recommendation"] == "Weak Accept"


def test_failed_noninferiority_is_retained_in_review_wording() -> None:
    module = load_module()
    result = module.assess(payloads(noninferior=False))
    review = module.render_review(result)
    assert result["simulated_recommendation"] == "Borderline / Weak Reject"
    assert "does not pass" in review
    assert "production safety" in review
