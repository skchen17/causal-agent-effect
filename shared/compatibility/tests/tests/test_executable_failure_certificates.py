from __future__ import annotations

import json
from pathlib import Path

from shared.compatibility.scripts.extract_executable_failure_certificates import validate


ROOT = Path(__file__).resolve().parents[4]
ROWS = ROOT / "experiments/human-authority-and-causal-validation/results/executable-failure-certificates/failure-certificates.jsonl"


def certificates():
    return [json.loads(line) for line in ROWS.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_six_diverse_certificates_are_present():
    rows = certificates()
    assert len(rows) == 6
    assert {row["category"] for row in rows} == {
        "target-principal", "compound-effects", "qualifier-recurrence",
        "state-dependent", "repeated-effects", "resource-authority-qualifier",
    }


def test_every_certificate_recomputes_the_failure_conjunction():
    for row in certificates():
        validate(row)


def test_certificates_reference_executable_rows():
    for row in certificates():
        assert row["source_row_u"]
        assert row["source_row_v"]
        assert row["source_effect_u"] != row["source_effect_v"]
