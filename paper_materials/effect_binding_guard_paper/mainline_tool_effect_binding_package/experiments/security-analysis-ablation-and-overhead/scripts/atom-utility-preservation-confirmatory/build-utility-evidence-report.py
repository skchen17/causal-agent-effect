#!/usr/bin/env python3
"""Build the fail-fast atom utility-preservation evidence summary."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
RESULTS = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/results/"
    "atom-utility-preservation-confirmatory"
)
DESCRIPTORS = ROOT / (
    "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)


def read_json(name: str) -> dict[str, Any]:
    path = RESULTS / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def require(mapping: dict[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise KeyError(".".join(keys))
        value = value[key]
    return value


def main() -> int:
    fixed = read_json("summary.json")
    verbose = read_json("deepseek_behavior_summary.json")
    compact = read_json("deepseek_compact_behavior_summary.json")
    full = read_json("deepseek_full_benign_noninferiority_summary.json")
    for report in (fixed, verbose, compact, full):
        if report.get("status") not in {"passed", "passed_with_model_failures"}:
            raise RuntimeError(f"required report not passed: {report.get('experiment')}")

    projection = require(
        fixed,
        "fixed_trajectory_utility_preservation",
        "atom_projection_roundtrip",
    )
    primary = require(full, "paired_statistics", "compact_atoms_vs_pristine")
    neutral = require(full, "paired_statistics", "compact_atoms_vs_compact_neutral")
    descriptors = [
        json.loads(line)
        for line in DESCRIPTORS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    evidence = {
        "experiment": "atom_utility_preservation_evidence_v1",
        "status": "passed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "fixed_successful_call_projection": projection,
        "verbose_development_pilot": {
            "pristine": verbose["metrics"]["pristine"],
            "validated_atoms": verbose["metrics"]["validated_atoms"],
            "validated_atoms_guided": verbose["metrics"]["validated_atoms_guided"],
            "interpretation": "Verbose descriptors exhibited attention-sensitive task losses and were not promoted.",
        },
        "compact_development_pilot": {
            "pristine": compact["metrics"]["pristine"],
            "compact_neutral": compact["metrics"]["compact_neutral"],
            "compact_atoms": compact["metrics"]["compact_atoms"],
            "interpretation": "Compact atom descriptions passed all 24 pilot observations and were frozen without extra guidance.",
        },
        "full_agentdojo_benign_noninferiority": {
            "descriptor_scope": {
                "registered_effectful_tools": len(descriptors),
                "security_fields": sum(len(row["security_fields"]) for row in descriptors),
                "llm_plus_counterfactual_tools": sum(
                    row["registration_policy"]
                    == "llm_effect_plus_independent_sandbox_state_output_diff_fail_closed"
                    for row in descriptors
                ),
                "explicit_network_effect_tools": sum(
                    row["registration_policy"] == "explicit_external_network_effect_rule"
                    for row in descriptors
                ),
            },
            "metrics": full["metrics"],
            "suite_metrics": full["suite_metrics"],
            "compact_atoms_vs_pristine": primary,
            "compact_atoms_vs_compact_neutral": neutral,
            "discordances": full["paired_discordances"],
            "prompt_leakage_violations": full["prompt_leakage_violations"],
            "runtime_guard_used": full["runtime_guard_used"],
        },
        "conclusions": {
            "fixed_call_representation_roundtrip_preserved": projection["rate"] == 1.0,
            "full_benign_noninferiority_passed": primary["noninferiority_passed"],
            "noninferiority_to_character_matched_neutral_passed": neutral["noninferiority_passed"],
            "authority_runtime_utility_cost_resolved": False,
        },
        "claim_boundary": (
            "The fixed replay tests representation round-trip on a reviewed successful-call subset. "
            "The DeepSeek experiment tests whether compact atom descriptions reduce native benign "
            "AgentDojo utility with the runtime guard disabled. Neither result establishes attack "
            "resistance, authority-interface completeness, or zero loss for every model and task."
        ),
    }
    (RESULTS / "atom_utility_preservation_evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    full_metrics = full["metrics"]
    lines = [
        "# Atom Utility-Preservation Evidence",
        "",
        "## Fixed Successful Trajectories",
        "",
        f"Atom projection and reconstruction preserves {projection['preserved']}/{projection['total']} "
        f"recorded effectful calls ({projection['rate']:.3f}).",
        "",
        "## Full AgentDojo Benign Comparison",
        "",
        "| Condition | Utility | Total | Rate |",
        "|---|---:|---:|---:|",
    ]
    for condition in ("pristine", "compact_neutral", "compact_atoms"):
        item = full_metrics[condition]
        lines.append(
            f"| {condition} | {item['utility_successes']} | {item['total']} | {item['utility_rate']:.3f} |"
        )
    interval = primary["clustered_bootstrap_95pct_interval"]
    neutral_interval = neutral["clustered_bootstrap_95pct_interval"]
    lines.extend(
        [
            "",
            "## Primary Paired Test",
            "",
            f"Compact atoms minus pristine: {primary['utility_rate_difference']:.3f}; "
            f"task-clustered bootstrap 95% interval [{interval[0]:.3f}, {interval[1]:.3f}]; "
            f"one-sided lower bound {primary['clustered_bootstrap_one_sided_95pct_lower']:.3f}; "
            f"5-point non-inferiority: `{primary['noninferiority_passed']}`.",
            "",
            f"Compact atoms minus character-matched neutral: "
            f"{neutral['utility_rate_difference']:.3f}; task-clustered bootstrap 95% interval "
            f"[{neutral_interval[0]:.3f}, {neutral_interval[1]:.3f}]; one-sided lower bound "
            f"{neutral['clustered_bootstrap_one_sided_95pct_lower']:.3f}; 5-point "
            f"non-inferiority: `{neutral['noninferiority_passed']}`. This secondary control "
            "precludes claiming an atom-specific utility improvement.",
            "",
            "## Boundary",
            "",
            evidence["claim_boundary"],
        ]
    )
    (RESULTS / "atom_utility_preservation_evidence.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
