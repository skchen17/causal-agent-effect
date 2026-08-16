from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SOURCE = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/source/"
    "joint-effect-authority-diagnostic/diagnostic.py"
)
COMPAT = ROOT / "shared/compatibility/code"
if str(COMPAT) not in sys.path:
    sys.path.insert(0, str(COMPAT))
spec = importlib.util.spec_from_file_location("joint_effect_authority_diagnostic", SOURCE)
assert spec and spec.loader
diagnostic = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = diagnostic
spec.loader.exec_module(diagnostic)


def small_catalog() -> dict:
    return {
        "status": "passed",
        "suites": {
            "suite": {
                "write": {
                    "effectful_or_external": True,
                    "fields": {
                        "resource": {"kind": "required"},
                        "payload": {"kind": "required"},
                    },
                    "security_fields": ["resource"],
                    "inactive_values": {},
                },
                "read": {
                    "effectful_or_external": False,
                    "fields": {"query": {"kind": "required"}},
                    "security_fields": [],
                    "inactive_values": {},
                },
            }
        },
    }


def small_projections() -> dict:
    return {
        ("suite", "write"): {
            "suite": "suite",
            "tool_name": "write",
            "field_classification": {
                "resource": {"decision": "SECURITY_RELEVANT"},
                "payload": {"decision": "SECURITY_RELEVANT"},
            },
            "security_effect_projections": [{"operation": "write"}],
        }
    }


def benign_payload(value: str = "allowed", *, utility: bool = True) -> dict:
    return {
        "suite_name": "suite",
        "user_task_id": "task",
        "injection_task_id": None,
        "attack_type": None,
        "utility": utility,
        "security": False,
        "error": None,
        "messages": [
            {"role": "user", "content": [{"type": "text", "content": "write allowed"}]},
            {
                "role": "tool",
                "tool_call": {
                    "function": "write",
                    "args": {"resource": value, "payload": "body"},
                },
                "content": [{"type": "text", "content": "{}"}],
                "error": None,
            },
        ],
    }


def oracle_row(value: str = "allowed") -> dict:
    return {
        "suite": "suite",
        "user_task_id": "task",
        "evaluation_only": True,
        "contains_attack_goal": False,
        "contains_attack_label": False,
        "contains_model_trace": False,
        "ground_truth_calls": [
            {
                "tool_name": "write",
                "arguments": {"resource": value, "payload": "body"},
            }
        ],
    }


def test_source_projection_compiles_independent_security_fields() -> None:
    semantics = diagnostic.tool_semantics(
        small_catalog(), small_projections(), "suite", "write", "source_reviewed_contract"
    )
    assert semantics.available is True
    assert semantics.fields == ("payload", "resource")


def test_missing_source_projection_fails_closed() -> None:
    semantics = diagnostic.tool_semantics(
        small_catalog(), {}, "suite", "write", "source_reviewed_contract"
    )
    assert semantics.available is False
    assert semantics.reason == "source_projection_unavailable"


def test_yaml_tool_result_is_recovered_as_structured_resolver_evidence() -> None:
    result = diagnostic.decode_tool_result(
        [{"type": "text", "content": "- id_: '24'\n  title: Introductory meeting"}]
    )
    assert result == [{"id_": "24", "title": "Introductory meeting"}]


def test_official_oracle_rejects_model_trace_or_attack_material() -> None:
    for field in ("contains_model_trace", "contains_attack_goal", "contains_attack_label"):
        row = oracle_row()
        row[field] = True
        with pytest.raises(ValueError, match="forbidden evidence"):
            diagnostic.build_official_ground_truth_oracle(
                row, small_catalog(), small_projections(), "current_contract"
            )


