#!/usr/bin/env python3
"""Extract path-free fixed evidence while binding it to raw result hashes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
OUTPUT = PAPER / "reproduction/sanitized_fixed_support.json"

DESCRIPTOR_SOURCE = (
    "experiments/intent-bound-runtime-guard/results/"
    "effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl"
)
PROJECTION_SOURCE = (
    "experiments/human-authority-and-causal-validation/results/"
    "causal-effect-projection-validation/agentdojo-projection-intervention-report.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_object(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(relative)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {relative}")
    return value


def read_jsonl(relative: str) -> list[dict[str, Any]]:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(relative)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise TypeError(f"expected nonempty JSONL objects: {relative}")
    return rows


def require_equal(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ValueError(f"unexpected {name}: expected {expected!r}, got {actual!r}")


def main() -> int:
    descriptor_rows = read_jsonl(DESCRIPTOR_SOURCE)
    projection = read_object(PROJECTION_SOURCE)

    require_equal("projection status", projection.get("status"), "passed_with_projection_gaps")

    evidence_rows = [
        evidence
        for descriptor in descriptor_rows
        for evidence in descriptor["field_counterfactual_evidence"]
    ]
    status_counts: dict[str, int] = {}
    for evidence in evidence_rows:
        for status in evidence["statuses"]:
            status_counts[status] = status_counts.get(status, 0) + 1
    descriptor_extract = {
        "n_registered_tools": sum(row.get("registered") is True for row in descriptor_rows),
        "n_security_fields": sum(len(row["security_fields"]) for row in descriptor_rows),
        "n_non_security_fields": sum(len(row["non_security_fields"]) for row in descriptor_rows),
        "n_field_evidence_rows": len(evidence_rows),
        "n_status_records": sum(status_counts.values()),
        "n_multi_status_fields": sum(len(row["statuses"]) > 1 for row in evidence_rows),
        "sandbox_counterfactual_status_counts": status_counts,
    }
    projection_extract = {
        "eight_field_projection": {
            key: projection["aggregate_by_contract_variant"]["eight_field_projection"][key]
            for key in ("n_cases", "mediation_gaps")
        }
    }

    # These checks make the snapshot fail loudly if a source result changes.
    require_equal("registered tools", descriptor_extract["n_registered_tools"], 25)
    require_equal("security fields", descriptor_extract["n_security_fields"], 67)
    require_equal("non-security fields", descriptor_extract["n_non_security_fields"], 0)
    require_equal("field evidence rows", descriptor_extract["n_field_evidence_rows"], 67)
    require_equal("status records", descriptor_extract["n_status_records"], 68)
    require_equal("multi-status fields", descriptor_extract["n_multi_status_fields"], 1)
    require_equal(
        "descriptor counterfactual counts",
        descriptor_extract["sandbox_counterfactual_status_counts"],
        {
            "effect_changed": 48,
            "effect_invariant": 1,
            "external_request_destination_changes": 1,
            "unresolved_fail_closed": 18,
        },
    )
    require_equal(
        "eight-field projection",
        projection_extract["eight_field_projection"],
        {"n_cases": 80, "mediation_gaps": 15},
    )

    payload = {
        "artifact": "sanitized_fixed_support",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "claim_boundary": (
            "This path-free snapshot contains only fixed paper metrics. Source hashes bind "
            "the extract to raw workspace results; the compact artifact does not expose "
            "machine-specific metadata from those raw reports."
        ),
        "source_hashes": {
            DESCRIPTOR_SOURCE: sha256(ROOT / DESCRIPTOR_SOURCE),
            PROJECTION_SOURCE: sha256(ROOT / PROJECTION_SOURCE),
        },
        "descriptor_registration": descriptor_extract,
        "projection_validation": projection_extract,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "output": str(OUTPUT.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
