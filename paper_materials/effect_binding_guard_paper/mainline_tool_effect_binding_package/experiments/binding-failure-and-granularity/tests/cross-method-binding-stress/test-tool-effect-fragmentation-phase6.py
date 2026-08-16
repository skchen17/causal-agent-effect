from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiments.tool_effect_fragmentation.io_utils import read_jsonl  # noqa: E402
from src.experiments.tool_effect_fragmentation.phase5_camel import build_camel_structural_counterfactuals  # noqa: E402
from src.experiments.tool_effect_fragmentation.phase6_core import (  # noqa: E402
    FORBIDDEN_MAPPER_FIELDS,
    build_human_audit_packets,
    build_controlled_semantic_dags,
    build_ipiguard_semantic_core,
    decompose_camel_misses,
    deterministic_mapper,
    evaluate_semantic_predictions,
    mapper_input,
    summarize_human_audit,
    validate_ipiguard_semantic_core,
)
from src.experiments.tool_effect_fragmentation.phase6_external import external_status  # noqa: E402
from src.experiments.tool_effect_fragmentation.run_tool_effect_fragmentation_phase6 import (  # noqa: E402
    camel_control_dependency_examples,
    camel_label_appendix_table,
    camel_label_delta,
)
from src.experiments.tool_effect_fragmentation.schema import ClaimScope  # noqa: E402


def semantic_cases():
    return build_ipiguard_semantic_core(
        read_jsonl(ROOT / "data/tool_effect_fragmentation/ipiguard_counterfactual_phase5.jsonl")
    )


def test_phase6_semantic_core_has_240_cases_and_fixed_pairs() -> None:
    rows = semantic_cases()
    validation = validate_ipiguard_semantic_core(rows)
    assert validation["errors"] == []
    assert validation["n_cases"] == 240
    assert validation["n_groups"] == 24
    groups = {}
    for row in rows:
        groups.setdefault(row["counterfactual_group_id"], {})[row["semantic_pair_role"]] = row
    for roles in groups.values():
        assert roles["original"]["candidate_dag"] == roles["unauthorized_same_effect"]["candidate_dag"]
        assert roles["resource_mismatch"]["candidate_dag"] == roles["authorized_resource_shift"]["candidate_dag"]
        assert roles["resource_mismatch"]["resource"] == roles["authorized_resource_shift"]["resource"]


def test_phase6_mapper_input_is_label_hidden() -> None:
    for case in semantic_cases():
        inputs = mapper_input(case)
        assert not (set(inputs) & FORBIDDEN_MAPPER_FIELDS)
        text = json.dumps(inputs, ensure_ascii=False)
        assert '"expected_decision"' not in text
        assert '"authorized_effects"' not in text
        assert '"authorized_resources"' not in text


def test_phase6_controlled_semantic_dags_cover_all_cases_without_new_planner_confounds() -> None:
    cases = semantic_cases()
    rows = build_controlled_semantic_dags(
        cases,
        read_jsonl(ROOT / "analysis/results/tool_effect_fragmentation_ipiguard_component_phase5.jsonl"),
    )
    assert len(rows) == 240
    assert all(row.get("parsed_dag") for row in rows)
    assert {row["semantic_dag_source"] for row in rows} == {
        "reused_phase5_original_component",
        "controlled_resource_transform_of_phase5_dag",
        "controlled_reuse_of_phase5_dag",
    }


def test_phase6_deterministic_mapper_detects_effect_authorization_and_resource_pairs() -> None:
    groups = {}
    for row in semantic_cases():
        groups.setdefault(row["counterfactual_group_id"], {})[row["semantic_pair_role"]] = row
    successes = {"effect": 0, "authorization": 0, "resource": 0}
    for roles in groups.values():
        predictions = {role: deterministic_mapper(case) for role, case in roles.items()}
        successes["effect"] += predictions["original"]["predicted_decision"] == "ALLOW" and predictions[
            "same_tool_different_effect"
        ]["predicted_decision"] == "DENY"
        successes["authorization"] += predictions["original"]["predicted_decision"] == "ALLOW" and predictions[
            "unauthorized_same_effect"
        ]["predicted_decision"] == "DENY"
        successes["resource"] += predictions["resource_mismatch"]["predicted_decision"] == "DENY" and predictions[
            "authorized_resource_shift"
        ]["predicted_decision"] == "ALLOW"
    assert successes["effect"] >= 18
    assert successes["authorization"] >= 18
    assert successes["resource"] >= 18


