from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiments.tool_effect_fragmentation.io_utils import read_jsonl  # noqa: E402
from src.experiments.tool_effect_fragmentation.phase5_camel import (  # noqa: E402
    STRUCTURAL_VARIANTS,
    build_camel_structural_counterfactuals,
    validate_camel_cases,
)
from src.experiments.tool_effect_fragmentation.phase5_ipiguard import (  # noqa: E402
    VARIANTS,
    build_ipiguard_counterfactuals,
    serialize_dag,
    validate_ipiguard_cases,
)
from src.experiments.tool_effect_fragmentation.phase5_metrics import (  # noqa: E402
    summarize_camel_component,
    summarize_ipiguard_component,
    summarize_pipeline,
)
from src.experiments.tool_effect_fragmentation.phase5_pipeline_worker import case_identity  # noqa: E402
from src.experiments.tool_effect_fragmentation.schema import ClaimScope  # noqa: E402
from src.experiments.tool_effect_fragmentation.run_tool_effect_fragmentation_phase5 import four_suite_complete  # noqa: E402


def test_phase5_claim_scopes_are_explicit() -> None:
    assert ClaimScope.ORIGINAL_PIPELINE_LOCAL_MODEL.value == "original_pipeline_local_model"
    assert ClaimScope.ORIGINAL_COMPONENT_CUSTOM_STRESS.value == "original_component_custom_stress"
    assert ClaimScope.ADAPTER_FAILED.value == "adapter_failed"


def test_ipiguard_counterfactual_core_preserves_effect_and_exposes_effect_change() -> None:
    anchors = read_jsonl(ROOT / "data/agentdojo_effect_verifier_t122_core.jsonl")[:3]
    rows = build_ipiguard_counterfactuals(anchors)
    validation = validate_ipiguard_cases(rows)
    assert validation["errors"] == []
    assert validation["n_cases"] == len(anchors) * len(VARIANTS)
    groups = {}
    for row in rows:
        groups.setdefault(row["counterfactual_group_id"], {})[row["variant"]] = row
    for variants in groups.values():
        original = variants["original"]
        for variant, row in variants.items():
            if variant != "same_tool_different_effect":
                assert row["realized_effect"] == original["realized_effect"]
        changed = variants["same_tool_different_effect"]
        assert changed["candidate_dag"]["nodes"][0]["tool_name"] == original["candidate_dag"]["nodes"][0]["tool_name"]
        assert changed["candidate_dag"] != original["candidate_dag"]
        for variant, row in variants.items():
            visible = json.dumps({"task": row["user_task"], "candidate": row["model_visible_candidate"]})
            if variant != "effect_resource_graph":
                assert row["realized_effect"] not in visible
            if variant not in {"graph_node_format", "effect_resource_graph"}:
                assert row["model_visible_candidate"] is None


def test_ipiguard_dag_roundtrip_serialization_preserves_edges() -> None:
    class Call:
        function = "send_email"
        args = {"recipient": "a@example.com"}

    dag = nx.DiGraph()
    dag.add_node("1", function_call=Call(), depends_on=[])
    dag.add_node("2", function_call=Call(), depends_on=["1"])
    dag.add_edge("1", "2")
    serialized = serialize_dag(dag)
    assert serialized["edges"] == [{"source": "1", "target": "2"}]
    assert serialized["nodes"][1]["depends_on"] == ["1"]


def test_camel_structural_core_separates_policy_coverage_failure() -> None:
    rows = build_camel_structural_counterfactuals()
    validation = validate_camel_cases(rows)
    assert validation["errors"] == []
    assert validation["n_cases"] == validation["n_groups"] * len(STRUCTURAL_VARIANTS)
    groups = {}
    for row in rows:
        groups.setdefault(row["counterfactual_group_id"], {})[row["variant"]] = row
    for variants in groups.values():
        trusted = variants["trusted_source"]["structure"]
        untrusted = variants["untrusted_source"]["structure"]
        changed = {key for key in trusted if trusted.get(key) != untrusted.get(key)}
        assert changed == {"data_source"}
        synced = variants["same_flow_tool_rename_policy_synced"]["structure"]
        assert synced["tool_name"] == synced["policy_name"]
        missing = variants["same_flow_tool_rename_policy_missing"]
        assert missing["expected_failure_type"] == "policy_coverage_failure"
        no_side_effect = variants["no_side_effect_tool"]
        assert no_side_effect["structure"]["effect"] == "no_external_side_effect"
        assert no_side_effect["structure"]["side_effectful"] is False
        assert no_side_effect["same_effect_as_trusted"] is False
    weak_rows = build_camel_structural_counterfactuals(effect_label_mode="weak")
    weak_no_side_effect = [row for row in weak_rows if row["variant"] == "no_side_effect_tool"]
    assert all(row["structure"]["effect"] != "no_external_side_effect" for row in weak_no_side_effect)
    assert all(row["same_effect_as_trusted"] is True for row in weak_no_side_effect)


