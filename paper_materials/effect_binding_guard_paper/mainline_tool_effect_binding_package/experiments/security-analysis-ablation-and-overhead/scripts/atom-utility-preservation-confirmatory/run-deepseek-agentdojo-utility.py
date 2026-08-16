#!/usr/bin/env python3
"""Run and summarize the paired DeepSeek AgentDojo benign-utility pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PYTHON = ROOT / "runs/e75_agentdojo_env/bin/python"
DEFAULT_PROTOCOL = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "atom-utility-preservation-confirmatory/deepseek_behavior_protocol.json"
)
RUNS_PARENT = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/runs/"
    "atom-utility-preservation-confirmatory"
)
RESULTS = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/results/"
    "atom-utility-preservation-confirmatory"
)
MODULE = "src.experiments.effect_binding_guard.atom_utility_preservation_confirmatory.deepseek_agentdojo_patch"
ADAPTER = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/source/"
    "atom-utility-preservation-confirmatory/deepseek_agentdojo_patch.py"
)
UNVALIDATED = ROOT / (
    "experiments/intent-bound-runtime-guard/results/llm-descriptor-agent-runtime/"
    "llm-descriptor-candidates.jsonl"
)
VALIDATED = ROOT / (
    "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)
NEUTRAL = ROOT / (
    "experiments/intent-bound-runtime-guard/results/atomized-tool-description-self-governance/"
    "token-matched-neutral-control.json"
)
SCHEDULER_AMENDMENT = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "atom-utility-preservation-confirmatory/full_run_scheduler_amendment.json"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def child_env(condition: str, root: Path, audit_id: str) -> dict[str, str]:
    required = ("DEEPSEEK_API_KEY",)
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"missing secret environment variables: {missing}")
    return {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": str(ROOT / "code"),
        "DEEPSEEK_BASE_URL": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        "DEEPSEEK_MODEL": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        "DEEPSEEK_AGENT_MAX_TOKENS": os.getenv("DEEPSEEK_AGENT_MAX_TOKENS", "4096"),
        "ATOM_UTILITY_DEEPSEEK": "1",
        "ATOM_UTILITY_CONDITION": condition,
        "ATOM_UTILITY_AUDIT_JSONL": str(root / f"audit.{audit_id}.jsonl"),
        "ATOM_UTILITY_UNVALIDATED_JSONL": str(UNVALIDATED),
        "ATOM_UTILITY_VALIDATED_JSONL": str(VALIDATED),
        "ATOM_UTILITY_NEUTRAL_JSON": str(NEUTRAL),
    }


def run(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol).resolve()
    run_root = RUNS_PARENT / args.run_tag
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    failures = []
    jobs: list[tuple[int, str, str, list[str], Path]] = []
    for repeat in range(protocol["repeats"]):
        conditions = list(protocol["conditions"])
        if args.job_order == "crossover" and repeat % 2 == 1:
            conditions.reverse()
        for condition in conditions:
            root = run_root / f"repeat-{repeat}" / condition
            root.mkdir(parents=True, exist_ok=True)
            for suite, tasks in protocol["tasks"].items():
                if args.job_granularity == "task":
                    jobs.extend((repeat, condition, suite, [task], root) for task in tasks)
                else:
                    jobs.append((repeat, condition, suite, tasks, root))

    def run_job(job: tuple[int, str, str, list[str], Path]) -> dict[str, Any]:
        repeat, condition, suite, tasks, root = job
        job_id = f"{suite}.{tasks[0]}" if len(tasks) == 1 else f"{suite}.batch"
        completed_logs = []
        for task in tasks:
            path = find_log(root, suite, task)
            if path is None:
                continue
            try:
                completed_logs.append("utility" in json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                completed_logs.append(False)
        if len(completed_logs) == len(tasks) and all(completed_logs):
            status = {
                "condition": condition,
                "repeat": repeat,
                "suite": suite,
                "tasks": tasks,
                "returncode": 0,
                "skipped_complete": True,
                "api_key_serialized": False,
            }
            write_json(root / f"command_status.{job_id}.json", status)
            return status
        command = [
            str(PYTHON), "-m", "agentdojo.scripts.benchmark",
            "--model", "LOCAL",
            "--benchmark-version", "v1.1.2",
            "--suite", suite,
            "--tool-delimiter", "user",
            "--logdir", str(root / "agentdojo_logs"),
            "--module-to-load", MODULE,
            # AgentDojo v1.1.2 has a broken internal multiprocessing path;
            # process-level parallelism is handled by this runner instead.
            "--max-workers", "1",
            "--force-rerun",
        ]
        for task in tasks:
            command.extend(["--user-task", task])
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=child_env(condition, root, job_id),
            text=True,
            capture_output=True,
            timeout=args.timeout,
        )
        status = {
            "condition": condition,
            "repeat": repeat,
            "suite": suite,
            "tasks": tasks,
            "returncode": completed.returncode,
            "skipped_complete": False,
            "api_key_serialized": False,
        }
        write_json(root / f"command_status.{job_id}.json", status)
        (root / f"stdout.{job_id}.log").write_text(completed.stdout, encoding="utf-8")
        (root / f"stderr.{job_id}.log").write_text(completed.stderr, encoding="utf-8")
        return status

    with ThreadPoolExecutor(max_workers=args.process_workers) as executor:
        futures = [executor.submit(run_job, job) for job in jobs]
        for future in as_completed(futures):
            status = future.result()
            print(
                f"[{status['repeat']}/{status['condition']}/{status['suite']}] rc={status['returncode']}",
                flush=True,
            )
            if status["returncode"]:
                failures.append(status)
    summarize(
        protocol,
        failures,
        protocol_path=protocol_path,
        run_root=run_root,
        result_prefix=args.result_prefix,
    )
    return 1 if failures else 0


def find_log(root: Path, suite: str, task: str) -> Path | None:
    candidates = list((root / "agentdojo_logs").glob(f"*/{suite}/{task}/none/none.json"))
    return candidates[0] if len(candidates) == 1 else None


def classify_missing_log(root: Path, suite: str, task: str) -> str:
    stderr = root / f"stderr.{suite}.{task}.log"
    if stderr.is_file():
        text = stderr.read_text(encoding="utf-8", errors="replace")
        if "json.decoder.JSONDecodeError" in text and "_openai_to_assistant_message" in text:
            return "model_tool_argument_parse_failure"
    return "missing_or_ambiguous_log"


def paired_cluster_bootstrap(
    rows: list[dict[str, Any]],
    baseline: str,
    treatment: str,
    *,
    seed: int = 7007,
    samples: int = 10_000,
) -> dict[str, Any]:
    index = {
        (row["repeat"], row["condition"], row["suite"], row["user_task_id"]): row
        for row in rows
    }
    tasks = sorted({(row["suite"], row["user_task_id"]) for row in rows})
    clusters = []
    for suite, task in tasks:
        differences = []
        for repeat in sorted({row["repeat"] for row in rows}):
            base = index[(repeat, baseline, suite, task)]["utility"]
            treated = index[(repeat, treatment, suite, task)]["utility"]
            differences.append(int(treated) - int(base))
        clusters.append(differences)
    observed = sum(sum(cluster) for cluster in clusters) / sum(map(len, clusters))
    rng = random.Random(seed)
    draws = []
    for _ in range(samples):
        selected = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        draws.append(sum(sum(cluster) for cluster in selected) / sum(map(len, selected)))
    draws.sort()

    def percentile(probability: float) -> float:
        return draws[min(len(draws) - 1, int(probability * len(draws)))]

    margin = None
    return {
        "baseline": baseline,
        "treatment": treatment,
        "utility_rate_difference": observed,
        "clustered_bootstrap_95pct_interval": [percentile(0.025), percentile(0.975)],
        "clustered_bootstrap_one_sided_95pct_lower": percentile(0.05),
        "n_task_clusters": len(clusters),
        "n_paired_observations": sum(map(len, clusters)),
        "bootstrap_samples": samples,
        "bootstrap_seed": seed,
        "noninferiority_margin": margin,
    }


def summarize(
    protocol: dict[str, Any] | None = None,
    failures: list[dict[str, Any]] | None = None,
    *,
    protocol_path: Path = DEFAULT_PROTOCOL,
    run_root: Path | None = None,
    result_prefix: str = "deepseek_behavior",
) -> None:
    run_root = run_root or RUNS_PARENT / "deepseek-agentdojo-benign-pilot"
    protocol = protocol or json.loads(protocol_path.read_text(encoding="utf-8"))
    rows = []
    for repeat in range(protocol["repeats"]):
        for condition in protocol["conditions"]:
            root = run_root / f"repeat-{repeat}" / condition
            for suite, tasks in protocol["tasks"].items():
                for task in tasks:
                    path = find_log(root, suite, task)
                    if path is None:
                        rows.append({
                            "repeat": repeat, "condition": condition, "suite": suite,
                            "user_task_id": task, "utility": False, "security": None,
                            "error": classify_missing_log(root, suite, task), "log_path": None,
                        })
                        continue
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    payload_complete = "utility" in payload
                    rows.append({
                        "repeat": repeat,
                        "condition": condition,
                        "suite": suite,
                        "user_task_id": task,
                        "utility": payload.get("utility") is True,
                        "security": payload.get("security"),
                        "error": (
                            payload.get("error")
                            if payload_complete
                            else classify_missing_log(root, suite, task)
                        ),
                        "duration": payload.get("duration"),
                        "pipeline_name": payload.get("pipeline_name"),
                        "log_path": str(path.relative_to(ROOT)),
                        "log_sha256": sha256_file(path),
                    })
    expected = protocol["repeats"] * len(protocol["conditions"]) * sum(
        len(tasks) for tasks in protocol["tasks"].values()
    )
    metrics = {}
    for condition in protocol["conditions"]:
        selected = [row for row in rows if row["condition"] == condition]
        metrics[condition] = {
            "utility_successes": sum(row["utility"] for row in selected),
            "total": len(selected),
            "utility_rate": sum(row["utility"] for row in selected) / len(selected) if selected else None,
            "error_rows": sum(row.get("error") not in (None, False) for row in selected),
            "repeat_rates": [
                sum(row["utility"] for row in selected if row["repeat"] == repeat)
                / sum(row["repeat"] == repeat for row in selected)
                for repeat in range(protocol["repeats"])
            ],
        }
    suite_metrics = {}
    for condition in protocol["conditions"]:
        suite_metrics[condition] = {}
        for suite in protocol["tasks"]:
            selected = [
                row for row in rows
                if row["condition"] == condition and row["suite"] == suite
            ]
            successes = sum(row["utility"] for row in selected)
            suite_metrics[condition][suite] = {
                "utility_successes": successes,
                "total": len(selected),
                "utility_rate": successes / len(selected) if selected else None,
            }
    paired = {}
    index = {(row["repeat"], row["condition"], row["suite"], row["user_task_id"]): row for row in rows}
    for condition in protocol["conditions"]:
        if condition == "pristine":
            continue
        counts: Counter[str] = Counter()
        for repeat in range(protocol["repeats"]):
            for suite, tasks in protocol["tasks"].items():
                for task in tasks:
                    base = index[(repeat, "pristine", suite, task)]["utility"]
                    treatment = index[(repeat, condition, suite, task)]["utility"]
                    counts[
                        "both_pass" if base and treatment else
                        "treatment_gain" if treatment else
                        "treatment_loss" if base else
                        "both_fail"
                    ] += 1
        paired[condition] = dict(counts)
    paired_statistics = {}
    paired_discordances = {}
    comparisons = protocol.get("primary_comparisons", [])
    for comparison in comparisons:
        treatment, baseline = [value.strip() for value in comparison.split(" vs ", 1)]
        if treatment not in protocol["conditions"] or baseline not in protocol["conditions"]:
            continue
        item = paired_cluster_bootstrap(rows, baseline, treatment)
        margin = protocol.get("noninferiority_margin")
        item["noninferiority_margin"] = margin
        item["noninferiority_passed"] = (
            item["clustered_bootstrap_one_sided_95pct_lower"] > -margin
            if margin is not None
            else None
        )
        comparison_key = f"{treatment}_vs_{baseline}"
        paired_statistics[comparison_key] = item
        discordances = []
        for repeat in range(protocol["repeats"]):
            for suite, tasks in protocol["tasks"].items():
                for task in tasks:
                    base = index[(repeat, baseline, suite, task)]["utility"]
                    treated = index[(repeat, treatment, suite, task)]["utility"]
                    if base == treated:
                        continue
                    discordances.append(
                        {
                            "repeat": repeat,
                            "suite": suite,
                            "user_task_id": task,
                            "baseline_utility": base,
                            "treatment_utility": treated,
                            "direction": "gain" if treated else "loss",
                        }
                    )
        paired_discordances[comparison_key] = discordances
    blocking_errors = [
        row for row in rows
        if row.get("error") not in (None, False, "model_tool_argument_parse_failure")
    ]
    model_failures = [
        row for row in rows if row.get("error") == "model_tool_argument_parse_failure"
    ]
    complete = len(rows) == expected and not blocking_errors
    report = {
        "experiment": protocol["experiment"],
        "status": (
            "passed_with_model_failures" if complete and model_failures
            else "passed" if complete
            else "incomplete_or_failed"
        ),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "n_rows": len(rows),
        "expected_rows": expected,
        "metrics": metrics,
        "suite_metrics": suite_metrics,
        "paired_vs_pristine": paired,
        "paired_statistics": paired_statistics,
        "paired_discordances": paired_discordances,
        "failures": failures or [],
        "blocking_error_rows": len(blocking_errors),
        "model_output_failure_rows": len(model_failures),
        "prompt_leakage_violations": sum(
            len(row.get("prompt_leakage_violations", []))
            for path in run_root.glob("repeat-*/*/audit.*.jsonl")
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
            for row in [json.loads(line)]
        ),
        "runtime_guard_used": False,
        "api_key_serialized": False,
        "inputs": {
            "protocol_path": str(protocol_path.relative_to(ROOT)),
            "protocol_sha256": sha256_file(protocol_path),
            "adapter_sha256": sha256_file(ADAPTER),
            "summarizer_sha256": sha256_file(Path(__file__).resolve()),
            "validated_descriptors_sha256": sha256_file(VALIDATED),
            "neutral_control_sha256": sha256_file(NEUTRAL),
        },
        "claim_boundary": protocol["claim_boundary"],
    }
    if SCHEDULER_AMENDMENT.is_file():
        amendment = json.loads(SCHEDULER_AMENDMENT.read_text(encoding="utf-8"))
        if amendment.get("experiment") == protocol.get("experiment"):
            report["scheduler_amendment"] = {
                "path": str(SCHEDULER_AMENDMENT.relative_to(ROOT)),
                "sha256": sha256_file(SCHEDULER_AMENDMENT),
                "execution_order": amendment["execution_order"],
                "case_deletion_or_relabeling": amendment["case_deletion_or_relabeling"],
            }
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / f"{result_prefix}_rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    write_json(RESULTS / f"{result_prefix}_summary.json", report)
    lines = [
        "# DeepSeek atom-description benign utility pilot",
        "",
        f"- Status: `{report['status']}`",
        f"- Rows: `{len(rows)}/{expected}`",
        "- Runtime guard: `disabled`",
        "",
        "| Condition | Utility | Total | Rate | Repeat rates |",
        "|---|---:|---:|---:|---|",
    ]
    for condition in protocol["conditions"]:
        item = metrics[condition]
        repeats = ", ".join(f"{value:.3f}" for value in item["repeat_rates"])
        lines.append(
            f"| {condition} | {item['utility_successes']} | {item['total']} | {item['utility_rate']:.3f} | {repeats} |"
        )
    lines.extend(
        [
            "",
            "## Paired against pristine",
            "",
            "```json",
            json.dumps(paired, indent=2, sort_keys=True),
            "```",
            "",
            "## Paired uncertainty",
            "",
            "```json",
            json.dumps(paired_statistics, indent=2, sort_keys=True),
            "```",
            "",
            report["claim_boundary"],
        ]
    )
    (RESULTS / f"{result_prefix}_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("run", "summarize"), default="run")
    parser.add_argument("--process-workers", type=int, default=3)
    parser.add_argument("--job-granularity", choices=("suite", "task"), default="suite")
    parser.add_argument("--job-order", choices=("protocol", "crossover"), default="protocol")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--run-tag", default="deepseek-agentdojo-benign-pilot")
    parser.add_argument("--result-prefix", default="deepseek_behavior")
    args = parser.parse_args()
    if args.mode == "summarize":
        summarize(
            protocol_path=Path(args.protocol).resolve(),
            run_root=RUNS_PARENT / args.run_tag,
            result_prefix=args.result_prefix,
        )
        return 0
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
