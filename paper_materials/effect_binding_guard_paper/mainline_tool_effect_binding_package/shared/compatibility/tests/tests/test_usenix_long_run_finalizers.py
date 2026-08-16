from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = (
    ROOT
    / "experiments/intent-bound-runtime-guard/scripts/"
    "counterfactual-atom-envelope-guard"
)


def load(name: str):
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_task_cluster_bootstrap_detects_noninferior_equal_outcomes() -> None:
    module = load("finalize_deepseek_benign_interleaved.py")
    no_guard = {f"task-{index}": [1, 0, 1, 0] for index in range(97)}
    c1f = {key: list(value) for key, value in no_guard.items()}
    result = module.bootstrap_difference(no_guard, c1f, iterations=500)
    assert result["difference_c1f_minus_no_guard"] == 0
    assert result["one_sided_95_lower_bound"] == 0
    assert result["noninferior"] is True


def test_task_cluster_bootstrap_rejects_large_loss() -> None:
    module = load("finalize_deepseek_benign_interleaved.py")
    no_guard = {f"task-{index}": [1, 1, 1, 1] for index in range(97)}
    c1f = {key: [0, 0, 0, 0] for key in no_guard}
    result = module.bootstrap_difference(no_guard, c1f, iterations=500)
    assert result["difference_c1f_minus_no_guard"] == -1
    assert result["noninferior"] is False


def test_exact_mcnemar_known_cases() -> None:
    module = load("finalize_qwen32_matched.py")
    assert module.exact_mcnemar(0, 0) == 1.0
    assert module.exact_mcnemar(5, 0) == 0.0625
    assert module.exact_mcnemar(4, 1) == 0.375


def test_deepseek_runner_marks_placeholder_row_incomplete(tmp_path) -> None:
    module = load("run_deepseek_confirmation.py")
    path = tmp_path / "placeholder.json"
    path.write_text('{"utility": null, "duration": null, "error": null}', encoding="utf-8")
    result = module.summarize([path], "benign")
    assert result["errors"] == 0
    assert result["incomplete"] == 1


def test_qwen_runner_requires_security_boolean_for_attack_row(tmp_path) -> None:
    module = load("run_qwen32_matched_comparison.py")
    path = tmp_path / "partial-attack.json"
    path.write_text('{"utility": true, "security": null, "error": null}', encoding="utf-8")
    result = module.summarize([path], "attack")
    assert result["errors"] == 0
    assert result["incomplete"] == 1
