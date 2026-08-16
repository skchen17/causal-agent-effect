from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/materialize_e82_adaptive_attack_cases.py"
SOURCE = ROOT / "runs/e77_agentdojo_official_v112_full_20260712_075718_e77_full_gpu1/local-ours_e77_effect_diff_runtime"


def load_module():
    spec = importlib.util.spec_from_file_location("materialize_e82", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_exact_official_inventory_and_deterministic_480_pair_subset() -> None:
    module = load_module()
    first, summary = module.materialize(SOURCE, 10)
    second, _ = module.materialize(SOURCE, 10)
    assert len(module.base_attack_keys(SOURCE)) == 629
    assert len(first) == 480
    assert [row["case_id"] for row in first] == [row["case_id"] for row in second]
    assert summary["suite_counts"] == {"banking": 10, "slack": 10, "travel": 10, "workspace": 10}
    assert set(summary["attack_counts"].values()) == {40}


def test_manifest_has_hashes_and_predicates_but_no_raw_payloads_or_outcomes() -> None:
    module = load_module()
    rows, summary = module.materialize(SOURCE, 10)
    assert summary["contains_raw_attack_payload"] is False
    assert summary["contains_environment_outcomes"] is False
    for row in rows:
        assert len(row["official_case_key_sha256"]) == 64
        assert len(row["frozen_source_log_sha256"]) == 64
        assert row["success_predicate"]
        assert row["base_payload_in_manifest"] is False
        raw = str(row).lower()
        assert "prompt" not in raw
        assert "model_output" not in raw
