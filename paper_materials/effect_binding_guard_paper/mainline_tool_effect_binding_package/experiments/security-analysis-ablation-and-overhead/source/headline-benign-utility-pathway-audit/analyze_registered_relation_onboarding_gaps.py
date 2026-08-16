#!/usr/bin/env python3
"""Inventory source-to-target relation gaps exposed by the frozen pilot."""

from __future__ import annotations

import collections
import json
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
MANIFEST = (
    ROOT
    / "experiments/intent-bound-runtime-guard/evaluation/"
    "effect-difference-runtime-guard/"
    "registered_relation_benign_pilot_manifest.json"
)
PILOT_REPORT = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "headline-benign-utility-pathway-audit/"
    "registered-relation-benign-pilot-v8.json"
)
RESULT_ROOT = PILOT_REPORT.parent


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report() -> dict[str, Any]:
    manifest = read_json(MANIFEST)
    pilot = read_json(PILOT_REPORT)
    if manifest.get("status") != "frozen_before_v8_pilot_execution":
        raise ValueError("pilot manifest is not frozen")
    if pilot.get("status") != "passed_fixed_denominator_outcomes_retained":
        raise ValueError("pilot report did not pass fixed-denominator checks")

    outcomes = {row["case_key"]: row for row in pilot["cases"]}
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    relation_rows: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        if case["stratum"] != "historical_trusted_source_resolver_loss":
            continue
        outcome = outcomes[case["case_key"]]
        pathway = (
            "plan_construction"
            if outcome["plan_validation_error_counts"]
            else "runtime_relation"
        )
        for relation in case["historical_relations"]:
            for source_tool in relation["observed_source_tools"]:
                key = (
                    source_tool,
                    relation["target_tool"],
                    relation["target_field"],
                )
                group = groups.setdefault(
                    key,
                    {
                        "source_tool": source_tool,
                        "target_tool": relation["target_tool"],
                        "target_field": relation["target_field"],
                        "case_keys": set(),
                        "recovered_case_keys": set(),
                        "failed_case_keys": set(),
                        "failure_pathways": collections.Counter(),
                    },
                )
                group["case_keys"].add(case["case_key"])
                if outcome["utility"]:
                    group["recovered_case_keys"].add(case["case_key"])
                else:
                    group["failed_case_keys"].add(case["case_key"])
                    group["failure_pathways"][pathway] += 1
                relation_rows.append(
                    {
                        "case_key": case["case_key"],
                        "source_tool": source_tool,
                        "target_tool": relation["target_tool"],
                        "target_field": relation["target_field"],
                        "utility": outcome["utility"],
                        "observed_failure_pathway": (
                            "recovered" if outcome["utility"] else pathway
                        ),
                    }
                )

    group_rows: list[dict[str, Any]] = []
    for key in sorted(groups):
        group = groups[key]
        group_rows.append(
            {
                "source_tool": group["source_tool"],
                "target_tool": group["target_tool"],
                "target_field": group["target_field"],
                "case_keys": sorted(group["case_keys"]),
                "recovered_case_keys": sorted(group["recovered_case_keys"]),
                "failed_case_keys": sorted(group["failed_case_keys"]),
                "failure_pathways": dict(
                    sorted(group["failure_pathways"].items())
                ),
            }
        )

    failed_groups = [row for row in group_rows if row["failed_case_keys"]]
    recovered_groups = [row for row in group_rows if row["recovered_case_keys"]]
    report = {
        "status": "passed",
        "experiment": "registered-relation-onboarding-gap-audit",
        "source_manifest": str(MANIFEST.relative_to(ROOT)),
        "source_pilot_report": str(PILOT_REPORT.relative_to(ROOT)),
        "counts": {
            "target_cases": 12,
            "exact_source_target_field_groups": len(group_rows),
            "groups_observed_in_recovered_cases": len(recovered_groups),
            "groups_observed_in_failed_cases": len(failed_groups),
            "relation_case_rows": len(relation_rows),
            "runtime_relation_failure_cases": pilot["failure_anatomy"][
                "runtime_relation_failure_case_count"
            ],
            "plan_construction_failure_cases": pilot["failure_anatomy"][
                "plan_construction_failure_case_count"
            ],
        },
        "groups": group_rows,
        "relation_case_rows": relation_rows,
        "interpretation": (
            "The fixed bill relation demonstrates one feasible source-derived "
            "binding but does not cover the observed relation inventory. The "
            "failed groups define onboarding requirements; they are not approved "
            "relations and cannot be copied into runtime authority without "
            "independent schema and counterfactual validation."
        ),
        "claim_boundary": (
            "This post-pilot audit groups historical source/target observations. "
            "It does not infer authorization, certify a parser, or estimate open-"
            "domain relation prevalence."
        ),
    }
    if report["counts"] != {
        "target_cases": 12,
        "exact_source_target_field_groups": 14,
        "groups_observed_in_recovered_cases": 2,
        "groups_observed_in_failed_cases": 12,
        "relation_case_rows": 17,
        "runtime_relation_failure_cases": 7,
        "plan_construction_failure_cases": 4,
    }:
        raise ValueError(f"unexpected onboarding inventory: {report['counts']}")
    return report


def main() -> int:
    report = build_report()
    json_path = RESULT_ROOT / "registered-relation-onboarding-gap-audit.json"
    md_path = RESULT_ROOT / "registered-relation-onboarding-gap-audit.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Registered-Relation Onboarding Gap Audit",
        "",
        f"- Exact source/target/field groups: `{report['counts']['exact_source_target_field_groups']}`",
        f"- Groups observed in recovered cases: `{report['counts']['groups_observed_in_recovered_cases']}`",
        f"- Groups observed in failed cases: `{report['counts']['groups_observed_in_failed_cases']}`",
        f"- Runtime-relation failure cases: `{report['counts']['runtime_relation_failure_cases']}`",
        f"- Plan-construction failure cases: `{report['counts']['plan_construction_failure_cases']}`",
        "",
        "| Source | Target field | Cases | Recovered | Failed | Pathways |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in report["groups"]:
        lines.append(
            f"| `{row['source_tool']}` | "
            f"`{row['target_tool']}.{row['target_field']}` | "
            f"{len(row['case_keys'])} | {len(row['recovered_case_keys'])} | "
            f"{len(row['failed_case_keys'])} | "
            f"`{json.dumps(row['failure_pathways'], sort_keys=True)}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
