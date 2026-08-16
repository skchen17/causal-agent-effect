from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/compute_usenix27_paired_statistics.py"


def module():
    spec = importlib.util.spec_from_file_location("paired_statistics", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def test_paired_statistics_are_deterministic_and_directional() -> None:
    loaded = module()
    a = {f"c{i}": i < 2 for i in range(10)}
    b = {f"c{i}": i < 8 for i in range(10)}
    first = loaded.compare(a, b, bootstrap_samples=2000, seed=7)
    second = loaded.compare(a, b, bootstrap_samples=2000, seed=7)
    assert first == second
    assert first["n_paired"] == 10
    assert first["paired_bootstrap"]["difference_b_minus_a"] == pytest.approx(0.6)
    assert first["exact_mcnemar"]["discordant"] == 6


def test_key_mismatch_and_duplicate_inputs_fail() -> None:
    loaded = module()
    with pytest.raises(ValueError, match="paired key mismatch"):
        loaded.compare({"a": True}, {"b": True}, bootstrap_samples=10)


def test_holm_adjustment_is_monotone() -> None:
    adjusted = module().holm({"x": 0.01, "y": 0.03, "z": 0.2})
    assert adjusted["x"] <= adjusted["y"] <= adjusted["z"]
    assert all(0 <= value <= 1 for value in adjusted.values())
