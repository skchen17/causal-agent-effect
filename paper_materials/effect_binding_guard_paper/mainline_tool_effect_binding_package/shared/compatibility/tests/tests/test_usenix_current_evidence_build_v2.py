from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper/current-usenix").is_dir()
    and (candidate / "analysis/results").is_dir()
)
SCRIPT = ROOT / "paper/current-usenix/reproduction/build_current_evidence.py"
OUTPUT = ROOT / "paper/current-usenix/reproduction/current_evidence.json"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "usenix_current_evidence_build_v2", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_current_evidence_retains_context_sensitivity_and_negative_utility() -> None:
    assert load_module().main() == 0
    report = json.loads(OUTPUT.read_text(encoding="utf-8"))

    assert len(report["rows"]) == 324
    assert report["gates"] == {
        "bounded_public_family_search_passed": True,
        "e78_uniform_context_complete_case_sensitivity_passed": True,
        "full_benign_fixed_denominator_passed": True,
        "full_benign_privacy_gate_passed": True,
        "full_benign_utility_failure_retained": True,
        "full_benign_utility_gate_passed": False,
        "full_benign_zero_unmanifested_effect_allows": True,
        "reproduction_artifacts_verified": True,
    }

    claims = {row["claim_id"]: row["value"] for row in report["rows"]}
    assert claims["E78-UNIFORM-714-N_CASE_KEYS"] == 714
    assert claims["E78-UNIFORM-714-OURS-ASR"] == 2 / 618
    assert claims["FULL-BENIGN-N_EXPECTED"] == 97
    assert claims["FULL-BENIGN-UTILITY_SUCCESSES"] == 26
    assert claims["FULL-BENIGN-ABSTAIN"] == 152
    assert claims["FULL-BENIGN-UNSAFE_UNMANIFESTED_EFFECT_ALLOWS"] == 0
    assert claims["FULL-BENIGN-UTILITY_GATE_PASSED"] is False
    assert claims["BOUNDED-ADAPTIVE-NO_GUARD-ATTACK_SUCCESSES"] == 4
    assert (
        claims[
            "BOUNDED-ADAPTIVE-OURS_E77_EFFECT_DIFF_RUNTIME-ATTACK_SUCCESSES"
        ]
        == 1
    )
    assert (
        claims[
            "BOUNDED-ADAPTIVE-ATTACK_SUCCESS-EXACT_MCNEMAR_TWO_SIDED_P"
        ]
        == 0.375
    )
