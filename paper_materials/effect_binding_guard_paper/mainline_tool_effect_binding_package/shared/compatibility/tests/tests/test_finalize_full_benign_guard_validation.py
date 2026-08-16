from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
SCRIPT = ROOT / "scripts/finalize_full_benign_guard_validation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("benign_finalizer", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_finalizer_keeps_fixed_denominator_and_abstentions(tmp_path: Path) -> None:
    module = load_module()
    tasks = {"workspace": [f"user_task_{index}" for index in range(97)]}
    protocol = {
        "tasks": tasks,
        "expected_benign_cases_per_method": 97,
        "agentdojo_version": "v1.1.2",
        "model_artifact": "fixed.gguf",
        "model_sha256": "abc",
    }
    (tmp_path / "protocol_manifest.json").write_text(json.dumps(protocol))
    logs = tmp_path / "agentdojo_logs/e84_reviewed_authority/local/workspace"
    for index in range(97):
        path = logs / f"user_task_{index}/none"
        path.mkdir(parents=True)
        (path / "none.json").write_text(
            json.dumps(
                {
                    "suite_name": "workspace",
                    "user_task_id": f"user_task_{index}",
                    "utility": index < 50,
                    "error": None,
                }
            )
        )
    (tmp_path / "e84_runtime_audit.jsonl").write_text(
        json.dumps(
            {
                "event": "precommit_check",
                "decision": "ABSTAIN",
                "manifest_available": False,
                "runtime_executed_tool": False,
            }
        )
        + "\n"
    )
    report = module.finalize(tmp_path)
    assert report["status"] == "passed"
    assert report["utility_successes"] == 50
    assert report["precommit_decision_counts"]["ABSTAIN"] == 1


def test_unsafe_unmanifested_effect_allow_fails_gate(tmp_path: Path) -> None:
    module = load_module()
    tasks = {"workspace": [f"user_task_{index}" for index in range(97)]}
    protocol = {
        "tasks": tasks,
        "expected_benign_cases_per_method": 97,
        "agentdojo_version": "v1.1.2",
        "model_artifact": "fixed.gguf",
        "model_sha256": "abc",
    }
    (tmp_path / "protocol_manifest.json").write_text(json.dumps(protocol))
    logs = tmp_path / "agentdojo_logs/e84_reviewed_authority/local/workspace"
    for index in range(97):
        path = logs / f"user_task_{index}/none"
        path.mkdir(parents=True)
        (path / "none.json").write_text(
            json.dumps(
                {
                    "suite_name": "workspace",
                    "user_task_id": f"user_task_{index}",
                    "utility": True,
                    "error": None,
                }
            )
        )
    (tmp_path / "e84_runtime_audit.jsonl").write_text(
        json.dumps(
            {
                "event": "precommit_check",
                "decision": "ALLOW",
                "manifest_available": False,
                "runtime_executed_tool": True,
                "globally_unprivileged_without_manifest": False,
            }
        )
        + "\n"
    )
    report = module.finalize(tmp_path)
    assert report["status"] == "failed"
    assert report["unsafe_unmanifested_effect_allows"] == 1
