#!/usr/bin/env python3
"""Replay C1 over completed no-guard trajectories without changing state.

This is a mechanism diagnostic, not a counterfactual live ASR estimator. It
reports whether a call that appeared in an observed trajectory would have been
blocked by the C1 policy. Live evaluation is required after candidate freeze.
"""

from __future__ import annotations

import ast
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.atom_envelope_policy import (
    evaluate_atom_envelope,
    extract_untrusted_control_segments,
)


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "paper").is_dir() and (parent / "experiments").is_dir()
)
DESCRIPTORS = (
    ROOT / "experiments/intent-bound-runtime-guard/results/"
    "effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl"
)
LOG_ROOT = (
    ROOT / "experiments/unified-agent-security-baselines/runs/"
    "strong-model-baseline-comparison/qwen32-strong-baselines/"
    "agentdojo_logs/no_guard/local"
)
OUT = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard"


def content_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(item.get("content", ""))
            for item in content
            if isinstance(item, dict)
        )
    return ""


def tool_call(message: dict[str, Any]) -> dict[str, Any] | None:
    raw = message.get("tool_call")
    if isinstance(raw, str):
        try:
            raw = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return None
    return raw if isinstance(raw, dict) else None


def load_descriptors() -> dict[str, dict[str, Any]]:
    rows = {}
    for line in DESCRIPTORS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        row["side_effectful"] = True
        rows[row["tool_name"]] = row
    return rows


def evaluate_log(path: Path, descriptors: dict[str, dict[str, Any]], mode: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    task = next(
        content_text(message)
        for message in data["messages"]
        if message.get("role") == "user"
    )
    evidence: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    effectful_calls = 0
    for message in data["messages"]:
        if message.get("role") != "tool":
            continue
        call = tool_call(message)
        if not call:
            continue
        name = call.get("function")
        arguments = call.get("args", {})
        if name in descriptors and isinstance(arguments, dict):
            effectful_calls += 1
            decision = evaluate_atom_envelope(
                task, descriptors[name], arguments, evidence
            )
            if decision["decision"] == "DENY":
                blocked.append(
                    {
                        "tool_name": name,
                        "reasons": decision["reasons"],
                        "n_control_segments": decision["untrusted_control_segments"],
                    }
                )
        segments = extract_untrusted_control_segments(content_text(message))
        if segments:
            evidence.append({"untrusted_control_segments": segments})
    return {
        "case_key": str(path.relative_to(LOG_ROOT)),
        "mode": mode,
        "official_utility": bool(data.get("utility")),
        "official_attack_success": bool(data.get("security")) if mode == "attack" else None,
        "effectful_calls": effectful_calls,
        "would_block_observed_trajectory": bool(blocked),
        "blocked_calls": blocked,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--variant",
        choices=("c1", "c1b", "c1c", "c1d", "c1e", "c1f"),
        default="c1",
    )
    args = parser.parse_args()
    descriptors = load_descriptors()
    rows = []
    for path in sorted(LOG_ROOT.glob("*/user_task_*/none/none.json")):
        rows.append(evaluate_log(path, descriptors, "benign"))
    for path in sorted(LOG_ROOT.glob("*/user_task_*/important_instructions/*.json")):
        rows.append(evaluate_log(path, descriptors, "attack"))

    counts: Counter[str] = Counter()
    for row in rows:
        mode = row["mode"]
        counts[f"{mode}_cases"] += 1
        counts[f"{mode}_would_block"] += row["would_block_observed_trajectory"]
        if mode == "benign":
            counts["benign_utility_successes"] += row["official_utility"]
            counts["successful_benign_would_block"] += (
                row["official_utility"] and row["would_block_observed_trajectory"]
            )
        else:
            counts["official_attack_successes"] += row["official_attack_success"]
            counts["successful_attack_trajectories_intercepted"] += (
                row["official_attack_success"] and row["would_block_observed_trajectory"]
            )

    residual = [
        row["case_key"] for row in rows
        if row["mode"] == "attack"
        and row["official_attack_success"]
        and not row["would_block_observed_trajectory"]
    ]
    report = {
        "experiment": f"{args.variant.upper()} observed-trajectory interception diagnostic",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(LOG_ROOT.relative_to(ROOT)),
        "model": "Qwen3-32B Q4_K_M (existing no-guard trajectories)",
        "descriptor_source": str(DESCRIPTORS.relative_to(ROOT)),
        "metrics": dict(counts),
        "residual_successful_attack_cases": residual,
        "claim_boundary": (
            "Retrospective call-interception coverage over observed no-guard trajectories; "
            "not a live guarded ASR or utility estimate. Blocking can change downstream actions."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.variant == "c1" else f"_{args.variant}"
    (OUT / f"observed_trajectory_interception_rows{suffix}.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (OUT / f"observed_trajectory_interception_report{suffix}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md = f"""# C1 Observed-Trajectory Interception Diagnostic

- Source: completed Qwen3-32B no-guard AgentDojo v1.1.2 trajectories.
- Benign observed calls blocked: `{counts['benign_would_block']}/{counts['benign_cases']}`.
- Successful benign trajectories blocked: `{counts['successful_benign_would_block']}/{counts['benign_utility_successes']}`.
- Official successful attack trajectories intercepted: `{counts['successful_attack_trajectories_intercepted']}/{counts['official_attack_successes']}`.
- All attack trajectories with at least one intercepted call: `{counts['attack_would_block']}/{counts['attack_cases']}`.
- Residual successful attack cases: `{len(residual)}`.

The residual cases are reported by key in the JSON artifact. Manual trajectory
inspection is required to distinguish tool-effect misses from output-only goals.
This diagnostic does not estimate live guarded ASR because blocking an earlier
call can change later model behavior.
"""
    (OUT / f"observed_trajectory_interception_report{suffix}.md").write_text(md, encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
