from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_e80_extended_authority_default_model.py"


def module():
    spec = importlib.util.spec_from_file_location("extended_model", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def test_extended_finite_model_checks_authority_and_defaults() -> None:
    report = module().run()
    assert report["status"] == "passed"
    assert report["sound_cases_checked"] == 8000
    assert report["authority_expansion_cases_rejected"] > 0
    assert report["dynamic_default_cases_abstained"] == report["sound_cases_checked"]
    assert report["omitted_explicit_default_equivalence_cases"] == report["sound_cases_checked"]
    assert set(report["counterexamples"]) == {
        "legacy_omitted_default_without_totalization",
        "llm_proposal_without_independent_bound",
    }
