#!/usr/bin/env python3
"""Summarize paired Qwen-32B E81 runtime-mechanism ablations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
sys.path.insert(0, str(ROOT / "code"))

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison import run_e75  # noqa: E402


RESULTS = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "runtime-mechanism-ablation"
)
E78_RUN = (
    ROOT
    / "experiments/unified-agent-security-baselines/runs/"
    "strong-model-baseline-comparison/qwen32-strong-baselines"
)
E78_PROTOCOL = (
    ROOT
    / "experiments/unified-agent-security-baselines/results/"
    "strong-model-baseline-comparison/qwen32-protocol-manifest.json"
)
E84_RUN = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/runs/"
    "runtime-mechanism-ablation/"
    "e84-qwen32-pilot-strong-baselines-full-v1"
)
APPLICABILITY_AUDIT = (
    RESULTS / "e81-ablation-applicability-audit.json"
)
ROWS = ("A0", "A1", "A2", "A7", "A9", "A11", "A12", "A13", "A15")
IMPLEMENTATION_SOURCES = {
    "ablation_runtime": (
        ROOT
        / "code/src/experiments/effect_binding_guard/"
        "e81_agentdojo_hardened_runtime/ablation_runtime.py"
    ),
    "agentdojo_ablation_patch": (
        ROOT
        / "code/src/experiments/effect_binding_guard/"
        "e81_agentdojo_hardened_runtime/agentdojo_ablation_runtime_patch.py"
    ),
    "hardened_runtime": (
        ROOT
        / "code/src/experiments/effect_binding_guard/"
        "e80_contract_obligation_hardening/runtime.py"
    ),
    "runner": Path(__file__).with_name(
        "run-e81-qwen32-runtime-ablations.py"
    ),
}
LABELS = {
    "A0": "No guard",
    "A1": "Full reviewed effect-contract guard",
    "A2": "Tool-call-level only",
    "A7": "No provenance/control binding",
    "A9": "Schema-description-only registration",
    "A11": "No task authority envelope",
    "A12": "No authorized-read grounding",
    "A13": "Omitted fields permissive",
    "A15": "No replan recovery",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument(
        "--output-stem", default="e81-qwen32-runtime-ablation-results"
    )
    parser.add_argument(
        "--reuse-a0-a1",
        action="store_true",
        help="Reuse A0 from E78 and A1 from the completed E84 Qwen32 run.",
    )
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row_key(row: dict[str, Any]) -> tuple[str, str, str, str | None]:
    return (
        row["suite"],
        row["mode"],
        row["user_task_id"],
        row["injection_task_id"],
    )


def expected_keys(
    protocol: dict[str, Any],
) -> set[tuple[str, str, str, str | None]]:
    keys = set()
    for suite, task_ids in protocol["tasks"].items():
        selected = protocol["selected_injection_tasks"][suite]
        injections = selected if isinstance(selected, list) else [selected]
        for task_id in task_ids:
            keys.add((suite, "benign", task_id, None))
            for injection_id in injections:
                keys.add((suite, "attack", task_id, injection_id))
    return keys


def import_logdir(
    logdir: Path,
    official_manifest: dict[str, Any],
    admitted: set[tuple[str, str, str, str | None]],
    row_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not logdir.is_dir():
        raise FileNotFoundError(f"missing {row_id} log directory: {logdir}")
    imported, report = run_e75.import_official_agentdojo_live_logs(
        [logdir], official_manifest
    )
    selected = [row for row in imported if row_key(row) in admitted]
    observed_ids = sorted({row["method_id"] for row in selected})
    if len(observed_ids) != 1:
        raise RuntimeError(
            f"{row_id} must contain exactly one pipeline, observed {observed_ids}"
        )
    for row in selected:
        row["source_method_id"] = row["method_id"]
        row["method_id"] = row_id
    return selected, report


def metric_vector(
    rows: list[dict[str, Any]], metric: str
) -> dict[tuple[str, str, str, str | None], bool]:
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
        raise ValueError(metric)
    values = {row_key(row): row.get(field) for row in selected}
    if len(values) != len(selected) or not all(
        isinstance(value, bool) for value in values.values()
    ):
        raise RuntimeError(f"invalid or duplicate values for {metric}")
    return {key: bool(value) for key, value in values.items()}


def exact_mcnemar(reference: list[bool], method: list[bool]) -> dict[str, Any]:
    reference_only = sum(
        left and not right for left, right in zip(reference, method, strict=True)
    )
    method_only = sum(
        not left and right for left, right in zip(reference, method, strict=True)
    )
    discordant = reference_only + method_only
    if discordant == 0:
        p_value = 1.0
    else:
        lower = min(reference_only, method_only)
        tail = sum(
            math.comb(discordant, index) for index in range(lower + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {
        "a1_only_success": reference_only,
        "ablation_only_success": method_only,
        "discordant": discordant,
        "p_value": p_value,
    }


def paired_bootstrap(
    reference: list[bool],
    method: list[bool],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    deltas = [
        int(right) - int(left)
        for left, right in zip(reference, method, strict=True)
    ]
    rng = random.Random(seed)
    n = len(deltas)
    draws = sorted(
        sum(deltas[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(samples)
    )
    return {
        "difference_ablation_minus_a1": sum(deltas) / n,
        "ci95": [
            draws[int(0.025 * samples)],
            draws[min(samples - 1, math.ceil(0.975 * samples) - 1)],
        ],
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


def paired_statistics(
    by_row: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    comparisons: dict[str, Any] = {}
    raw_p: dict[str, float] = {}
    for row_index, row_id in enumerate(ROWS):
        if row_id in {"A0", "A1"} or row_id not in by_row:
            continue
        comparisons[row_id] = {}
        for metric_index, metric in enumerate(
            ("attack_success", "benign_utility", "attack_utility")
        ):
            reference_map = metric_vector(by_row["A1"], metric)
            method_map = metric_vector(by_row[row_id], metric)
            if set(reference_map) != set(method_map):
                raise RuntimeError(f"paired key mismatch for {row_id}/{metric}")
            keys = sorted(reference_map)
            reference = [reference_map[key] for key in keys]
            method = [method_map[key] for key in keys]
            test = exact_mcnemar(reference, method)
            comparison_id = f"{row_id}:{metric}"
            raw_p[comparison_id] = test["p_value"]
            comparisons[row_id][metric] = {
                "n_paired": len(keys),
                "a1_successes": sum(reference),
                "ablation_successes": sum(method),
                "paired_bootstrap": paired_bootstrap(
                    reference,
                    method,
                    samples=10000,
                    seed=20260724 + row_index * 10 + metric_index,
                ),
                "exact_mcnemar": test,
            }
    adjusted = holm(raw_p)
    for row_id, metrics in comparisons.items():
        for metric, result in metrics.items():
            result["holm_adjusted_p"] = adjusted[f"{row_id}:{metric}"]
    return {
        "reference_row": "A1",
        "multiple_testing": (
            "Holm correction over seven ablations and three paired metrics"
        ),
        "comparisons": comparisons,
    }


def relative_artifact(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    protocol = json.loads(
        (run_dir / "protocol_manifest.json").read_text(encoding="utf-8")
    )
    if protocol["model_sha256"] != (
        "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
    ):
        raise RuntimeError("E81 summarizer admits only the fixed Qwen3-32B checkpoint")
    if protocol["context_window"] != 65536:
        raise RuntimeError("E81 requires the common 65,536-token context")
    for name, path in IMPLEMENTATION_SOURCES.items():
        expected = protocol["source_hashes"].get(name)
        observed = file_sha256(path)
        if expected != observed:
            raise RuntimeError(
                f"E81 implementation hash mismatch for {name}: "
                f"protocol={expected} current={observed}"
            )
    admitted = expected_keys(protocol)
    expected_per_row = len(admitted)
    if expected_per_row != protocol["expected_cases_per_row"]:
        raise RuntimeError("protocol case count does not match its exact key set")

    official_manifest, _ = run_e75.build_official_case_manifest(
        protocol["agentdojo_version"]
    )
    source_logdirs: dict[str, Path] = {
        row_id: run_dir / "agentdojo_logs" / row_id.lower()
        for row_id in protocol["rows"]
    }
    source_protocols: dict[str, Any] = {"e81": relative_artifact(run_dir)}
    if args.reuse_a0_a1:
        e78_protocol = json.loads(E78_PROTOCOL.read_text(encoding="utf-8"))
        e84_protocol = json.loads(
            (E84_RUN / "protocol_manifest.json").read_text(encoding="utf-8")
        )
        if not (
            protocol["model_sha256"]
            == e78_protocol["model"]["sha256"]
            == e84_protocol["model_sha256"]
        ):
            raise RuntimeError("A0/A1 reuse checkpoint hashes differ")
        if not (
            protocol["context_window"]
            == e78_protocol["model"]["context_window"]
            == e84_protocol["context_window"]
        ):
            raise RuntimeError("A0/A1 reuse context windows differ")
        source_logdirs["A0"] = E78_RUN / "agentdojo_logs/no_guard"
        source_logdirs["A1"] = (
            E84_RUN / "agentdojo_logs/e84_reviewed_authority"
        )
        source_protocols["A0"] = relative_artifact(E78_PROTOCOL)
        source_protocols["A1"] = relative_artifact(
            E84_RUN / "protocol_manifest.json"
        )

    missing_rows = sorted(set(ROWS) - set(source_logdirs))
    if missing_rows:
        raise RuntimeError(f"missing E81 rows: {missing_rows}")

    by_row: dict[str, list[dict[str, Any]]] = {}
    import_reports: dict[str, Any] = {}
    for row_id in ROWS:
        rows, import_report = import_logdir(
            source_logdirs[row_id], official_manifest, admitted, row_id
        )
        if len(rows) != expected_per_row:
            raise RuntimeError(
                f"{row_id}: expected {expected_per_row} rows, found {len(rows)}"
            )
        if {row_key(row) for row in rows} != admitted:
            raise RuntimeError(f"{row_id}: admitted exact-key set mismatch")
        by_row[row_id] = rows
        import_reports[row_id] = {
            "source_logdir": relative_artifact(source_logdirs[row_id]),
            "imported_rows_before_exact_key_filter": import_report.get(
                "imported_rows"
            ),
            "admitted_rows": len(rows),
        }

    metrics = {
        row_id: run_e75.metrics_for_method(row_id, rows)
        for row_id, rows in by_row.items()
    }
    audit_summary: dict[str, Any] = {}
    for row_id in ROWS:
        if row_id == "A0":
            continue
        if row_id == "A1" and args.reuse_a0_a1:
            audit_path = E84_RUN / "e84_runtime_audit.jsonl"
        else:
            audit_path = run_dir / f"{row_id.lower()}_runtime_audit.jsonl"
        if not audit_path.exists():
            raise FileNotFoundError(f"missing {row_id} audit: {audit_path}")
        events = read_jsonl(audit_path)
        checks = [row for row in events if row.get("event") == "precommit_check"]
        blocked_executed = sum(
            row.get("decision") != "ALLOW"
            and row.get("runtime_executed_tool") is True
            for row in checks
        )
        if blocked_executed:
            raise RuntimeError(f"{row_id}: {blocked_executed} blocked calls executed")
        audit_summary[row_id] = {
            "source": relative_artifact(audit_path),
            "precommit_checks": len(checks),
            "decision_counts": dict(
                sorted(Counter(row["decision"] for row in checks).items())
            ),
            "blocked_calls_executed": blocked_executed,
            "switch_applicable_checks": sum(
                row.get("switch_applicable") is True for row in checks
            ),
        }

    is_full = (
        protocol["scope"] == "full"
        and protocol["attack_selection"]
        == "all_official_injection_tasks_per_suite"
        and expected_per_row == 195
    )
    all_rows = [
        row for row_id in ROWS for row in by_row[row_id]
    ]
    applicability = json.loads(
        APPLICABILITY_AUDIT.read_text(encoding="utf-8")
    )
    status = "passed" if is_full else "smoke_passed"
    if not applicability["rows"]["A13"]["claim_eligible"]:
        status += "_with_nonapplicable_a13"
    report = {
        "experiment": "E81-Qwen32-runtime-mechanism-ablation",
        "status": status,
        "protocol": protocol,
        "source_protocols": source_protocols,
        "expected_cases_per_row": expected_per_row,
        "admitted_case_rows": len(all_rows),
        "row_case_counts": {
            row_id: len(rows) for row_id, rows in by_row.items()
        },
        "metrics": metrics,
        "paired_statistics": paired_statistics(by_row),
        "runtime_audit": audit_summary,
        "static_applicability_audit": applicability,
        "import_reports": import_reports,
        "single_variable_interpretation": {
            "A2": "removes field-level authorization after the tool is in the reviewed task envelope",
            "A7": "accepts resolver values without trusted provenance/type marks",
            "A9": "uses the unrefined round-0 schema-description security-field partition",
            "A11": "removes the reviewed task-scoped tool and field authority envelope",
            "A12": "removes values grounded by authorized typed reads",
            "A13": "ignores omitted unresolved dynamic security defaults",
            "A15": "terminates after a blocked call instead of returning recoverable replan feedback",
        },
        "claim_boundary": (
            "This is a paired Qwen3-32B AgentDojo v1.1.2 ablation on 26 "
            "reviewed tasks and 169 official task-injection pairs. A7 is an "
            "operational ablation of typed/provenance-bound resolver evidence; "
            "it is not a general provenance-system evaluation."
        ),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS / f"{args.output_stem}.json"
    csv_path = RESULTS / f"{args.output_stem}-cases.csv"
    md_path = RESULTS / f"{args.output_stem}.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fieldnames = [
        "suite",
        "mode",
        "user_task_id",
        "injection_task_id",
        "method_id",
        "source_method_id",
        "utility",
        "attack_success",
        "error",
        "source_file",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(all_rows, key=lambda item: (item["method_id"], row_key(item))):
            output = {field: row.get(field) for field in fieldnames}
            output["source_file"] = relative_artifact(
                Path(str(output["source_file"]))
            )
            writer.writerow(output)

    n_benign = protocol["expected_benign_cases_per_row"]
    n_attack = protocol["expected_attack_cases_per_row"]
    lines = [
        "# E81 Qwen3-32B Runtime-Mechanism Ablation",
        "",
        f"- Status: `{report['status']}`",
        f"- Exact-key cases per row: `{expected_per_row}`",
        "",
        "| Row | Variant | Benign utility | ASR | Utility under attack |",
        "|---|---|---:|---:|---:|",
    ]
    for row_id in ROWS:
        metric = metrics[row_id]
        lines.append(
            f"| {row_id} | {LABELS[row_id]} | "
            f"{metric['benign_utility_successes']}/{n_benign} "
            f"({metric['benign_utility_rate']:.3f}) | "
            f"{metric['attack_successes']}/{n_attack} "
            f"({metric['attack_success_rate']:.3f}) | "
            f"{metric['attack_user_utility_successes']}/{n_attack} "
            f"({metric['attack_user_utility_rate']:.3f}) |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "json": relative_artifact(json_path),
                "csv": relative_artifact(csv_path),
                "md": relative_artifact(md_path),
                "row_case_counts": report["row_case_counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
