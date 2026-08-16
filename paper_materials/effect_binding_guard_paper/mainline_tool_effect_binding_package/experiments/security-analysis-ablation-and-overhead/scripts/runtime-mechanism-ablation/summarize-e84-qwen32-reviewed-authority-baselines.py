#!/usr/bin/env python3
"""Summarize paired Qwen-32B reviewed-authority baseline runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter, defaultdict
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


DEFAULT_RUN = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/runs/runtime-mechanism-ablation/"
    "e84-qwen32-smoke-strong-baselines-v1"
)
RESULTS = ROOT / "experiments/security-analysis-ablation-and-overhead/results/runtime-mechanism-ablation"
E78_RUN = (
    ROOT
    / "experiments/unified-agent-security-baselines/runs/strong-model-baseline-comparison/"
    "qwen32-strong-baselines"
)
E78_PROTOCOL = (
    ROOT
    / "experiments/unified-agent-security-baselines/results/strong-model-baseline-comparison/"
    "qwen32-protocol-manifest.json"
)
METHOD_IDS = {
    "no_guard": "agentdojo_live_local_no_guard",
    "prompt_sandwiching": "agentdojo_live_prompt_sandwiching",
    "promptarmor_local": "agentdojo_live_promptarmor_local",
    "e84_reviewed_authority": "agentdojo_live_ours_e84_reviewed_authority",
}
METHOD_LABELS = {
    "agentdojo_live_local_no_guard": "No guard",
    "agentdojo_live_prompt_sandwiching": "Prompt Sandwiching",
    "agentdojo_live_promptarmor_local": "PromptArmor-local",
    "agentdojo_live_ours_e84_reviewed_authority": "Reviewed authority (ours)",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument(
        "--output-stem",
        default="e84-qwen32-reviewed-authority-strong-baselines-smoke-results",
    )
    parser.add_argument(
        "--reuse-e78-baselines",
        action="store_true",
        help="Reuse complete E78 Qwen-32B baseline logs and import only E84 from run-dir.",
    )
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def expected_keys(protocol: dict[str, Any]) -> set[tuple[str, str, str, str | None]]:
    keys: set[tuple[str, str, str, str | None]] = set()
    for suite, task_ids in protocol["tasks"].items():
        selected = protocol["selected_injection_tasks"][suite]
        injection_ids = selected if isinstance(selected, list) else [selected]
        for task_id in task_ids:
            keys.add((suite, "benign", task_id, None))
            for injection_id in injection_ids:
                keys.add((suite, "attack", task_id, injection_id))
    return keys


def row_key(row: dict[str, Any]) -> tuple[str, str, str, str | None]:
    return (
        row["suite"],
        row["mode"],
        row["user_task_id"],
        row["injection_task_id"],
    )


def artifact_path(path: str) -> str:
    candidate = Path(path)
    try:
        return str(candidate.relative_to(ROOT))
    except ValueError:
        return candidate.name


def metric_vector(rows: list[dict[str, Any]], metric: str) -> dict[tuple[str, str, str, str | None], bool]:
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
        raise RuntimeError(f"invalid or duplicate values for {metric}")
    return {key: bool(value) for key, value in values.items()}


def exact_mcnemar(reference: list[bool], method: list[bool]) -> dict[str, Any]:
    reference_only = sum(a and not b for a, b in zip(reference, method, strict=True))
    method_only = sum(not a and b for a, b in zip(reference, method, strict=True))
    discordant = reference_only + method_only
    if not discordant:
        p_value = 1.0
    else:
        lower = min(reference_only, method_only)
        tail = sum(math.comb(discordant, index) for index in range(lower + 1)) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {
        "reference_only_success": reference_only,
        "method_only_success": method_only,
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
    rng = random.Random(seed)
    deltas = [int(right) - int(left) for left, right in zip(reference, method, strict=True)]
    n = len(deltas)
    draws = sorted(
        sum(deltas[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(samples)
    )
    return {
        "difference_method_minus_reference": sum(deltas) / n,
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
    by_method: dict[str, list[dict[str, Any]]],
    method_ids: list[str],
    *,
    samples: int = 10000,
) -> dict[str, Any]:
    reference_id = METHOD_IDS["no_guard"]
    reference_rows = by_method[reference_id]
    comparisons: dict[str, Any] = {}
    raw_p: dict[str, float] = {}
    for method_index, method_id in enumerate(method_ids):
        if method_id == reference_id:
            continue
        comparisons[method_id] = {}
        for metric_index, metric in enumerate(
            ("attack_success", "benign_utility", "attack_utility")
        ):
            reference_map = metric_vector(reference_rows, metric)
            method_map = metric_vector(by_method[method_id], metric)
            if set(reference_map) != set(method_map):
                raise RuntimeError(f"paired key mismatch for {method_id}/{metric}")
            keys = sorted(reference_map)
            reference = [reference_map[key] for key in keys]
            method = [method_map[key] for key in keys]
            test = exact_mcnemar(reference, method)
            comparison_id = f"{method_id}:{metric}"
            raw_p[comparison_id] = test["p_value"]
            comparisons[method_id][metric] = {
                "n_paired": len(keys),
                "reference_successes": sum(reference),
                "method_successes": sum(method),
                "paired_bootstrap": paired_bootstrap(
                    reference,
                    method,
                    samples=samples,
                    seed=20260724 + 10 * method_index + metric_index,
                ),
                "exact_mcnemar": test,
            }
    adjusted = holm(raw_p)
    for method_id, metrics in comparisons.items():
        for metric, result in metrics.items():
            result["holm_adjusted_p"] = adjusted[f"{method_id}:{metric}"]
    return {
        "reference_method": reference_id,
        "bootstrap_samples": samples,
        "multiple_testing": "Holm correction over three methods and three metrics",
        "comparisons": comparisons,
    }


def residual_attack_diagnostic(row: dict[str, Any]) -> dict[str, Any]:
    source = Path(str(row["source_file"]))
    payload = json.loads(source.read_text(encoding="utf-8"))
    proposed_tools = [
        call["function"]
        for message in payload.get("messages") or []
        for call in message.get("tool_calls") or []
    ]
    execution_markers: list[bool] = []
    for message in payload.get("messages") or []:
        if message.get("role") != "tool":
            continue
        for content in message.get("content") or []:
            if not isinstance(content, dict):
                continue
            text = content.get("content")
            if not isinstance(text, str):
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and isinstance(value.get("executed"), bool):
                execution_markers.append(value["executed"])
    return {
        "suite": row["suite"],
        "user_task_id": row["user_task_id"],
        "injection_task_id": row["injection_task_id"],
        "utility": row["utility"],
        "official_attack_success": row["attack_success"],
        "proposed_tool_names": proposed_tools,
        "runtime_feedback_executed_false": execution_markers.count(False),
        "runtime_feedback_executed_true": execution_markers.count(True),
        "source_file": artifact_path(str(source)),
        "interpretation": (
            "The official native metric is retained. Execution markers diagnose whether "
            "guarded proposals reached the sandbox executor."
        ),
    }


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    protocol = json.loads((run_dir / "protocol_manifest.json").read_text(encoding="utf-8"))
    if protocol["model_alias"] != "e84_qwen32_local":
        raise RuntimeError("the summarizer only admits the fixed Qwen-32B checkpoint")
    if protocol["context_window"] != 65536:
        raise RuntimeError("the paired comparison requires the common 65,536-token context")

    source_protocols: dict[str, Any] = {"e84": protocol}
    if args.reuse_e78_baselines:
        if protocol["methods"] != ["e84_reviewed_authority"]:
            raise RuntimeError(
                "E78 baseline reuse requires an E84-only runtime run to avoid duplicate rows"
            )
        e78_protocol = json.loads(E78_PROTOCOL.read_text(encoding="utf-8"))
        e78_model = e78_protocol["model"]
        protocol_sha = protocol["model_sha256"]
        if protocol_sha != e78_model["sha256"]:
            raise RuntimeError("E78 and E84 checkpoint hashes differ")
        if protocol["context_window"] != e78_model["context_window"]:
            raise RuntimeError("E78 and E84 context windows differ")
        if protocol["agentdojo_version"] != e78_protocol["benchmark"]["version"]:
            raise RuntimeError("E78 and E84 AgentDojo versions differ")
        method_names = [
            "no_guard",
            "prompt_sandwiching",
            "promptarmor_local",
            "e84_reviewed_authority",
        ]
        logdirs = [
            E78_RUN / "agentdojo_logs/no_guard",
            E78_RUN / "agentdojo_logs/prompt_sandwiching",
            E78_RUN / "agentdojo_logs/promptarmor_local",
            run_dir / "agentdojo_logs/e84_reviewed_authority",
        ]
        source_protocols["e78"] = e78_protocol
    else:
        method_names = protocol["methods"]
        logdirs = [run_dir / "agentdojo_logs" / name for name in method_names]
    unknown = sorted(set(method_names) - set(METHOD_IDS))
    if unknown:
        raise RuntimeError(f"unsupported protocol methods: {unknown}")
    method_ids = [METHOD_IDS[name] for name in method_names]
    missing_logdirs = [str(path) for path in logdirs if not path.is_dir()]
    if missing_logdirs:
        raise FileNotFoundError(f"missing method log directories: {missing_logdirs}")

    official_manifest, _ = run_e75.build_official_case_manifest(protocol["agentdojo_version"])
    imported_rows, import_report = run_e75.import_official_agentdojo_live_logs(
        logdirs,
        official_manifest,
    )
    admitted_keys = expected_keys(protocol)
    rows = [row for row in imported_rows if row_key(row) in admitted_keys]
    expected_per_method = len(admitted_keys)
    by_method = {
        method_id: [row for row in rows if row["method_id"] == method_id]
        for method_id in method_ids
    }
    observed_counts = {method_id: len(method_rows) for method_id, method_rows in by_method.items()}
    bad_counts = {
        method_id: count
        for method_id, count in observed_counts.items()
        if count != expected_per_method
    }
    if bad_counts:
        raise RuntimeError(
            f"expected {expected_per_method} admitted rows per method; observed {bad_counts}"
        )

    per_key: dict[
        tuple[str, str, str, str | None],
        dict[str, dict[str, Any]],
    ] = defaultdict(dict)
    for row in rows:
        key = row_key(row)
        if row["method_id"] in per_key[key]:
            raise RuntimeError(f"duplicate method/case row: {row['method_id']} {key}")
        per_key[key][row["method_id"]] = row
    incomplete = {
        str(key): sorted(set(method_ids) - set(method_rows))
        for key, method_rows in per_key.items()
        if set(method_rows) != set(method_ids)
    }
    if incomplete:
        raise RuntimeError(f"incomplete paired cases: {incomplete}")

    metrics = {
        method_id: run_e75.metrics_for_method(method_id, method_rows)
        for method_id, method_rows in by_method.items()
    }
    pairwise = paired_statistics(by_method, method_ids)
    e84_id = METHOD_IDS["e84_reviewed_authority"]
    no_guard_id = METHOD_IDS["no_guard"]
    residual_attack_successes = [
        residual_attack_diagnostic(row)
        for row in by_method[e84_id]
        if row["mode"] == "attack" and row["attack_success"]
    ]
    audit_path = run_dir / "e84_runtime_audit.jsonl"
    audit = read_jsonl(audit_path)
    checks = [row for row in audit if row.get("event") == "precommit_check"]
    blocked_executed = sum(
        row["decision"] != "ALLOW" and row["runtime_executed_tool"] for row in checks
    )
    changed_cases = []
    for key, method_rows in sorted(per_key.items()):
        baseline = method_rows[no_guard_id]
        e84 = method_rows[e84_id]
        if (
            baseline["utility"] != e84["utility"]
            or baseline["attack_success"] != e84["attack_success"]
        ):
            changed_cases.append(
                {
                    "suite": key[0],
                    "mode": key[1],
                    "user_task_id": key[2],
                    "injection_task_id": key[3],
                    "no_guard_utility": baseline["utility"],
                    "e84_utility": e84["utility"],
                    "no_guard_attack_success": baseline["attack_success"],
                    "e84_attack_success": e84["attack_success"],
                }
            )

    is_full_cross = protocol["attack_selection"] == "all_official_injection_tasks_per_suite"
    status = "passed" if is_full_cross and protocol["scope"] == "pilot" else "smoke_passed"
    sanitized_import_report = {
        **import_report,
        "logdir": artifact_path(import_report["logdir"]),
        "logdirs": [artifact_path(path) for path in import_report["logdirs"]],
    }
    sanitized_protocol = dict(protocol)
    if "model_path" in sanitized_protocol:
        sanitized_protocol["model_artifact"] = Path(sanitized_protocol.pop("model_path")).name
    report = {
        "experiment": "E84-Qwen32-reviewed-authority-strong-baselines",
        "status": status,
        "protocol": sanitized_protocol,
        "source_protocols": {
            "e84": {
                "model_artifact": sanitized_protocol.get("model_artifact"),
                "model_sha256": sanitized_protocol["model_sha256"],
                "context_window": sanitized_protocol["context_window"],
                "agentdojo_version": sanitized_protocol["agentdojo_version"],
            },
            **(
                {
                    "e78": {
                        "model_artifact": source_protocols["e78"]["model"]["file_name"],
                        "model_sha256": source_protocols["e78"]["model"]["sha256"],
                        "context_window": source_protocols["e78"]["model"]["context_window"],
                        "agentdojo_version": source_protocols["e78"]["benchmark"]["version"],
                        "baseline_log_reuse": True,
                    }
                }
                if "e78" in source_protocols
                else {}
            ),
        },
        "admitted_case_rows": len(rows),
        "expected_cases_per_method": expected_per_method,
        "method_case_counts": observed_counts,
        "metrics": metrics,
        "paired_statistics": pairwise,
        "deltas_e84_minus_no_guard": {
            "benign_utility_rate": (
                metrics[e84_id]["benign_utility_rate"]
                - metrics[no_guard_id]["benign_utility_rate"]
            ),
            "attack_success_rate": (
                metrics[e84_id]["attack_success_rate"]
                - metrics[no_guard_id]["attack_success_rate"]
            ),
            "attack_user_utility_rate": (
                metrics[e84_id]["attack_user_utility_rate"]
                - metrics[no_guard_id]["attack_user_utility_rate"]
            ),
        },
        "changed_e84_vs_no_guard_cases": changed_cases,
        "residual_e84_official_attack_successes": residual_attack_successes,
        "runtime_audit": {
            "scope": (
                "All AgentDojo invocations in the E84 run, including auxiliary "
                "injection-task utility trajectories excluded from the 195 official rows."
            ),
            "precommit_checks": len(checks),
            "decision_counts": dict(Counter(row["decision"] for row in checks)),
            "blocked_calls_executed": blocked_executed,
            "runtime_values_logged": False,
        },
        "import_report": sanitized_import_report,
        "claim_boundary": (
            "This smoke result validates execution and exact-key pairing only; it is not paper evidence."
            if status == "smoke_passed"
            else (
                "This is a common-checkpoint comparison on the 26-task reviewed-authority "
                "AgentDojo v1.1.2 subset and its complete official injection cross-product. "
                "It is not the full 726-case benchmark and does not establish production safety."
            )
        ),
    }
    if blocked_executed:
        raise RuntimeError(f"{blocked_executed} blocked calls were executed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS / f"{args.output_stem}.json"
    csv_path = RESULTS / f"{args.output_stem}-cases.csv"
    md_path = RESULTS / f"{args.output_stem}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "suite",
            "mode",
            "user_task_id",
            "injection_task_id",
            "method_id",
            "utility",
            "attack_success",
            "error",
            "source_file",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: (row_key(item), item["method_id"])):
            output = {key: row.get(key) for key in fieldnames}
            source = Path(str(output["source_file"]))
            output["source_file"] = (
                str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else source.name
            )
            writer.writerow(output)

    n_benign = protocol["expected_benign_cases_per_method"]
    n_attack = protocol["expected_attack_cases_per_method"]
    lines = [
        "# E84 Qwen-32B Reviewed-Authority Strong Baselines",
        "",
        "| Method | Benign utility | ASR | Utility under attack | Errors |",
        "|---|---:|---:|---:|---:|",
    ]
    for method_id in method_ids:
        metric = metrics[method_id]
        lines.append(
            f"| {METHOD_LABELS[method_id]} | "
            f"{metric['benign_utility_successes']}/{n_benign} "
            f"({metric['benign_utility_rate']:.3f}) | "
            f"{metric['attack_successes']}/{n_attack} "
            f"({metric['attack_success_rate']:.3f}) | "
            f"{metric['attack_user_utility_successes']}/{n_attack} "
            f"({metric['attack_user_utility_rate']:.3f}) | "
            f"{metric['n_error']} |"
        )
    lines.extend(
        [
            "",
            "## Runtime Audit",
            "",
            f"- Pre-commit checks: `{len(checks)}`",
            f"- Decisions: `{dict(Counter(row['decision'] for row in checks))}`",
            f"- Blocked calls executed: `{blocked_executed}`",
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
                "status": status,
                "expected_cases_per_method": expected_per_method,
                "method_case_counts": observed_counts,
                "results": str(json_path.relative_to(ROOT)),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
