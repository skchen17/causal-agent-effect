#!/usr/bin/env python3
"""Finite-model sanity checks for the Tool-Effect Binding theorems."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path


EFFECTS = frozenset({"create_event", "invite_external"})
CONTEXTS = {
    "none": frozenset(),
    "create": frozenset({"create_event"}),
    "create_and_invite": EFFECTS,
}
BOUNDS = tuple(
    frozenset(effect for effect, keep in zip(sorted(EFFECTS), mask) if keep)
    for mask in itertools.product((False, True), repeat=len(EFFECTS))
)
DECISIONS = ("ALLOW", "DENY", "ABSTAIN")
POLICY_TABLE = {
    "allow_create_only": {
        "none": True,
        "create": True,
        "create_and_invite": False,
    },
    "require_a_commit": {
        "none": False,
        "create": True,
        "create_and_invite": True,
    },
}


def ideal(effect_set: frozenset[str], bound: frozenset[str]) -> bool:
    return effect_set.issubset(bound)


def authorization_sufficient(representation: dict[str, int]) -> bool:
    for left, right in itertools.product(CONTEXTS, repeat=2):
        if representation[left] != representation[right]:
            continue
        for bound in BOUNDS:
            if ideal(CONTEXTS[left], bound) != ideal(CONTEXTS[right], bound):
                return False
    return True


def authorization_sufficient_for_policy_table(
    representation: dict[str, int],
) -> bool:
    """Check sufficiency when the monitor also receives a policy identifier."""
    for left, right in itertools.product(CONTEXTS, repeat=2):
        if representation[left] != representation[right]:
            continue
        for decisions in POLICY_TABLE.values():
            if decisions[left] != decisions[right]:
                return False
    return True


def check_conditional_mediation() -> dict[str, object]:
    """Exhaust the allow implication and exhibit failures of omitted premises."""
    checked = 0
    for context in CONTEXTS:
        for decisions in POLICY_TABLE.values():
            descriptor_decision = decisions[context]  # descriptor fidelity
            for monitor_decision in DECISIONS:
                if monitor_decision == "ALLOW" and not descriptor_decision:
                    continue  # excluded by authorizer soundness
                checked += 1
                if monitor_decision == "ALLOW":
                    assert decisions[context]

    check_policy = POLICY_TABLE["require_a_commit"]
    commit_policy = POLICY_TABLE["allow_create_only"]
    context = "create_and_invite"
    assert check_policy[context] and not commit_policy[context]

    return {
        "sound_cases_checked": checked,
        "policy_snapshot_mismatch_counterexample": {
            "context": context,
            "authorized_at_check": check_policy[context],
            "authorized_at_commit": commit_policy[context],
        },
    }


def check_provenance_profile() -> dict[str, object]:
    """Check the two inclusion guards and necessity of extraction/grounding."""
    values = ("trusted-target", "injected-target")
    effects = ("create", "invite")
    checked = 0
    for field_values in map(frozenset, itertools.chain.from_iterable(
        itertools.combinations(values, size) for size in range(len(values) + 1)
    )):
        for effect_kinds in map(frozenset, itertools.chain.from_iterable(
            itertools.combinations(effects, size) for size in range(len(effects) + 1)
        )):
            for untrusted_values in map(frozenset, itertools.chain.from_iterable(
                itertools.combinations(values, size) for size in range(len(values) + 1)
            )):
                for untrusted_effects in map(frozenset, itertools.chain.from_iterable(
                    itertools.combinations(effects, size) for size in range(len(effects) + 1)
                )):
                    grounded_values = frozenset({"trusted-target"})
                    grounded_effects = frozenset({"create"})
                    allow = (
                        field_values & untrusted_values <= grounded_values
                        and effect_kinds & untrusted_effects <= grounded_effects
                    )
                    checked += 1
                    if allow:
                        assert not (
                            (field_values & untrusted_values) - grounded_values
                        )
                        assert not (
                            (effect_kinds & untrusted_effects) - grounded_effects
                        )

    # Both calls would be allowed if an adapter omitted the untrusted effect or
    # incorrectly declared it grounded, despite the unsupported invite effect.
    effect_kinds = frozenset({"invite"})
    missing_extraction_allows = not (effect_kinds & frozenset())
    unsound_grounding_allows = (
        effect_kinds & frozenset({"invite"}) <= frozenset({"invite"})
    )
    assert missing_extraction_allows and unsound_grounding_allows
    return {
        "profiles_checked": checked,
        "missing_effect_extraction_counterexample": missing_extraction_allows,
        "unsound_grounding_counterexample": unsound_grounding_allows,
    }


def check_provenance_sensitive_collision() -> dict[str, object]:
    """Same concrete effect can require opposite decisions by provenance."""
    contexts = {
        "task_requested_send": {
            "effects": frozenset({"send_message"}),
            "provenance": "authenticated_task",
        },
        "injected_send": {
            "effects": frozenset({"send_message"}),
            "provenance": "untrusted_observation",
        },
    }
    effect_only = {name: value["effects"] for name, value in contexts.items()}
    full_semantics = {
        name: (value["effects"], value["provenance"])
        for name, value in contexts.items()
    }
    ideal = {
        name: value["provenance"] == "authenticated_task"
        for name, value in contexts.items()
    }
    assert len(set(effect_only.values())) == 1
    assert len(set(full_semantics.values())) == 2
    assert len(set(ideal.values())) == 2
    return {
        "same_effect_multiset": True,
        "opposite_provenance_policy_decisions": True,
        "effect_only_representation_insufficient": True,
    }


def separating_collisions(
    representation: dict[str, int],
) -> list[tuple[str, str, frozenset[str]]]:
    collisions = []
    for left, right in itertools.combinations(CONTEXTS, 2):
        if representation[left] != representation[right]:
            continue
        for bound in BOUNDS:
            if ideal(CONTEXTS[left], bound) != ideal(CONTEXTS[right], bound):
                collisions.append((left, right, bound))
    return collisions


def collision_decision_check(
    left: str, right: str, bound: frozenset[str]
) -> dict[str, bool]:
    left_ideal = ideal(CONTEXTS[left], bound)
    right_ideal = ideal(CONTEXTS[right], bound)
    if left_ideal == right_ideal:
        raise ValueError("pair is not authorization-separating")

    outcomes: dict[str, bool] = {}
    for decision in DECISIONS:
        sound = not (
            decision == "ALLOW" and (not left_ideal or not right_ideal)
        )
        permissive = not (
            decision != "ALLOW" and (left_ideal or right_ideal)
        )
        outcomes[decision] = sound and permissive
    return outcomes


def run_checks() -> dict[str, object]:
    representation_count = 0
    insufficient_count = 0
    separating_collision_count = 0

    for labels in itertools.product(range(len(CONTEXTS)), repeat=len(CONTEXTS)):
        representation = dict(zip(CONTEXTS, labels))
        representation_count += 1
        collisions = separating_collisions(representation)
        sufficient = authorization_sufficient(representation)
        assert sufficient == (not collisions)
        if sufficient:
            continue
        insufficient_count += 1
        separating_collision_count += len(collisions)
        for left, right, bound in collisions:
            outcomes = collision_decision_check(left, right, bound)
            assert not any(outcomes.values())

    compound_representation = {
        "none": 0,
        "create": 1,
        "create_and_invite": 1,
    }
    separating_bound = frozenset({"create_event"})
    compound_outcomes = collision_decision_check(
        "create", "create_and_invite", separating_bound
    )
    assert not any(compound_outcomes.values())

    adequate_representation = {
        "none": 0,
        "create": 1,
        "create_and_invite": 2,
    }
    assert authorization_sufficient(adequate_representation)
    assert authorization_sufficient_for_policy_table(adequate_representation)
    assert not authorization_sufficient_for_policy_table(compound_representation)

    mediation = check_conditional_mediation()
    provenance = check_provenance_profile()
    provenance_collision = check_provenance_sensitive_collision()

    # Finite instance of the confinement inclusion chain.
    concrete_effects = frozenset({"create_event"})
    atom_concretization = frozenset({"create_event"})
    envelope_closure = frozenset({"create_event", "write_calendar"})
    authority_bound = frozenset(
        {"create_event", "write_calendar", "read_calendar"}
    )
    assert concrete_effects.issubset(atom_concretization)
    assert atom_concretization.issubset(envelope_closure)
    assert envelope_closure.issubset(authority_bound)

    return {
        "status": "passed",
        "model": {
            "effects": sorted(EFFECTS),
            "contexts": {
                key: sorted(value) for key, value in CONTEXTS.items()
            },
            "n_authority_bounds": len(BOUNDS),
        },
        "enumeration": {
            "n_representations": representation_count,
            "n_insufficient_representations": insufficient_count,
            "n_separating_collisions_checked": separating_collision_count,
            "n_monitor_decisions_per_collision": len(DECISIONS),
        },
        "compound_effect_witness": {
            "representation": compound_representation,
            "separating_bound": sorted(separating_bound),
            "decision_can_be_sound_and_permissive": compound_outcomes,
        },
        "adequate_representation_verified": adequate_representation,
        "multi_policy_sufficiency_verified": True,
        "conditional_mediation": mediation,
        "provenance_profile": provenance,
        "provenance_sensitive_collision": provenance_collision,
        "confinement_chain_verified": True,
        "claim_boundary": (
            "Executable finite-model sanity check of the definitions and "
            "proof implications; not empirical evidence or a substitute for "
            "the mathematical proofs."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "analysis/results/tool_effect_binding_finite_model_check.json"
        ),
    )
    args = parser.parse_args()
    result = run_checks()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
