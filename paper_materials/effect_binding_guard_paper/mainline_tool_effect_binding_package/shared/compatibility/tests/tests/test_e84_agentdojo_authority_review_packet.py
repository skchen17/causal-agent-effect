from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "evaluation/e84_authority_manifests/review_packet.jsonl"
TEMPLATE = ROOT / "evaluation/e84_authority_manifests/review_packet.template.jsonl"
SUMMARY = ROOT / "evaluation/e84_authority_manifests/summary.json"


def test_authority_review_packet_is_complete_and_label_hidden() -> None:
    rows = [json.loads(line) for line in PACKET.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert len(rows) == summary["n_tasks"] == 97
    assert summary["suite_counts"] == {"banking": 16, "slack": 21, "travel": 20, "workspace": 40}
    assert summary["reviewed_tasks"] == summary["accepted_tasks"] == 0
    assert TEMPLATE.read_bytes() == PACKET.read_bytes()
    assert all(len(row["candidate_payload_sha256"]) == 64 for row in rows)
    assert all(not row["forbidden_hidden_evidence_present"] for row in rows)
    raw = PACKET.read_text(encoding="utf-8")
    assert "injection_task_" not in raw
    assert '"security"' not in raw and '"utility"' not in raw and "gold_atoms" not in raw


def test_packet_does_not_upgrade_lexical_grounding_to_authority() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["status"] == "awaiting_human_or_trusted_interface_review"
    assert "not authority approval" in summary["claim_boundary"]
