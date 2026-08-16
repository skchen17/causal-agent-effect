#!/usr/bin/env python3
"""Freeze a deterministic, offline ToolSandbox feasibility subset for E79."""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runs/e79_external_benchmarks/ToolSandbox"
OUTPUT = ROOT / "evaluation/e79_long_horizon"
RESULTS = ROOT / "analysis/results"
TARGET_SIZE = 30


def _category_names(scenario: Any) -> tuple[str, ...]:
    return tuple(sorted(str(category) for category in scenario.categories))


def build_manifest() -> dict[str, Any]:
    sys.path.insert(0, str(SOURCE))
    import tool_sandbox.tools  # noqa: PLC0415
    from tool_sandbox.common.tool_discovery import ToolBackend, find_tools_by_module  # noqa: PLC0415
    from tool_sandbox.scenarios import named_scenarios  # noqa: PLC0415

    tools = find_tools_by_module(tool_sandbox.tools, preferred_tool_backend=ToolBackend.DEFAULT)
    all_scenarios = named_scenarios(preferred_tool_backend=ToolBackend.DEFAULT)
    base = {
        name: scenario
        for name, scenario in all_scenarios.items()
        if not any(token in name for token in ("distraction", "scrambled", "all_tools"))
    }
    rows: list[dict[str, Any]] = []
    for name, scenario in sorted(base.items()):
        allowed_tools = tuple(sorted(scenario.starting_context.tool_allow_list or ()))
        modules = tuple(
            sorted(
                {
                    inspect.getmodule(tools[tool]).__name__
                    for tool in allowed_tools
                    if tool in tools and inspect.getmodule(tools[tool]) is not None
                }
            )
        )
        categories = _category_names(scenario)
        rows.append(
            {
                "scenario_name": name,
                "categories": categories,
                "allowed_tools": allowed_tools,
                "tool_modules": modules,
                "n_milestones": len(scenario.evaluation.milestone_matcher.milestones),
                "n_minefields": len(scenario.evaluation.minefield_matcher.milestones),
                "max_messages": scenario.max_messages,
                "uses_external_search": any(module.endswith("rapid_api_search_tools") for module in modules),
                "selected_strata": [],
            }
        )

    eligible = [row for row in rows if not row["uses_external_search"]]
    selected: dict[str, dict[str, Any]] = {}
    strata = (
        ("state_dependency", "STATE_DEPENDENCY", 7),
        ("canonicalization", "CANONICALIZATION", 7),
        ("insufficient_information", "INSUFFICIENT_INFORMATION", 6),
        ("multi_tool_high_milestone", "MULTIPLE_TOOL_CALL", 10),
    )
    for stratum, category, quota in strata:
        candidates = sorted(
            (row for row in eligible if category in row["categories"]),
            key=lambda row: (-row["n_milestones"], -len(row["allowed_tools"]), row["scenario_name"]),
        )
        added = 0
        for row in candidates:
            if row["scenario_name"] in selected:
                selected[row["scenario_name"]]["selected_strata"].append(stratum)
                continue
            selected[row["scenario_name"]] = {**row, "selected_strata": [stratum]}
            added += 1
            if added == quota:
                break

    if len(selected) < TARGET_SIZE:
        remainder = sorted(
            (row for row in eligible if row["scenario_name"] not in selected),
            key=lambda row: (-row["n_milestones"], -len(row["allowed_tools"]), row["scenario_name"]),
        )
        for row in remainder[: TARGET_SIZE - len(selected)]:
            selected[row["scenario_name"]] = {**row, "selected_strata": ["offline_complexity_fill"]}
    if len(selected) > TARGET_SIZE:
        ordered = sorted(
            selected.values(),
            key=lambda row: (
                -len(row["selected_strata"]),
                -row["n_milestones"],
                -len(row["allowed_tools"]),
                row["scenario_name"],
            ),
        )
        selected = {row["scenario_name"]: row for row in ordered[:TARGET_SIZE]}

    selected_rows = sorted(selected.values(), key=lambda row: row["scenario_name"])
    canonical = json.dumps(selected_rows, sort_keys=True, separators=(",", ":"))
    category_counts = Counter(category for row in selected_rows for category in row["categories"])
    manifest = {
        "experiment": "E79",
        "subset_id": "toolsandbox_offline_feasibility_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_repository": "https://github.com/apple/ToolSandbox",
        "source_revision": "165848b9a78cead7ca7fe7c89c688b58e6501219",
        "selection_hash": hashlib.sha256(canonical.encode()).hexdigest(),
        "status": "frozen_for_adapter_smoke",
        "n_source_base_scenarios": len(base),
        "n_offline_eligible_scenarios": len(eligible),
        "n_selected": len(selected_rows),
        "category_counts": dict(sorted(category_counts.items())),
        "milestone_count_range": [
            min(row["n_milestones"] for row in selected_rows),
            max(row["n_milestones"] for row in selected_rows),
        ],
        "all_external_search_excluded": all(not row["uses_external_search"] for row in selected_rows),
        "selection_policy": {
            "target_size": TARGET_SIZE,
            "strata": {stratum: quota for stratum, _, quota in strata},
            "ranking": "milestones_desc_then_tool_count_desc_then_name",
            "excluded": ["RapidAPI-backed search tools", "tool augmentation variants"],
        },
        "scenarios": selected_rows,
        "claim_boundary": (
            "This is a frozen 30-scenario offline adapter subset. ToolSandbox has at most five milestones in the "
            "selected tasks, so it tests stateful compositional utility but does not by itself establish 20+ call horizon behavior."
        ),
    }
    assert manifest["n_selected"] == TARGET_SIZE
    assert manifest["all_external_search_excluded"] is True
    return manifest


def write_outputs(manifest: dict[str, Any]) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "toolsandbox_feasibility_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E79 ToolSandbox Frozen Offline Subset",
        "",
        f"Subset: `{manifest['subset_id']}`; selected {manifest['n_selected']} of {manifest['n_offline_eligible_scenarios']} offline-eligible base scenarios.",
        "",
        f"Selection hash: `{manifest['selection_hash']}`.",
        "",
        "| Scenario | Milestones | Tools | Strata |",
        "|---|---:|---:|---|",
    ]
    for row in manifest["scenarios"]:
        lines.append(
            f"| `{row['scenario_name']}` | {row['n_milestones']} | {len(row['allowed_tools'])} | "
            f"{', '.join(row['selected_strata'])} |"
        )
    lines.extend(["", "## Claim Boundary", "", manifest["claim_boundary"], ""])
    (RESULTS / "e79_toolsandbox_subset_manifest.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    manifest = build_manifest()
    write_outputs(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
