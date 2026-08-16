from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "evaluation/e79_long_horizon/agentlab_saved_attack_manifest.json"
CASES = ROOT / "evaluation/e79_long_horizon/agentlab_saved_attack_cases.jsonl"


def rows():
    return [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_saved_attack_transfer_set_is_exact_and_leakage_free() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data = rows()
    assert manifest["status"] == "frozen_saved_attack_transfer_set"
    assert len(data) == manifest["n_cases"] == 303
    assert Counter(row["suite"] for row in data) == {
        "workspace": 49, "travel": 25, "banking": 144, "slack": 85
    }
    assert manifest["leakage_scan"]["n_violations"] == 0


def test_each_saved_attack_is_hash_bound_and_not_claimed_adaptive_to_ours() -> None:
    import hashlib

    for row in rows():
        path = ROOT / row["saved_attack_path"]
        assert path.exists()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["saved_attack_sha256"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "not generated adaptively against this paper's method" in manifest["claim_boundary"]
