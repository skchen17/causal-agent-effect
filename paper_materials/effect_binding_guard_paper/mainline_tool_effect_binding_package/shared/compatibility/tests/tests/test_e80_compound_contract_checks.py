from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_e80_compound_contract_checks.py"


def load_module():
    spec = importlib.util.spec_from_file_location("e80_compound_contract_checks", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_real_agentdojo_compound_effects_are_covered() -> None:
    report = load_module().run()
    assert report["status"] == "passed_with_scope_boundary"
    assert len(report["agentdojo"]["cases"]) == 4
    assert all(row["actual_subset_of_contract"] for row in report["agentdojo"]["cases"])
    multi = [row for row in report["agentdojo"]["cases"] if row["participants"]]
    assert all(len(row["actual_atoms"]) == 4 for row in multi)
    no_explicit = [row for row in report["agentdojo"]["cases"] if not row["participants"]]
    assert all(len(row["actual_atoms"]) == 2 for row in no_explicit)


def test_one_field_registration_has_an_interaction_counterexample() -> None:
    interaction = load_module().synthetic_interaction_check()
    assert interaction["one_field_tests_miss_joint_branch"]
    assert interaction["required_registration_extension"] == "pairwise_or_condition-aware_counterfactuals"
