"""Unit tests: CEGAR replay (gates, registration/refusal, convergence)."""
import json

import pytest

from cegar import CegarReplay
from domain_oracle import DomainOracle
from paths import FAILURE_CASES_FILE, FINITE_CONTEXTS, PREREG_FILE
from registry import Registry


def _prereg() -> dict:
    return json.loads(PREREG_FILE.read_text(encoding="utf-8"))


def _load_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in FAILURE_CASES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.fixture(scope="module")
def oracle() -> DomainOracle:
    prereg = _prereg()
    return DomainOracle(
        FINITE_CONTEXTS, prereg["tool_arg_roles"], prereg["oracle_semantics"]
    )


def test_replay_3_cases(oracle):
    replay = CegarReplay(oracle, registry=Registry())
    record = replay.run(_load_cases())
    assert record["n_failures"] == 3
    assert record["registered_rule_ids"] == ["CEGAR-R01", "CEGAR-R02"]
    assert record["n_registered_rules"] == 2
    assert record["n_refused"] == 1
    assert record["all_failures_disposed"] is True
    # The refused case is correctly NOT covered (fail-closed literal retained).
    assert record["all_failures_covered"] is False


def test_expected_matches_3_of_3(oracle):
    replay = CegarReplay(oracle, registry=Registry())
    record = replay.run(_load_cases())
    n_match = sum(
        1 for step in record["trace"] if step.get("matches_expected") is True
    )
    assert n_match == 3


def test_registered_rules_have_validation_records(oracle):
    replay = CegarReplay(oracle, registry=Registry())
    replay.run(_load_cases())
    for rule_id in ("CEGAR-R01", "CEGAR-R02"):
        rule = replay.registry.get(rule_id)
        assert rule is not None
        assert rule["validation_record"]["verdict"] == "ACCEPT"
        assert rule["frozen_hash"]


def test_gate1_security_event_stops(oracle):
    case = {
        "failure_id": "F-SEC-01",
        "classification": "security_event",
        "gate1_note": "safety-critical",
        "induced_rule": {
            "rule_id": "NEVER",
            "field_role": "amount",
            "tool": "banking/schedule_transaction",
            "transform": {"name": "amount_trailing_zeros", "params": {}},
            "scope": {"tools": ["banking/schedule_transaction"], "roles": ["amount"]},
        },
    }
    replay = CegarReplay(oracle, registry=Registry())
    record = replay.run([case])
    step = record["trace"][0]
    assert step["gate1"]["decision"] == "stop"
    assert step["action"] == "no_rule"
    assert step["fail_closed"] is True
    assert "gate3" not in step
    assert not replay.registry.has_rule("NEVER")


def test_gate2_structural_reject(oracle):
    case = {
        "failure_id": "F-STR-01",
        "classification": "false_negative",
        "induced_rule": {
            "rule_id": "BAD-SPEC",
            "field_role": "amount",
            "transform": {"name": "no_such_transform", "params": {}},
            "scope": {"tools": ["banking/schedule_transaction"], "roles": ["amount"]},
        },
    }
    replay = CegarReplay(oracle, registry=Registry())
    record = replay.run([case])
    step = record["trace"][0]
    assert step["gate2"]["decision"] == "reject"
    assert step["action"] == "candidate_rejected_structural"
    assert step["fail_closed"] is True


def test_deduplication_on_replay(oracle):
    """Replaying the same accepted failure twice registers the rule once."""
    cases = _load_cases()[:2]
    replay = CegarReplay(oracle, registry=Registry())
    first = replay.run(cases)
    second = replay.run(cases)
    assert first["registry_n_rules"] == 2
    assert second["registry_n_rules"] == 2
    assert all(step["action"] == "already_registered" for step in second["trace"])
