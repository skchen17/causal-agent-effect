#!/usr/bin/env python3
"""v17 merged interface-finding inventory (read-only, CPU-only, stdlib only).

PURPOSE
  Task A of interface_fix_and_deepseek_pilot (2026-08-07): attribute the three
  interface finding families of the v17 merged caliber to cases, tools, fields
  and value types, so a data/config-level repair list can be derived:
    - task_permission_plan_parse_failed      (143 retained rows; benign 15)
    - tool_not_in_initial_permission_plan    ( 80 retained rows; benign  4)
    - resolver_fill_requires_replan          (391 retained rows; benign 41 / attack 350)

CALIBER
  Identical to v17-merged-utility-loss-decomposition.py (K0-K3): the D6
  case-bound retained precommit rows of the v17 merged run.  This script
  imports that module and reuses build_retained() unchanged.  The three
  anchor row counts above are verified fail-closed before any attribution is
  emitted; any mismatch aborts with a nonzero exit code.

OUTPUT
  experiments/security-analysis-ablation-and-overhead/results/
  strict-atom-representation-attribution/interface-fix-inventory/
  v17-interface-finding-inventory.json

  Inputs are opened read-only; nothing is written outside the output
  directory.  No GPU, no network.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *HERE.parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
SCRIPT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/scripts/"
    "strict-atom-representation-attribution"
)
OUT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "strict-atom-representation-attribution/interface-fix-inventory"
)

# Anchors reported in utility_problem_analysis_and_design_2026-08-06.md
# (v17 merged retained precommit rows, reason-token counts).
EXPECTED_ROW_COUNTS = {
    "manifest_parse": 143,
    "tool_not_in": 80,
    "resolver_finding": 391,
}
EXPECTED_BENIGN_ROW_COUNTS = {
    "manifest_parse": 15,
    "tool_not_in": 4,
    "resolver_finding": 41,
}
EXPECTED_ATTACK_ROW_COUNTS = {
    "resolver_finding": 350,
}
# Case-level counts reported in A.2.4 (all-benign, case containment).
EXPECTED_BENIGN_CASE_COUNTS = {
    "manifest_parse": 8,
    "tool_not_in": 4,
    "resolver_finding": 21,
}

RESOLVER_REASON_RE = re.compile(
    r"^(?P<field>[A-Za-z_][A-Za-z_0-9.]*)="
    r"(?:'(?P<value>.*)'|\"(?P<value_dq>.*)\"|(?P<value_bare>[^'\"].*))"
    r": resolver_fill_requires_replan$"
)
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$")
URL_RE = re.compile(r"^(https?://|www\.)", re.IGNORECASE)
DATE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}$|^(?:today|tomorrow|yesterday)$|"
    r"^\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}$")


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def classify_value(value: str) -> str:
    value = str(value)
    if not value:
        return "empty"
    if EMAIL_RE.match(value):
        return "email"
    if URL_RE.match(value):
        return "url"
    if IBAN_RE.match(value):
        return "iban"
    if NUMBER_RE.match(value):
        return "number"
    if DATE_RE.match(value):
        return "date_like"
    if len(value) <= 40:
        return "short_text"
    return "long_text"


def reason_tokens(row: dict[str, Any]) -> list[str]:
    return [str(item) for item in row.get("reasons", []) or []]


def main() -> int:
    decomp = load_module(
        "v17_loss_decomposition",
        SCRIPT_DIR / "v17-merged-utility-loss-decomposition.py",
    )
    d6 = decomp.load_d6()
    merged_root = d6.DEFAULT_MERGED
    universe, bundle, manifest = decomp.build_retained(d6, merged_root)
    rows_by_case: dict[str, list[dict[str, Any]]] = bundle["rows_by_case"]
    plan_events_by_case: dict[str, list[dict[str, Any]]] = bundle["plan_events_by_case"]

    kind_of = {key: info["kind"] for key, info in universe.items()}
    utility_of = {key: bool(info["utility"]) for key, info in universe.items()}

    # ---- anchor verification (fail-closed) ----------------------------------
    row_counts: Counter[str] = Counter()
    row_counts_by_kind: dict[str, Counter[str]] = {
        "benign": Counter(),
        "attack": Counter(),
    }
    cases_with: dict[str, set[str]] = defaultdict(set)
    for key, rows in rows_by_case.items():
        for row in rows:
            for text in reason_tokens(row):
                family = None
                if text == "task_permission_plan_parse_failed":
                    family = "manifest_parse"
                elif text.endswith(": resolver_fill_requires_replan"):
                    family = "resolver_finding"
                elif text.startswith("tool_not_in"):
                    family = "tool_not_in"
                if family is None:
                    continue
                row_counts[family] += 1
                row_counts_by_kind[kind_of[key]][family] += 1
                cases_with[family].add(key)

    problems = []
    for family, expected in EXPECTED_ROW_COUNTS.items():
        if row_counts[family] != expected:
            problems.append(f"row count {family}: {row_counts[family]} != {expected}")
    for family, expected in EXPECTED_BENIGN_ROW_COUNTS.items():
        if row_counts_by_kind["benign"][family] != expected:
            problems.append(
                f"benign row count {family}: {row_counts_by_kind['benign'][family]} != {expected}"
            )
    for family, expected in EXPECTED_BENIGN_CASE_COUNTS.items():
        benign_cases = {k for k in cases_with[family] if kind_of[k] == "benign"}
        if len(benign_cases) != expected:
            problems.append(
                f"benign case count {family}: {len(benign_cases)} != {expected}"
            )
    for family, expected in EXPECTED_ATTACK_ROW_COUNTS.items():
        if row_counts_by_kind["attack"][family] != expected:
            problems.append(
                f"attack row count {family}: {row_counts_by_kind['attack'][family]} != {expected}"
            )
    if problems:
        print("anchor verification failed: " + "; ".join(problems), file=sys.stderr)
        return 1

    # ---- manifest_parse attribution -----------------------------------------
    manifest_cases: dict[str, dict[str, Any]] = {}
    for key in sorted(cases_with["manifest_parse"]):
        rows = rows_by_case[key]
        n_rows = sum(
            1
            for row in rows
            if "task_permission_plan_parse_failed" in reason_tokens(row)
        )
        plan_events = plan_events_by_case[key]
        error_counter: Counter[str] = Counter()
        for event in plan_events:
            for error in event.get("plan_validation_errors", []) or []:
                error_counter[str(error).split(":")[0]] += 1
        manifest_cases[key] = {
            "kind": kind_of[key],
            "utility": utility_of[key],
            "finding_rows": n_rows,
            "plan_events": len(plan_events),
            "plan_accepted_any": any(e.get("plan_accepted") for e in plan_events),
            "parse_valid_any": any(e.get("parse_valid") for e in plan_events),
            "validation_error_prefix_counts": dict(error_counter.most_common()),
        }

    # ---- tool_not_in attribution ---------------------------------------------
    tool_not_in_rows_detail: list[dict[str, Any]] = []
    tool_counter: Counter[str] = Counter()
    for key, rows in rows_by_case.items():
        for row in rows:
            if not any(t.startswith("tool_not_in") for t in reason_tokens(row)):
                continue
            tool_name = str(row.get("tool_name", ""))
            tool_counter[tool_name] += 1
            tool_not_in_rows_detail.append(
                {
                    "case": key,
                    "kind": kind_of[key],
                    "utility": utility_of[key],
                    "tool_name": tool_name,
                    "decision": row.get("decision"),
                    "guard_decision": row.get("guard_decision"),
                    "execution_attempted": bool(row.get("execution_attempted")),
                    "recovery_state": row.get("recovery_state"),
                }
            )
    tool_not_in_by_case: dict[str, dict[str, Any]] = {}
    for item in tool_not_in_rows_detail:
        entry = tool_not_in_by_case.setdefault(
            item["case"],
            {
                "kind": item["kind"],
                "utility": item["utility"],
                "rows": 0,
                "tools": Counter(),
                "blocked_rows": 0,
            },
        )
        entry["rows"] += 1
        entry["tools"][item["tool_name"]] += 1
        if not item["execution_attempted"]:
            entry["blocked_rows"] += 1

    # ---- resolver_fill attribution -------------------------------------------
    resolver_detail: list[dict[str, Any]] = []
    field_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    benign_blocked_resolver_rows = 0
    for key, rows in rows_by_case.items():
        for row in rows:
            for text in reason_tokens(row):
                match = RESOLVER_REASON_RE.match(text)
                if not match:
                    continue
                field = match.group("field")
                value = match.group("value")
                if value is None:
                    value = match.group("value_dq")
                if value is None:
                    value = match.group("value_bare")
                vtype = classify_value(value)
                field_counter[f"{row.get('tool_name')}.{field}"] += 1
                type_counter[vtype] += 1
                blocked = not bool(row.get("execution_attempted"))
                if kind_of[key] == "benign" and blocked:
                    benign_blocked_resolver_rows += 1
                resolver_detail.append(
                    {
                        "case": key,
                        "kind": kind_of[key],
                        "utility": utility_of[key],
                        "tool_name": row.get("tool_name"),
                        "field": field,
                        "value_type": vtype,
                        "value_prefix": value[:60],
                        "execution_attempted": bool(row.get("execution_attempted")),
                        "decision": row.get("decision"),
                    }
                )
    resolver_by_case: dict[str, dict[str, Any]] = {}
    for item in resolver_detail:
        entry = resolver_by_case.setdefault(
            item["case"],
            {"kind": item["kind"], "utility": item["utility"], "rows": 0,
             "blocked_rows": 0, "fields": Counter()},
        )
        entry["rows"] += 1
        entry["fields"][f"{item['tool_name']}.{item['field']}"] += 1
        if not item["execution_attempted"]:
            entry["blocked_rows"] += 1

    # ---- serialization -------------------------------------------------------
    def dump_case_table(table: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        rows_out = []
        for key in sorted(table):
            entry = dict(table[key])
            for field_name in ("tools", "fields"):
                if isinstance(entry.get(field_name), Counter):
                    entry[field_name] = dict(entry[field_name].most_common())
            entry["case"] = key
            rows_out.append(entry)
        return rows_out

    report = {
        "schema": "v17-interface-finding-inventory/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "merged_root": str(merged_root),
            "merge_plan_hash": manifest.get("plan_hash"),
            "decomposition_module": str(SCRIPT_DIR / "v17-merged-utility-loss-decomposition.py"),
        },
        "anchors_verified": {
            "row_counts": dict(row_counts),
            "benign_case_counts": {
                family: len({k for k in cases_with[family] if kind_of[k] == "benign"})
                for family in EXPECTED_ROW_COUNTS
            },
            "attack_row_counts": {
                family: row_counts_by_kind["attack"][family]
                for family in EXPECTED_ROW_COUNTS
            },
        },
        "manifest_parse": {
            "cases": dump_case_table(manifest_cases),
            "benign_cases": sorted(
                k for k in manifest_cases if manifest_cases[k]["kind"] == "benign"
            ),
        },
        "tool_not_in": {
            "tool_row_counts": dict(tool_counter.most_common()),
            "cases": dump_case_table(tool_not_in_by_case),
            "benign_cases": sorted(
                k for k in tool_not_in_by_case if tool_not_in_by_case[k]["kind"] == "benign"
            ),
            "rows": tool_not_in_rows_detail,
        },
        "resolver_finding": {
            "tool_field_row_counts": dict(field_counter.most_common()),
            "value_type_counts": dict(type_counter.most_common()),
            "benign_blocked_rows": benign_blocked_resolver_rows,
            "cases": dump_case_table(resolver_by_case),
            "benign_cases": sorted(
                k for k in resolver_by_case if resolver_by_case[k]["kind"] == "benign"
            ),
        },
        "caveats": [
            "Row counts are on D6 case-bound retained precommit rows (same caliber as the 2026-08-06 decomposition).",
            "resolver_fill rows executed under allow_with_trail are recorded as findings but were NOT blocked; blocked_rows fields separate the two.",
            "Attribution is necessary-condition evidence, not causal proof of utility loss.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "v17-interface-finding-inventory.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[interface-finding-inventory] anchors ok -> {out_path}")
    print(json.dumps(report["anchors_verified"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
