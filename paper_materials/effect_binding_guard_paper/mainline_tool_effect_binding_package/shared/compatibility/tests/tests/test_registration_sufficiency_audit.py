from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.registration_sufficiency_audit import (
    aggregate_rows,
    changed_paths,
    classify_pair,
    mutation_candidates,
)


def test_changed_paths_and_pair_classification_separate_state_from_output():
    assert changed_paths({"x": 1}, {"x": 2}) == ["x"]
    base = {"error": None, "before": {"x": 0}, "after": {"x": 1}, "output": "a"}
    same_state = {"error": None, "before": {"x": 0}, "after": {"x": 1}, "output": "b"}
    other_state = {"error": None, "before": {"x": 0}, "after": {"x": 2}, "output": "b"}
    assert classify_pair(base, same_state) == "output_only_changed"
    assert classify_pair(base, other_state) == "committed_effect_changed"


def test_mutations_are_deterministic_and_bounded():
    first = mutation_candidates("alice@example.com", ["bob@example.com"], "recipient")
    second = mutation_candidates("alice@example.com", ["bob@example.com"], "recipient")
    assert first == second
    assert 1 <= len(first) <= 5
    assert len({repr(value) for _, value in first}) == len(first)


def test_aggregate_does_not_treat_invalid_attempt_as_evidence():
    rows = [
        {"tool_name": "send", "field": "recipient", "classification": "invalid_or_unresolved"},
        {"tool_name": "send", "field": "recipient", "classification": "committed_effect_changed"},
    ]
    report = aggregate_rows(rows)
    assert report["n_fields"] == 1
    assert report["n_valid"] == 1
    assert report["n_fields_with_committed_effect_witness"] == 1