def test_official_oracle_sidecar_carries_task_identity_hash() -> None:
    manifest = diagnostic.AuthorityManifest(task_id="task", tools={})
    interface = diagnostic.CompiledTrustedInterface(
        manifest=manifest,
        resolver_specs={},
        original_task_sha256="task-hash",
        reviewer_anonymous_id="reviewer",
        review_date="2026-07-30",
    )
    rows = {("suite", "task"): {"original_task_sha256": "task-hash"}}
    interfaces = {("suite", "task"): interface}
    assert diagnostic.oracle_task_hashes_match_interfaces(rows, interfaces)
    rows[("suite", "task")]["original_task_sha256"] = "changed"
    assert not diagnostic.oracle_task_hashes_match_interfaces(rows, interfaces)


def test_official_oracle_allows_expected_value_and_denies_mutation() -> None:
    oracle = diagnostic.build_official_ground_truth_oracle(
        oracle_row(), small_catalog(), small_projections(), "current_contract"
    )
    assert oracle.available and oracle.manifest
    semantics = diagnostic.tool_semantics(
        small_catalog(), small_projections(), "suite", "write", "current_contract"
    )
    interface = diagnostic.CompiledTrustedInterface(
        manifest=oracle.manifest,
        resolver_specs={},
        original_task_sha256="unused",
        reviewer_anonymous_id="diagnostic",
        review_date="2026-07-30",
    )
    allowed = diagnostic._decision(
        semantics,
        {"__tool_name__": "write", "resource": "allowed", "payload": "body"},
        "official_ground_truth_oracle_authority",
        interface,
        oracle,
        [],
        "hash",
    )
    denied = diagnostic._decision(
        semantics,
        {"__tool_name__": "write", "resource": "changed", "payload": "body"},
        "official_ground_truth_oracle_authority",
        interface,
        oracle,
        [],
        "hash",
    )
    assert allowed["decision"] == "ALLOW"
    assert denied["decision"] == "DENY"


def test_output_contract_records_no_llm_or_tool_execution(tmp_path: Path) -> None:
    report = {
        "claim_boundary": "diagnostic only",
        "cells": {
            cell: {
                "n_evaluable": 1,
                "n_cases": 1,
                "coverage": 1.0,
                "successful_benign_traces_retained": 1,
                "successful_benign_traces": 1,
                "successful_benign_trace_retention": 1.0,
                "successful_no_guard_attack_traces_admitted": 0,
                "successful_no_guard_attack_traces": 1,
                "successful_attack_trace_exposure": 0.0,
            }
            for cell in diagnostic.CELL_IDS
        },
        "common_support_case_count": 1,
        "factorial_deltas_on_common_support": {
            "source_contract_minus_current_at_reviewed_authority": 0.0,
            "official_oracle_minus_reviewed_at_current_contract": 0.0,
            "joint_minus_current_current": 0.0,
        },
        "source_current_field_audit": {
            "all_source_reviewed_tools_match_current_security_fields": True
        },
        "authority_agreement_audit": {
            "same_fixed_trace_admissibility": 1,
            "n_cases": 1,
            "reviewed_authority_retained_official_admissible_benign_traces": 1,
            "official_oracle_admissible_successful_benign_traces": 1,
            "utility_success_with_extra_unofficial_effect": 0,
        },
        "successful_attack_scope_audit": {
            "blocked_by_reviewed_authority": 1,
            "with_privileged_calls": 1,
            "without_privileged_calls": 0,
        },
    }
    cases = [
        {
            "case_key": "k",
            "cell_id": "c",
            "decision_counts": {},
            "fixed_trace_admitted": True,
        }
    ]
    calls = [
        {
            "runtime_called_llm": False,
            "tool_executed_by_diagnostic": False,
        }
    ]
    manifest = {"runtime": {"llm_calls": 0, "tool_executions": 0}}
    diagnostic.write_outputs(tmp_path, report, manifest, cases, calls)
    saved = json.loads((tmp_path / "diagnostic-manifest.json").read_text())
    assert saved["runtime"] == {"llm_calls": 0, "tool_executions": 0}
