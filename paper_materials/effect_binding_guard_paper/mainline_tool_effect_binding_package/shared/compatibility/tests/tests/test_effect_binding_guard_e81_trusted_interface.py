from __future__ import annotations

from src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime import (
    build_typed_resolver_ledger_entry,
    compile_trusted_interface,
)


def reviewed_row():
    return {
        "suite": "workspace",
        "user_task_id": "user_task_1",
        "original_task_sha256": "a" * 64,
        "reviewer_anonymous_id": "R1",
        "review_date": "2026-07-13",
        "authority_tools": {
            "share_file": {
                "recipient": {"mode": "exact", "values": ["alice@example.com"], "source_spans": ["Alice"], "canonical_transform": ""},
                "file_id": {"mode": "resolve", "resolver_id": "resolve::share_file::file_id"},
                "public": {"mode": "forbidden"},
            }
        },
        "resolver_specs": {
            "resolve::share_file::file_id": {
                "read_tool": "search_files",
                "query_constraint": {
                    "arguments": {"query": {"mode": "exact", "values": ["budget"]}},
                    "allow_additional_arguments": False,
                },
                "output_projection": {"kind": "record_list_field", "field": "id"},
                "max_cardinality": 2,
            }
        },
    }


def test_reviewed_row_compiles_to_authority_and_fixed_resolver_catalog() -> None:
    compiled = compile_trusted_interface(reviewed_row())
    assert compiled.manifest.task_id == "workspace/user_task_1"
    assert compiled.manifest.resolver_catalog == frozenset({"resolve::share_file::file_id"})
    assert compiled.manifest.tools["share_file"]["recipient"].exact_values == ("alice@example.com",)


def test_only_exact_reviewed_read_call_builds_typed_ledger_entry() -> None:
    spec = compile_trusted_interface(reviewed_row()).resolver_specs["resolve::share_file::file_id"]
    valid = build_typed_resolver_ledger_entry(
        spec, tool_name="search_files", arguments={"query": "budget"}, result=[{"id": "file-1"}, {"id": "file-2"}]
    )
    wrong_query = build_typed_resolver_ledger_entry(
        spec, tool_name="search_files", arguments={"query": "secrets"}, result=[{"id": "file-x"}]
    )
    wrong_tool = build_typed_resolver_ledger_entry(
        spec, tool_name="get_all_files", arguments={"query": "budget"}, result=[{"id": "file-x"}]
    )
    assert valid == {
        "resolver_id": "resolve::share_file::file_id", "values": ["file-1", "file-2"],
        "typed_projection": True, "provenance": "authorized_read", "read_tool": "search_files",
    }
    assert wrong_query is None
    assert wrong_tool is None


def test_projection_type_and_cardinality_fail_closed() -> None:
    spec = compile_trusted_interface(reviewed_row()).resolver_specs["resolve::share_file::file_id"]
    nested = build_typed_resolver_ledger_entry(
        spec, tool_name="search_files", arguments={"query": "budget"}, result=[{"id": ["nested"]}]
    )
    too_many = build_typed_resolver_ledger_entry(
        spec, tool_name="search_files", arguments={"query": "budget"},
        result=[{"id": "1"}, {"id": "2"}, {"id": "3"}],
    )
    assert nested is None
    assert too_many is None


def test_projection_rejects_non_scalar_runtime_records() -> None:
    class RuntimeRecord:
        pass

    spec = compile_trusted_interface(reviewed_row()).resolver_specs["resolve::share_file::file_id"]
    assert build_typed_resolver_ledger_entry(
        spec,
        tool_name="search_files",
        arguments={"query": "budget"},
        result=[RuntimeRecord()],
    ) is None


def test_record_projection_accepts_structured_runtime_records() -> None:
    class RuntimeRecord:
        def model_dump(self):
            return {"id": "file-1", "title": "Budget"}

    spec = compile_trusted_interface(reviewed_row()).resolver_specs["resolve::share_file::file_id"]
    assert build_typed_resolver_ledger_entry(
        spec,
        tool_name="search_files",
        arguments={"query": "budget"},
        result=[RuntimeRecord()],
    ) == {
        "resolver_id": "resolve::share_file::file_id",
        "values": ["file-1"],
        "typed_projection": True,
        "provenance": "authorized_read",
        "read_tool": "search_files",
    }


def test_unreviewed_canonical_literal_cannot_compile() -> None:
    row = reviewed_row()
    row["authority_tools"]["share_file"]["recipient"]["source_spans"] = []
    row["authority_tools"]["share_file"]["recipient"]["canonical_transform"] = ""
    try:
        compile_trusted_interface(row)
    except ValueError as exc:
        assert "source span" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unreviewed literal compiled")
