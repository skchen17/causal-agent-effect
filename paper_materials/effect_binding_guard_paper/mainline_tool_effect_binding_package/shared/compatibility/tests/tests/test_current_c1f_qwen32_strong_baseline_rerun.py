from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "shared/compatibility/scripts/run_current_c1f_qwen32_strong_baseline_rerun.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("current_strong_baseline", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_protocol_covers_current_c1f_and_strong_baselines() -> None:
    runner = load_runner()
    assert runner.METHODS == (
        "no_guard",
        "spotlighting",
        "prompt_sandwiching",
        "promptarmor_local",
        "c1f",
    )
    assert sum(runner.EXPECTED["benign"].values()) == 97
    assert sum(runner.EXPECTED["attack"].values()) == 629
    assert runner.MODEL_SHA256 == "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"


def test_current_c1f_environment_uses_frozen_shadow_and_fail_closed_audit(tmp_path) -> None:
    runner = load_runner()
    env = runner.environment("c1f", tmp_path, 18093)
    assert env["PYTHONPATH"].split(":")[0] == str(runner.SHADOW)
    assert env["E77_POLICY_VARIANT"] == "atom_control_taint_envelope"
    assert env["E77_UNCERTAINTY_POLICY"] == "allow_with_trail"
    assert env["E77_AUDIT_JSONL"].endswith("runtime-audit.jsonl")


def test_baselines_do_not_receive_c1f_policy_inputs(tmp_path) -> None:
    runner = load_runner()
    for method in ("spotlighting", "prompt_sandwiching", "promptarmor_local"):
        env = runner.environment(method, tmp_path / method, 18093)
        assert "E77_REGISTERED_DESCRIPTOR_JSONL" not in env
        assert "E77_RELATION_CATALOG" not in env
        assert env["PYTHONPATH"] == str(runner.ROOT / "code")


def test_paired_metric_is_exact_and_key_checked() -> None:
    runner = load_runner()
    reference = {"a": {"security": True}, "b": {"security": False}}
    candidate = {"a": {"security": False}, "b": {"security": True}}
    result = runner.paired_metric(reference, candidate, "security")
    assert result["reference_only"] == 1
    assert result["method_only"] == 1
    assert result["exact_mcnemar_two_sided_p"] == 1.0
