from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiments.tool_effect_fragmentation.mechanism import build_controlled_mechanism_records, run_mechanism_experiment  # noqa: E402
from src.experiments.tool_effect_fragmentation.phase2_metrics import (  # noqa: E402
    baseline_vs_upper_bound_deltas,
    failure_examples,
    paired_method_delta,
)
from src.experiments.tool_effect_fragmentation.reproduction_audit import audit_external_reproductions  # noqa: E402
from src.experiments.tool_effect_fragmentation.schema import (  # noqa: E402
    AdapterStatus,
    ClaimScope,
    Decision,
    GranularityLevel,
    MethodInputView,
    PerturbationFamily,
    ToolEffectPrediction,
    ToolEffectStressCase,
)


def _case(case_id: str, expected: str, effect: str = "message_sent", tool: str = "send_email") -> ToolEffectStressCase:
    return ToolEffectStressCase(
        case_id=case_id,
        semantic_group_id=case_id.split("_")[0],
        source_system="unit",
        source_case_id=case_id,
        granularity=GranularityLevel.STEP_INVOCATION.value,
        perturbation_type=PerturbationFamily.ORIGINAL.value,
        user_task="Task.",
        tool_inventory=[{"name": tool}],
        tool_call_or_plan={"tool_name": tool, "arguments": {"recipient": "a@example.com"}},
        realized_effect=effect,
        resource="a@example.com",
        risk_label="unsafe" if expected == Decision.DENY.value else "safe",
        expected_decision=expected,
        surface_seen_status="seen",
        trace_view="full",
        adapter_status=AdapterStatus.PROXY_DIAGNOSTIC.value,
        paper_grade_eligible=False,
    )


def _pred(case_id: str, method: str, decision: str, scope: str = ClaimScope.BASELINE.value) -> ToolEffectPrediction:
    return ToolEffectPrediction(
        prediction_id=f"{method}:{case_id}",
        case_id=case_id,
        source_system="unit",
        method_name=method,
        predicted_decision=decision,
        predicted_effect="message_sent",
        predicted_risk_label="unsafe" if decision == Decision.DENY.value else "safe",
        method_input_view=MethodInputView.STEP_TEXT.value,
        claim_scope=scope,
    )


def test_paired_delta_matches_gold_case() -> None:
    cases = [_case("g1_a", Decision.DENY.value), _case("g2_a", Decision.DENY.value)]
    bad = [_pred("g1_a", "bad", Decision.ALLOW.value), _pred("g2_a", "bad", Decision.ALLOW.value)]
    good = [_pred("g1_a", "good", Decision.DENY.value), _pred("g2_a", "good", Decision.DENY.value)]

    delta = paired_method_delta(cases, bad, good, lambda rows, preds: 0.0 if all(p.predicted_decision == Decision.DENY.value for p in preds) else 1.0, bootstrap_iters=10)

    assert delta["baseline_rate"] == 1.0
    assert delta["comparison_rate"] == 0.0
    assert delta["delta"] == -1.0
    assert delta["n_groups"] == 2


def test_baseline_vs_upper_bound_delta_reports_metrics() -> None:
    cases = [_case("g1_a", Decision.DENY.value), _case("g2_a", Decision.ALLOW.value)]
    preds = [
        _pred("g1_a", "tool_name_classifier", Decision.ALLOW.value),
        _pred("g2_a", "tool_name_classifier", Decision.ALLOW.value),
        _pred("g1_a", "execution_evidence_upper_bound", Decision.DENY.value, ClaimScope.UPPER_BOUND.value),
        _pred("g2_a", "execution_evidence_upper_bound", Decision.ALLOW.value, ClaimScope.UPPER_BOUND.value),
    ]

    deltas = baseline_vs_upper_bound_deltas(cases, preds, bootstrap_iters=10)

    assert deltas["fnr"]["delta"] < 0
    assert deltas["unsafe_pre_allow"]["delta"] < 0


def test_failure_examples_have_required_schema() -> None:
    cases = [_case("g1_a", Decision.DENY.value)]
    preds = [_pred("g1_a", "tool_name_classifier", Decision.ALLOW.value)]

    examples = failure_examples(cases, preds)

    assert examples
    required = {
        "failure_type",
        "source_system",
        "method",
        "perturbation_family",
        "expected_decision",
        "predicted_decision",
        "realized_effect",
        "tool_surface",
        "failure_reason",
        "claim_scope",
    }
    assert required <= set(examples[0])


def test_mechanism_experiment_reports_effect_tool_gap() -> None:
    result = run_mechanism_experiment(build_controlled_mechanism_records())

    assert result["n_records"] > 0
    assert result["similarities"]["effect_vs_tool_clustering_gap"] is not None
    assert result["separability"]["effect_balanced_accuracy"]["n_classes"] >= 2


def test_reproduction_audit_has_complete_non_agentdojo_failure_or_candidate() -> None:
    audit = audit_external_reproductions(ROOT)

    assert audit["acceptance_summary"]["non_agentdojo_complete_audit"] is True
    assert "toolsafe" in audit["audits"]
    assert audit["audits"]["toolsafe"]["audit_complete"] is True
    assert audit["audits"]["toolsafe"]["status"] in {"original_method_runnable", "adapter_failed_complete"}


def test_phase2_runner_smoke_outputs_required_reports(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    results_dir = tmp_path / "results"
    experiment_dir = tmp_path / "experiment"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "src.experiments.tool_effect_fragmentation.run_tool_effect_fragmentation_phase2",
            "--max-base-cases",
            "4",
            "--bootstrap-iters",
            "10",
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
    report = results_dir / "tool_effect_fragmentation_phase2_unified.json"
    summary = experiment_dir / "phase2_summary.md"

    assert report.exists()
    assert summary.exists()
    payload = json.loads(report.read_text())
    assert len(payload["answers"]) == 7
    assert payload["acceptance_gates"]["agentdojo_random_vs_heldout_complete"] is True
