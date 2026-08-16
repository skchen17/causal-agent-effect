from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = next(
    candidate
    for candidate in Path(__file__).resolve().parents
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
RUNNER = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/scripts/"
    "runtime-mechanism-ablation/run-e81-qwen32-runtime-ablations.py"
)
SUMMARIZER = RUNNER.with_name(
    "summarize-e81-qwen32-runtime-ablations.py"
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_e81_runner_freezes_reviewed_subset_and_qwen32_checkpoint() -> None:
    runner = load(RUNNER, "e81_runner")
    smoke = runner.selected_tasks("smoke")
    full = runner.selected_tasks("full")
    assert sum(map(len, smoke.values())) == 4
    assert sum(map(len, full.values())) == 26
    assert smoke["banking"] == ["user_task_14"]
    assert smoke["workspace"] == ["user_task_8"]
    assert runner.MODEL.name == "Qwen3-32B-Q4_K_M.gguf"
    assert runner.MODEL_SHA256 == (
        "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
    )
    assert set(runner.ROWS) == {
        "A0",
        "A1",
        "A2",
        "A7",
        "A9",
        "A11",
        "A12",
        "A13",
        "A15",
    }


def test_e81_runner_loads_patch_for_every_guarded_row_only() -> None:
    runner = load(RUNNER, "e81_runner_command")
    common = {
        "suite": "workspace",
        "mode": "benign",
        "task_ids": ["user_task_0"],
        "injection_task_id": None,
        "logdir": Path("/tmp/e81-test"),
        "force_rerun": False,
    }
    a0 = runner.benchmark_command(row_id="A0", **common)
    a1 = runner.benchmark_command(row_id="A1", **common)
    assert "--module-to-load" not in a0
    assert runner.PATCH_MODULE in a1


def test_e81_paired_statistics_are_exact_and_deterministic() -> None:
    summarizer = load(SUMMARIZER, "e81_summarizer")
    exact = summarizer.exact_mcnemar(
        [True, True, False, False],
        [False, True, True, False],
    )
    assert exact == {
        "a1_only_success": 1,
        "ablation_only_success": 1,
        "discordant": 2,
        "p_value": 1.0,
    }
    assert summarizer.holm({"a": 0.01, "b": 0.20, "c": 0.03}) == {
        "a": 0.03,
        "c": 0.06,
        "b": 0.20,
    }