def test_camel_component_metrics_do_not_count_policy_coverage_as_invariance() -> None:
    cases = build_camel_structural_counterfactuals()
    rows = [
        {
            "case_id": case["case_id"],
            "counterfactual_group_id": case["counterfactual_group_id"],
            "variant": case["variant"],
            "expected_decision": case["expected_decision"],
            "predicted_decision": case["expected_decision"],
        }
        for case in cases
    ]
    result = summarize_camel_component(rows, bootstrap_iters=10)
    assert result["overall_accuracy"]["rate"] == 1.0
    assert result["structural_invariance"]["rate"] == 1.0


def test_phase5_all_rows_forbid_real_side_effects() -> None:
    ipiguard = build_ipiguard_counterfactuals(read_jsonl(ROOT / "data/agentdojo_effect_verifier_t122_core.jsonl")[:2])
    camel = build_camel_structural_counterfactuals()
    assert all(not row["real_side_effects"] for row in [*ipiguard, *camel])
    assert all(not row["tools_executed_in_simulation"] for row in [*ipiguard, *camel])


def test_ipiguard_metrics_separate_topology_from_content_sensitivity() -> None:
    rows = []
    for variant, function_name, arguments, same_effect in (
        ("original", "send_email", {"recipient": "a@example.com"}, True),
        ("tool_rename", "surface_alias__send_email", {"recipient": "a@example.com"}, True),
        ("same_tool_different_effect", "send_email", {"mode": "delete"}, False),
    ):
        rows.append(
            {
                "case_id": variant,
                "counterfactual_group_id": "group",
                "variant": variant,
                "same_effect_as_original": same_effect,
                "parse_valid": True,
                "parsed_dag": {
                    "nodes": [
                        {
                            "id": "1",
                            "function_name": function_name,
                            "arguments": arguments,
                            "depends_on": [],
                        }
                    ],
                    "edges": [],
                },
            }
        )
    result = summarize_ipiguard_component(rows, bootstrap_iters=10)
    assert result["same_effect_topology_consistency"]["rate"] == 1.0
    assert result["same_effect_exact_dag_consistency"]["rate"] == 0.0
    assert result["same_effect_normalized_dag_consistency"]["rate"] == 1.0
    assert result["same_tool_different_effect_topology_sensitivity"]["rate"] == 0.0
    assert result["same_tool_different_effect_content_sensitivity"]["rate"] == 1.0


def test_pipeline_case_identity_supports_resume_without_duplicates() -> None:
    assert case_identity("user_task_1", None) == case_identity("user_task_1", None)
    assert case_identity("user_task_1", "injection_task_1") != case_identity("user_task_1", None)
    assert case_identity("user_task_1", "injection_task_1") != case_identity("user_task_1", "injection_task_2")


def test_ipiguard_non_effect_graph_prompts_hide_normalized_effect_labels() -> None:
    anchors = read_jsonl(ROOT / "data/agentdojo_effect_verifier_t122_core.jsonl")[:2]
    rows = build_ipiguard_counterfactuals(anchors)
    for row in rows:
        visible = json.dumps(
            {"user_task": row["user_task"], "candidate": row["model_visible_candidate"]},
            ensure_ascii=False,
        )
        if row["variant"] != "effect_resource_graph":
            assert row["realized_effect"] not in visible


def test_four_suite_gate_requires_every_full_cross_product_setting() -> None:
    rows = [
        {
            "suite": suite,
            "mode": mode,
            "policy_mode": policy,
            "case_protocol": "full_cross_product",
        }
        for suite in ("workspace", "slack", "travel", "banking")
        for mode in ("benign", "attack")
        for policy in ("none", "normal")
    ]
    assert four_suite_complete(rows, "ipiguard")
    assert not four_suite_complete(rows[:-1], "ipiguard")
    assert not four_suite_complete(rows, "camel")


def test_pipeline_metrics_separate_policy_denials_from_runtime_errors() -> None:
    rows = [
        {"error": None, "injection_task_id": "i1", "utility": True, "attack_success": True, "dag": None},
        {
            "error": {"type": "SecurityPolicyDeniedError"},
            "injection_task_id": "i2",
            "utility": False,
            "attack_success": False,
            "dag": None,
        },
        {
            "error": {"type": "JSONDecodeError"},
            "injection_task_id": "i3",
            "utility": False,
            "attack_success": False,
            "dag": None,
        },
    ]
    result = summarize_pipeline(rows)
    assert result["policy_denial_rate"]["successes"] == 1
    assert result["runtime_error_rate"]["successes"] == 1
    assert result["attack_success_rate"]["total"] == 2
