#!/usr/bin/env python3
"""Exhaustively check manifest bounding and default totalization in a finite model."""

from __future__ import annotations

import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.experiments.effect_binding_guard.e80_effect_contract_security_model.model import Atom


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"


def powerset(values: tuple[Atom, ...]) -> Iterable[frozenset[Atom]]:
    for size in range(len(values) + 1):
        for subset in itertools.combinations(values, size):
            yield frozenset(subset)


def bound(proposal: frozenset[Atom], trusted: frozenset[Atom]) -> frozenset[Atom] | None:
    return proposal if proposal <= trusted else None


def decide(
    trusted: frozenset[Atom],
    proposal: frozenset[Atom],
    explicit: frozenset[Atom],
    static_defaults: frozenset[Atom],
    contracted: frozenset[Atom],
    *,
    dynamic_default_unresolved: bool = False,
) -> tuple[str, frozenset[Atom]]:
    envelope = bound(proposal, trusted)
    totalized = explicit | static_defaults
    if envelope is None or dynamic_default_unresolved:
        return "ABSTAIN", frozenset()
    if not totalized <= contracted:
        return "ALLOW_UNSOUND_CONTRACT", totalized
    if contracted <= envelope:
        return "ALLOW", totalized
    return "DENY", frozenset()


def run() -> dict:
    universe = (
        Atom("send", "commit", "message:body", "alice"),
        Atom("disclose", "commit", "file:budget", "alice"),
        Atom("publish", "commit", "file:budget", "public"),
    )
    subsets = tuple(powerset(universe))
    sound_cases = 0
    allow_cases = 0
    rejected_expansions = 0
    unresolved_dynamic_cases = 0
    default_equivalence_cases = 0
    for trusted, proposal, explicit, defaults, contracted in itertools.product(subsets, repeat=5):
        totalized = explicit | defaults
        if not totalized <= contracted:
            continue
        sound_cases += 1
        decision, committed = decide(trusted, proposal, explicit, defaults, contracted)
        if proposal <= trusted:
            if decision == "ALLOW":
                allow_cases += 1
                assert committed <= trusted
        else:
            rejected_expansions += 1
            assert decision == "ABSTAIN" and not committed

        unresolved, unresolved_committed = decide(
            trusted, proposal, explicit, defaults, contracted, dynamic_default_unresolved=True
        )
        unresolved_dynamic_cases += 1
        assert unresolved == "ABSTAIN" and not unresolved_committed

        omitted = decide(trusted, proposal, explicit, defaults, contracted)
        explicit_equivalent = decide(trusted, proposal, explicit | defaults, frozenset(), contracted)
        default_equivalence_cases += 1
        assert omitted == explicit_equivalent

    authorized = universe[0]
    dangerous_default = universe[2]
    trusted = frozenset({authorized})
    proposal = frozenset({authorized})
    legacy_actual = frozenset({authorized, dangerous_default})
    legacy_contracted = frozenset({authorized})
    assert legacy_contracted <= proposal
    assert not legacy_actual <= trusted

    expanding_proposal = frozenset({authorized, dangerous_default})
    unbounded_decision = "ALLOW" if expanding_proposal <= expanding_proposal else "DENY"
    assert unbounded_decision == "ALLOW" and dangerous_default not in trusted

    report = {
        "experiment": "E80",
        "check_type": "extended_authority_bound_and_default_totalization_model",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "universe_size": len(universe),
        "sound_cases_checked": sound_cases,
        "allow_cases_checked": allow_cases,
        "authority_expansion_cases_rejected": rejected_expansions,
        "dynamic_default_cases_abstained": unresolved_dynamic_cases,
        "omitted_explicit_default_equivalence_cases": default_equivalence_cases,
        "properties": {
            "accepted_proposals_are_subsets_of_trusted_authority": True,
            "allow_implies_committed_effects_within_trusted_authority": True,
            "unresolved_dynamic_defaults_abstain": True,
            "omitted_and_explicit_static_defaults_are_equivalent": True,
        },
        "counterexamples": {
            "legacy_omitted_default_without_totalization": {
                "trusted": [str(atom) for atom in trusted],
                "contracted": [str(atom) for atom in legacy_contracted],
                "actual": [str(atom) for atom in legacy_actual],
                "unauthorized_committed": str(dangerous_default),
            },
            "llm_proposal_without_independent_bound": {
                "trusted": [str(atom) for atom in trusted],
                "proposal": [str(atom) for atom in expanding_proposal],
                "decision_under_self_authorizing_proposal": unbounded_decision,
                "unauthorized_authority": str(dangerous_default),
            },
        },
        "claim_boundary": (
            "This is exhaustive validation of a three-atom finite model. It validates the proof obligations and "
            "counterexamples, not natural-language authority compilation, real contract coverage, or remote defaults."
        ),
    }
    return report


def main() -> int:
    report = run()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e80_extended_authority_default_model.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E80 Extended Authority/Default Finite Model", "", f"Status: `{report['status']}`.", "",
        f"- Sound combinations checked: `{report['sound_cases_checked']}`.",
        f"- Authority-expanding proposals rejected: `{report['authority_expansion_cases_rejected']}`.",
        f"- Dynamic-default abstention cases: `{report['dynamic_default_cases_abstained']}`.",
        f"- Omitted/explicit static-default equivalence cases: `{report['omitted_explicit_default_equivalence_cases']}`.",
        "", "## Claim Boundary", "", report["claim_boundary"], "",
    ]
    (RESULTS / "e80_extended_authority_default_model.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
