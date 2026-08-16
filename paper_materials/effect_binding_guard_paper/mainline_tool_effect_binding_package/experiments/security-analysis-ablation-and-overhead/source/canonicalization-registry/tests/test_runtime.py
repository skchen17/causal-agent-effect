"""Unit tests: runtime canonicalization, fail-closed scope, symmetry audit."""
import pytest

from registry import Registry
from runtime import CanonicalizationRuntime

R01 = {
    "rule_id": "R01",
    "field_role": "amount",
    "tool": "banking/schedule_transaction",
    "transform": {"name": "amount_trailing_zeros", "params": {}},
    "scope": {"tools": ["banking/schedule_transaction"], "roles": ["amount"]},
    "rationale": "test",
}
R05 = {
    "rule_id": "R05",
    "field_role": "subject_label",
    "tool": "banking/schedule_transaction",
    "transform": {"name": "casefold_value", "params": {}},
    "scope": {"tools": ["banking/schedule_transaction"], "roles": ["subject_label"]},
    "rationale": "test",
}


@pytest.fixture
def runtime() -> CanonicalizationRuntime:
    reg = Registry()
    reg.add_rule(R01)
    reg.add_rule(R05)
    return CanonicalizationRuntime(reg)


def test_canonicalize_amount(runtime):
    assert runtime.canonicalize("amount", "2200.00", "banking/schedule_transaction") == "2200"
    assert runtime.canonicalize("amount", "2200.0", "banking/schedule_transaction") == "2200"


def test_canonicalize_subject_label(runtime):
    assert runtime.canonicalize("subject_label", "Invoice-A", "banking/schedule_transaction") == "invoice-a"


def test_out_of_scope_fail_closed(runtime):
    # Rule scoped only to banking; share_file out of scope -> literal value.
    assert runtime.canonicalize("amount", "2200.00", "workspace/share_file") == "2200.00"
    # No tool context -> scope cannot be confirmed -> literal value.
    assert runtime.canonicalize("amount", "2200.00", None) == "2200.00"


def test_unregistered_role_unchanged(runtime):
    value = "CH9300762011623852957"
    assert runtime.canonicalize("recipient_iban", value, "banking/schedule_transaction") == value


def test_equivalent(runtime):
    assert runtime.equivalent("amount", "2200.00", "2200", "banking/schedule_transaction") is True
    assert runtime.equivalent("amount", "2200", "2200.5", "banking/schedule_transaction") is False


def test_forbidden_match_symmetry(runtime):
    """Exact and forbidden paths share the same canonicalization function."""
    pairs = [("2200.00", "2200"), ("2200", "2200.5"), ("2200.0", "2200")]
    audit = runtime.symmetry_audit("amount", pairs, "banking/schedule_transaction")
    assert audit["consistent"] is True
    assert audit["n_pairs"] == 3
    for row in audit["rows"]:
        assert row["equivalent"] == row["forbidden_match"]


def test_forbidden_match_result(runtime):
    assert runtime.forbidden_match("amount", "2200.00", "2200", "banking/schedule_transaction") is True
    assert runtime.forbidden_match("amount", "2200", "2200.5", "banking/schedule_transaction") is False


def test_canonicalize_args_integration(runtime):
    args = {
        "amount": "2200.00",
        "date": "2026-08-01",
        "recipient": "CH9300762011623852957",
        "recurring": False,
        "subject": "Invoice-A",
    }
    role_map = {"amount": "amount", "subject": "subject_label"}
    out = runtime.canonicalize_args("banking/schedule_transaction", args, role_map)
    assert out["amount"] == "2200"
    assert out["subject"] == "invoice-a"
    # Untyped fields are unchanged.
    assert out["recipient"] == "CH9300762011623852957"
    assert out["date"] == "2026-08-01"
    assert out["recurring"] is False
    # Input is not mutated.
    assert args["amount"] == "2200.00"
    assert args["subject"] == "Invoice-A"
