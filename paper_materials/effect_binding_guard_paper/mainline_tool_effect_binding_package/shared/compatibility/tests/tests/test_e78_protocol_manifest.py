from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "analysis/results/e78_qwen32_protocol_manifest.json"


def test_e78_protocol_manifest_is_scrubbed_and_not_a_result() -> None:
    report = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert report["status"] == "running_protocol_frozen"
    assert report["benchmark"]["official_case_keys"] == 726
    assert report["model"]["sha256"] == "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
    assert report["model"]["context_window"] == 65536
    assert len(report["hardware"]) == 2
    assert all(memory["memory_mib"] == 24564 for memory in report["hardware"])
    assert "/data/" not in MANIFEST.read_text(encoding="utf-8")
    assert "not a performance result" in report["claim_boundary"]
