from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/analyze_e77_failure_taxonomy.py"


def module():
    spec = importlib.util.spec_from_file_location("e77_failure_taxonomy", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


def test_taxonomy_reconciles_official_metrics_without_payloads() -> None:
    report = module().build()
    assert report["status"] == "passed"
    assert report["official_cases"] == 726
    assert report["modes"]["benign"]["n"] == 97
    assert report["modes"]["benign"]["utility_successes"] == 33
    assert report["modes"]["attack"]["n"] == 629
    assert report["modes"]["attack"]["utility_successes"] == 207
    assert report["security_check"] == {"attack_cases": 629, "benchmark_attack_successes": 3}
    assert report["strict_finalizer_reconciliation"]["passed"] is True
    assert report["contains_prompts_or_model_outputs"] is False


def test_every_case_belongs_to_one_mechanistic_stratum() -> None:
    report = module().build()
    for item in report["modes"].values():
        assert sum(item["strata"].values()) == item["n"]
        assert sum(item["utility_failure_strata"].values()) == item["n"] - item["utility_successes"]
