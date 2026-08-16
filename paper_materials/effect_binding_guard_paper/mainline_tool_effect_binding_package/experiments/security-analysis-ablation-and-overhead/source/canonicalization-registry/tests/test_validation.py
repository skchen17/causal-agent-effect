"""Unit tests: counterfactual validation pipeline (verdicts, fail-closed)."""
import json

import pytest

from domain_oracle import DomainOracle
from paths import FINITE_CONTEXTS, PREREG_FILE
from validation import (
    ValidationPipeline,
    VERDICT_ACCEPT,
    VERDICT_REJECT,
    VERDICT_UNDETERMINED,
)


def _prereg() -> dict:
    return json.loads(PREREG_FILE.read_text(encoding="utf-8"))


def _rule_by_id(rule_id: str) -> dict:
    for rule in _prereg()["rules"]:
        if rule["rule_id"] == rule_id:
            return rule
    raise KeyError(rule_id)


@pytest.fixture(scope="module")
def pipeline() -> ValidationPipeline:
    prereg = _prereg()
    oracle = DomainOracle(
        FINITE_CONTEXTS, prereg["tool_arg_roles"], prereg["oracle_semantics"]
    )
    return ValidationPipeline(oracle)


@pytest.mark.parametrize("rule_id", ["R01", "R02", "R03", "R04", "R05"])
def test_accept_rules(pipeline, rule_id):
    rec = pipeline.validate_rule(_rule_by_id(rule_id))
    assert rec["verdict"] == VERDICT_ACCEPT, rec["verdict_reason"]


@pytest.mark.parametrize("rule_id", ["R06", "R07", "R08", "R09", "R10"])
def test_reject_rules(pipeline, rule_id):
    rec = pipeline.validate_rule(_rule_by_id(rule_id))
    assert rec["verdict"] == VERDICT_REJECT, rec["verdict_reason"]


def test_all_10_match_expected(pipeline):
    """Core mechanism evidence: 10/10 verdicts match pre-registered expectations."""
    matched = 0
    for rule in _prereg()["rules"]:
        rec = pipeline.validate_rule(rule)
        if rec["verdict"] == rule["expected"]:
            matched += 1
    assert matched == 10


def test_undetermined_uncalibrated_tool(pipeline):
    """Fail-closed: a rule scoped to an uncalibrated tool is UNDETERMINED."""
    rule = {
        "rule_id": "T-SLACK",
        "field_role": "subject_label",
        "tool": "slack/send_direct_message",
        "transform": {"name": "fold_whitespace", "params": {}},
        "scope": {"tools": ["slack/send_direct_message"], "roles": ["subject_label"]},
        "samples": [{"kind": "positive", "v": "a  b", "w": "a b"}],
    }
    rec = pipeline.validate_rule(rule)
    assert rec["verdict"] == VERDICT_UNDETERMINED
    assert rec["calibrated"] is False


def test_no_samples_undetermined(pipeline):
    rule = dict(_rule_by_id("R01"))
    rule["rule_id"] = "T-NOSAMPLES"
    rule["samples"] = []
    rec = pipeline.validate_rule(rule)
    assert rec["verdict"] == VERDICT_UNDETERMINED


def test_probe_overmerge_detection(pipeline):
    """A rule that merges oracle-distinct probe values must be REJECTed."""
    rule = {
        "rule_id": "T-OVERMERGE",
        "field_role": "amount",
        "tool": "banking/schedule_transaction",
        "transform": {"name": "amount_round_to_int", "params": {}},
        "scope": {"tools": ["banking/schedule_transaction"], "roles": ["amount"]},
        "samples": [{"kind": "positive", "v": "2200", "w": "2200"}],
        "probes": [{"v": "2200", "w": "2200.5"}],
    }
    rec = pipeline.validate_rule(rule)
    assert rec["verdict"] == VERDICT_REJECT
    assert rec["overmerges"] == [0]


def test_accept_rule_probe_guard_holds(pipeline):
    """R01's probe must not over-merge (2200 vs 2200.5 stays distinct)."""
    rec = pipeline.validate_rule(_rule_by_id("R01"))
    assert rec["probes"][0]["oracle_distinct"] is True
    assert rec["probes"][0]["overmerge"] is False
