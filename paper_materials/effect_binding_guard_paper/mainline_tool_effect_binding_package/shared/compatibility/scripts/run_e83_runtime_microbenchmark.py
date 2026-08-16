#!/usr/bin/env python3
"""Measure controlled hardened-kernel cost versus fields and resolver ledger size."""

from __future__ import annotations

import argparse
import json
import math
import platform
import resource
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.experiments.effect_binding_guard.e80_contract_obligation_hardening import (
    AuthorityManifest,
    FieldAuthority,
    FieldDefault,
    mediate_hardened_call,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"
EVAL = ROOT / "evaluation/e83_overhead"
PAPER_TABLE = ROOT / "usenix27_candidate/tables/table_e83_kernel_overhead.tex"


def percentile(values: list[int], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def fixture(n_fields: int, ledger_noise: int) -> dict[str, Any]:
    fields = {}
    args = {}
    semantics = {}
    proposal_fields = {}
    resolver_catalog = set()
    ledger = []
    for index in range(n_fields):
        name = f"field_{index}"
        value = f"value_{index}"
        args[name] = value
        semantics[name] = FieldDefault(required=True)
        if index % 2:
            resolver_id = f"resolver_{index}"
            fields[name] = FieldAuthority(mode="resolve", resolver_id=resolver_id)
            proposal_fields[name] = {"mode": "resolve", "values": [], "resolver_id": resolver_id}
            resolver_catalog.add(resolver_id)
            ledger.append({
                "resolver_id": resolver_id, "values": [value], "typed_projection": True,
                "provenance": "authorized_read",
            })
        else:
            fields[name] = FieldAuthority(mode="exact", exact_values=(value,), source_spans=(value,))
            proposal_fields[name] = {"mode": "exact", "values": [value], "resolver_id": None}
    for index in range(ledger_noise):
        ledger.append({
            "resolver_id": f"noise_{index}", "values": [f"noise_value_{index}"],
            "typed_projection": True, "provenance": "authorized_read",
        })
    return {
        "tool_name": "benchmark_tool",
        "arguments": args,
        "field_semantics": semantics,
        "security_fields": list(args),
        "inactive_values": {},
        "proposal": {"tools": {"benchmark_tool": {"fields": proposal_fields}}},
        "manifest": AuthorityManifest(
            task_id="benchmark_task", tools={"benchmark_tool": fields},
            resolver_catalog=frozenset(resolver_catalog),
        ),
        "resolver_ledger": ledger,
        "registry_hash": "benchmark-registry",
    }


def measure(n_fields: int, ledger_noise: int, iterations: int, warmup: int) -> dict[str, Any]:
    kwargs = fixture(n_fields, ledger_noise)
    for _ in range(warmup):
        result = mediate_hardened_call(**kwargs)
        if result["decision"] != "ALLOW":
            raise RuntimeError(result)
    wall = []
    cpu = []
    for _ in range(iterations):
        wall_start = time.perf_counter_ns()
        cpu_start = time.process_time_ns()
        result = mediate_hardened_call(**kwargs)
        cpu.append(time.process_time_ns() - cpu_start)
        wall.append(time.perf_counter_ns() - wall_start)
        if result["decision"] != "ALLOW" or result["runtime_called_llm"]:
            raise RuntimeError("microbenchmark correctness gate failed")
    return {
        "n_security_fields": n_fields,
        "n_resolver_bindings": n_fields // 2,
        "resolver_ledger_noise_entries": ledger_noise,
        "iterations": iterations,
        "wall_ns": {
            "mean": statistics.fmean(wall), "p50": percentile(wall, 0.50),
            "p90": percentile(wall, 0.90), "p95": percentile(wall, 0.95), "max": max(wall),
        },
        "cpu_ns": {
            "mean": statistics.fmean(cpu), "p50": percentile(cpu, 0.50),
            "p90": percentile(cpu, 0.90), "p95": percentile(cpu, 0.95), "max": max(cpu),
        },
        "all_decisions": "ALLOW",
        "runtime_llm_calls": 0,
    }


def slope(rows: list[dict[str, Any]], ledger_noise: int) -> float:
    selected = [row for row in rows if row["resolver_ledger_noise_entries"] == ledger_noise]
    xs = [row["n_security_fields"] for row in selected]
    ys = [row["wall_ns"]["p50"] for row in selected]
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator


def run(iterations: int, warmup: int) -> dict[str, Any]:
    rows = [
        measure(n_fields, ledger_noise, iterations, warmup)
        for ledger_noise in (0, 16, 64)
        for n_fields in (1, 2, 4, 8, 16, 32)
    ]
    return {
        "experiment": "E83",
        "artifact_type": "controlled_hardened_runtime_microbenchmark",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "processor": platform.processor(), "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "iterations_per_configuration": iterations,
        "warmup_per_configuration": warmup,
        "configurations": len(rows),
        "rows": rows,
        "p50_wall_ns_slope_per_field": {
            str(noise): slope(rows, noise) for noise in (0, 16, 64)
        },
        "correctness": {
            "all_allow": all(row["all_decisions"] == "ALLOW" for row in rows),
            "runtime_llm_calls": sum(row["runtime_llm_calls"] for row in rows),
        },
        "claim_boundary": (
            "This is an in-process CPU microbenchmark of the pure hardened precommit kernel. It excludes model, sandbox, "
            "canonicalization I/O, user simulation, and end-to-end trajectory latency; final E83 must report those separately."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--warmup", type=int, default=100)
    args = parser.parse_args()
    report = run(args.iterations, args.warmup)
    RESULTS.mkdir(parents=True, exist_ok=True)
    EVAL.mkdir(parents=True, exist_ok=True)
    for path in (
        RESULTS / "e83_runtime_microbenchmark.json",
        EVAL / "runtime_microbenchmark.json",
    ):
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# E83 Hardened Runtime Microbenchmark", "", f"Status: `{report['status']}`.", "",
        "| Fields | Ledger noise | p50 wall (us) | p95 wall (us) | p50 CPU (us) |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['n_security_fields']} | {row['resolver_ledger_noise_entries']} | "
            f"{row['wall_ns']['p50']/1000:.3f} | {row['wall_ns']['p95']/1000:.3f} | {row['cpu_ns']['p50']/1000:.3f} |"
        )
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    (RESULTS / "e83_runtime_microbenchmark.md").write_text("\n".join(lines), encoding="utf-8")
    selected = [
        row for row in report["rows"]
        if row["n_security_fields"] in {1, 8, 32} and row["resolver_ledger_noise_entries"] in {0, 64}
    ]
    table = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Controlled hardened-kernel latency. Ledger noise is the number of unrelated typed resolver entries. This excludes model and sandbox latency.}",
        r"\label{tab:e83-kernel-overhead}",
        r"\begin{tabular}{rrrr}",
        r"\toprule",
        r"Fields & Ledger noise & p50 ($\mu$s) & p95 ($\mu$s) \\",
        r"\midrule",
    ]
    for row in selected:
        table.append(
            f"{row['n_security_fields']} & {row['resolver_ledger_noise_entries']} & "
            f"{row['wall_ns']['p50']/1000:.1f} & {row['wall_ns']['p95']/1000:.1f} \\\\"
        )
    table.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    PAPER_TABLE.parent.mkdir(parents=True, exist_ok=True)
    PAPER_TABLE.write_text("\n".join(table), encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "configurations": report["configurations"],
        "iterations_per_configuration": report["iterations_per_configuration"],
        "p50_wall_ns_slope_per_field": report["p50_wall_ns_slope_per_field"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
