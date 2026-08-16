from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT.parents[1]
    / "experiments/security-analysis-ablation-and-overhead/scripts/"
    "runtime-mechanism-ablation/run-e84-qwen9b-agentdojo-pilot.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("run_e84_subset", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_qwen32_server_uses_both_gpus_and_frozen_context() -> None:
    module = load_module()
    model = module.MODELS["qwen32"]
    command = module.build_server_command(model, 18084, 65536)
    split_index = command.index("--split_mode")
    tensor_index = command.index("--tensor_split")
    context_index = command.index("--n_ctx")
    assert command[split_index + 1] == "1"
    assert command[tensor_index + 1 : tensor_index + 3] == ["0.5", "0.5"]
    assert command[context_index + 1] == "65536"
    assert model["gpu_visible"] == "0,1"


def test_all_subset_methods_use_expected_modules() -> None:
    module = load_module()
    assert module.METHOD_MODULES["no_guard"] is None
    assert "prompt_sandwiching" in module.METHOD_MODULES["prompt_sandwiching"]
    assert "promptarmor" in module.METHOD_MODULES["promptarmor_local"]
    assert "reviewed_runtime" in module.METHOD_MODULES["e84_reviewed_authority"]


def test_benchmark_command_selects_only_requested_tasks() -> None:
    module = load_module()
    command = module.benchmark_command(
        suite="workspace",
        mode="attack",
        task_ids=["user_task_0", "user_task_1"],
        injection_task_id=None,
        method="promptarmor_local",
        logdir=Path("/tmp/e84-test"),
        force_rerun=False,
    )
    assert command.count("--user-task") == 2
    assert "--attack" in command
    module_index = command.index("--module-to-load")
    assert "promptarmor" in command[module_index + 1]
