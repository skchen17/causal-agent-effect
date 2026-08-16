from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.experiments.effect_binding_guard.e68_llm_counterfactual_atom_field_stress.run_e68 import load_external_cases
from src.experiments.effect_binding_guard.e70_counterfactual_atom_runtime_guard.run_e70 import decision_metrics
from src.experiments.effect_binding_guard.e73_intent_binding_replan_runtime.score_agentdojo_official_labels import (
    build_agentdojo_official_asr_labels,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[5]
RESULTS = PACKAGE_ROOT / "analysis/results"
RAW_TRACES = PACKAGE_ROOT / "data/data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl"
IPIGUARD_REPO = PACKAGE_ROOT / "external/systems/ipiguard"
MODEL_NAME = "Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf"

REPORT_JSON = RESULTS / "e74_agentdojo_no_guard_baseline_report.json"
REPORT_MD = RESULTS / "e74_agentdojo_no_guard_baseline_report.md"
PREDICTIONS_JSONL = RESULTS / "e74_agentdojo_no_guard_baseline_predictions.jsonl"
COMPARISON_CSV = RESULTS / "e74_agentdojo_no_guard_baseline_comparison.csv"
CLAIM_BOUNDARY_MD = RESULTS / "e74_agentdojo_no_guard_baseline_claim_boundary.md"


def main() -> None:
    report = run()
    print(json.dumps({"status": report["status"], "report": str(REPORT_JSON)}, indent=2))


def run() -> dict[str, Any]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    raw_rows = read_jsonl(RAW_TRACES)
    no_guard_rows = [row for row in raw_rows if is_no_guard_row(row)]
    ipiguard_normal_rows = [row for row in raw_rows if str(row.get("policy_mode")) == "normal"]
    cases = load_external_cases(limit=0)
    official_rows = build_agentdojo_official_asr_labels()
    official_by_case = {row["case_id"]: row for row in official_rows}
    missing = sorted({case["case_id"] for case in cases} - set(official_by_case))
    if missing:
        raise RuntimeError(f"Missing AgentDojo saved-run labels for {len(missing)} E61 cases, e.g. {missing[:5]}")

    labels_official = {case["case_id"]: official_by_case[case["case_id"]]["official_decision"] for case in cases}
    labels_sidecar = {case["case_id"]: case["base_label"] for case in cases}
    no_guard_predictions = {case["case_id"]: "ALLOW" for case in cases}
    prediction_rows = build_prediction_rows(cases, official_by_case, labels_official, labels_sidecar, no_guard_predictions)
    write_jsonl(PREDICTIONS_JSONL, prediction_rows)

    e73 = load_e73_comparison()
    comparison_rows = comparison_rows_for_report(
        no_guard_predictions=no_guard_predictions,
        labels_official=labels_official,
        labels_sidecar=labels_sidecar,
        e73=e73,
    )
    write_comparison_csv(comparison_rows)

    report = {
        "experiment": "E74_agentdojo_no_guard_baseline",
        "status": "passed",
        "baseline_type": "saved_no_defense_agentdojo_ipiguard_local_qwen_rescore",
        "model": MODEL_NAME,
        "source_trace_path": str(RAW_TRACES.relative_to(PACKAGE_ROOT)),
        "source_trace_sha256": sha256_file(RAW_TRACES) if RAW_TRACES.exists() else "",
        "official_agentdojo_runtime_available_in_package": IPIGUARD_REPO.exists(),
        "agentdojo_python_import_available": importlib.util.find_spec("agentdojo") is not None,
        "live_official_agentdojo_rerun_performed": False,
        "live_rerun_blocker": live_rerun_blocker(),
        "source_file_summary": summarize_raw_saved_run(raw_rows),
        "no_guard_saved_run_summary": summarize_raw_saved_run(no_guard_rows),
        "ipiguard_normal_saved_run_summary": summarize_raw_saved_run(ipiguard_normal_rows),
        "e61_aligned_subset": {
            "n_cases": len(cases),
            "source": "E61 external deployable subset built from the same saved AgentDojo/IPIGuard local-model source file; the deployable artifact does not preserve policy_mode/component fields.",
            "prediction_rule": "No pre-commit guard: every selected mutating candidate tool call is treated as ALLOW.",
            "sidecar_label_counts": dict(Counter(labels_sidecar.values())),
            "agentdojo_official_asr_label_counts": dict(Counter(labels_official.values())),
            "no_guard_prediction_counts": dict(Counter(no_guard_predictions.values())),
            "no_guard_vs_agentdojo_official_asr": decision_metrics(no_guard_predictions, labels_official),
            "no_guard_vs_strict_sidecar_diagnostic": decision_metrics(no_guard_predictions, labels_sidecar),
        },
        "comparison_rows": comparison_rows,
        "outputs": {
            "report_json": str(REPORT_JSON),
            "report_md": str(REPORT_MD),
            "predictions_jsonl": str(PREDICTIONS_JSONL),
            "comparison_csv": str(COMPARISON_CSV),
            "claim_boundary_md": str(CLAIM_BOUNDARY_MD),
        },
        "claim_boundary": claim_boundary_text(),
    }
    write_json(REPORT_JSON, report)
    write_report_md(report)
    return report


def summarize_raw_saved_run(rows: list[dict[str, Any]]) -> dict[str, Any]:
    attack_rows = [row for row in rows if row.get("mode") == "attack"]
    benign_rows = [row for row in rows if row.get("mode") == "benign"]
    non_error_rows = [row for row in rows if not row.get("error")]
    replay_only_rows = [row for row in rows if row.get("real_side_effects") is False]
    attack_success_rows = [row for row in attack_rows if row.get("attack_success") is True]
    valid_attack_rows = [row for row in attack_rows if not row.get("error") and row.get("real_side_effects") is False]
    valid_attack_success_rows = [row for row in valid_attack_rows if row.get("attack_success") is True]
    return {
        "n_rows": len(rows),
        "mode_counts": dict(Counter(str(row.get("mode")) for row in rows)),
        "suite_counts": dict(Counter(str(row.get("suite")) for row in rows)),
        "component_counts": dict(Counter(str(row.get("component")) for row in rows)),
        "model_counts": dict(Counter(str(row.get("model")) for row in rows)),
        "policy_mode_counts": dict(Counter(str(row.get("policy_mode")) for row in rows)),
        "real_side_effects_counts": dict(Counter(str(row.get("real_side_effects")) for row in rows)),
        "error_counts": dict(Counter(str(bool(row.get("error"))) for row in rows)),
        "utility_counts": dict(Counter(str(row.get("utility")) for row in rows)),
        "security_counts": dict(Counter(str(row.get("security")) for row in rows)),
        "attack_success_counts": dict(Counter(str(row.get("attack_success")) for row in rows)),
        "benign_rows": len(benign_rows),
        "attack_rows": len(attack_rows),
        "non_error_rows": len(non_error_rows),
        "replay_only_rows": len(replay_only_rows),
        "attack_success_rate_all_attack_rows": rate(len(attack_success_rows), len(attack_rows)),
        "attack_success_rate_valid_replay_attack_rows": rate(len(valid_attack_success_rows), len(valid_attack_rows)),
        "current_model_rows": sum(MODEL_NAME in str(row.get("model", "")) for row in rows),
        "all_rows_use_current_model_name": all(MODEL_NAME in str(row.get("model", "")) for row in rows) if rows else False,
    }


def is_no_guard_row(row: dict[str, Any]) -> bool:
    return row.get("component") == "agentdojo_no_defense_local_model" or row.get("policy_mode") == "none"


def build_prediction_rows(
    cases: list[dict[str, Any]],
    official_by_case: dict[str, dict[str, Any]],
    labels_official: dict[str, str],
    labels_sidecar: dict[str, str],
    predictions: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        case_id = case["case_id"]
        official = official_by_case[case_id]
        visible = case["visible"]
        rows.append(
            {
                "case_id": case_id,
                "domain": case.get("domain"),
                "tool_name": visible.get("tool_call", {}).get("tool", "unknown"),
                "prediction": predictions[case_id],
                "agentdojo_official_asr_label": labels_official[case_id],
                "strict_sidecar_label": labels_sidecar[case_id],
                "mode": official.get("mode"),
                "attack": official.get("attack"),
                "attack_success": official.get("attack_success"),
                "utility": official.get("utility"),
                "security": official.get("security"),
                "source_case_id_hash": official.get("source_case_id_hash"),
                "baseline_boundary": "no_guard_allows_selected_mutating_candidate_call",
            }
        )
    return rows


def comparison_rows_for_report(
    *,
    no_guard_predictions: dict[str, str],
    labels_official: dict[str, str],
    labels_sidecar: dict[str, str],
    e73: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = [
        {
            "system": "E74_no_guard",
            "label_source": "agentdojo_official_asr",
            **flatten_metrics(decision_metrics(no_guard_predictions, labels_official)),
        },
        {
            "system": "E74_no_guard",
            "label_source": "strict_sidecar_diagnostic",
            **flatten_metrics(decision_metrics(no_guard_predictions, labels_sidecar)),
        },
    ]
    if e73:
        runtime = e73.get("runtime_results", {})
        rows.append(
            {
                "system": f"E73_{runtime.get('agent_policy', 'unknown')}",
                "label_source": "agentdojo_official_asr",
                **flatten_metrics(runtime.get("agentdojo_official_asr_metrics", {})),
            }
        )
        rows.append(
            {
                "system": f"E73_{runtime.get('agent_policy', 'unknown')}",
                "label_source": "strict_sidecar_diagnostic",
                **flatten_metrics(runtime.get("agent_policy_metrics_not_safety_claim", {})),
            }
        )
    return rows


def load_e73_comparison() -> dict[str, Any]:
    path = RESULTS / "e73_report.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    def metric(name: str, key: str) -> Any:
        value = metrics.get(name, {})
        return value.get(key) if isinstance(value, dict) else ""

    return {
        "n": metrics.get("n", ""),
        "accuracy_successes": metric("accuracy", "successes"),
        "accuracy_total": metric("accuracy", "total"),
        "accuracy_rate": metric("accuracy", "rate"),
        "coverage_successes": metric("coverage", "successes"),
        "coverage_total": metric("coverage", "total"),
        "coverage_rate": metric("coverage", "rate"),
        "abstain_successes": metric("abstain", "successes"),
        "abstain_total": metric("abstain", "total"),
        "abstain_rate": metric("abstain", "rate"),
        "unsafe_pre_allow_successes": metric("unsafe_pre_allow", "successes"),
        "unsafe_pre_allow_total": metric("unsafe_pre_allow", "total"),
        "unsafe_pre_allow_rate": metric("unsafe_pre_allow", "rate"),
        "false_deny_successes": metric("false_deny", "successes"),
        "false_deny_total": metric("false_deny", "total"),
        "false_deny_rate": metric("false_deny", "rate"),
        "n_predictions_available": metrics.get("n_predictions_available", ""),
    }


def write_comparison_csv(rows: list[dict[str, Any]]) -> None:
    fields = [
        "system",
        "label_source",
        "n",
        "accuracy_successes",
        "accuracy_total",
        "accuracy_rate",
        "coverage_successes",
        "coverage_total",
        "coverage_rate",
        "abstain_successes",
        "abstain_total",
        "abstain_rate",
        "unsafe_pre_allow_successes",
        "unsafe_pre_allow_total",
        "unsafe_pre_allow_rate",
        "false_deny_successes",
        "false_deny_total",
        "false_deny_rate",
        "n_predictions_available",
    ]
    COMPARISON_CSV.parent.mkdir(parents=True, exist_ok=True)
    with COMPARISON_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_report_md(report: dict[str, Any]) -> None:
    source = report["source_file_summary"]
    no_guard = report["no_guard_saved_run_summary"]
    normal = report["ipiguard_normal_saved_run_summary"]
    e61 = report["e61_aligned_subset"]
    official = e61["no_guard_vs_agentdojo_official_asr"]
    sidecar = e61["no_guard_vs_strict_sidecar_diagnostic"]
    lines = [
        "# E74 AgentDojo No-Guard Baseline",
        "",
        f"Status: `{report['status']}`.",
        f"Baseline type: `{report['baseline_type']}`.",
        f"Model: `{report['model']}`.",
        f"Source trace: `{report['source_trace_path']}`.",
        f"Live official AgentDojo rerun performed: `{report['live_official_agentdojo_rerun_performed']}`.",
        f"Live rerun blocker: `{report['live_rerun_blocker'] or 'none'}`.",
        "",
        "## Full Saved Source File",
        "",
        f"Rows: `{source['n_rows']}`; modes: `{source['mode_counts']}`; suites: `{source['suite_counts']}`.",
        f"Components: `{source['component_counts']}`; policy modes: `{source['policy_mode_counts']}`.",
        f"Errors: `{source['error_counts']}`; real-side-effect flags: `{source['real_side_effects_counts']}`.",
        "",
        "## No-Guard Component",
        "",
        f"Rows: `{no_guard['n_rows']}`; modes: `{no_guard['mode_counts']}`.",
        f"Attack success over all no-guard attack rows: `{no_guard['attack_success_rate_all_attack_rows']}`.",
        f"Attack success over valid no-guard replay attack rows: `{no_guard['attack_success_rate_valid_replay_attack_rows']}`.",
        f"IPIGuard-normal comparison attack success over all attack rows: `{normal['attack_success_rate_all_attack_rows']}`.",
        "",
        "## E61-Aligned Mutating Subset",
        "",
        f"Cases: `{e61['n_cases']}`.",
        f"Prediction rule: {e61['prediction_rule']}",
        f"AgentDojo official-ASR labels: `{e61['agentdojo_official_asr_label_counts']}`.",
        f"Strict sidecar diagnostic labels: `{e61['sidecar_label_counts']}`.",
        f"No-guard vs official-ASR: `{official}`.",
        f"No-guard vs strict sidecar diagnostic: `{sidecar}`.",
        "",
        "## Boundary",
        "",
        report["claim_boundary"],
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    CLAIM_BOUNDARY_MD.write_text(report["claim_boundary"] + "\n", encoding="utf-8")


def claim_boundary_text() -> str:
    return (
        "E74 is a no-guard baseline over the saved AgentDojo/IPIGuard local-Qwen replay artifact already present in the package. "
        "It separately reports the mixed full saved source file, the pure no-guard component, and the E61-aligned mutating-call subset. The E61-aligned pre-commit "
        "baseline treats every selected candidate side-effectful tool call as ALLOW because no guard mediated the call. This is not "
        "a live official AgentDojo rerun: the package does not contain external/systems/ipiguard. It also does not execute real tools "
        "or external side effects. AgentDojo targeted-ASR labels come from saved replay metadata; strict sidecar labels remain a "
        "diagnostic overreach/provenance view rather than official AgentDojo labels."
    )


def live_rerun_blocker() -> str:
    blockers = []
    if not IPIGUARD_REPO.exists():
        blockers.append("external/systems/ipiguard is absent from this package")
    if importlib.util.find_spec("agentdojo") is None:
        blockers.append("agentdojo is not importable in the current Python environment")
    return "; ".join(blockers)


def rate(successes: int, total: int) -> dict[str, Any]:
    return {"successes": int(successes), "total": int(total), "rate": None if total == 0 else round(successes / total, 3)}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


if __name__ == "__main__":
    main()
