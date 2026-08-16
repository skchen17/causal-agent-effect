from __future__ import annotations

from src.experiments.effect_binding_guard.e80_effect_contract_security_model.model import (
    Atom,
    Call,
    Decision,
    Envelope,
    guard,
    multiset_within,
    trajectory_prefixes,
)


def test_sound_contract_allow_confines_actual_effects() -> None:
    authorized = Atom("send", "create", "message:1", "alice")
    envelope = Envelope((authorized,))
    result = guard(Call("c", (authorized,), (authorized,)), envelope)
    assert result.decision == Decision.ALLOW
    assert multiset_within(result.committed_effects, envelope.allowed)


def test_unsound_contract_exposes_necessity_of_o1() -> None:
    authorized = Atom("send", "create", "message:1", "alice")
    omitted = Atom("disclose", "read", "file:secret", "mallory")
    result = guard(
        Call("c", (authorized, omitted), (authorized,)),
        Envelope((authorized,)),
    )
    assert result.decision == Decision.ALLOW
    assert omitted in result.committed_effects


def test_missing_unresolved_and_check_use_mismatch_fail_closed() -> None:
    atom = Atom("send", "create", "message:1", "alice")
    envelope = Envelope((atom,))
    assert guard(Call("missing", (atom,), None), envelope).decision == Decision.ABSTAIN
    assert guard(Call("u", (atom,), (atom,), True), envelope).decision == Decision.ABSTAIN
    assert guard(Call("checked", (atom,), (atom,)), envelope, executed_call_id="other").decision == Decision.ABSTAIN


def test_reusable_authority_is_pointwise_not_a_cumulative_quota() -> None:
    effect = Atom("send", "create", "message:1", "alice")
    envelope = Envelope((effect,))
    calls = [
        Call("1", (effect,), (effect,)),
        Call("2", (effect,), (effect,)),
    ]
    prefixes = trajectory_prefixes(calls, envelope)
    assert multiset_within(prefixes[0], envelope.allowed)
    assert not multiset_within(prefixes[1], envelope.allowed)


def test_consumable_authority_confines_cumulative_prefix() -> None:
    effect = Atom("send", "create", "message:1", "alice")
    envelope = Envelope((effect,))
    calls = [
        Call("1", (effect,), (effect,)),
        Call("2", (effect,), (effect,)),
    ]
    prefixes = trajectory_prefixes(calls, envelope, consume=True)
    assert prefixes == [(effect,), (effect,)]
    assert all(multiset_within(prefix, envelope.allowed) for prefix in prefixes)


def test_consumable_authority_supports_distinct_effects() -> None:
    first = Atom("send", "create", "message:1", "alice")
    second = Atom("share", "grant", "file:1", "alice")
    envelope = Envelope((first, second))
    calls = [
        Call("1", (first,), (first,)),
        Call("2", (second,), (second,)),
    ]
    assert all(
        multiset_within(prefix, envelope.allowed)
        for prefix in trajectory_prefixes(calls, envelope, consume=True)
    )
