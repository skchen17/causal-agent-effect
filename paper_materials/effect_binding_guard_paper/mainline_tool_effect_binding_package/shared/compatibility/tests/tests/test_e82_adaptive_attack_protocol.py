from __future__ import annotations

from src.experiments.effect_binding_guard.e82_adaptive_attack_protocol import protocol_rows, validate_protocol


def rows():
    return [row.to_dict() for row in protocol_rows()]


def test_protocol_covers_t1_through_t12_with_environment_predicates() -> None:
    source = rows()
    report = validate_protocol(source)
    assert report["status"] == "passed"
    assert {row["attack_id"] for row in source} == {f"T{index}" for index in range(1, 13)}
    assert report["all_environment_scored"] is True
    assert report["all_no_llm_judge"] is True
    assert report["all_no_external_side_effects"] is True


def test_protocol_retains_failures_and_contains_no_hidden_payload_fields() -> None:
    for row in rows():
        assert {"attack_success", "attack_failure", "abstain", "timeout", "parse_failure"} <= set(row["retained_outcomes"])
        raw = str(row).lower()
        assert "gold_atoms" not in raw
        assert "expected_decision" not in raw
        assert "attack_payload" not in raw


def test_protocol_gate_fails_on_missing_environment_predicate() -> None:
    source = rows()
    source[0]["success_predicate"] = ""
    report = validate_protocol(source)
    assert report["status"] == "failed"
    assert any("success_predicate" in error for error in report["errors"])


def test_protocol_gate_fails_if_an_outcome_can_be_silently_dropped() -> None:
    source = rows()
    source[1]["retained_outcomes"] = ["attack_success", "attack_failure"]
    report = validate_protocol(source)
    assert report["status"] == "failed"
    assert any("denominator-retention" in error for error in report["errors"])
