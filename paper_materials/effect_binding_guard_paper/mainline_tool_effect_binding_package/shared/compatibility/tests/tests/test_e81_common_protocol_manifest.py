from __future__ import annotations

import json
from pathlib import Path


ROOT = next(
    candidate
    for candidate in Path(__file__).resolve().parents
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
MANIFEST = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "runtime-mechanism-ablation/final_common_protocol_manifest.json"
)
QWEN32_MANIFEST = MANIFEST.with_name("final_common_protocol_manifest_qwen32.json")


def test_e81_reviewed_subset_protocol_is_frozen_but_not_reported_as_result() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = payload["case_manifest"]
    assert payload["status"] == "protocol_frozen_runner_pending"
    assert cases["n_benign_per_row"] == 26
    assert cases["n_attack_per_row"] == 169
    assert cases["n_total_per_row"] == 195
    assert cases["all_official_injection_tasks_for_reviewed_tasks"] is True
    assert sum(cases["suite_task_counts"].values()) == 26
    assert sum(cases["attack_pair_counts"].values()) == 169


def test_e81_main_rows_each_declare_one_change_from_a1() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert set(rows) == {"A0", "A1", "A2", "A7", "A9", "A11", "A12", "A13", "A15"}
    assert rows["A1"]["single_change_from_a1"] is None
    for row_id in set(rows) - {"A1"}:
        assert rows[row_id]["single_change_from_a1"]


def test_e81_qwen32_protocol_uses_the_final_common_checkpoint() -> None:
    payload = json.loads(QWEN32_MANIFEST.read_text(encoding="utf-8"))
    assert payload["model"]["file_name"] == "Qwen3-32B-Q4_K_M.gguf"
    assert payload["model"]["sha256"] == (
        "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
    )
    assert payload["model"]["context_window"] == 65536
    assert payload["case_manifest"]["n_total_per_row"] == 195