def test_phase6_semantic_metrics_report_explicit_effect_graph_separately() -> None:
    rows = []
    for case in semantic_cases():
        result = deterministic_mapper(case)
        rows.append(
            {
                "case_id": case["case_id"],
                "counterfactual_group_id": case["counterfactual_group_id"],
                "semantic_pair_role": case["semantic_pair_role"],
                "variant": case["variant"],
                "method": "deterministic_effect_resource_mapper",
                "predicted_decision": result["predicted_decision"],
                "predicted_effect": result["predicted_effect"],
                "predicted_resource": result["predicted_resource"],
                "expected_decision": case["expected_decision"],
                "realized_effect": case["realized_effect"],
                "resource": case["resource"],
            }
        )
    result = evaluate_semantic_predictions(rows, bootstrap_iters=10)["deterministic_effect_resource_mapper"]
    assert result["hidden_label_row_metrics"]["n"] == 216


def test_phase6_audit_packets_are_222_and_56_with_required_coverage() -> None:
    primary, secondary = build_human_audit_packets(
        read_jsonl(ROOT / "analysis/results/tool_effect_fragmentation_counterfactual_phase4_audit_packet.jsonl"),
        semantic_cases(),
        build_camel_structural_counterfactuals(),
    )
    assert len(primary) == 222
    assert len(secondary) == 56
    assert {row["audit_source"] for row in primary} == {"phase4", "ipiguard", "camel"}
    assert any(row["proposed_expected_decision"] == "ALLOW" for row in primary)
    assert any(row["proposed_expected_decision"] == "DENY" for row in primary)
    summary = summarize_human_audit(primary, secondary)
    assert summary["status"] == "pending_human_audit"
    assert summary["upgrade_gate"] is False


def test_phase6_camel_decomposition_covers_all_six_control_dependency_misses() -> None:
    cases = build_camel_structural_counterfactuals()
    predictions = read_jsonl(ROOT / "analysis/results/tool_effect_fragmentation_camel_component_phase5.jsonl")
    result = decompose_camel_misses(cases, predictions)
    weak = decompose_camel_misses(build_camel_structural_counterfactuals(effect_label_mode="weak"), predictions)
    assert result["unsafe_miss_count"] == 6
    assert result["misses_by_failure_category"]["control_dependency_violation"]["misses"] == 6
    assert result["not_evaluable_capabilities"] == [
        "effect_mismatch",
        "resource_mismatch",
        "authorization_mismatch",
    ]
    delta = camel_label_delta(result, weak)
    assert delta["changed_rows"] == 6
    assert delta["decision_metric_changed"] is False
    appendix = camel_label_appendix_table(result, weak)
    decision_rows = [row for row in appendix if row["metric"] in {"unsafe_blocked", "safe_false_denial", "unsafe_miss_count"}]
    assert all(row["conclusion"] == "unchanged" for row in decision_rows)
    examples = camel_control_dependency_examples(result, limit=3)
    assert len(examples) == 3
    assert all(example["expected_decision"] == "DENY" and example["predicted_decision"] == "ALLOW" for example in examples)


def test_phase6_claim_scope_includes_external_pipeline_without_upgrading_original_method() -> None:
    assert ClaimScope.ORIGINAL_PIPELINE_EXTERNAL_MODEL.value == "original_pipeline_external_model"


def test_phase6_external_defense_gate_is_false_without_no_defense_results(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    result = external_status(tmp_path)
    assert result["api_key_present"] is False
    assert result["status"] == "pending_missing_deepseek_api_key"
    assert all(not gate["passed"] for gate in result["gates"].values())
    artifact = (tmp_path / "analysis/results/tool_effect_fragmentation_external_pipeline_phase6.json").read_text()
    assert "DEEPSEEK_API_KEY" not in artifact
