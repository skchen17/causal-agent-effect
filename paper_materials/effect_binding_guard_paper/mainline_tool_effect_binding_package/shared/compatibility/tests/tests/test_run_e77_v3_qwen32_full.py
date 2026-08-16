from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_e77_v3_qwen32_full.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_e77_v3", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_server_configuration_is_frozen_to_requested_dual_gpu_split() -> None:
    module = load_module()
    command = module.server_command(18083, 65536)
    assert command[command.index("--n_gpu_layers") + 1] == "65"
    index = command.index("--tensor_split")
    assert command[index + 1 : index + 3] == ["0.35", "0.65"]
    assert command[command.index("--n_ctx") + 1] == "65536"


def test_smoke_and_full_use_disjoint_artifact_roots() -> None:
    module = load_module()
    assert module.run_root("smoke") != module.run_root("full")


def test_full_command_uses_new_logdir_without_force_overwrite(tmp_path: Path) -> None:
    module = load_module()
    command = module.live_command("full", tmp_path, 18083, 0)
    assert "--live-force-rerun" not in command
    assert command[command.index("--live-logdir") + 1] == str(tmp_path / "agentdojo_logs")
    assert command[command.index("--live-suites") + 1] == "workspace,slack,travel,banking"
