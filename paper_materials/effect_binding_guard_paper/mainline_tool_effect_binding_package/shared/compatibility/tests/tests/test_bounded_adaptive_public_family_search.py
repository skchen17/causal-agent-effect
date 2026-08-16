from __future__ import annotations

from collections import Counter
import importlib.util
import json
from pathlib import Path

import pytest

from src.experiments.effect_binding_guard.e88_agentdojo_attack_dataset.bounded_search import (
    FAMILIES,
    METHODS,
    build_preregistration,
    summarize_predictions,
    validate_preregistration,
)


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/run_bounded_adaptive_public_family_search.py"


def runner_module():
    spec = importlib.util.spec_from_file_location("bounded_search_runner", RUNNER)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


def test_preregistration_is_balanced_locked_and_payload_free() -> None:
    protocol, cases = build_preregistration()
    validate_preregistration(protocol, cases)
    assert len(cases) == 40
    assert Counter(row["suite"] for row in cases) == Counter(
        {"banking": 10, "slack": 10, "travel": 10, "workspace": 10}
    )
    assert all(row["adaptive_split"] == "adaptive_locked_test" for row in cases)
    assert all(row["contains_raw_attack_text"] is False for row in cases)
    forbidden = {
        "raw_attack_text",
        "attack_payload",
        "expected_decision",
        "gold_atoms",
        "violation_reason",
    }
    assert all(not forbidden.intersection(row) for row in cases)


def test_development_family_order_is_frozen_and_complete() -> None:
    protocol, _ = build_preregistration()
    assert set(protocol["development_selected_family_order"]) == set(FAMILIES)
    assert protocol["search_budget_per_locked_key"] == 4
    assert protocol["development_selected_family_order"][:2] == [
        "tool_knowledge",
        "important_instructions",
    ]


def synthetic_predictions(cases: list[dict]) -> list[dict]:
    rows = []
    for method in METHODS:
        for case_index, case in enumerate(cases):
            for family in FAMILIES:
                rows.append(
                    {
                        "method": method,
                        "case_id": case["case_id"],
                        "attack_family": family,
                        "attack_success": (
                            method == "no_guard"
                            and case_index == 0
                            and family == "important_instructions"
                        ),
                        "user_utility": family == "injecagent",
                        "error": False,
                    }
                )
    return rows


def test_worst_of_four_search_retains_fixed_denominator() -> None:
    protocol, cases = build_preregistration()
    report = summarize_predictions(synthetic_predictions(cases), protocol, cases)
    assert report["status"] == "passed"
    assert report["variant_rows"] == 320
    rows = {row["method"]: row for row in report["search_metrics"]}
    assert rows["no_guard"]["n"] == 40
    assert rows["no_guard"]["attack_successes"] == 1
    assert rows["ours_e77_effect_diff_runtime"]["attack_successes"] == 0
    assert report["paired_statistics"]["attack_success"] == {
        "reference_only": 1,
        "method_only": 0,
        "discordant_pairs": 1,
        "exact_mcnemar_two_sided_p": 1.0,
    }


def test_exact_mcnemar_handles_observed_bounded_search_discordance() -> None:
    module = __import__(
        "src.experiments.effect_binding_guard."
        "e88_agentdojo_attack_dataset.bounded_search",
        fromlist=["exact_mcnemar_p"],
    )
    assert module.exact_mcnemar_p(4, 1) == 0.375
    assert module.exact_mcnemar_p(7, 1) == 0.0703125
    assert module.exact_mcnemar_p(0, 0) == 1.0


def test_missing_variant_fails_fast() -> None:
    protocol, cases = build_preregistration()
    rows = synthetic_predictions(cases)
    rows.pop()
    with pytest.raises(ValueError, match="prediction key mismatch"):
        summarize_predictions(rows, protocol, cases)


def test_prediction_collection_accepts_agentdojo_nested_log_layout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = runner_module()
    monkeypatch.setattr(runner, "RUN_ROOT", tmp_path)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "METHODS", ("no_guard",))
    monkeypatch.setattr(runner, "FAMILIES", ("important_instructions",))
    result = (
        tmp_path
        / "logs/no_guard/important_instructions/local/workspace/user_task_2/"
        "important_instructions/injection_task_5.json"
    )
    result.parent.mkdir(parents=True)
    result.write_text(
        json.dumps(
            {
                "attack_type": "important_instructions",
                "suite_name": "workspace",
                "user_task_id": "user_task_2",
                "injection_task_id": "injection_task_5",
                "security": False,
                "utility": True,
                "error": None,
            }
        ),
        encoding="utf-8",
    )
    cases = [
        {
            "case_id": "locked-case-1",
            "suite": "workspace",
            "user_task_id": "user_task_2",
            "injection_task_id": "injection_task_5",
        }
    ]
    rows = runner.collect_predictions({}, cases)
    assert rows == [
        {
            "method": "no_guard",
            "case_id": "locked-case-1",
            "suite": "workspace",
            "user_task_id": "user_task_2",
            "injection_task_id": "injection_task_5",
            "attack_family": "important_instructions",
            "attack_success": False,
            "user_utility": True,
            "error": False,
            "result_sha256": runner.sha256_file(result),
            "result_source": str(result.relative_to(tmp_path)),
        }
    ]
