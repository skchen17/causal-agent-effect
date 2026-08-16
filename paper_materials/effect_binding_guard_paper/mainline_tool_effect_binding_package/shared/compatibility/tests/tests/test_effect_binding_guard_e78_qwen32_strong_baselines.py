from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_e78_qwen32_strong_baselines.py"


def load_e78():
    spec = importlib.util.spec_from_file_location("e78_runner", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_direct_methods_have_expected_import_ids() -> None:
    module = load_e78()
    expected = {
        "no_guard": "agentdojo_live_local_no_guard",
        "transformers_pi_detector": "agentdojo_live_transformers_pi_detector",
        "piguard": "agentdojo_live_piguard",
        "spotlighting": "agentdojo_live_spotlighting_with_delimiting",
        "prompt_sandwiching": "agentdojo_live_prompt_sandwiching",
        "promptarmor_local": "agentdojo_live_promptarmor_local",
        "melon_local": "agentdojo_live_melon_local",
        "ours_e77_effect_diff_runtime": "agentdojo_live_ours_e77_effect_diff_runtime",
    }
    assert {method: module.expected_method_id(method) for method in module.DIRECT_METHODS} == expected


def test_comparable_adapters_are_not_labeled_official_reproductions() -> None:
    module = load_e78()
    for method in ("prompt_sandwiching", "promptarmor_local", "melon_local"):
        _, implementation, evidence = module.METHOD_METADATA[method]
        assert evidence == "comparable_adapter"
        assert "official" not in implementation.lower()


def test_protocol_requires_full_official_case_set() -> None:
    module = load_e78()
    assert module.EXPECTED_CASES == 726
    assert "ours_e77_effect_diff_runtime" in module.DIRECT_METHODS
    assert "no_guard" in module.DIRECT_METHODS


def test_server_command_matches_installed_llama_cpp_split_mode_contract() -> None:
    module = load_e78()
    command = module.build_server_command(18082, 65536)
    split_index = command.index("--split_mode")
    assert command[split_index + 1] == "1"
    tensor_index = command.index("--tensor_split")
    assert command[tensor_index + 1 : tensor_index + 3] == ["0.5", "0.5"]


def test_direct_method_creates_importer_log_directory(tmp_path: Path) -> None:
    module = load_e78()
    module.RUNS = tmp_path / "runs"
    observed = {}

    def fake_run(command, *, env, log_path, timeout=None):
        observed["command"] = command
        observed["log_path"] = log_path

    module.run_command = fake_run
    module.run_direct_method("transformers_pi_detector", 18082, 0)
    assert (module.RUNS / "agentdojo_logs/transformers_pi_detector").is_dir()
    assert observed["log_path"] == module.RUNS / "runner_transformers_pi_detector.log"


def test_attriguard_requires_all_726_protocol_clean_attempts() -> None:
    module = load_e78()
    status = {
        "status": "failed",
        "protocol_clean_imported_official_keys": 716,
        "failed_case_keys": 10,
        "import_report": {"method_key_counts": {"agentdojo_live_attriguard": 726}},
    }
    passed, detail = module.attriguard_protocol_gate(status)
    assert not passed
    assert "clean=716" in detail
