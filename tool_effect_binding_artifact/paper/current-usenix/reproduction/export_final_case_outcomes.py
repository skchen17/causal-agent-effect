#!/usr/bin/env python3
"""Export compact per-case outcomes for the final USENIX validation runs."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
OUT = PAPER / "reproduction"
RUNS = ROOT / "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard"
PIPELINE = {
    "no_guard": "local",
    "spotlighting": "local-spotlighting_with_delimiting",
    "c1f": "local-ours_e77_effect_diff_runtime",
}
SUITES = ("banking", "slack", "travel", "workspace")
REPS = tuple(f"matched-r{index}" for index in range(1, 5))


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path.relative_to(ROOT))
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(path.relative_to(ROOT))
    return payload


def require_passed(relative: str) -> dict[str, Any]:
    payload = read_json(ROOT / relative)
    if payload.get("status") != "passed":
        raise RuntimeError(f"required result is not passed: {relative}")
    return payload


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outcome(
    dataset: str,
    condition: str,
    path: Path,
    *,
    repetition: str = "",
    attack_family: str = "",
) -> dict[str, Any]:
    payload = read_json(path)
    if payload.get("error") is not None or not isinstance(payload.get("utility"), bool):
        raise RuntimeError(f"non-evaluable row: {path.relative_to(ROOT)}")
    injection = payload.get("injection_task_id") or "none"
    attack_success = payload.get("security") if injection != "none" else None
    if injection != "none" and not isinstance(attack_success, bool):
        raise RuntimeError(f"missing attack validator result: {path.relative_to(ROOT)}")
    return {
        "dataset": dataset,
        "condition": condition,
        "repetition": repetition,
        "suite": payload["suite_name"],
        "user_task_id": payload["user_task_id"],
        "injection_task_id": injection,
        "attack_family": attack_family or str(payload.get("attack_type") or "none"),
        "utility": payload["utility"],
        "attack_success": attack_success,
        "source_sha256": digest(path),
    }


def deepseek_rows() -> list[dict[str, Any]]:
    require_passed(
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "deepseek_benign_interleaved_results.json"
    )
    rows = []
    for repetition in REPS:
        for condition in PIPELINE:
            root = RUNS / f"deepseek-confirmation-{condition}-benign-{repetition}"
            for suite in SUITES:
                paths = sorted(
                    (root / suite / "agentdojo_logs" / PIPELINE[condition] / suite).glob(
                        "user_task_*/none/none.json"
                    )
                )
                rows.extend(
                    outcome("deepseek_repeated_benign", condition, path, repetition=repetition)
                    for path in paths
                )
    if len(rows) != 3 * 4 * 97:
        raise RuntimeError(f"DeepSeek row mismatch: {len(rows)}")
    return rows


def qwen_rows() -> list[dict[str, Any]]:
    require_passed(
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "qwen32_matched_results.json"
    )
    rows = []
    for condition in PIPELINE:
        for mode, pattern in (
            ("benign", "user_task_*/none/none.json"),
            ("attack", "user_task_*/important_instructions/*.json"),
        ):
            root = RUNS / f"qwen32-matched-{condition}-{mode}-r1"
            for suite in SUITES:
                paths = sorted(
                    (root / suite / "agentdojo_logs" / PIPELINE[condition] / suite).glob(pattern)
                )
                rows.extend(outcome("qwen32_matched", condition, path) for path in paths)
    if len(rows) != 3 * 726:
        raise RuntimeError(f"Qwen row mismatch: {len(rows)}")
    return rows


def heldout_rows() -> list[dict[str, Any]]:
    require_passed(
        "experiments/adaptive-injection-benchmark/results/usenix-heldout-public-families/results.json"
    )
    manifest_path = (
        ROOT
        / "experiments/adaptive-injection-benchmark/evaluation/usenix-heldout-public-families/"
        "locked_manifest.jsonl"
    )
    manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line]
    rows = []
    run_root = ROOT / "experiments/adaptive-injection-benchmark/runs/usenix-heldout-public-families/deepseek"
    for condition in PIPELINE:
        for case in manifest:
            path = (
                run_root
                / condition
                / PIPELINE[condition]
                / case["suite"]
                / case["user_task_id"]
                / case["attack_family"]
                / f'{case["injection_task_id"]}.json'
            )
            rows.append(
                outcome(
                    "deepseek_locked_heldout",
                    condition,
                    path,
                    attack_family=case["attack_family"],
                )
            )
    if len(rows) != 3 * 320:
        raise RuntimeError(f"held-out row mismatch: {len(rows)}")
    return rows


def agentlab_rows() -> list[dict[str, Any]]:
    require_passed("analysis/results/e79_agentlab_saved_transfer_current_pair_results.json")
    expected_path = ROOT / "evaluation/e79_long_horizon/agentlab_saved_attack_cases.jsonl"
    expected = {
        (row["suite"], row["user_task_id"], row["injection_task_id"])
        for row in (
            json.loads(line)
            for line in expected_path.read_text(encoding="utf-8").splitlines()
            if line
        )
    }
    rows = []
    base = (
        ROOT
        / "experiments/long-horizon-transfer/runs/long-horizon-cross-environment-transfer/"
        "agentlab-c1f-current-profile/full"
    )
    for condition in ("no_guard", "c1f"):
        indexed: dict[tuple[str, str, str], Path] = {}
        for path in sorted((base / condition).rglob("*.json")):
            payload = read_json(path)
            key = (
                payload.get("suite_name"),
                payload.get("user_task_id"),
                payload.get("injection_task_id"),
            )
            if key not in expected:
                continue
            if key in indexed:
                raise RuntimeError(f"duplicate AgentLAB key for {condition}: {key}")
            indexed[key] = path
        if set(indexed) != expected:
            raise RuntimeError(
                f"AgentLAB {condition} key mismatch: {len(indexed)}/{len(expected)}"
            )
        rows.extend(
            outcome("agentlab_saved_transfer", condition, indexed[key])
            for key in sorted(expected)
        )
    if len(rows) != 606:
        raise RuntimeError(f"AgentLAB paired row mismatch: {len(rows)}")
    return rows


def bounded_rows() -> list[dict[str, Any]]:
    require_passed(
        "experiments/adaptive-injection-benchmark/results/"
        "bounded-public-family-search-current-c1f/results.json"
    )
    path = (
        ROOT
        / "experiments/adaptive-injection-benchmark/results/"
        "bounded-public-family-search-current-c1f/predictions.jsonl"
    )
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        source = json.loads(line)
        if source.get("error") is not False:
            raise RuntimeError("bounded adaptive prediction contains an error")
        if not isinstance(source.get("user_utility"), bool) or not isinstance(source.get("attack_success"), bool):
            raise RuntimeError("bounded adaptive prediction is not evaluable")
        condition = "c1f" if source["method"] == "ours_e77_effect_diff_runtime" else source["method"]
        rows.append(
            {
                "dataset": "qwen_bounded_adaptive",
                "condition": condition,
                "repetition": "",
                "suite": source["suite"],
                "user_task_id": source["user_task_id"],
                "injection_task_id": source["injection_task_id"],
                "attack_family": source["attack_family"],
                "utility": source["user_utility"],
                "attack_success": source["attack_success"],
                "source_sha256": source["result_sha256"],
            }
        )
    if len(rows) != 320 or Counter(row["condition"] for row in rows) != Counter({"no_guard": 160, "c1f": 160}):
        raise RuntimeError(f"bounded adaptive row mismatch: {len(rows)}")
    return rows


def main() -> int:
    rows = [*deepseek_rows(), *qwen_rows(), *heldout_rows(), *agentlab_rows(), *bounded_rows()]
    if len(rows) != 5228:
        raise RuntimeError(f"final compact outcome ledger must contain 5228 rows, observed {len(rows)}")
    jsonl = OUT / "final_case_outcomes.jsonl"
    jsonl.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    with (OUT / "final_case_outcomes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "status": "passed",
        "n_rows": len(rows),
        "by_dataset_condition": {
            f"{dataset}:{condition}": count
            for (dataset, condition), count in sorted(
                Counter((row["dataset"], row["condition"]) for row in rows).items()
            )
        },
        "contains_prompts_or_messages": False,
        "contains_evaluator_sidecars": False,
    }
    (OUT / "final_case_outcomes_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
