from collections import Counter

from src.experiments.effect_binding_guard.e88_agentdojo_attack_dataset.lock_usenix_heldout import (  # type: ignore[import-not-found]
    FAMILIES,
    PER_CELL,
    SUITES,
    select,
    stable_rank,
)


def test_selection_is_balanced_deterministic_and_label_free() -> None:
    rows = []
    for suite in SUITES:
        for family in FAMILIES:
            for index in range(PER_CELL + 3):
                rows.append(
                    {
                        "case_id": f"{suite}-{family}-{index}",
                        "suite": suite,
                        "agentdojo_attack_name": family,
                        "user_task_id": f"user_task_{index}",
                        "injection_task_id": "injection_task_0",
                        "adaptive_split": "adaptive_locked_test",
                    }
                )
    first = select(rows)
    second = select(list(reversed(rows)))
    assert first == second
    assert len(first) == len(SUITES) * len(FAMILIES) * PER_CELL
    counts = Counter((row["suite"], row["attack_family"]) for row in first)
    assert set(counts.values()) == {PER_CELL}
    assert all("security" not in row and "utility" not in row for row in first)


def test_stable_rank_changes_with_case_identity() -> None:
    base = {
        "case_id": "a",
        "suite": "banking",
        "agentdojo_attack_name": "ignore_previous",
        "user_task_id": "user_task_0",
        "injection_task_id": "injection_task_0",
    }
    changed = dict(base, case_id="b")
    assert stable_rank(base) != stable_rank(changed)
