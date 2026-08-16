from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = next(
    candidate
    for candidate in Path(__file__).resolve().parents
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
SCRIPT = ROOT / "scripts/analyze_e78_capacity_matched_statistics.py"


def load_module():
    spec = importlib.util.spec_from_file_location("e78_matched_stats", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(method, mode, index, value, *, error=False):
    return {
        "method_id": method,
        "suite": "workspace",
        "mode": mode,
        "user_task_id": f"user_task_{index}",
        "injection_task_id": "injection_task_0" if mode == "attack" else None,
        "attack_success": value if mode == "attack" else False,
        "utility": value,
        "error": error,
    }


def test_evaluable_pairs_exclude_errors_and_missing_metrics() -> None:
    module = load_module()
    index = {
        module.NO_GUARD: {
            module.case_key(row(module.NO_GUARD, "attack", 0, True)): row(
                module.NO_GUARD, "attack", 0, True
            ),
            module.case_key(row(module.NO_GUARD, "attack", 1, True)): row(
                module.NO_GUARD, "attack", 1, True, error=True
            ),
        },
        module.OURS: {
            module.case_key(row(module.OURS, "attack", 0, False)): row(
                module.OURS, "attack", 0, False
            ),
            module.case_key(row(module.OURS, "attack", 1, False)): row(
                module.OURS, "attack", 1, False
            ),
        },
    }
    paired, left, right = module.evaluable_pairs(
        index, module.OURS, "attack_success"
    )
    assert len(paired) == 1
    assert left == [True]
    assert right == [False]


def test_exact_mcnemar_and_bootstrap_preserve_direction() -> None:
    module = load_module()
    left = [True, True, False, False]
    right = [False, False, False, True]
    exact = module.exact_mcnemar(left, right)
    bootstrap = module.paired_bootstrap(left, right, samples=1000, seed=7)
    assert exact["no_guard_only_success"] == 2
    assert exact["method_only_success"] == 1
    assert bootstrap["difference_method_minus_no_guard"] == pytest.approx(-0.25)


def test_holm_is_monotone() -> None:
    adjusted = load_module().holm({"a": 0.01, "b": 0.03, "c": 0.5})
    assert adjusted["a"] <= adjusted["b"] <= adjusted["c"]
