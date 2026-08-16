from __future__ import annotations

from dataclasses import replace

from src.experiments.effect_binding_guard.e55_precommit_authz.dataset_builder import build_dataset
from src.experiments.effect_binding_guard.e55_precommit_authz.e56_audit import (
    REQUIRED_METHODS,
    ablation_table,
    decision_path_audit,
    renamed_case,
    sanity_checks,
    slice_flags,
    slice_table,
    spot_audit_packet,
)
from src.experiments.effect_binding_guard.e55_precommit_authz.guards import run_methods
from src.experiments.effect_binding_guard.e55_precommit_authz.metrics import summarize_methods


def strict_predictions(cases):
    return [pred for case in cases for pred in run_methods(case, strict_label_hidden=True)]


def test_strict_decision_path_audit_passes() -> None:
    cases = build_dataset()[:20]
    audit = decision_path_audit(strict_predictions(cases))
    assert audit["passed"]
    assert audit["methods"]["authz_aware_effect_binding_guard"]["object_passed"] == "DeployableE55Input in strict mode"
    assert not audit["methods"]["authz_aware_effect_binding_guard"]["forbidden_fields_observed"]


def test_forbidden_canary_fields_do_not_affect_strict_decisions() -> None:
    case = build_dataset()[0]
    poisoned = replace(
        case,
        expected_decision="DENY" if case.expected_decision != "DENY" else "ALLOW",
        violation_reasons=("poisoned_label",),
        expanded_atoms=(),
        metadata={"atom_authorization": [{"decision": "DENY"}], "gold_args_for_label_only": {"to": ["attacker@example.com"]}},
    )
    original = {pred.method: pred.decision for pred in run_methods(case, strict_label_hidden=True)}
    poisoned_decisions = {pred.method: pred.decision for pred in run_methods(poisoned, strict_label_hidden=True)}
    assert original == poisoned_decisions


def test_ablation_and_slice_tables_cover_required_methods_and_slices() -> None:
    cases = build_dataset()
    predictions = strict_predictions(cases)
    methods = summarize_methods(cases, predictions)
    ablations = ablation_table(methods)
    assert {row["method"] for row in ablations} == set(REQUIRED_METHODS)
    slices = slice_table(cases, predictions)
    slice_names = {row["slice"] for row in slices}
    assert {"unsafe_extra_recipient", "unsafe_public_link", "unsafe_commit_when_draft_only", "unsafe_untrusted_control"} <= slice_names
    assert any(row["n_rows"] > 0 for row in slices if row["slice"] == "unsafe_extra_recipient")


def test_resource_renaming_preserves_expected_decisions_and_metrics() -> None:
    cases = build_dataset()[:50]
    renamed = [renamed_case(case) for case in cases]
    assert [case.expected_decision for case in cases] == [case.expected_decision for case in renamed]
    sanity = sanity_checks(cases, strict_predictions(cases), summarize_methods(cases, strict_predictions(cases)), {"metrics_equal": True, "changed_decision_count": 0})
    assert sanity["resource_renaming"]["metrics_stable"]


def test_spot_audit_packet_has_30_rows_and_required_fields() -> None:
    packet = spot_audit_packet(build_dataset())
    assert len(packet) == 30
    required = {"task", "authorization_context", "tool_call", "expanded_atoms", "expected_decision", "violation_reasons", "deployable_input"}
    assert required <= set(packet[0])


def test_derived_slice_flags_are_available() -> None:
    cases = build_dataset()
    counts = {name: sum(slice_flags(case).get(name, False) for case in cases) for name in ("safe_draft_or_read_only", "unsafe_public_link", "unsafe_untrusted_control")}
    assert all(value > 0 for value in counts.values())
