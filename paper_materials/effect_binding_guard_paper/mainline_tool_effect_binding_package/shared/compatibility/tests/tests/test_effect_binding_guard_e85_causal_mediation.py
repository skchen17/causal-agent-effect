from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from src.experiments.effect_binding_guard.e85_causal_effect_contract_validation.controlled_suite import (
    atom_policy,
    atomizer_for,
    concrete_policy,
    execute,
    intervention_cases,
)
from src.experiments.effect_binding_guard.e85_causal_effect_contract_validation.evaluator import (
    evaluate_contract,
    summarize_rows,
)


ROOT = Path(__file__).resolve().parents[2]


def evaluate(contract_id: str):
    return evaluate_contract(
        contract_id=contract_id,
        cases=intervention_cases(),
        execute=execute,
        atomize=atomizer_for(contract_id),
        concrete_policy=concrete_policy,
        atom_policy=atom_policy,
    )


def test_complete_contract_mediates_effect_changes_and_placebos() -> None:
    summary = summarize_rows(evaluate("none"))
    assert summary["atom_mediation_recall"] == 1.0
    assert summary["atom_mediation_precision"] == 1.0
    assert summary["surface_invariance_rate"] == 1.0
    assert summary["authorization_flip_agreement"] == 1.0


def test_target_multi_resource_default_and_compound_ablations_create_gaps() -> None:
    for ablation in (
        "omit_target",
        "collapse_multi_resource",
        "omit_default_effect",
        "omit_compound_effect",
    ):
        summary = summarize_rows(evaluate(ablation))
        assert summary["relation_counts"].get("mediation_gap", 0) >= 1
        assert 0.0 <= summary["mediation_gap_rate"] <= 1.0
        assert 0.0 <= summary["effect_change_miss_rate"] <= 1.0


def test_placebo_binding_is_over_sensitive() -> None:
    rows = evaluate("include_placebo")
    placebo = next(row for row in rows if row["case_id"] == "surface-placebo")
    assert placebo["relation"] == "over_sensitive"


def test_default_omission_and_explicit_default_are_invariant() -> None:
    row = next(row for row in evaluate("none") if row["case_id"] == "default-equivalence")
    assert row["relation"] == "true_invariance"


def test_report_runner_writes_bounded_artifacts() -> None:
    script = ROOT / "scripts/run_e85_causal_mediation_checks.py"
    spec = importlib.util.spec_from_file_location("run_e85_causal_mediation_checks", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    report = module.run()
    assert report["status"] == "passed_bounded_finite_model"
    assert report["n_rows"] == 54
    for name in (
        "e85_causal_mediation_report.json",
        "e85_causal_mediation_report.md",
        "e85_causal_mediation_rows.jsonl",
        "e85_causal_mediation_metrics.csv",
    ):
        assert (ROOT / "analysis/results" / name).exists()
