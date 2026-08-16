"""Unit tests: registry schema, frozen hashing, freeze/load, tamper detection."""
import json

from registry import (
    Registry,
    rule_frozen_hash,
    validate_rule_spec,
)

VALID_RULE = {
    "rule_id": "T01",
    "field_role": "amount",
    "tool": "banking/schedule_transaction",
    "transform": {"name": "amount_trailing_zeros", "params": {}},
    "scope": {"tools": ["banking/schedule_transaction"], "roles": ["amount"]},
    "rationale": "test rule",
}


def test_validate_rule_spec_ok():
    assert validate_rule_spec(VALID_RULE) == []


def test_validate_rule_spec_missing_key():
    bad = {k: v for k, v in VALID_RULE.items() if k != "transform"}
    errors = validate_rule_spec(bad)
    assert any("transform" in e for e in errors)


def test_validate_rule_spec_unknown_transform():
    bad = dict(VALID_RULE)
    bad["transform"] = {"name": "no_such_transform"}
    errors = validate_rule_spec(bad)
    assert any("unknown transform" in e for e in errors)


def test_validate_rule_spec_empty_scope():
    bad = dict(VALID_RULE)
    bad["scope"] = {"tools": [], "roles": ["amount"]}
    assert validate_rule_spec(bad)


def test_rule_frozen_hash_stability():
    assert rule_frozen_hash(VALID_RULE) == rule_frozen_hash(dict(VALID_RULE))
    changed = dict(VALID_RULE)
    changed["transform"] = {"name": "casefold_value", "params": {}}
    assert rule_frozen_hash(VALID_RULE) != rule_frozen_hash(changed)


def test_frozen_hash_excludes_validation_record():
    with_evidence = dict(VALID_RULE)
    with_evidence["validation_record"] = {"verdict": "ACCEPT"}
    with_evidence["frozen_hash"] = "stale"
    assert rule_frozen_hash(VALID_RULE) == rule_frozen_hash(with_evidence)


def test_add_rule_duplicate_raises():
    reg = Registry()
    reg.add_rule(VALID_RULE)
    try:
        reg.add_rule(VALID_RULE)
        assert False, "expected ValueError for duplicate rule_id"
    except ValueError:
        pass


def test_rules_for_scope_filter():
    reg = Registry()
    reg.add_rule(VALID_RULE)
    assert len(reg.rules_for("amount", "banking/schedule_transaction")) == 1
    assert reg.rules_for("amount", "workspace/share_file") == []
    assert reg.rules_for("subject_label", "banking/schedule_transaction") == []


def test_freeze_save_load_roundtrip(tmp_path):
    reg = Registry()
    reg.add_rule(VALID_RULE)
    path = tmp_path / "registry.frozen.json"
    reg.save(path)
    loaded = Registry.load(path)
    assert loaded.has_rule("T01")
    assert loaded.verify_frozen_hashes() == []
    assert loaded.verify_frozen_file(path) == []


def test_verify_frozen_hashes_detects_tamper(tmp_path):
    reg = Registry()
    reg.add_rule(VALID_RULE)
    path = tmp_path / "registry.frozen.json"
    reg.save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["rules"][0]["rule_id"] = "T01-TAMPERED"
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = Registry.load(path)
    mismatched = loaded.verify_frozen_hashes()
    assert "T01-TAMPERED" in mismatched
