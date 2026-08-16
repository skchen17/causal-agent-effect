#!/usr/bin/env python3
"""Strictly freeze existing E78 Qwen3-32B AgentDojo comparison artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT.parents[1]
RESULTS = ROOT / "analysis/results"
RUN_ROOT = ROOT / "runs/e78_qwen32_strong_baselines"
LOG_ROOT = RUN_ROOT / "agentdojo_logs"
CURRENT_METHOD_DIRECTORY = "ours_e77_effect_diff_runtime"
CURRENT_METHOD_LOG_ROOT = (
    PACKAGE_ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-context-repaired/agentdojo_logs"
)
CURRENT_METHOD_REPORT = (
    PACKAGE_ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-context-repaired-report.json"
)
PROTOCOL_MANIFEST = RESULTS / "e78_qwen32_protocol_manifest.json"
ATTR_LEDGER = LOG_ROOT / "attriguard/e75_attriguard_protocol_attempts.jsonl"
EXPECTED_CASES = 726
EXPECTED_SUITES = {"workspace": 280, "slack": 126, "travel": 160, "banking": 160}
NO_GUARD = "agentdojo_live_local_no_guard"

DIRECT_METHODS = {
    "no_guard": (NO_GUARD, "No defense", "official_same_protocol", True),
    "melon_local": ("agentdojo_live_melon_local", "MELON-style", "comparable_local_adapter", True),
    "spotlighting": (
        "agentdojo_live_spotlighting_with_delimiting",
        "Spotlighting",
        "agentdojo_builtin_prompting_defense",
        True,
    ),
    "prompt_sandwiching": (
        "agentdojo_live_prompt_sandwiching",
        "Prompt Sandwiching",
        "comparable_prompting_adapter",
        True,
    ),
    "promptarmor_local": (
        "agentdojo_live_promptarmor_local",
        "PromptArmor-style",
        "comparable_local_adapter",
        True,
    ),
    "ours_e77_effect_diff_runtime": (
        "agentdojo_live_ours_e77_effect_diff_runtime",
        "Effect-binding runtime guard",
        "proposed_method_strict_finalizer",
        True,
    ),
}
ATTR_METHOD = "agentdojo_live_attriguard"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: malformed JSON") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append(row)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def relative_artifact_path(value: str | Path) -> str:
    path = Path(value)
    if not path.is_absolute():
        return str(path)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def scrub_import_row(row: dict[str, Any], *, protocol_clean: bool = True) -> dict[str, Any]:
    kept = {
        key: row.get(key)
        for key in (
            "unified_case_id",
            "suite",
            "mode",
            "user_task_id",
            "injection_task_id",
            "method_id",
            "utility",
            "attack_success",
            "error",
            "source_benchmark_version",
            "source_agentdojo_package_version",
            "duration",
        )
    }
    kept["source_file"] = relative_artifact_path(str(row.get("source_file") or ""))
    kept["protocol_clean"] = protocol_clean
    return kept


def wilson(successes: int, n: int, z: float = 1.959963984540054) -> list[float]:
    if n <= 0:
        raise ValueError("Wilson interval requires a positive denominator")
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [max(0.0, center - radius), min(1.0, center + radius)]


def exact_mcnemar(left: list[bool], right: list[bool]) -> dict[str, Any]:
    left_only = sum(a and not b for a, b in zip(left, right, strict=True))
    right_only = sum(not a and b for a, b in zip(left, right, strict=True))
    discordant = left_only + right_only
    if not discordant:
        p_value = 1.0
    else:
        lower = min(left_only, right_only)
        tail = sum(math.comb(discordant, k) for k in range(lower + 1)) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {
        "reference_only_success": left_only,
        "method_only_success": right_only,
        "discordant": discordant,
        "p_value": p_value,
    }


def paired_bootstrap(
    left: list[bool],
    right: list[bool],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    if len(left) != len(right) or not left:
        raise ValueError("paired bootstrap requires equal nonempty vectors")
    rng = random.Random(seed)
    deltas = [int(b) - int(a) for a, b in zip(left, right, strict=True)]
    n = len(deltas)
    draws = sorted(sum(deltas[rng.randrange(n)] for _ in range(n)) / n for _ in range(samples))
    return {
        "difference_method_minus_no_guard": sum(deltas) / n,
        "ci95": [draws[int(0.025 * samples)], draws[min(samples - 1, math.ceil(0.975 * samples) - 1)]],
        "samples": samples,
        "seed": seed,
    }


def holm(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    for index, (name, value) in enumerate(ordered):
        running = max(running, min(1.0, (len(ordered) - index) * value))
        adjusted[name] = running
    return adjusted


def row_key(row: dict[str, Any]) -> str:
    return str(row["unified_case_id"])


def metric_vector(rows: list[dict[str, Any]], metric: str) -> dict[str, bool]:
    if metric == "attack_success":
        selected = [row for row in rows if row["mode"] == "attack"]
        field = "attack_success"
    elif metric == "attack_utility":
        selected = [row for row in rows if row["mode"] == "attack"]
        field = "utility"
    elif metric == "benign_utility":
        selected = [row for row in rows if row["mode"] == "benign"]
        field = "utility"
    else:
        raise ValueError(f"unsupported metric: {metric}")
    values = {row_key(row): row.get(field) for row in selected}
    if len(values) != len(selected) or not all(isinstance(value, bool) for value in values.values()):
        raise ValueError(f"invalid or duplicate {metric} values")
    return {key: bool(value) for key, value in values.items()}


def summarize_rows(method_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    benign = [row for row in rows if row["mode"] == "benign"]
    attack = [row for row in rows if row["mode"] == "attack"]
    bu = sum(bool(row["utility"]) for row in benign)
    au = sum(bool(row["utility"]) for row in attack)
    attacks = sum(bool(row["attack_success"]) for row in attack)
    return {
        "method_id": method_id,
        "n_total": len(rows),
        "n_benign": len(benign),
        "n_attack": len(attack),
        "n_error": sum(bool(row["error"]) for row in rows),
        "benign_utility_successes": bu,
        "benign_utility_rate": bu / len(benign),
        "benign_utility_wilson95": wilson(bu, len(benign)),
        "attack_utility_successes": au,
        "attack_utility_rate": au / len(attack),
        "attack_utility_wilson95": wilson(au, len(attack)),
        "attack_successes": attacks,
        "attack_success_rate": attacks / len(attack),
        "attack_success_wilson95": wilson(attacks, len(attack)),
        "suite_counts": dict(Counter(row["suite"] for row in rows)),
    }


def validate_current_method_summary(
    summary: dict[str, Any],
    strict_report: dict[str, Any],
) -> None:
    report_metrics = strict_report.get("metrics") or {}
    exact_fields = (
        "method_id",
        "n_total",
        "n_benign",
        "n_attack",
        "n_error",
        "benign_utility_successes",
        "attack_user_utility_successes",
        "attack_successes",
    )
    summary_aliases = {
        "attack_user_utility_successes": "attack_utility_successes",
    }
    mismatches = []
    for report_field in exact_fields:
        summary_field = summary_aliases.get(report_field, report_field)
        if summary.get(summary_field) != report_metrics.get(report_field):
            mismatches.append(
                f"{summary_field}: imported={summary.get(summary_field)!r}, "
                f"strict_report={report_metrics.get(report_field)!r}"
            )
    if mismatches:
        raise ValueError(
            "current-method imported rows do not match the strict report: "
            + "; ".join(mismatches)
        )


def validate_direct_import(rows: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    expected_ids = {value[0] for value in DIRECT_METHODS.values()}
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_method[str(row["method_id"])].append(row)
    failures = []
    for method_id in sorted(expected_ids):
        method_rows = by_method.get(method_id, [])
        if len(method_rows) != EXPECTED_CASES:
            failures.append(f"{method_id}: expected 726 rows, observed {len(method_rows)}")
        if len({row_key(row) for row in method_rows}) != EXPECTED_CASES:
            failures.append(f"{method_id}: official key set is incomplete or duplicated")
        if dict(Counter(row["suite"] for row in method_rows)) != EXPECTED_SUITES:
            failures.append(f"{method_id}: suite counts differ from {EXPECTED_SUITES}")
        if any(row.get("error") for row in method_rows):
            failures.append(f"{method_id}: one or more rows have missing metrics/errors")
    key_sets = [{row_key(row) for row in by_method[method_id]} for method_id in sorted(expected_ids)]
    if key_sets and any(keys != key_sets[0] for keys in key_sets[1:]):
        failures.append("direct methods do not share the exact paired official key set")
    for field in ("malformed_logs", "duplicate_method_case_logs", "target_version_mismatch_rows", "included_rows_with_missing_metrics"):
        if report.get(field) != 0:
            failures.append(f"direct import {field}={report.get(field)}")
    if failures:
        raise ValueError("; ".join(failures))
    return dict(by_method)


def protocol_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("suite")),
        str(row.get("mode")),
        str(row.get("user_task_id")),
        str(row.get("injection_task_id") or "none"),
    )


def attriguard_protocol_failures(ledger_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(ledger_rows) != EXPECTED_CASES or len({protocol_key(row) for row in ledger_rows}) != EXPECTED_CASES:
        raise ValueError("AttriGuard protocol ledger must contain exactly 726 unique official attempts")
    failures = []
    for row in ledger_rows:
        clean = (
            row.get("status") == "passed"
            and row.get("returncode") == 0
            and row.get("timed_out") is False
            and row.get("server_400_error") is False
            and row.get("server_500_error") is False
            and row.get("context_length_exceeded") is False
            and row.get("log_exists_after") is True
            and row.get("log_metrics_complete") is True
        )
        if not clean:
            failures.append(
                {
                    "unified_case_id": row.get("unified_case_id"),
                    "suite": row.get("suite"),
                    "mode": row.get("mode"),
                    "user_task_id": row.get("user_task_id"),
                    "injection_task_id": row.get("injection_task_id"),
                    "status": row.get("status"),
                    "server_400_error": row.get("server_400_error"),
                    "context_length_exceeded": row.get("context_length_exceeded"),
                }
            )
    return failures


def paired_statistics(by_method: dict[str, list[dict[str, Any]]], *, samples: int) -> dict[str, Any]:
    reference = by_method[NO_GUARD]
    comparisons: dict[str, Any] = {}
    raw_p: dict[str, float] = {}
    for method_index, (directory, (method_id, _, _, _)) in enumerate(DIRECT_METHODS.items()):
        if method_id == NO_GUARD:
            continue
        comparisons[method_id] = {}
        for metric_index, metric in enumerate(("attack_success", "benign_utility", "attack_utility")):
            left_map = metric_vector(reference, metric)
            right_map = metric_vector(by_method[method_id], metric)
            if set(left_map) != set(right_map):
                raise ValueError(f"paired key mismatch for {method_id}/{metric}")
            keys = sorted(left_map)
            left = [left_map[key] for key in keys]
            right = [right_map[key] for key in keys]
            mcnemar = exact_mcnemar(left, right)
            comparison_id = f"{directory}:{metric}"
            raw_p[comparison_id] = mcnemar["p_value"]
            comparisons[method_id][metric] = {
                "n_paired": len(keys),
                "no_guard_successes": sum(left),
                "method_successes": sum(right),
                "no_guard_rate": sum(left) / len(left),
                "method_rate": sum(right) / len(right),
                "paired_bootstrap": paired_bootstrap(
                    left,
                    right,
                    samples=samples,
                    seed=20260721 + 10 * method_index + metric_index,
                ),
                "exact_mcnemar": mcnemar,
            }
    adjusted = holm(raw_p)
    for directory, (method_id, _, _, _) in DIRECT_METHODS.items():
        if method_id == NO_GUARD:
            continue
        for metric in ("attack_success", "benign_utility", "attack_utility"):
            comparisons[method_id][metric]["holm_adjusted_p"] = adjusted[f"{directory}:{metric}"]
    return {
        "reference_method": NO_GUARD,
        "bootstrap_samples": samples,
        "multiple_testing": "Holm correction over all direct method/metric comparisons",
        "comparisons": comparisons,
    }


def import_e75_rows() -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    sys.path.insert(0, str(ROOT / "code"))
    from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison import run_e75

    manifest, _ = run_e75.build_official_case_manifest("v1.1.2")
    direct_paths = [
        CURRENT_METHOD_LOG_ROOT if directory == CURRENT_METHOD_DIRECTORY else LOG_ROOT / directory
        for directory in DIRECT_METHODS
    ]
    direct_rows, direct_report = run_e75.import_official_agentdojo_live_logs(direct_paths, manifest)
    attr_rows, attr_report = run_e75.import_official_agentdojo_live_logs(LOG_ROOT / "attriguard", manifest)
    return direct_rows, direct_report, attr_rows, attr_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(PROTOCOL_MANIFEST.read_text(encoding="utf-8"))
    if not CURRENT_METHOD_REPORT.exists():
        raise FileNotFoundError(f"current-method strict report is missing: {CURRENT_METHOD_REPORT}")
    current_method_report = json.loads(CURRENT_METHOD_REPORT.read_text(encoding="utf-8"))
    if current_method_report.get("status") != "passed":
        raise ValueError("current-method strict finalizer has not passed")
    if current_method_report.get("runtime_version") != "effect_diff_runtime_recovery_normalization_v2":
        raise ValueError("current-method runtime version does not match the frozen recovery-normalization protocol")
    current_metric = current_method_report.get("metrics") or {}
    if current_metric.get("n_total") != EXPECTED_CASES:
        raise ValueError("current-method strict report does not cover all 726 official keys")
    repair_metadata = current_method_report.get("repair_metadata") or {}
    if repair_metadata.get("repaired_official_rows") != 12:
        raise ValueError("current-method report does not identify the 12-row context-repair overlay")
    if repair_metadata.get("original_official_rows_retained") != 714:
        raise ValueError("current-method report does not retain the expected 714 original rows")
    if repair_metadata.get("uniform_context_window") is not False:
        raise ValueError("current-method context-repair boundary is missing")
    direct_rows, direct_report, attr_rows, attr_report = import_e75_rows()
    by_method = validate_direct_import(direct_rows, direct_report)
    current_summary = summarize_rows(
        "agentdojo_live_ours_e77_effect_diff_runtime",
        by_method["agentdojo_live_ours_e77_effect_diff_runtime"],
    )
    validate_current_method_summary(current_summary, current_method_report)
    if len(attr_rows) != EXPECTED_CASES or len({row_key(row) for row in attr_rows}) != EXPECTED_CASES:
        raise ValueError("AttriGuard raw import does not cover all 726 official keys")
    failures = attriguard_protocol_failures(read_jsonl(ATTR_LEDGER))
    failed_ids = {str(row["unified_case_id"]) for row in failures}

    frozen_rows = []
    for method_rows in by_method.values():
        frozen_rows.extend(scrub_import_row(row) for row in method_rows)
    frozen_rows.extend(
        scrub_import_row(row, protocol_clean=row_key(row) not in failed_ids)
        for row in attr_rows
    )
    frozen_rows.sort(key=lambda row: (str(row["method_id"]), str(row["unified_case_id"])))
    write_jsonl(RESULTS / "e78_qwen32_frozen_case_rows.jsonl", frozen_rows)
    write_jsonl(RESULTS / "e78_qwen32_attriguard_protocol_failures.jsonl", failures)

    metrics = []
    metadata_by_id = {value[0]: value[1:] for value in DIRECT_METHODS.values()}
    for method_id, method_rows in sorted(by_method.items()):
        display, evidence, primary_eligible = metadata_by_id[method_id]
        summary = summarize_rows(method_id, method_rows)
        is_current_method = method_id == "agentdojo_live_ours_e77_effect_diff_runtime"
        summary.update(
            {
                "display_name": display,
                "evidence_class": evidence,
                "protocol_status": (
                    "strict_context_repair_overlay_finalizer_passed"
                    if is_current_method
                    else "complete_726_native_metrics_command_diagnostics_not_frozen"
                ),
                "protocol_clean_certified": is_current_method,
                "paper_primary_eligible_now": primary_eligible,
            }
        )
        metrics.append(summary)
    attr_summary = summarize_rows(ATTR_METHOD, attr_rows)
    attr_summary.update(
        {
            "display_name": "AttriGuard adapted artifact",
            "evidence_class": "released_artifact_adapter",
            "protocol_status": f"provisional_{len(failures)}_of_726_protocol_errors",
            "protocol_clean_certified": False,
            "paper_primary_eligible_now": False,
        }
    )
    metrics.append(attr_summary)

    pairwise = paired_statistics(by_method, samples=args.bootstrap_samples)
    write_json(RESULTS / "e78_qwen32_paired_statistics.json", pairwise)
    with (RESULTS / "e78_qwen32_strong_baseline_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "method_id",
            "display_name",
            "evidence_class",
            "protocol_status",
            "paper_primary_eligible_now",
            "n_total",
            "benign_utility_successes",
            "benign_utility_rate",
            "attack_utility_successes",
            "attack_utility_rate",
            "attack_successes",
            "attack_success_rate",
            "n_error",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(metrics)

    report = {
        "experiment": "E78 Qwen3-32B same-protocol AgentDojo strong baselines",
        "status": "frozen_complete_metrics_with_protocol_caveats",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "benchmark": manifest["benchmark"],
            "model": manifest["model"],
            "controls": manifest["controls"],
        },
        "frozen_case_rows": len(frozen_rows),
        "complete_direct_method_rows": len(direct_rows),
        "complete_direct_methods": len(by_method),
        "historical_command_diagnostics": (
            "The historical E75 runner overwrote its shared command-status artifact after each method. "
            "All direct rows have complete native utility/security fields, but per-case HTTP/context diagnostics "
            "cannot be reconstructed as a clean-protocol certificate."
        ),
        "primary_baseline_methods": [
            method_id
            for method_id, _, _, primary_eligible in DIRECT_METHODS.values()
            if primary_eligible
        ],
        "current_proposed_method": "agentdojo_live_ours_e77_effect_diff_runtime",
        "current_method_strict_report": relative_artifact_path(CURRENT_METHOD_REPORT),
        "current_method_context_repair": {
            "original_rows_retained": repair_metadata["original_official_rows_retained"],
            "repaired_rows": repair_metadata["repaired_official_rows"],
            "uniform_context_window": repair_metadata["uniform_context_window"],
            "context_windows": repair_metadata.get("repair_context_windows"),
            "longest_repair_kv_cache_type": repair_metadata.get("r3_kv_cache_type"),
        },
        "metrics": metrics,
        "attriguard": {
            "raw_official_keys": len(attr_rows),
            "protocol_clean_keys": EXPECTED_CASES - len(failures),
            "protocol_error_keys": len(failures),
            "primary_table_eligible": False,
            "failure_artifact": "analysis/results/e78_qwen32_attriguard_protocol_failures.jsonl",
            "note": "Raw 726-key metrics are retained as provisional sensitivity only; protocol-error rows prevent strict primary comparison.",
        },
        "missing_planned_methods": {
            "transformers_pi_detector": "no full-run logs",
            "piguard": "no full-run logs",
        },
        "paired_statistics": "analysis/results/e78_qwen32_paired_statistics.json",
        "claim_boundary": (
            "Five baseline rows and the current effect-binding runtime share one Qwen3-32B checkpoint, the same 726 "
            "AgentDojo v1.1.2 case keys, native evaluators, and sandbox execution. MELON-style, Prompt "
            "Sandwiching, and PromptArmor-style are comparable local adapters, not original-paper reproductions. "
            "AttriGuard remains provisional because 10 workspace attempts exceeded the frozen context protocol. "
            "The proposed-method row is admitted only after its recovery-normalization strict finalizer passes. "
            "It combines 714 original trajectories with 12 disclosed context-capacity repairs; it is therefore "
            "a complete native-metric overlay, not a uniform-context rerun."
        ),
    }
    write_json(RESULTS / "e78_qwen32_strong_baseline_report.json", report)
    write_json(
        RESULTS / "e78_qwen32_reproduction_status.json",
        {
            "status": "passed",
            "expected_state": "complete_native_metrics_frozen_with_protocol_caveats",
            "complete_direct_rows": len(direct_rows),
            "frozen_rows_including_provisional_attriguard": len(frozen_rows),
            "attriguard_protocol_errors": len(failures),
            "required_artifacts": [
                "analysis/results/e78_qwen32_strong_baseline_report.json",
                "analysis/results/e78_qwen32_strong_baseline_metrics.csv",
                "analysis/results/e78_qwen32_paired_statistics.json",
                "analysis/results/e78_qwen32_frozen_case_rows.jsonl",
                "analysis/results/e78_qwen32_attriguard_protocol_failures.jsonl",
            ],
            "blocking_before_final_paper_table": [
                "keep AttriGuard out of the strict main table unless all 726 attempts share a clean protocol",
                "do not describe historical direct rows as protocol-clean because per-method command diagnostics were overwritten",
            ],
        },
    )

    lines = [
        "# E78 Qwen3-32B Strong Baseline Finalization",
        "",
        "- Status: `frozen_complete_metrics_with_protocol_caveats`",
        f"- Complete direct native-metric rows: `{len(direct_rows)} = 6 x 726`",
        f"- Frozen rows including provisional AttriGuard: `{len(frozen_rows)}`",
        f"- AttriGuard clean protocol attempts: `{EXPECTED_CASES - len(failures)}/726`; excluded from the strict primary table.",
        "- Direct methods have complete native metrics, but the historical runner did not preserve per-method command diagnostics.",
        "- The proposed-method row is sourced from the strict 714+12 context-repair overlay finalizer.",
        "- The proposed-method overlay is complete but not a uniform-context rerun.",
        "",
        "| Method | Protocol | BU | Attack utility | ASR | Primary eligible now |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in metrics:
        lines.append(
            f"| {row['display_name']} | {row['protocol_status']} | {row['benign_utility_rate']:.3f} | "
            f"{row['attack_utility_rate']:.3f} | {row['attack_success_rate']:.3f} | "
            f"{str(row['paper_primary_eligible_now']).lower()} |"
        )
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    (RESULTS / "e78_qwen32_strong_baseline_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "complete_rows": len(direct_rows), "attriguard_failures": len(failures)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
