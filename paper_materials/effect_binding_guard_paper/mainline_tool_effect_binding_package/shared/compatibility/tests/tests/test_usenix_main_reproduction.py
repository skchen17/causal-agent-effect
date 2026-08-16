"""Regression tests for the active USENIX claim reproducer."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "paper/current-usenix/reproduction/reproduce_main_claims.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reproduce_main_claims", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixed_claims_trace_to_existing_artifacts_and_tables() -> None:
    module = load_module()
    rows = []
    module.fixed_claims(rows)
    assert len(rows) == 187
    assert all(row["status"] == "verified" for row in rows)
    assert all((ROOT / row["source"]).is_file() for row in rows)
    claim_ids = {row["claim_id"] for row in rows}
    assert {
        "PREVALENCE-MULTI-TARGET",
        "BINDING-TS-GUARD-RESOURCE",
        "STRESS-NO-AUTH-UPA",
        "COLLISION-REPAIRED-FULL_GUARD_DECISION_REPRESENTATION-ERROR-LB",
        "FINITE-SOURCE_FULL_EFFECT-PAIRS",
        "TOOLSANDBOX-SOURCE_FULL_EFFECT-OVERPARTITION",
        "REGISTRATION-INVALID",
        "DEEPSEEK-C1F-AU",
        "ATTRIBUTION-ATOM_FIELD-BU",
        "TRANSFER-NO-GUARD-ASR",
        "REFINEMENT-COMPARABLE-EDGES",
        "PROJECTION-COMMON-GAPS",
        "INITIAL-DESCRIPTOR-UNRESOLVED",
        "INITIAL-DESCRIPTOR-EXTERNAL-DESTINATION",
        "INITIAL-DESCRIPTOR-MULTI-STATUS-FIELDS",
        "TOOLSANDBOX-WITNESS-CELLS",
        "REGISTRATION-NO-VALID-MUTATION",
        "DEEPSEEK-ALLOWS",
        "DEEPSEEK-UTILITY-CHURN-NO-GUARD-ONLY",
        "POLICY-VIEW-REGISTERED_FIELD_C1F-TOUCHED",
        "POLICY-VIEW-BENIGN-TOUCHED",
        "TRANSFER-OLDER-PROFILE-PRECOMMIT-CHECKS",
        "AUTHORITY-EVALUATION-CONTEXTS",
        "AUTHORITY-CANONICAL_RAW_ARGUMENTS-AUTHORIZED-WITHHELD",
        "AUTHORITY-VALIDATED_TYPED_EFFECTS-EXACT",
    }.issubset(claim_ids)


def test_sanitized_fixed_support_is_path_free_and_hash_bound() -> None:
    path = ROOT / "paper/current-usenix/reproduction/sanitized_fixed_support.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")
    assert payload["status"] == "passed"
    forbidden_literals = (
        "/data" + "/CSK",
        "/home" + "/user",
        "causal-agent-" + "safety-research",
    )
    assert not any(value in text for value in forbidden_literals)
    assert payload["descriptor_registration"]["n_registered_tools"] == 25
    assert payload["descriptor_registration"]["sandbox_counterfactual_status_counts"] == {
        "effect_changed": 48,
        "effect_invariant": 1,
        "external_request_destination_changes": 1,
        "unresolved_fail_closed": 18,
    }
    assert payload["projection_validation"]["eight_field_projection"] == {
        "mediation_gaps": 15,
        "n_cases": 80,
    }
    assert len(payload["source_hashes"]) == 2
    for relative, expected_hash in payload["source_hashes"].items():
        assert len(expected_hash) == 64
        raw = ROOT / relative
        if raw.is_file():
            assert hashlib.sha256(raw.read_bytes()).hexdigest() == expected_hash


def test_missing_final_artifacts_remain_explicit() -> None:
    module = load_module()
    pending = module.pending_claims([])
    assert {row["artifact"] for row in pending}.issubset(
        {
            "deepseek_repeated_benign",
            "qwen32_matched_full",
            "deepseek_locked_heldout",
            "agentlab_c1f_transfer",
            "current_c1f_closed_loop_four_view",
            "current_c1f_bounded_adaptive",
            "current_c1f_raw_field_attribution",
            "current_c1f_qwen32_strong_baselines",
            "toolsandbox_concrete_atom_authorizer",
        }
    )
    assert all(row["reason"].startswith(("missing", "status=")) for row in pending)


def test_concrete_atom_authorizer_extractor_has_fixed_denominators(monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "require_table_snippets", lambda *_args: None)
    metrics = []
    for method in (
        "whole_call_tool_name",
        "raw_arguments_exact",
        "common_effect_atoms",
        "concrete_effect_atoms",
        "source_effect_oracle",
    ):
        metrics.append(
            {
                "method": method,
                "unsafe_pre_allow": {"successes": 0, "total": 100, "rate": 0.0},
                "safe_false_deny": {"successes": 0, "total": 132, "rate": 0.0},
                "coverage": {"successes": 232, "total": 232, "rate": 1.0},
                "decision_accuracy": {"successes": 232, "total": 232, "rate": 1.0},
            }
        )
    rows = []
    module.add_concrete_atom_authorizer_claims(
        rows,
        {
            "status": "passed",
            "experiment": "toolsandbox_concrete_atom_authorizer_mechanism",
            "mode": "full",
            "n_tools": 5,
            "n_contexts": 32,
            "n_queries": 232,
            "ideal_decisions": {"ALLOW": 132, "DENY": 100},
            "metrics": metrics,
            "gates": {"all_queries_emitted": True},
        },
        "authorizer.json",
        "run_toolsandbox_concrete_atom_authorizer.py",
    )
    assert len(rows) == 25
    assert {row["claim_id"] for row in rows} >= {
        "CONCRETE-AUTHORIZER-QUERIES",
        "CONCRETE-AUTHORIZER-CONCRETE_EFFECT_ATOMS-UPA",
        "CONCRETE-AUTHORIZER-RAW_ARGUMENTS_EXACT-FD",
    }


def test_final_extractors_emit_numeric_claim_rows() -> None:
    module = load_module()
    rows = []
    module.add_deepseek_repeated_claims(
        rows,
        {
            "benchmark": "AgentDojo v1.1.2 benign tasks",
            "aggregates": [
                {
                    "condition": condition,
                    "runs": 4,
                    "task_evaluations": 388,
                    "utility_successes": 300,
                    "mean_utility_rate": 300 / 388,
                }
                for condition in ("no_guard", "spotlighting", "c1f")
            ],
            "task_cluster_bootstrap": {
                "difference_c1f_minus_no_guard": 0.0,
                "one_sided_95_lower_bound": -0.02,
                "noninferior": True,
            },
        },
        "deepseek.json",
        "finalize_deepseek.py",
    )
    module.add_qwen_claims(
        rows,
        {
            "case_keys_per_condition": 726,
            "metrics": [
                {
                    "condition": condition,
                    "n_benign": 97,
                    "benign_utility_successes": 70,
                    "n_attack": 629,
                    "attack_utility_successes": 400,
                    "attack_successes": 5,
                    "errors": 0,
                }
                for condition in ("no_guard", "spotlighting", "c1f")
            ],
        },
        "qwen.json",
        "finalize_qwen.py",
    )
    module.add_heldout_claims(
        rows,
        {
            "benchmark": "AgentDojo v1.1.2",
            "official_validator": True,
            "real_external_side_effects": False,
            "manifest_sha256": "c" * 64,
            "frozen_c1f_source_hashes": {
                "freeze_manifest": "a" * 64,
                "registered_descriptors": "b" * 64,
            },
            "failures": [],
            "summaries": [
                {
                    "method": method,
                    "n": 320,
                    "expected": 320,
                    "errors": 0,
                    "attack_successes": 4,
                    "utility_successes": 200,
                }
                for method in ("no_guard", "spotlighting", "c1f")
            ],
        },
        "heldout.json",
        "run_heldout.py",
    )
    module.add_agentlab_claims(
        rows,
        {
            "experiment": "agentlab_saved_transfer_current_c1f_pair",
            "method": "c1f",
            "official_validator": True,
            "real_external_side_effects": False,
            "model_sha256": "a" * 64,
            "case_manifest_sha256": "b" * 64,
            "c1f_source_hashes": {
                "freeze_manifest": "c" * 64,
                "registered_descriptors": "d" * 64,
            },
            "expected_case_keys": 303,
            "metrics": {
                "n": 303,
                "evaluable": True,
                "attack_successes": 2,
                "utility_successes": 180,
            },
            "comparison_metrics": [
                {
                    "condition": "no_guard",
                    "n": 303,
                    "evaluable": True,
                    "attack_successes": 95,
                    "utility_successes": 180,
                },
                {
                    "condition": "c1f",
                    "n": 303,
                    "evaluable": True,
                    "attack_successes": 2,
                    "utility_successes": 180,
                },
            ],
            "precommit_mediation": {
                "signature_multiset_exact_match": True,
                "executed_tool_result_calls": 1000,
                "precommit_checks": 1000,
                "missing_check_occurrences": 0,
            },
        },
        "agentlab.json",
        "finalize_agentlab.py",
    )
    module.add_four_view_claims(
        rows,
        {
            "experiment": "current_c1f_closed_loop_four_view",
            "n_cases": 321,
            "selection_conditioned": True,
            "gates": {
                "all_selected_keys_present": True,
                "no_error_rows": True,
                "new_variants_emit_precommit_checks": True,
                "no_execution_without_allow": True,
            },
            "aggregates": [
                {
                    "variant": variant,
                    "n_cases": 321,
                    "benign_n": 48,
                    "benign_utility_successes": 35,
                    "attack_n": 273,
                    "attack_utility_successes": 200,
                    "attack_successes": 3,
                    "precommit_audit": (
                        {
                            "precommit_checks": 100,
                            "executed_without_allow": 0,
                        }
                        if variant in {"whole_call_provenance", "effect_only"}
                        else None
                    ),
                }
                for variant in (
                    "no_guard",
                    "whole_call_provenance",
                    "effect_only",
                    "registered_field_c1f",
                )
            ],
        },
        "four-view.json",
        "run_four_view.py",
    )
    module.add_bounded_adaptive_claims(
        rows,
        {
            "experiment": "bounded_public_family_search_current_c1f",
            "locked_cases": 40,
            "variant_rows": 320,
            "current_c1f_source_hashes": {
                "freeze_manifest": "a" * 64,
                "registered_descriptors": "b" * 64,
            },
            "no_guard_source_hashes": {
                "preregistration": "c" * 64,
                "locked_manifest": "d" * 64,
                "old_report": "e" * 64,
                "old_predictions": "f" * 64,
                "declared_model": "0" * 64,
            },
            "model_sha256": "0" * 64,
            "locked_manifest_sha256": "d" * 64,
            "search_metrics": [
                {
                    "method": method,
                    "n": 40,
                    "attack_successes": attack_successes,
                    "terminal_user_utility_successes": utility_successes,
                }
                for method, attack_successes, utility_successes in (
                    ("no_guard", 4, 18),
                    ("ours_e77_effect_diff_runtime", 1, 12),
                )
            ],
            "paired_statistics": {
                "attack_success": {"exact_mcnemar_two_sided_p": 0.375}
            },
        },
        "bounded.json",
        "run_current_c1f_bounded_adaptive.py",
    )
    module.add_raw_field_attribution_claims(
        rows,
        {
            "experiment": "current_c1f_raw_field_attribution",
            "n_cases": 321,
            "selection_conditioned": True,
            "gates": {
                "all_selected_keys_present": True,
                "no_error_rows": True,
                "raw_field_emits_precommit_checks": True,
                "no_execution_without_allow": True,
                "runtime_guard_llm_calls_zero": True,
                "retrospective_exact_trajectory_coverage": True,
            },
            "aggregates": [
                {
                    "variant": "raw_field_taint",
                    "n_cases": 321,
                    "benign_n": 48,
                    "benign_utility_successes": 40,
                    "attack_n": 273,
                    "attack_utility_successes": 200,
                    "attack_successes": 3,
                    "precommit_audit": {
                        "precommit_checks": 100,
                        "executed_without_allow": 0,
                    },
                }
            ],
            "retrospective_same_call": {
                "n_trajectories": 726,
                "n_effectful_call_checks": 1000,
                "decision_disagreements": 30,
                "raw_allow_atom_deny": 20,
                "raw_deny_atom_allow": 10,
                "trajectories_with_disagreement": 25,
            },
        },
        "raw-field.json",
        "run_c1f_raw_field_attribution.py",
    )
    assert len(rows) == 52
    assert 155 + len(rows) == 207
    assert all(row["status"] == "verified" for row in rows)
    assert any(row["claim_id"] == "DEEPSEEK-REPEATED-C1F-NONINFERIOR" for row in rows)
    assert any(row["claim_id"] == "QWEN32-C1F-ASR" and row["denominator"] == 629 for row in rows)
    assert any(row["claim_id"] == "HELDOUT-C1F-ASR" and row["denominator"] == 320 for row in rows)
    assert any(row["claim_id"] == "AGENTLAB-C1F-MISSING-CHECKS" for row in rows)
    assert any(
        row["claim_id"] == "AGENTLAB-NO-GUARD-ASR" and row["denominator"] == 303
        for row in rows
    )
    assert any(
        row["claim_id"] == "C1F-FOUR-VIEW-REGISTERED_FIELD_C1F-ASR"
        and row["denominator"] == 273
        for row in rows
    )
    assert any(
        row["claim_id"] == "BOUNDED-CURRENT-OURS_E77_EFFECT_DIFF_RUNTIME-ASR"
        and row["denominator"] == 40
        for row in rows
    )
    assert any(
        row["claim_id"] == "RAW-FIELD-CLOSED-LOOP-ASR"
        and row["denominator"] == 273
        for row in rows
    )
