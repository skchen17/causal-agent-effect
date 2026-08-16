#!/usr/bin/env python3
"""Build the E78 uniform-context sensitivity and capacity-matched rerun plan."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)

ROWS_PATH = (
    ROOT
    / "experiments/unified-agent-security-baselines/results/"
    "strong-model-baseline-comparison/qwen32-frozen-case-rows.jsonl"
)
REPAIR_REPORT = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/"
    "effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-context-repaired-report.json"
)
OUT_DIR = ROOT / "analysis/results"

OURS = "agentdojo_live_ours_e77_effect_diff_runtime"
METHODS = {
    "agentdojo_live_local_no_guard": "No defense",
    "agentdojo_live_melon_local": "MELON-style",
    "agentdojo_live_prompt_sandwiching": "Prompt Sandwiching",
    "agentdojo_live_promptarmor_local": "PromptArmor-style",
    "agentdojo_live_spotlighting_with_delimiting": "Spotlighting",
    OURS: "Effect-binding runtime guard",
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def case_key(suite: str, user_task_id: str, injection_task_id: str | None) -> str:
    suffix = injection_task_id if injection_task_id else "none"
    return f"{suite}:{user_task_id}:{suffix}"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_repair_specs() -> list[dict[str, Any]]:
    report = read_json(REPAIR_REPORT)
    metadata = report.get("repair_metadata", {})
    rows = metadata.get("replacement_rows")
    if not isinstance(rows, list) or len(rows) != 12:
        raise ValueError("expected exactly 12 disclosed E78 repair rows")

    specs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        relative = Path(row["relative_case_path"])
        parts = relative.parts
        if len(parts) != 4:
            raise ValueError(f"unexpected repair case path: {relative}")
        suite, user_task_id, attack_name, file_name = parts
        injection_task_id = None if attack_name == "none" else Path(file_name).stem
        key = case_key(suite, user_task_id, injection_task_id)
        if key in seen:
            raise ValueError(f"duplicate repair key: {key}")
        seen.add(key)

        run_root = ROOT / row["run_root"]
        manifest = read_json(run_root / "protocol_manifest.json")
        context_window = (
            manifest.get("model", {}).get("context_window")
            or manifest.get("context_window")
            or manifest.get("protocol", {}).get("context_window")
        )
        if not isinstance(context_window, int) or context_window <= 65536:
            raise ValueError(f"missing larger context capacity for {key}")
        kv_cache_type = (
            manifest.get("gpu_configuration", {}).get("kv_cache_type") or "f16"
        )
        if kv_cache_type not in {"f16", "q8_0"}:
            raise ValueError(f"unsupported reference KV-cache type for {key}")

        specs.append(
            {
                "case_key": key,
                "suite": suite,
                "user_task_id": user_task_id,
                "injection_task_id": injection_task_id,
                "mode": "benign" if injection_task_id is None else "attack",
                "target_context_window": context_window,
                "target_kv_cache_type": kv_cache_type,
                "reference_method": OURS,
                "reference_utility": row["utility"],
                "reference_security": row["security"],
            }
        )
    return sorted(specs, key=lambda item: item["case_key"])


def load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with ROWS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def summarize(rows: list[dict[str, Any]], method_id: str) -> dict[str, Any]:
    selected = [row for row in rows if row["method_id"] == method_id]
    benign = [row for row in selected if row["mode"] == "benign"]
    attack = [row for row in selected if row["mode"] == "attack"]
    if len(benign) != 96 or len(attack) != 618:
        raise ValueError(
            f"{method_id}: expected 96 benign and 618 attack rows, "
            f"observed {len(benign)} and {len(attack)}"
        )
    return {
        "method_id": method_id,
        "display_name": METHODS[method_id],
        "n_total": len(selected),
        "n_benign": len(benign),
        "n_attack": len(attack),
        "benign_utility_successes": sum(bool(row["utility"]) for row in benign),
        "benign_utility_rate": sum(bool(row["utility"]) for row in benign)
        / len(benign),
        "attack_utility_successes": sum(bool(row["utility"]) for row in attack),
        "attack_utility_rate": sum(bool(row["utility"]) for row in attack)
        / len(attack),
        "attack_successes": sum(bool(row["attack_success"]) for row in attack),
        "attack_success_rate": sum(bool(row["attack_success"]) for row in attack)
        / len(attack),
        "error_rows": sum(bool(row["error"]) for row in selected),
        "protocol_clean_rows": sum(bool(row["protocol_clean"]) for row in selected),
    }


def main() -> int:
    repair_specs = load_repair_specs()
    repair_keys = {row["case_key"] for row in repair_specs}
    rows = load_rows()

    indexed: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["method_id"] not in METHODS:
            continue
        key = case_key(
            row["suite"], row["user_task_id"], row.get("injection_task_id")
        )
        indexed[(row["method_id"], key)].append(row)

    expected_keys = {
        case_key(row["suite"], row["user_task_id"], row.get("injection_task_id"))
        for row in rows
        if row["method_id"] == OURS
    }
    if len(expected_keys) != 726 or not repair_keys <= expected_keys:
        raise ValueError("repair keys do not match the frozen 726-case population")

    for method_id in METHODS:
        method_keys = {key for method, key in indexed if method == method_id}
        if method_keys != expected_keys:
            raise ValueError(f"{method_id}: case-key population differs")
        duplicates = [
            key
            for (method, key), values in indexed.items()
            if method == method_id and len(values) != 1
        ]
        if duplicates:
            raise ValueError(f"{method_id}: duplicate rows for {duplicates[:3]}")

    uniform_keys = expected_keys - repair_keys
    if len(uniform_keys) != 714:
        raise ValueError(f"expected 714 uniform-context keys, got {len(uniform_keys)}")
    uniform_rows = [
        row
        for row in rows
        if row["method_id"] in METHODS
        and case_key(
            row["suite"], row["user_task_id"], row.get("injection_task_id")
        )
        in uniform_keys
    ]
    metrics = [summarize(uniform_rows, method_id) for method_id in METHODS]

    generated_at = datetime.now(timezone.utc).isoformat()
    sensitivity = {
        "experiment": "E78 uniform-base-context complete-case sensitivity",
        "status": "passed",
        "generated_at": generated_at,
        "source_rows": str(ROWS_PATH.relative_to(ROOT)),
        "source_rows_sha256": file_sha256(ROWS_PATH),
        "base_context_window": 65536,
        "n_case_keys": 714,
        "n_benign": 96,
        "n_attack": 618,
        "excluded_context_failure_keys": sorted(repair_keys),
        "metrics": metrics,
        "claim_boundary": (
            "All six methods are compared on the same 714 case keys whose original "
            "Qwen3-32B trajectories completed at 65,536 tokens. The 12 excluded keys "
            "were selected because the proposed method exceeded that capacity, so this "
            "is a disclosed complete-case sensitivity analysis, not an unbiased "
            "replacement for a capacity-matched 726-case comparison."
        ),
    }
    write_json(
        OUT_DIR / "e78_uniform_context_complete_case_sensitivity.json",
        sensitivity,
    )

    with (
        OUT_DIR / "e78_uniform_context_complete_case_sensitivity.csv"
    ).open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "method_id",
            "display_name",
            "n_total",
            "n_benign",
            "n_attack",
            "benign_utility_successes",
            "benign_utility_rate",
            "attack_utility_successes",
            "attack_utility_rate",
            "attack_successes",
            "attack_success_rate",
            "error_rows",
            "protocol_clean_rows",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(metrics)

    comparison_methods = [method for method in METHODS if method != OURS]
    rerun_rows = [
        {
            **spec,
            "method_id": method_id,
            "display_name": METHODS[method_id],
        }
        for spec in repair_specs
        for method_id in comparison_methods
    ]
    protocol = {
        "experiment": "E78 per-case capacity-matched repair protocol",
        "status": "ready",
        "generated_at": generated_at,
        "model": "Qwen3-32B-Q4_K_M.gguf",
        "model_sha256": (
            "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
        ),
        "temperature": 0,
        "output_cap": 4096,
        "benchmark": "AgentDojo v1.1.2",
        "reference_method": OURS,
        "comparison_methods": comparison_methods,
        "n_reference_cases": len(repair_specs),
        "n_comparison_runs": len(rerun_rows),
        "runs": rerun_rows,
        "acceptance_gates": {
            "all_60_comparison_runs_present": True,
            "same_case_key_and_context_as_reference_repair": True,
            "same_kv_cache_type_as_reference_repair": True,
            "native_utility_and_security_metrics_present": True,
            "errors_retained": True,
            "no_real_external_side_effects": True,
        },
        "claim_boundary": (
            "This protocol matches each comparison method to the larger context "
            "capacity used by the proposed method for the same repaired case. "
            "Capacities may differ across cases, but never across methods within a "
            "case. It is not a globally uniform-context rerun."
        ),
    }
    write_json(OUT_DIR / "e78_capacity_matched_repair_protocol.json", protocol)

    markdown = [
        "# E78 Context-Fairness Preparation",
        "",
        "## Uniform 65,536-token complete-case sensitivity",
        "",
        "| Method | BU | UA | ASR |",
        "|---|---:|---:|---:|",
    ]
    for row in metrics:
        markdown.append(
            f"| {row['display_name']} | {row['benign_utility_rate']:.3f} "
            f"| {row['attack_utility_rate']:.3f} "
            f"| {row['attack_success_rate']:.3f} |"
        )
    markdown.extend(
        [
            "",
            sensitivity["claim_boundary"],
            "",
            "## Capacity-matched repair plan",
            "",
            f"- Reference cases: {len(repair_specs)}",
            f"- Comparison methods: {len(comparison_methods)}",
            f"- Required targeted runs: {len(rerun_rows)}",
            "- Status: ready; no targeted comparison run is counted before all "
            "acceptance gates pass.",
            "",
            protocol["claim_boundary"],
            "",
        ]
    )
    (OUT_DIR / "e78_context_fairness_preparation.md").write_text(
        "\n".join(markdown), encoding="utf-8"
    )

    print(json.dumps({"status": "passed", "sensitivity_rows": len(uniform_rows),
                      "targeted_runs": len(rerun_rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
