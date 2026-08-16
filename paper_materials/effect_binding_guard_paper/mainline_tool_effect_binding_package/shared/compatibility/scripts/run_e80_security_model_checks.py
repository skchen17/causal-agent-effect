#!/usr/bin/env python3
"""Exhaustively check the finite effect-contract confinement model."""

from __future__ import annotations

import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.experiments.effect_binding_guard.e80_effect_contract_security_model.model import (
    Atom,
    Call,
    Decision,
    Envelope,
    guard,
    multiset_within,
    trajectory_prefixes,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"


def bounded_multisets(values: tuple[Atom, ...], max_count: int = 2) -> Iterable[tuple[Atom, ...]]:
    for counts in itertools.product(range(max_count + 1), repeat=len(values)):
        yield tuple(
            atom
            for atom, count in zip(values, counts, strict=True)
            for _ in range(count)
        )


def run_checks() -> dict:
    universe = (
        Atom("send", "create", "message:user", "alice"),
        Atom("disclose", "read", "file:budget", "alice"),
        Atom("transfer", "commit", "account:team", "mallory"),
    )
    multisets = tuple(bounded_multisets(universe))
    single_cases = 0
    allow_cases = 0
    for allowed in multisets:
        envelope = Envelope(allowed)
        for actual in multisets:
            for contracted in multisets:
                if not multiset_within(actual, contracted):
                    continue
                single_cases += 1
                result = guard(Call("c", actual, contracted), envelope)
                if result.decision == Decision.ALLOW:
                    allow_cases += 1
                    assert multiset_within(result.committed_effects, envelope.allowed)

    trajectory_cases = 0
    sound_calls = [Call(f"c{i}", actual, contracted) for i, (actual, contracted) in enumerate(
        (
            pair
            for pair in itertools.product(multisets, multisets)
            if multiset_within(pair[0], pair[1])
        )
    )]
    for allowed in multisets:
        envelope = Envelope(allowed)
        for calls in itertools.product(sound_calls, repeat=2):
            trajectory_cases += 1
            assert all(
                multiset_within(prefix, envelope.allowed)
                for prefix in trajectory_prefixes(calls, envelope, consume=True)
            )

    authorized = universe[0]
    omitted = universe[2]
    unsound = Call("unsound", (authorized, omitted), (authorized,))
    unsound_result = guard(unsound, Envelope((authorized,)))
    assert unsound_result.decision == Decision.ALLOW
    assert omitted in unsound_result.committed_effects

    missing = guard(Call("missing", (authorized,), None), Envelope((authorized,)))
    unresolved = guard(
        Call("unresolved", (authorized,), (authorized,), unresolved=True),
        Envelope((authorized,)),
    )
    check_use = guard(
        Call("checked", (authorized,), (authorized,)),
        Envelope((authorized,)),
        executed_call_id="different",
    )
    assert {missing.decision, unresolved.decision, check_use.decision} == {Decision.ABSTAIN}
    repeated = (
        Call("repeat-1", (authorized,), (authorized,)),
        Call("repeat-2", (authorized,), (authorized,)),
    )
    reusable_prefixes = trajectory_prefixes(repeated, Envelope((authorized,)))
    assert not multiset_within(reusable_prefixes[-1], (authorized,))
    consumable_prefixes = trajectory_prefixes(
        repeated,
        Envelope((authorized,)),
        consume=True,
    )
    assert multiset_within(consumable_prefixes[-1], (authorized,))

    return {
        "experiment": "E80",
        "check_type": "finite_effect_contract_security_model",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "universe_size": len(universe),
        "single_commit_sound_cases_checked": single_cases,
        "single_commit_allow_cases_checked": allow_cases,
        "two_step_trajectory_cases_checked": trajectory_cases,
        "properties": {
            "o1_to_o5_imply_single_commit_confinement": True,
            "fixed_reusable_envelope_implies_pointwise_only": True,
            "consumable_residual_implies_cumulative_prefix_confinement": True,
            "missing_contract_fails_closed": missing.decision == Decision.ABSTAIN,
            "unresolved_fact_fails_closed": unresolved.decision == Decision.ABSTAIN,
            "check_use_mismatch_fails_closed": check_use.decision == Decision.ABSTAIN,
        },
        "counterexample_without_contract_soundness": {
            "guard_decision": unsound_result.decision,
            "contracted_effects": [str(atom) for atom in sorted(unsound.contracted_effects or ())],
            "actual_effects": [str(atom) for atom in sorted(unsound.actual_effects)],
            "unauthorized_committed_effect": str(omitted),
        },
        "reusable_authority_cumulative_counterexample": {
            "allowed_occurrences": 1,
            "committed_occurrences_after_two_calls": len(reusable_prefixes[-1]),
            "consumable_committed_occurrences_after_two_calls": len(consumable_prefixes[-1]),
        },
        "claim_boundary": (
            "This is exhaustive validation of a three-atom finite model, not a proof that the implementation's "
            "real contracts, envelopes, executor interception, or remote services satisfy O1-O5."
        ),
    }


def write_report(report: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e80_security_model_checks.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E80 Finite Security-Model Checks",
        "",
        f"Status: `{report['status']}`.",
        "",
        f"- Single-commit sound cases checked: {report['single_commit_sound_cases_checked']}.",
        f"- Allow cases checked: {report['single_commit_allow_cases_checked']}.",
        f"- Two-step trajectory cases checked: {report['two_step_trajectory_cases_checked']}.",
        "- Missing contracts, unresolved required facts, and check-use mismatches all abstain.",
        "- Removing contract soundness yields an explicit unsafe-allow counterexample.",
        "- A reusable one-occurrence bound permits the same occurrence class at each commit; "
        "a consumable residual bound prevents the second cumulative occurrence.",
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
    ]
    (RESULTS / "e80_security_model_checks.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    report = run_checks()
    write_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
