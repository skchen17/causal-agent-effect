from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
AGENTDOJO_SITE_PACKAGES = ROOT / "runs/e75_agentdojo_env/lib/python3.12/site-packages"
if str(AGENTDOJO_SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(AGENTDOJO_SITE_PACKAGES))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_e85_agentdojo_projection_review_packet import build, candidate_payload_hash  # noqa: E402
from run_e85_projection_review_web import ReviewStore  # noqa: E402
from validate_e85_projection_review import validate  # noqa: E402


@pytest.fixture(scope="module")
def packet_rows():
    rows, summary, freeze = build()
    return rows, summary, freeze


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def completed_rows(rows: list[dict]) -> list[dict]:
    completed = copy.deepcopy(rows)
    for row in completed:
        review = row["review"]
        review.update({
            "reviewer_anonymous_id": "REVIEWER_TEST",
            "review_date": "2026-07-13",
            "implementation_inspected": True,
            "state_mutation_paths_verified": True,
            "defaults_reviewed": True,
            "interactions_reviewed": True,
            "expansions_reviewed": True,
            "negative_controls_reviewed": True,
            "no_attack_outcomes_or_method_labels_used": True,
            "no_missing_security_effects_confirmed": True,
            "overall_decision": "APPROVE",
            "rationale": "Test fixture confirms the frozen implementation and state projection.",
        })
        for field in review["field_reviews"]:
            field.update({
                "decision": "SECURITY_RELEVANT",
                "role": "other_security_relevant",
                "rationale": "Test fixture classifies the frozen schema field.",
            })
        for projection in review["projection_reviews"]:
            projection.update({
                "decision": "APPROVE",
                "rationale": "Test fixture approves the source-bound candidate projection.",
            })
    return completed


def test_packet_freezes_all_effectful_tool_instances(packet_rows):
    rows, summary, freeze = packet_rows
    assert summary["n_tool_instances"] == 28
    assert summary["n_unique_tools"] == 25
    assert summary["n_candidate_projections"] == 35
    assert len(freeze["tool_instance_keys"]) == 28
    assert len(set(freeze["tool_instance_keys"])) == 28
    assert all(row["candidate_payload_sha256"] == candidate_payload_hash(row) for row in rows)
    assert all(not row["source_evidence"]["relative_path"].startswith("/") for row in rows)
    assert all(row["forbidden_hidden_evidence_present"] is False for row in rows)


def test_complete_approval_compiles_every_instance(tmp_path: Path, packet_rows):
    rows, _, _ = packet_rows
    template = tmp_path / "template.jsonl"
    reviewed = tmp_path / "reviewed.jsonl"
    write_jsonl(template, rows)
    write_jsonl(reviewed, completed_rows(rows))
    summary, compiled = validate(template, reviewed)
    assert summary["status"] == "passed"
    assert summary["n_errors"] == 0
    assert len(compiled) == 28


def test_complete_rejection_is_valid_but_not_compiled(tmp_path: Path, packet_rows):
    rows, _, _ = packet_rows
    completed = completed_rows(rows)
    rejected = completed[0]["review"]
    rejected["overall_decision"] = "REJECT"
    rejected["rationale"] = "The candidate omits a source-visible compound effect."
    rejected["no_missing_security_effects_confirmed"] = False
    rejected["projection_reviews"][0]["decision"] = "REJECT"
    rejected["projection_reviews"][0]["rationale"] = "Rejected by the independent test fixture."
    template = tmp_path / "template.jsonl"
    reviewed = tmp_path / "reviewed.jsonl"
    write_jsonl(template, rows)
    write_jsonl(reviewed, completed)
    summary, compiled = validate(template, reviewed)
    assert summary["status"] == "passed_with_rejections"
    assert summary["review_decision_counts"]["reject"] == 1
    assert len(compiled) == 27


def test_immutable_candidate_tampering_blocks_compilation(tmp_path: Path, packet_rows):
    rows, _, _ = packet_rows
    reviewed_rows = completed_rows(rows)
    reviewed_rows[0]["tool_description"] = "tampered"
    template = tmp_path / "template.jsonl"
    reviewed = tmp_path / "reviewed.jsonl"
    write_jsonl(template, rows)
    write_jsonl(reviewed, reviewed_rows)
    summary, compiled = validate(template, reviewed)
    assert summary["status"] == "blocked_by_incomplete_or_invalid_review"
    assert compiled == []
    assert any("immutable candidate content was changed" in error for error in summary["errors"])


def test_review_store_writes_only_review_fields(tmp_path: Path, packet_rows):
    rows, _, _ = packet_rows
    template = tmp_path / "template.jsonl"
    reviewed = tmp_path / "reviewed.jsonl"
    write_jsonl(template, rows)
    store = ReviewStore(template, reviewed)
    original = rows[0]
    review = completed_rows([original])[0]["review"]
    result = store.save(original["suite"], original["tool_name"], {"review": review})
    assert result["row"]["review"]["overall_decision"] == "APPROVE"
    saved = json.loads(reviewed.read_text(encoding="utf-8").splitlines()[0])
    assert saved["candidate_payload_sha256"] == original["candidate_payload_sha256"]
    assert saved["source_evidence"] == original["source_evidence"]
