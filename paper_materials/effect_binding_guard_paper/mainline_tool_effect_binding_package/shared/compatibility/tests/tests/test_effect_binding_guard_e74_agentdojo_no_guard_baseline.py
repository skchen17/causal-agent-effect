from __future__ import annotations

from src.experiments.effect_binding_guard.e74_agentdojo_no_guard_baseline import run_e74


def test_raw_saved_run_summary_uses_current_qwen_no_guard_artifact() -> None:
    rows = run_e74.read_jsonl(run_e74.RAW_TRACES)
    source_summary = run_e74.summarize_raw_saved_run(rows)
    assert source_summary["n_rows"] == 1452
    assert source_summary["policy_mode_counts"] == {"none": 726, "normal": 726}
    assert source_summary["mode_counts"] == {"attack": 1258, "benign": 194}
    assert source_summary["real_side_effects_counts"] == {"False": 1452}
    assert source_summary["current_model_rows"] == 1452
    assert source_summary["all_rows_use_current_model_name"] is True

    no_guard_summary = run_e74.summarize_raw_saved_run([row for row in rows if run_e74.is_no_guard_row(row)])
    assert no_guard_summary["n_rows"] == 726
    assert no_guard_summary["mode_counts"] == {"attack": 629, "benign": 97}
    assert no_guard_summary["attack_success_rate_all_attack_rows"] == {"successes": 0, "total": 629, "rate": 0.0}


def test_e61_no_guard_predictions_are_all_allow_and_scored_against_two_label_views() -> None:
    report = run_e74.run()
    assert report["no_guard_saved_run_summary"]["attack_success_rate_all_attack_rows"] == {
        "successes": 0,
        "total": 629,
        "rate": 0.0,
    }
    e61 = report["e61_aligned_subset"]
    assert e61["n_cases"] == 156
    assert e61["no_guard_prediction_counts"] == {"ALLOW": 156}
    assert e61["agentdojo_official_asr_label_counts"] == {"ALLOW": 156}
    assert e61["sidecar_label_counts"] == {"DENY": 134, "ALLOW": 22}
    assert e61["no_guard_vs_agentdojo_official_asr"]["coverage"] == {"successes": 156, "total": 156, "rate": 1.0}
    assert e61["no_guard_vs_agentdojo_official_asr"]["accuracy"] == {"successes": 156, "total": 156, "rate": 1.0}
    assert e61["no_guard_vs_agentdojo_official_asr"]["unsafe_pre_allow"] == {"successes": 0, "total": 0, "rate": None}
    assert e61["no_guard_vs_strict_sidecar_diagnostic"]["unsafe_pre_allow"] == {"successes": 134, "total": 134, "rate": 1.0}


def test_report_records_not_live_official_rerun_boundary() -> None:
    report = run_e74.run()
    assert report["live_official_agentdojo_rerun_performed"] is False
    assert "external/systems/ipiguard" in report["claim_boundary"]
    assert report["outputs"]["predictions_jsonl"].endswith("e74_agentdojo_no_guard_baseline_predictions.jsonl")
