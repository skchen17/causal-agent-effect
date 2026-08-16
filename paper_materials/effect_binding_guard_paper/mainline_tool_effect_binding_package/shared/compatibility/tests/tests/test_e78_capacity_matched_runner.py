from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = next(
    candidate
    for candidate in Path(__file__).resolve().parents
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
SCRIPT = ROOT / "shared/compatibility/scripts/run_e78_capacity_matched_repairs.py"
METHOD_ID = "agentdojo_live_local_no_guard"


def load_module():
    spec = importlib.util.spec_from_file_location("run_e78_capacity_matched", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_spec(*, mode: str = "attack") -> dict:
    return {
        "case_key": "workspace:user_task_0:injection_task_0",
        "method_id": METHOD_ID,
        "display_name": "No defense",
        "suite": "workspace",
        "mode": mode,
        "user_task_id": "user_task_0",
        "injection_task_id": (
            "injection_task_0" if mode == "attack" else None
        ),
        "target_context_window": 73728,
        "target_kv_cache_type": "f16",
    }


def write_payload(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_native_security_true_means_attack_success(tmp_path, monkeypatch) -> None:
    module = load_module()
    result_path = write_payload(
        tmp_path,
        {
            "utility": True,
            "security": True,
            "error": None,
            "messages": [{"role": "assistant", "content": "complete"}],
        },
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "result_candidates", lambda *_: [result_path])

    result = module.inspect_result(tmp_path, run_spec())
    assert result["evaluable"] is True
    assert result["native_injection_goal_achieved"] is True
    assert result["attack_success"] is True


def test_post_tool_empty_is_retained_but_not_scored(tmp_path, monkeypatch) -> None:
    module = load_module()
    result_path = write_payload(
        tmp_path,
        {
            "utility": False,
            "security": False,
            "error": None,
            "messages": [
                {"role": "tool", "content": "large tool result"},
                {"role": "assistant", "content": ""},
            ],
        },
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "result_candidates", lambda *_: [result_path])

    with pytest.raises(ValueError, match="post_tool_empty_continuation"):
        module.inspect_result(tmp_path, run_spec())

    result = module.inspect_result(
        tmp_path, run_spec(), allow_non_evaluable=True
    )
    assert result["evaluable"] is False
    assert result["utility"] is None
    assert result["attack_success"] is None
    assert result["raw_diagnostic_utility"] is False
    assert result["raw_diagnostic_injection_goal_achieved"] is False
    assert result["error_categories"] == ["post_tool_empty_continuation"]


def test_summary_reports_evaluable_rates_and_all_key_bounds() -> None:
    module = load_module()
    rows = []
    for index in range(97):
        rows.append(
            {
                "method_id": METHOD_ID,
                "mode": "benign",
                "utility": index < 50,
                "attack_success": False,
                "error": False,
                "protocol_clean": True,
            }
        )
    for index in range(629):
        evaluable = index != 628
        rows.append(
            {
                "method_id": METHOD_ID,
                "mode": "attack",
                "utility": (index < 100) if evaluable else None,
                "attack_success": (index < 10) if evaluable else None,
                "error": not evaluable,
                "protocol_clean": evaluable,
            }
        )

    result = module.summarize(rows, METHOD_ID)
    assert result["n_benign_evaluable"] == 97
    assert result["n_attack_evaluable"] == 628
    assert result["attack_evaluable_coverage"] == pytest.approx(628 / 629)
    assert result["attack_utility_rate"] == pytest.approx(100 / 628)
    assert result["attack_utility_all_key_lower_bound"] == pytest.approx(100 / 629)
    assert result["attack_utility_all_key_upper_bound"] == pytest.approx(101 / 629)
    assert result["attack_success_rate"] == pytest.approx(10 / 628)
    assert result["attack_success_all_key_lower_bound"] == pytest.approx(10 / 629)
    assert result["attack_success_all_key_upper_bound"] == pytest.approx(11 / 629)
    assert result["error_rows"] == 1


def test_exhausted_cached_case_is_retained_without_rerun(
    tmp_path, monkeypatch
) -> None:
    module = load_module()
    run = run_spec()
    non_evaluable = {
        "evaluable": False,
        "error": True,
        "protocol_clean": False,
        "error_categories": ["post_tool_empty_continuation"],
    }
    monkeypatch.setattr(module, "RUN_ROOT", tmp_path)
    monkeypatch.setattr(
        module,
        "inspect_result",
        lambda *_args, **_kwargs: dict(non_evaluable),
    )
    diagnostic_path = (
        tmp_path
        / "invalid_attempts"
        / module.METHOD_ALIAS[METHOD_ID]
        / hashlib.sha256(run["case_key"].encode()).hexdigest()[:16]
        / "diagnostics.json"
    )
    diagnostic_path.parent.mkdir(parents=True)
    diagnostic_path.write_text(
        json.dumps({"attempts": [{}, {}, {}]}), encoding="utf-8"
    )

    result = module.run_one(run, port=1)
    assert result["evaluable"] is False
    assert result["attempt_count"] == 3
    assert result["runner_status"] == "cached_non_evaluable_after_retries"
