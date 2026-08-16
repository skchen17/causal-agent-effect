from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiments.tool_effect_fragmentation.access_guards import audit_prediction_access  # noqa: E402
from src.experiments.tool_effect_fragmentation.adapters import build_system_cases, run_baselines  # noqa: E402
from src.experiments.tool_effect_fragmentation.mechanism import build_controlled_mechanism_records  # noqa: E402
from src.experiments.tool_effect_fragmentation.phase3_agentdojo import agentdojo_phase3_analysis, balance_protocols  # noqa: E402
from src.experiments.tool_effect_fragmentation.phase3_evidence import infer_effect_from_observable_evidence, predict_non_oracle_envdiff  # noqa: E402
from src.experiments.tool_effect_fragmentation.phase3_external_smoke import parse_system_output, run_system_smoke  # noqa: E402
from src.experiments.tool_effect_fragmentation.phase3_mechanism import ABLATIONS, permutation_controls, run_phase3_mechanism  # noqa: E402
from src.experiments.tool_effect_fragmentation.phase3_official_stress import (  # noqa: E402
    build_stress_prompt,
    decision_from_parse,
    summarize_by_perturbation,
)
from src.experiments.tool_effect_fragmentation.phase3_reproduction import run_phase3_reproduction_audit  # noqa: E402
from src.experiments.tool_effect_fragmentation.schema import PerturbationFamily, ToolEffectPrediction  # noqa: E402


def test_balanced_protocols_use_common_effect_risk_strata() -> None:
    cases, _ = build_system_cases("agentdojo", ROOT, max_base_cases=4)
    pools = {
        "random": [case for case in cases if case.perturbation_type == PerturbationFamily.ORIGINAL.value],
        "held_out_tool": [case for case in cases if case.perturbation_type == PerturbationFamily.SAME_EFFECT_TOOL_RENAME.value],
        "same_effect_different_tool": [
            case
            for case in cases
            if case.perturbation_type in {PerturbationFamily.SAME_EFFECT_TOOL_RENAME.value, PerturbationFamily.SAME_EFFECT_WRAPPER_TOOL.value}
        ],
    }

    balanced = balance_protocols(pools)
    strata = {
        protocol: {(case.realized_effect, case.risk_label) for case in rows}
        for protocol, rows in balanced.items()
    }

    assert strata["random"] == strata["held_out_tool"] == strata["same_effect_different_tool"]
    assert all(rows for rows in balanced.values())


def test_agentdojo_phase3_reports_subgroups_and_degradation() -> None:
    cases, _ = build_system_cases("agentdojo", ROOT, max_base_cases=4)
    preds = run_baselines(cases)

    result = agentdojo_phase3_analysis(cases, preds, bootstrap_iters=10)

    assert result["methods"]
    assert "tool_name_classifier" in result["methods"]
    assert "subgroups" in result["methods"]["tool_name_classifier"]
    assert "random_vs_heldout_degradation" in result["methods"]["tool_name_classifier"]


def test_phase3_mechanism_has_ablation_bootstrap_and_permutation() -> None:
    result = run_phase3_mechanism(root=ROOT, bootstrap_iters=10, run_local_encoder=False)
    primary = result["backends"][result["primary_backend"]]

    assert set(ABLATIONS).issubset({name.split("::", 1)[1] for name in result["backends"]})
    assert "effect_vs_tool_gap_ci" in primary["bootstrap"]
    assert "effect_label_shuffle_gap" in primary["permutation_controls"]
    assert primary["permutation_controls"]["observed_gap"] is not None


def test_permutation_controls_change_labels_without_crashing() -> None:
    result = permutation_controls(build_controlled_mechanism_records(), bootstrap_iters=5)
    assert "effect_label_shuffle_gap" in result


def test_non_oracle_envdiff_verifier_uses_allowed_fields_and_detects_message() -> None:
    cases, _ = build_system_cases("agentdojo", ROOT, max_base_cases=1)
    case = cases[0]
    effect, status = infer_effect_from_observable_evidence(case.tool_call_or_plan)
    pred = predict_non_oracle_envdiff(case)
    audit = audit_prediction_access(pred)

    assert status in {"observable_envdiff", "insufficient_evidence"}
    assert effect
    assert audit.allowed
    assert "realized_effect" not in pred.accessed_input_fields


