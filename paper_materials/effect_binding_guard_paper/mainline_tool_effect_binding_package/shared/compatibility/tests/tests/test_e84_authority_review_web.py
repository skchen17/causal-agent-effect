from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_e84_authority_review_web import ReviewStore  # noqa: E402
from validate_e84_authority_review import payload_hash, read_jsonl  # noqa: E402


PACKET_DIR = ROOT / "evaluation/e84_authority_manifests"
TEMPLATE = PACKET_DIR / "review_packet.template.jsonl"
CATALOG = PACKET_DIR / "resolver_catalog.json"


def make_store(tmp_path: Path) -> ReviewStore:
    return ReviewStore(TEMPLATE, tmp_path / "review_packet.reviewed.jsonl", CATALOG)


def human(*, accepted: bool) -> dict:
    return {
        "accepted": accepted,
        "notes": "Reviewed from the original task only.",
        "original_task_only_confirmed": True,
        "review_date": "2026-07-13",
        "reviewer_anonymous_id": "REVIEWER_TEST",
    }


def rejected_reviews(row: dict) -> list[dict]:
    reviews = []
    for binding in row["candidate_bindings"]:
        review = copy.deepcopy(binding["review"])
        review["decision"] = "REJECT"
        review["rationale"] = "The original task does not establish this authority binding."
        reviews.append(review)
    return reviews


def test_save_preserves_immutable_packet_and_writes_all_rows(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    row = store.rows[0]
    original_hash = payload_hash(row)
    result = store.save_task(
        row["suite"],
        row["user_task_id"],
        {"binding_reviews": rejected_reviews(row), "human_review": human(accepted=True)},
    )

    written = read_jsonl(store.reviewed_path)
    assert len(written) == 97
    assert payload_hash(written[0]) == original_hash
    assert written[0]["original_task"] == row["original_task"]
    assert result["task_state"]["status"] == "accepted"
    assert result["progress"]["reviewed_packet_exists"] is True


def test_rejected_binding_marks_completed_task_as_reviewed_rejected(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    row = next(item for item in store.rows if item["candidate_bindings"])
    result = store.save_task(
        row["suite"],
        row["user_task_id"],
        {"binding_reviews": rejected_reviews(row), "human_review": human(accepted=False)},
    )

    assert result["task_state"]["status"] == "reviewed_rejected"
    assert result["task_state"]["decided_bindings"] == len(row["candidate_bindings"])


def test_server_rejects_unknown_review_fields_and_binding_count_changes(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    row = next(item for item in store.rows if item["candidate_bindings"])
    reviews = rejected_reviews(row)
    reviews[0]["hidden_override"] = True
    with pytest.raises(ValueError, match="unsupported fields"):
        store.save_task(
            row["suite"], row["user_task_id"],
            {"binding_reviews": reviews, "human_review": human(accepted=False)},
        )

    with pytest.raises(ValueError, match="count differs"):
        store.save_task(
            row["suite"], row["user_task_id"],
            {"binding_reviews": [], "human_review": human(accepted=False)},
        )


def test_draft_is_saved_but_full_validation_remains_blocked(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    row = next(item for item in store.rows if item["candidate_bindings"])
    pending = [copy.deepcopy(binding["review"]) for binding in row["candidate_bindings"]]
    result = store.save_task(
        row["suite"],
        row["user_task_id"],
        {"binding_reviews": pending, "human_review": human(accepted=False)},
    )

    assert result["task_state"]["status"] == "in_progress"
    validation = store.validate_all()
    assert validation["status"] == "blocked_by_incomplete_or_invalid_review"
    assert validation["n_errors"] > 0


def test_exact_approval_requires_source_span_or_canonical_transform(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    row = next(
        item for item in store.rows
        if item["candidate_bindings"] and all(binding["mode"] == "exact" for binding in item["candidate_bindings"])
    )
    reviews = []
    for binding in row["candidate_bindings"]:
        review = copy.deepcopy(binding["review"])
        review.update({"decision": "APPROVE", "rationale": "Explicitly stated in the task."})
        review["source_spans"] = []
        review["canonical_transform"] = ""
        reviews.append(review)
    result = store.save_task(
        row["suite"], row["user_task_id"],
        {"binding_reviews": reviews, "human_review": human(accepted=False)},
    )

    assert result["task_state"]["status"] == "in_progress"
    assert any("source span or canonical transform" in error for error in result["task_state"]["binding_errors"])


def test_static_review_interface_files_exist() -> None:
    static_dir = PACKET_DIR / "review_web"
    for name in ("index.html", "styles.css", "app.js"):
        path = static_dir / name
        assert path.is_file()
        assert path.stat().st_size > 1_000
    assert "gold" not in (static_dir / "index.html").read_text(encoding="utf-8").lower()
