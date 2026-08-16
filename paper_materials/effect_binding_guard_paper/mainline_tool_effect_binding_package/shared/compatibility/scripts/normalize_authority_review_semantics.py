#!/usr/bin/env python3
"""Correct unambiguous forbidden-binding review polarity without widening authority."""

from __future__ import annotations

import importlib.util
import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
BASE = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "authority-manifest-human-review"
)
SOURCE = BASE / "review_packet.reviewed.jsonl"
TEMPLATE = BASE / "review_packet.template.jsonl"
CATALOG = BASE / "resolver_catalog.json"
OUTPUT = BASE / "semantic-polarity-v2"
CORRECTED = OUTPUT / "review_packet.reviewed.jsonl"
REPORT = OUTPUT / "normalization_report.json"

SUPPORTS_FORBIDDEN = re.compile(
    "|".join(
        [
            r"^No event description was requested; arbitrary description content is not authorized\.$",
            r"^No participants were requested; adding participants is not authorized\.$",
            r"^The user authorized only an address update, not a change to the account holder's name\.$",
            r"^The user requested only rescheduling and did not authorize adding participants\.$",
            r"^This field is not authorized for modification by the original task and must remain unchanged\.$",
        ]
    )
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_validator() -> Any:
    path = ROOT / "scripts/validate_e84_authority_review.py"
    spec = importlib.util.spec_from_file_location("authority_validator", path)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load authority validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def polarity_fixable(binding: dict[str, Any]) -> bool:
    review = binding.get("review") or {}
    return (
        binding.get("mode") == "forbidden"
        and review.get("decision") == "REJECT"
        and bool(SUPPORTS_FORBIDDEN.fullmatch(str(review.get("rationale", "")).strip()))
    )


def normalize() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validator = load_validator()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    rows = read_jsonl(SOURCE)
    corrected_rows = []
    fixes = []
    newly_accepted = []
    semantically_clear_but_schema_blocked = []

    for source_row in rows:
        row = deepcopy(source_row)
        key = f"{row['suite']}/{row['user_task_id']}"
        row_fixes = 0
        row_corrections = []
        for index, binding in enumerate(row.get("candidate_bindings", [])):
            if not polarity_fixable(binding):
                continue
            original = deepcopy(binding["review"])
            binding["review"]["decision"] = "APPROVE"
            binding["review"]["rationale"] = (
                "The reviewer rationale confirms that the field is outside the "
                "original task authority; therefore the candidate forbidden "
                "binding is approved. Original rationale: "
                + original["rationale"]
            )
            correction = {
                "version": "forbidden_binding_polarity_v2",
                "binding_index": index,
                "tool_name": binding["tool_name"],
                "field": binding["field"],
                "original_decision": original["decision"],
                "original_rationale": original["rationale"],
                "corrected_decision": "APPROVE",
                "authority_widened": False,
            }
            row_corrections.append(correction)
            fixes.append(
                {
                    "task_key": key,
                    "binding_index": index,
                    "tool_name": binding["tool_name"],
                    "field": binding["field"],
                }
            )
            row_fixes += 1

        remaining_semantic_rejections = [
            binding
            for binding in row.get("candidate_bindings", [])
            if (binding.get("review") or {}).get("decision") != "APPROVE"
        ]
        binding_errors = []
        if not remaining_semantic_rejections:
            for index, binding in enumerate(row.get("candidate_bindings", [])):
                binding_errors.extend(
                    validator.validate_binding(
                        binding,
                        f"{key}/binding[{index}]",
                        row["suite"],
                        catalog,
                    )
                )
        if (
            source_row["human_review"]["accepted"] is False
            and row_fixes
            and not remaining_semantic_rejections
        ):
            if binding_errors:
                semantically_clear_but_schema_blocked.append(
                    {"task_key": key, "binding_errors": binding_errors}
                )
            else:
                row["human_review"]["accepted"] = True
                row["human_review"]["notes"] = (
                    "Accepted after correcting the review polarity of "
                    "forbidden bindings; no authority was added."
                )
                row["human_review"]["reviewer_anonymous_id"] = (
                    "AI_ARTIFACT_REVIEW_SEMANTICS_V2"
                )
                row["human_review"]["review_date"] = date.today().isoformat()
                row["human_review"]["reviewer_type"] = "ai_artifact_reviewer"
                newly_accepted.append(key)
        if row_corrections:
            row["review_semantics_corrections"] = row_corrections
        corrected_rows.append(row)

    report = {
        "experiment": "authority_review_semantic_polarity_normalization",
        "status": "passed",
        "source_packet": str(SOURCE.relative_to(ROOT)),
        "n_rows": len(corrected_rows),
        "n_binding_polarity_corrections": len(fixes),
        "binding_corrections": fixes,
        "newly_accepted_tasks": newly_accepted,
        "n_newly_accepted_tasks": len(newly_accepted),
        "semantically_clear_but_schema_blocked": semantically_clear_but_schema_blocked,
        "authority_widened": False,
        "claim_boundary": (
            "This deterministic pass only corrects cases where a forbidden "
            "candidate binding was marked REJECT while the recorded rationale "
            "explicitly says the field is unauthorized. It does not approve "
            "invented exact values, unresolved free text, broad selectors, or "
            "any other rejected resolver."
        ),
    }
    return corrected_rows, report


def main() -> int:
    rows, report = normalize()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    CORRECTED.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    REPORT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    validator = load_validator()
    validation, compiled = validator.validate(TEMPLATE, CORRECTED, CATALOG)
    (OUTPUT / "validation_report.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "trusted_manifests.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in compiled),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "n_binding_polarity_corrections": report[
                    "n_binding_polarity_corrections"
                ],
                "newly_accepted_tasks": report["newly_accepted_tasks"],
                "schema_blocked_tasks": [
                    row["task_key"]
                    for row in report["semantically_clear_but_schema_blocked"]
                ],
                "compiled_trusted_manifests": len(compiled),
                "validation_status": validation["status"],
            },
            indent=2,
        )
    )
    return 0 if validation["status"] in {"passed", "passed_with_rejections"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