def test_phase3_reproduction_audit_does_not_fake_original_method() -> None:
    audit = run_phase3_reproduction_audit(ROOT, allow_model_download=False)

    assert audit["acceptance_summary"]["non_agentdojo_phase3_target_satisfied"] is True
    assert all(
        item["status"]
        in {
            "adapter_failed_complete",
            "original_method_result_available",
            "original_method_custom_stress_available",
            "original_method_smoke_available",
            "local_model_substitute_result_available",
        }
        for item in audit["audits"].values()
    )
    if not (ROOT / "models/Safiron/Safiron").exists():
        assert audit["audits"]["safiron"]["status"] == "adapter_failed_complete"


def test_external_smoke_parsers_and_local_substitute_scope(tmp_path: Path) -> None:
    assert parse_system_output("toolsafe", "<judgment>1.0</judgment>")["valid"]
    assert parse_system_output("safiron", "There are no risks in these actions.")["valid"]
    assert parse_system_output("ipiguard", '{"nodes": [], "edges": []}')["valid"]
    assert parse_system_output("camel", "x = 1\nPOLICY_CHECK: allow")["valid"]

    fake_model = tmp_path / "model.gguf"
    fake_model.write_text("fake")
    result = run_system_smoke(
        ROOT,
        "ipiguard",
        examples=1,
        gguf_path=fake_model,
        n_gpu_layers=0,
        n_ctx=1024,
        max_new_tokens=16,
        max_input_tokens=128,
        skip_official_models=False,
        completion_override=lambda _: '{"nodes": [], "edges": []}',
    )
    assert result["status"] == "smoke_passed"
    assert result["claim_scope"] == "local_model_substitute"
    assert result["rows"][0]["side_effects_executed"] is False


def test_official_stress_prompt_and_decision_mapping() -> None:
    toolsafe_cases, _ = build_system_cases("toolsafe", ROOT, max_base_cases=1)
    safiron_cases, _ = build_system_cases("safiron", ROOT, max_base_cases=1)

    assert "current_action" in build_stress_prompt(ROOT, "toolsafe", toolsafe_cases[0]).lower()
    assert "Risks catalog" in build_stress_prompt(ROOT, "safiron", safiron_cases[0])
    assert decision_from_parse("toolsafe", {"valid": True, "risk_rating": 1.0}) == "DENY"
    assert decision_from_parse("safiron", {"valid": True, "decision": "safe"}) == "ALLOW"


def test_official_stress_reports_each_perturbation() -> None:
    cases, _ = build_system_cases("toolsafe", ROOT, max_base_cases=1)
    predictions = [
        ToolEffectPrediction(
            prediction_id=f"test::{case.case_id}",
            case_id=case.case_id,
            source_system=case.source_system,
            method_name="test",
            predicted_decision=case.expected_decision,
            predicted_effect=case.realized_effect,
            predicted_risk_label=case.risk_label,
        )
        for case in cases
    ]

    result = summarize_by_perturbation(cases, predictions)

    assert set(result) == {case.perturbation_type for case in cases}
    assert all(metrics["n_cases"] > 0 for metrics in result.values())


def test_phase3_runner_smoke_outputs_required_reports(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    results_dir = tmp_path / "results"
    experiment_dir = tmp_path / "experiment"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "src.experiments.tool_effect_fragmentation.run_tool_effect_fragmentation_phase3",
            "--max-base-cases",
            "4",
            "--bootstrap-iters",
            "10",
            "--skip-local-encoder",
            "--data-dir",
            str(data_dir),
            "--results-dir",
            str(results_dir),
            "--experiment-dir",
            str(experiment_dir),
        ],
        cwd=ROOT,
        check=True,
    )
    unified = json.loads((results_dir / "tool_effect_fragmentation_phase3_unified.json").read_text())

    assert len(unified["answers"]) == 10
    assert unified["acceptance_gates"]["agentdojo_phase3_table_complete"] is True
    assert unified["acceptance_gates"]["oracle_non_oracle_evidence_separated"] is True
    assert (experiment_dir / "phase3_summary.md").exists()
