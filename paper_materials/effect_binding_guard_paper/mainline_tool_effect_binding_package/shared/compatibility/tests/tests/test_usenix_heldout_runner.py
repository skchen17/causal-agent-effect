from __future__ import annotations

import json

from src.experiments.effect_binding_guard.e88_agentdojo_attack_dataset import run_deepseek_heldout


def test_heldout_runner_verifies_all_frozen_c1f_sources() -> None:
    hashes = run_deepseek_heldout.verify_frozen_c1f()
    assert "freeze_manifest" in hashes
    assert {
        "policy",
        "runtime_patch",
        "registered_descriptors",
        "runtime_catalog",
        "relation_catalog",
    }.issubset(hashes)


def test_heldout_evaluable_result_rejects_placeholder(tmp_path) -> None:
    path = tmp_path / "row.json"
    path.write_text(
        json.dumps({"error": None, "utility": None, "security": None}),
        encoding="utf-8",
    )
    assert run_deepseek_heldout.evaluable_result(path) is False
    path.write_text(
        json.dumps({"error": None, "utility": True, "security": False}),
        encoding="utf-8",
    )
    assert run_deepseek_heldout.evaluable_result(path) is True
