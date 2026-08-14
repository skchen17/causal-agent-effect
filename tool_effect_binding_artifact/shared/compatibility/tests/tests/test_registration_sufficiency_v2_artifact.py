"""Integrity gates for the multi-base registration sufficiency artifact."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RESULT = (
    ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
    "registration_sufficiency_audit_v2.json"
)
ROWS = RESULT.with_name("registration_sufficiency_counterfactual_rows_v2.jsonl")


def test_v2_artifact_preserves_every_attempt() -> None:
    report = json.loads(RESULT.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in ROWS.read_text(encoding="utf-8").splitlines()]
    assert report["status"] == "passed"
    assert len(rows) == report["n_attempts"]
    assert sum(row["classification"] != "invalid_or_unresolved" for row in rows) == report["n_valid"]
    assert dict(sorted(Counter(row["classification"] for row in rows).items())) == report["classification_counts"]


def test_v2_artifact_keeps_unresolved_fields_conservative() -> None:
    report = json.loads(RESULT.read_text(encoding="utf-8"))
    assert report["n_fields"] == 75
    assert report["n_fields_with_valid_base"] == 75
    assert report["n_fields_with_five_valid_distinct_intervention_kinds"] == 38
    assert report["n_fields_with_committed_effect_witness"] == 66
    unresolved = [row for row in report["field_rows"] if row["valid"] == 0]
    assert len(unresolved) == 7
    assert all(not row["committed_effect_witness"] for row in unresolved)
