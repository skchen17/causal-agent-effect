from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = next(
    candidate
    for candidate in Path(__file__).resolve().parents
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
SCRIPT = (
    ROOT
    / "shared/compatibility/scripts/build_e78_context_fairness_protocol.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("e78_context_fairness", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repair_protocol_has_twelve_unique_cases_and_known_capacities():
    module = load_module()
    specs = module.load_repair_specs()
    assert len(specs) == 12
    assert len({row["case_key"] for row in specs}) == 12
    assert {row["target_context_window"] for row in specs} == {
        73728,
        81920,
        122880,
    }
    assert {row["target_kv_cache_type"] for row in specs} == {"f16", "q8_0"}
    assert sum(row["mode"] == "benign" for row in specs) == 1
    assert sum(row["mode"] == "attack" for row in specs) == 11


def test_main_emits_complete_case_metrics_and_fail_fast_rerun_plan():
    module = load_module()
    assert module.main() == 0

    sensitivity = json.loads(
        (
            ROOT / "analysis/results/e78_uniform_context_complete_case_sensitivity.json"
        ).read_text(encoding="utf-8")
    )
    assert sensitivity["status"] == "passed"
    assert sensitivity["n_case_keys"] == 714
    assert sensitivity["n_benign"] == 96
    assert sensitivity["n_attack"] == 618
    assert len(sensitivity["metrics"]) == 6
    assert all(row["n_total"] == 714 for row in sensitivity["metrics"])
    assert all(row["error_rows"] == 0 for row in sensitivity["metrics"])

    protocol = json.loads(
        (
            ROOT / "analysis/results/e78_capacity_matched_repair_protocol.json"
        ).read_text(encoding="utf-8")
    )
    assert protocol["status"] == "ready"
    assert protocol["n_reference_cases"] == 12
    assert protocol["n_comparison_runs"] == 60
    assert len(protocol["runs"]) == 60
    assert len(
        {(row["case_key"], row["method_id"]) for row in protocol["runs"]}
    ) == 60
