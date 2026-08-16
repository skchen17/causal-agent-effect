from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_e84_authority_review.py"
TEMPLATE = ROOT / "evaluation/e84_authority_manifests/review_packet.template.jsonl"
CATALOG = ROOT / "evaluation/e84_authority_manifests/resolver_catalog.json"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_e84", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def rows() -> list[dict]:
    return [json.loads(line) for line in TEMPLATE.read_text(encoding="utf-8").splitlines() if line.strip()]


def complete_review(source: list[dict]) -> list[dict]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    reviewed = copy.deepcopy(source)
    for row in reviewed:
        row["human_review"].update({
            "reviewer_anonymous_id": "REVIEWER_TEST",
            "review_date": "2026-07-12",
            "original_task_only_confirmed": True,
            "accepted": True,
            "notes": "Test fixture review.",
        })
        for binding in row["candidate_bindings"]:
            review = binding["review"]
            review["decision"] = "APPROVE"
            review["rationale"] = "Required by the original task in this test fixture."
            if binding["mode"] == "exact":
                review["canonical_transform"] = "Reviewer-confirmed identity or canonical transform."
            elif binding["mode"] == "resolve":
                tool_name, metadata = next(
                    (name, item)
                    for name, item in sorted(catalog["suites"][row["suite"]].items())
                    if item["eligible_as_authorized_read"]
                )
                review["resolver"] = {
                    "read_tool": tool_name,
                    "query_constraint": {
                        "arguments": {
                            field: {"mode": "exact", "values": ["test-fixture-value"]}
                            for field in metadata["required_parameter_fields"]
                        },
                        "allow_additional_arguments": False,
                    },
                    "output_projection": {"kind": "list_items", "field": ""},
                    "max_cardinality": 1,
                }
    return reviewed


def write_jsonl(path: Path, source: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in source), encoding="utf-8")


def test_pending_packet_cannot_compile_trusted_manifests(tmp_path: Path) -> None:
    module = load_module()
    pending = tmp_path / "pending.jsonl"
    write_jsonl(pending, rows())
    summary, compiled = module.validate(TEMPLATE, pending)
    assert summary["status"] == "blocked_by_incomplete_or_invalid_review"
    assert summary["compiled_trusted_manifests"] == 0
    assert compiled == []


def test_complete_review_compiles_all_97_manifests(tmp_path: Path) -> None:
    module = load_module()
    reviewed = tmp_path / "reviewed.jsonl"
    write_jsonl(reviewed, complete_review(rows()))
    summary, compiled = module.validate(TEMPLATE, reviewed)
    assert summary["status"] == "passed"
    assert summary["n_errors"] == 0
    assert len(compiled) == 97


def test_explicit_rejections_compile_only_the_accepted_subset(tmp_path: Path) -> None:
    module = load_module()
    source = complete_review(rows())
    source[0]["human_review"]["accepted"] = False
    for binding in source[0]["candidate_bindings"]:
        binding["review"]["decision"] = "REJECT"
        binding["review"]["rationale"] = "Not justified by the original task."
    reviewed = tmp_path / "reviewed-with-rejection.jsonl"
    write_jsonl(reviewed, source)
    summary, compiled = module.validate(TEMPLATE, reviewed)
    assert summary["status"] == "passed_with_rejections"
    assert summary["n_errors"] == 0
    assert summary["task_status_counts"] == {"accepted": 96, "not_accepted": 1}
    assert len(compiled) == 96


def test_candidate_tampering_fails_even_with_completed_review(tmp_path: Path) -> None:
    module = load_module()
    source = complete_review(rows())
    source[0]["candidate_task_goal"] = "tampered goal"
    reviewed = tmp_path / "tampered.jsonl"
    write_jsonl(reviewed, source)
    summary, _ = module.validate(TEMPLATE, reviewed)
    assert summary["status"] == "blocked_by_incomplete_or_invalid_review"
    assert any("immutable candidate payload changed" in error for error in summary["errors"])


def test_approved_resolver_requires_typed_bounded_interface(tmp_path: Path) -> None:
    module = load_module()
    source = complete_review(rows())
    target = next(
        binding
        for row in source
        for binding in row["candidate_bindings"]
        if binding["mode"] == "resolve"
    )
    target["review"]["resolver"]["max_cardinality"] = None
    reviewed = tmp_path / "invalid_resolver.jsonl"
    write_jsonl(reviewed, source)
    summary, _ = module.validate(TEMPLATE, reviewed)
    assert summary["status"] == "blocked_by_incomplete_or_invalid_review"
    assert any("max_cardinality" in error for error in summary["errors"])


def test_effectful_tool_cannot_be_used_as_authorized_read(tmp_path: Path) -> None:
    module = load_module()
    source = complete_review(rows())
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    row = next(row for row in source if any(binding["mode"] == "resolve" for binding in row["candidate_bindings"]))
    target = next(binding for binding in row["candidate_bindings"] if binding["mode"] == "resolve")
    effectful = next(
        name for name, item in catalog["suites"][row["suite"]].items()
        if item["effectful_or_external_by_registry"]
    )
    target["review"]["resolver"]["read_tool"] = effectful
    reviewed = tmp_path / "effectful_resolver.jsonl"
    write_jsonl(reviewed, source)
    summary, _ = module.validate(TEMPLATE, reviewed)
    assert any("effectful or external" in error for error in summary["errors"])


def test_resolver_query_cannot_use_unknown_schema_field(tmp_path: Path) -> None:
    module = load_module()
    source = complete_review(rows())
    target = next(
        binding
        for row in source
        for binding in row["candidate_bindings"]
        if binding["mode"] == "resolve"
    )
    target["review"]["resolver"]["query_constraint"]["arguments"]["not_a_schema_field"] = {
        "mode": "exact", "values": ["x"]
    }
    reviewed = tmp_path / "unknown_query_field.jsonl"
    write_jsonl(reviewed, source)
    summary, _ = module.validate(TEMPLATE, reviewed)
    assert any("unknown fields" in error for error in summary["errors"])
