#!/usr/bin/env python3
"""Run four deterministic monitor views over fixed no-guard trajectories."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.runtime_policy_view_ablation import (
    VARIANTS,
    evaluate_trajectory,
)


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper/current-usenix").is_dir()
)
LOG_ROOT = (
    ROOT / "experiments/unified-agent-security-baselines/runs/strong-model-baseline-comparison/"
    "qwen32-strong-baselines/agentdojo_logs/no_guard/local"
)
DESCRIPTORS = (
    ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)
OUT = (
    ROOT / "experiments/security-analysis-ablation-and-overhead/results/"
    "runtime-policy-view-ablation"
)


def read_descriptors() -> dict[str, dict[str, Any]]:
    result = {}
    for line in DESCRIPTORS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        row["side_effectful"] = True
        result[row["tool_name"]] = row
    return result


def case_key(payload: dict[str, Any]) -> str:
    return ":".join(
        (
            payload["suite_name"],
            payload["user_task_id"],
            payload.get("attack_type") or "none",
            payload.get("injection_task_id") or "none",
        )
    )


def aggregate(rows: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    benign = [row for row in rows if row["mode"] == "benign"]
    attacks = [row for row in rows if row["mode"] == "attack"]
    successful = [row for row in attacks if row["official_attack_success"]]
    return {
        "variant": variant,
        "n": len(rows),
        "benign_n": len(benign),
        "benign_trajectories_would_block": sum(
            row["variants"][variant]["would_block"] for row in benign
        ),
        "successful_benign_trajectories_would_block": sum(
            row["official_utility"] and row["variants"][variant]["would_block"]
            for row in benign
        ),
        "attack_n": len(attacks),
        "official_attack_successes": len(successful),
        "successful_attack_trajectories_intercepted": sum(
            row["variants"][variant]["would_block"] for row in successful
        ),
        "all_attack_trajectories_would_block": sum(
            row["variants"][variant]["would_block"] for row in attacks
        ),
    }


def main() -> int:
    paths = sorted(LOG_ROOT.glob("*/user_task_*/none/none.json")) + sorted(
        LOG_ROOT.glob("*/user_task_*/important_instructions/*.json")
    )
    descriptors = read_descriptors()
    rows = []
    seen = set()
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        key = case_key(payload)
        if key in seen:
            raise RuntimeError(f"duplicate case key: {key}")
        seen.add(key)
        result = evaluate_trajectory(payload, descriptors)
        rows.append(
            {
                "case_key": key,
                "mode": "attack" if payload.get("injection_task_id") else "benign",
                "suite": payload["suite_name"],
                "source_file": str(path.relative_to(ROOT)),
                **result,
            }
        )
    counts = Counter(row["mode"] for row in rows)
    if counts != {"attack": 629, "benign": 97}:
        raise RuntimeError(f"expected 97+629 fixed rows, observed {dict(counts)}")
    aggregates = [aggregate(rows, variant) for variant in VARIANTS]
    report = {
        "experiment": "runtime_policy_view_ablation",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "Qwen3-32B-Q4_K_M existing no-guard trajectories",
        "benchmark": "AgentDojo v1.1.2",
        "n_cases": len(rows),
        "variants": list(VARIANTS),
        "aggregates": aggregates,
        "claim_boundary": (
            "Retrospective interceptability on fixed trajectories. This isolates deterministic "
            "policy views but is not a closed-loop ASR or utility estimate because blocking can "
            "change later model actions."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "runtime-policy-view-rows.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (OUT / "runtime-policy-view-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Runtime Policy-View Ablation",
        "",
        "| View | Successful attacks intercepted | All attacks blocked | Benign blocked | Successful benign blocked |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in aggregates:
        lines.append(
            f"| {row['variant']} | {row['successful_attack_trajectories_intercepted']}/"
            f"{row['official_attack_successes']} | {row['all_attack_trajectories_would_block']}/629 | "
            f"{row['benign_trajectories_would_block']}/97 | "
            f"{row['successful_benign_trajectories_would_block']} |"
        )
    lines.extend(["", report["claim_boundary"], ""])
    (OUT / "runtime-policy-view-report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "passed", "aggregates": aggregates}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
