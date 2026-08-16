from __future__ import annotations

from collections import Counter, defaultdict

from src.experiments.effect_binding_guard.e88_agentdojo_attack_dataset.dataset import (
    ATTACK_FAMILIES,
    EXPECTED_ADAPTIVE_ROWS,
    EXPECTED_ATTACK_PAIRS,
    EXPECTED_BENIGN_CONTROLS,
    EXPECTED_SMOKE_ROWS,
    build_dataset,
    validate_dataset,
)


def test_e88_expected_scale_and_attack_families() -> None:
    dataset = build_dataset()
    assert len(dataset["static_rows"]) == EXPECTED_ATTACK_PAIRS * len(ATTACK_FAMILIES)
    assert len(dataset["benign_rows"]) == EXPECTED_BENIGN_CONTROLS
    assert len(dataset["adaptive_rows"]) == EXPECTED_ADAPTIVE_ROWS
    assert len(dataset["smoke_rows"]) == EXPECTED_SMOKE_ROWS
    assert Counter(row["agentdojo_attack_name"] for row in dataset["static_rows"]) == {
        "ignore_previous": EXPECTED_ATTACK_PAIRS,
        "injecagent": EXPECTED_ATTACK_PAIRS,
        "important_instructions": EXPECTED_ATTACK_PAIRS,
        "tool_knowledge": EXPECTED_ATTACK_PAIRS,
    }


def test_e88_payloads_are_separated_and_execution_is_sandboxed() -> None:
    dataset = build_dataset()
    forbidden = {"raw_attack_text", "attack_payload", "injection_goal", "expected_decision", "gold_atoms"}
    for row in dataset["static_rows"] + dataset["benign_rows"] + dataset["adaptive_rows"]:
        assert not forbidden.intersection(row)
        assert row["contains_raw_attack_text"] is False
        assert row["no_external_side_effects"] is True
        assert row["environment_evaluator"]
    assert dataset["manifest"]["contains_raw_attack_text"] is False
    assert "API safety-classifier evasion" in dataset["manifest"]["prohibited_use"]


def test_e88_adaptive_split_is_group_disjoint() -> None:
    dataset = build_dataset()
    group_splits = defaultdict(set)
    for row in dataset["static_rows"]:
        group_splits[(row["suite"], row["injection_task_id"])].add(row["adaptive_split"])
    assert all(len(splits) == 1 for splits in group_splits.values())
    assert {next(iter(splits)) for splits in group_splits.values()} == {
        "adaptive_development",
        "adaptive_locked_test",
    }
    assert all(row["adaptive_split"] == "adaptive_development" for row in dataset["smoke_rows"])
    assert Counter(row["agentdojo_attack_name"] for row in dataset["smoke_rows"]) == {
        "ignore_previous": 20,
        "injecagent": 20,
        "important_instructions": 20,
        "tool_knowledge": 20,
    }


def test_e88_validation_passes_and_case_ids_are_unique() -> None:
    dataset = build_dataset()
    validation = validate_dataset(dataset)
    assert validation["status"] == "passed", validation["errors"]
    rows = dataset["static_rows"] + dataset["benign_rows"] + dataset["adaptive_rows"]
    ids = [row["case_id"] for row in rows]
    assert len(ids) == len(set(ids))
