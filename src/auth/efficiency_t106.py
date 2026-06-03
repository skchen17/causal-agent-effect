"""T106 efficiency measurements for the future-constrained prototype."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Callable

import future_constraints as fc
from future_shadow_replay_t103 import compile_replay_plan, replay_locked_plan, run_shadow_trace
from precommit_blocking_benchmark_t104 import build_cases
from shadow_real_divergence_t105 import evaluate_pair, mutate_authorized_intent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure T106 local prototype efficiency.")
    parser.add_argument("--tasks", default="data/future_constraint_tasks_t102_v1.jsonl")
    parser.add_argument("--intents", default="data/future_constraint_intents_t102_v1.jsonl")
    parser.add_argument("--compiler-outputs", default="data/future_constraint_compiler_outputs_t102_v1.jsonl")
    parser.add_argument("--output", default="analysis/results/efficiency_t106_v1.json")
    parser.add_argument("--output-md", default="analysis/results/efficiency_t106_v1.md")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return ordered[idx]


def summarize_times(name: str, values_ms: list[float]) -> dict[str, Any]:
    return {
        "stage": name,
        "n": len(values_ms),
        "total_ms": sum(values_ms),
        "mean_ms": statistics.mean(values_ms) if values_ms else 0.0,
        "median_ms": statistics.median(values_ms) if values_ms else 0.0,
        "p95_ms": percentile(values_ms, 0.95),
        "max_ms": max(values_ms) if values_ms else 0.0,
    }


def measure_rows(name: str, rows: list[Any], fn: Callable[[Any], Any]) -> dict[str, Any]:
    values_ms: list[float] = []
    for row in rows:
        t0 = time.perf_counter()
        fn(row)
        values_ms.append((time.perf_counter() - t0) * 1000.0)
    return summarize_times(name, values_ms)


def artifact_size(path: str) -> dict[str, Any]:
    p = Path(path)
    return {"path": path, "exists": p.exists(), "bytes": p.stat().st_size if p.exists() else 0}


def md_table(rows: list[tuple[Any, ...]], headers: list[str]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def write_report(path: Path, result: dict[str, Any]) -> None:
    timing_rows = []
    for stage in result["timings"]:
        timing_rows.append(
            (
                stage["stage"],
                stage["n"],
                f"{stage['total_ms']:.2f}",
                f"{stage['mean_ms']:.4f}",
                f"{stage['median_ms']:.4f}",
                f"{stage['p95_ms']:.4f}",
                f"{stage['max_ms']:.4f}",
            )
        )
    artifact_rows = [(item["path"], item["bytes"]) for item in result["artifact_sizes"]]
    text = "\n\n".join(
        [
            "# T106 Efficiency Report",
            "## Local Stage Timings",
            md_table(timing_rows, ["stage", "n", "total_ms", "mean_ms", "median_ms", "p95_ms", "max_ms"]),
            "## Artifact Sizes",
            md_table(artifact_rows, ["path", "bytes"]),
            "## Claim Boundary",
            (
                "These timings measure the local deterministic Python prototype only. "
                "They exclude LLM generation, real provider sandbox latency, HTTP browser "
                "automation, human review, and deployed-runtime logging overhead."
            ),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    tasks = load_jsonl(Path(args.tasks))
    intents = load_jsonl(Path(args.intents))
    outputs = load_jsonl(Path(args.compiler_outputs))
    task_by_id = {task["task_id"]: task for task in tasks}
    output_by_intent = {output["intent_id"]: output for output in outputs}

    def compile_one(intent: dict[str, Any]) -> None:
        task = task_by_id[intent["task_id"]]
        envelope = fc.rule_extract_authorized_envelope(task)
        pred = fc.rule_compile_future_constraint(task, intent, envelope)
        fc.validate_future_constraint(pred, envelope)

    def shadow_one(intent: dict[str, Any]) -> None:
        task = task_by_id[intent["task_id"]]
        output = output_by_intent[intent["intent_id"]]
        pred = output["predicted_future_constraint"]
        envelope = output["predicted_authorized_envelope"]
        shadow = run_shadow_trace(task=task, intent=intent, pred_fc=pred, envelope=envelope)
        if pred.get("constraint_decision") == "ALLOW_CONSTRAINT":
            plan = compile_replay_plan(task=task, intent=intent, pred_fc=pred, envelope=envelope)
            replay_locked_plan(plan)
        return shadow

    authorized = [intent for intent in intents if intent["intent_type"] == "authorized_minimal"]

    def divergence_faithful_one(intent: dict[str, Any]) -> None:
        task = task_by_id[intent["task_id"]]
        evaluate_pair(
            task=task,
            shadow_intent=intent,
            real_intent=intent,
            output=output_by_intent[intent["intent_id"]],
            substitution_type="faithful",
        )

    def divergence_unsafe_one(intent: dict[str, Any]) -> None:
        task = task_by_id[intent["task_id"]]
        evaluate_pair(
            task=task,
            shadow_intent=intent,
            real_intent=mutate_authorized_intent(task, intent),
            output=output_by_intent[intent["intent_id"]],
            substitution_type="unsafe",
        )

    timings = [
        measure_rows("T102_compile_validate", intents, compile_one),
        measure_rows("T103_shadow_plan_replay", intents, shadow_one),
        measure_rows("T105_divergence_faithful", authorized, divergence_faithful_one),
        measure_rows("T105_divergence_unsafe", authorized, divergence_unsafe_one),
    ]

    t0 = time.perf_counter()
    cases = build_cases(tasks=tasks, intents=intents, outputs=outputs)
    t104_ms = (time.perf_counter() - t0) * 1000.0
    timings.append(
        {
            "stage": "T104_build_precommit_cases",
            "n": len(cases),
            "total_ms": t104_ms,
            "mean_ms": t104_ms / len(cases) if cases else 0.0,
            "median_ms": t104_ms / len(cases) if cases else 0.0,
            "p95_ms": t104_ms / len(cases) if cases else 0.0,
            "max_ms": t104_ms / len(cases) if cases else 0.0,
        }
    )

    artifacts = [
        args.tasks,
        args.intents,
        args.compiler_outputs,
        "data/future_shadow_replay_traces_t103_v1.jsonl",
        "data/precommit_blocking_traces_t104_v1.jsonl",
        "data/shadow_real_divergence_t105_v1.jsonl",
        "analysis/results/future_constraint_compiler_eval_t102_v1.json",
        "analysis/results/future_shadow_replay_t103_v1.json",
        "analysis/results/precommit_blocking_t104_v1.json",
        "analysis/results/shadow_real_divergence_t105_v1.json",
    ]
    result = {
        "dataset": "efficiency_t106_v1",
        "timings": timings,
        "artifact_sizes": [artifact_size(path) for path in artifacts],
        "claim_boundary": [
            "local deterministic Python prototype only",
            "excludes LLM generation and provider sandbox latency",
            "excludes HTTP browser automation and human review overhead",
        ],
    }
    write_json(Path(args.output), result)
    write_report(Path(args.output_md), result)
    print(f"Wrote T106 result to {args.output}")
    print(f"Wrote T106 report to {args.output_md}")


if __name__ == "__main__":
    main()
