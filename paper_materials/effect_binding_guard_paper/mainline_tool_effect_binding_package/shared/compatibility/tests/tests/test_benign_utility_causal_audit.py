from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCE = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/source/"
    "benign-utility-causal-audit/run_audit.py"
)
spec = importlib.util.spec_from_file_location("benign_utility_causal_audit", SOURCE)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def test_visible_answer_removes_hidden_reasoning() -> None:
    text = "<think>intermediate 1050</think>\nThe answer is 1060."
    assert audit.visible_answer(text) == "The answer is 1060."


def test_visible_answer_removes_analysis_blocks_case_insensitively() -> None:
    text = "<ANALYSIS>hidden</ANALYSIS>\nVisible"
    assert audit.visible_answer(text) == "Visible"


def test_canonical_calls_preserves_structured_arguments() -> None:
    payload = {
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": "search_emails",
                        "args": {"query": "family reunion"},
                    }
                ],
            }
        ]
    }
    assert audit.canonical_calls(payload) == [
        {
            "function": "search_emails",
            "args": {"query": "family reunion"},
        }
    ]


def test_guard_feedback_extracts_runtime_decisions_only() -> None:
    payload = {
        "messages": [
            {
                "role": "tool",
                "content": [
                    {
                        "type": "text",
                        "content": (
                            '{"runtime_guard":"ABSTAIN","executed":false,'
                            '"reasons":["missing"]}'
                        ),
                    }
                ],
            },
            {
                "role": "tool",
                "content": [{"type": "text", "content": "ordinary result"}],
            },
        ]
    }
    assert audit.guard_feedback(payload) == [
        {
            "runtime_guard": "ABSTAIN",
            "executed": False,
            "reasons": ["missing"],
        }
    ]


def test_root_cause_inventory_matches_expected_cases() -> None:
    assert set(audit.ROOT_CAUSES) == audit.EXPECTED_DISCORDANT_CASES
    buckets = [
        value["causal_bucket"] for value in audit.ROOT_CAUSES.values()
    ]
    assert buckets.count("reasoning_sensitive_official_scoring") == 4
    assert buckets.count("model_run_output_variation") == 3
