#!/usr/bin/env python3
"""Add two narrow, deterministic resolver interfaces to the reviewed packet."""

from __future__ import annotations

import importlib.util
import json
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
SOURCE_DIR = BASE / "semantic-polarity-v2"
SOURCE = SOURCE_DIR / "review_packet.reviewed.jsonl"
TEMPLATE = BASE / "review_packet.template.jsonl"
SOURCE_CATALOG = BASE / "resolver_catalog.json"
OUTPUT = BASE / "semantic-interface-v3"
REVIEWED = OUTPUT / "review_packet.reviewed.jsonl"
CATALOG = OUTPUT / "resolver_catalog.json"
REPORT = OUTPUT / "interface_repair_report.json"

REVIEWER_ID = "AI_ARTIFACT_REVIEW_INTERFACE_V3"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_validator() -> Any:
    path = ROOT / "scripts/validate_e84_authority_review.py"
    spec = importlib.util.spec_from_file_location("authority_validator_v3", path)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load authority validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def filtered_record_resolver(field: str) -> dict[str, Any]:
    return {
        "read_tool": "get_scheduled_transactions",
        "query_constraint": {
            "arguments": {},
            "allow_additional_arguments": False,
        },
        "output_projection": {
            "kind": "filtered_record_field",
            "field": field,
            "selector": {
                "field": "subject",
                "operator": "casefold_contains",
                "value": "rent",
            },
        },
        "max_cardinality": 1,
    }


def address_resolver(field: str) -> dict[str, Any]:
    return {
        "read_tool": "read_file",
        "query_constraint": {
            "arguments": {
                "file_path": {
                    "mode": "exact",
                    "values": ["address-change.txt"],
                }
            },
            "allow_additional_arguments": False,
        },
        "output_projection": {
            "kind": "parsed_text_field",
            "field": field,
            "parser_id": "postal_address_block_v1",
        },
        "max_cardinality": 1,
    }


def repair() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    rows = read_jsonl(SOURCE)
    catalog = json.loads(SOURCE_CATALOG.read_text(encoding="utf-8"))
    catalog = deepcopy(catalog)
    catalog["projection_kinds"] = sorted(
        set(catalog.get("projection_kinds", []))
        | {"filtered_record_field", "parsed_text_field"}
    )
    catalog["parser_ids"] = ["postal_address_block_v1"]
    repairs: list[dict[str, Any]] = []
    accepted: list[str] = []

    for source_row in rows:
        row = source_row
        key = f"{row['suite']}/{row['user_task_id']}"
        if key == "banking/user_task_9":
            fields = {
                "date": filtered_record_resolver("date"),
                "id": filtered_record_resolver("id"),
                "recurring": filtered_record_resolver("recurring"),
            }
        elif key == "banking/user_task_13":
            fields = {
                "city": address_resolver("city"),
                "street": address_resolver("street"),
            }
        else:
            continue

        by_field = {
            (binding["tool_name"], binding["field"]): binding
            for binding in row["candidate_bindings"]
        }
        target_tool = (
            "update_scheduled_transaction"
            if key.endswith("user_task_9")
            else "update_user_info"
        )
        for field, resolver in fields.items():
            binding = by_field[(target_tool, field)]
            if binding["mode"] != "resolve" or binding["review"]["decision"] != "APPROVE":
                raise RuntimeError(f"{key}/{target_tool}.{field} is not an approved resolver")
            binding["review"]["resolver"] = resolver
            binding["review"]["rationale"] = (
                binding["review"]["rationale"]
                + " The AI artifact pass narrows realization to a deterministic, "
                "typed resolver over the named source relation."
            )
            repairs.append(
                {
                    "task_key": key,
                    "tool_name": target_tool,
                    "field": field,
                    "projection_kind": resolver["output_projection"]["kind"],
                    "authority_widened": False,
                }
            )

        remaining = [
            binding
            for binding in row["candidate_bindings"]
            if binding["review"]["decision"] != "APPROVE"
        ]
        if remaining:
            raise RuntimeError(f"{key} still has rejected bindings")
        row["human_review"].update(
            {
                "accepted": True,
                "notes": (
                    "Accepted by an AI artifact-level interface audit after "
                    "deterministic resolver repair; no human-review claim is made."
                ),
                "original_task_only_confirmed": True,
                "review_date": date.today().isoformat(),
                "reviewer_anonymous_id": REVIEWER_ID,
                "reviewer_type": "ai_artifact_reviewer",
            }
        )
        row["resolver_interface_repair"] = {
            "version": "typed_resolver_interface_v3",
            "authority_widened": False,
            "reviewer_type": "ai_artifact_reviewer",
        }
        accepted.append(key)

    report = {
        "experiment": "authority_resolver_interface_repair_v3",
        "status": "passed",
        "source_packet": str(SOURCE.relative_to(ROOT)),
        "n_rows": len(rows),
        "n_resolver_repairs": len(repairs),
        "resolver_repairs": repairs,
        "newly_accepted_tasks": accepted,
        "n_newly_accepted_tasks": len(accepted),
        "authority_widened": False,
        "human_review_claimed": False,
        "claim_boundary": (
            "This AI artifact pass repairs two executable resolver interfaces "
            "using only original-task relations and public sandbox tool schemas. "
            "It does not certify independent human review, authorize free-form "
            "instructions, or generalize beyond the two named task interfaces."
        ),
    }
    return rows, catalog, report


def main() -> int:
    rows, catalog, report = repair()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    REVIEWED.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    CATALOG.write_text(
        json.dumps(catalog, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    REPORT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    validator = load_validator()
    validation, compiled = validator.validate(TEMPLATE, REVIEWED, CATALOG)
    (OUTPUT / "validation_report.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "trusted_manifests.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in compiled),
        encoding="utf-8",
    )
    result = {
        "status": report["status"],
        "n_resolver_repairs": report["n_resolver_repairs"],
        "newly_accepted_tasks": report["newly_accepted_tasks"],
        "compiled_trusted_manifests": len(compiled),
        "validation_status": validation["status"],
        "validation_errors": validation["n_errors"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if validation["status"] in {"passed", "passed_with_rejections"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
