"""Merge base, main-conference increment, and trace rows.

Default output is ``scenarios_mainconf_v2`` so existing v1 embeddings/results
remain historically valid.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


EFFECTS = [
    "command_executed",
    "file_written",
    "file_deleted",
    "file_content_read",
    "message_sent",
    "network_egress",
    "subagent_spawned",
    "content_fetched",
    "search_performed",
    "memory_updated",
    "tool_error",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_effects(row: dict[str, Any]) -> dict[str, int]:
    source_effects = row.get("effects", {})
    return {effect: int(source_effects.get(effect, 0)) for effect in EFFECTS}


def normalize_row(row: dict[str, Any], source_name: str, idx: int) -> dict[str, Any]:
    out = dict(row)
    out.setdefault("id", f"{source_name}-{idx:06d}")
    out["effects"] = normalize_effects(out)
    out["_source"] = source_name
    out["source"] = out.get("source") or source_name

    if source_name == "agent_tool_trace":
        out["tool_name"] = out.get("mapped_abstract_tool") or out.get("tool_name") or out.get("registered_tool_name", "unknown")
    else:
        out.setdefault("tool_name", "unknown")

    out.setdefault("scenario_text", "")
    out.setdefault("context_type", "unknown")
    return out


def build_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = Counter(row.get("_source", "missing") for row in rows)
    tool_counts = Counter(row.get("tool_name", "unknown") for row in rows)
    trace_types = Counter(row.get("trace_type", "none") for row in rows if row.get("_source") == "agent_tool_trace")
    effect_counts: Counter[str] = Counter()
    cell_counts: dict[str, dict[str, int]] = {}

    for row in rows:
        tool = row.get("tool_name", "unknown")
        for effect, value in row.get("effects", {}).items():
            key = f"{effect}/{tool}"
            cell_counts.setdefault(key, {"n": 0, "n_positive": 0, "n_negative": 0})
            cell_counts[key]["n"] += 1
            if value:
                cell_counts[key]["n_positive"] += 1
                effect_counts[effect] += 1
            else:
                cell_counts[key]["n_negative"] += 1

    required_increment = ["tool_call", "call_flow"]
    required_trace = ["tool_schema", "pre_state", "authorization_scope", "observed_or_simulated_effects"]
    schema_checks = {
        "increment_missing_tool_call": sum(
            row.get("_source") == "mainconf_increment" and "tool_call" not in row for row in rows
        ),
        "increment_missing_call_flow": sum(
            row.get("_source") == "mainconf_increment" and "call_flow" not in row for row in rows
        ),
        "trace_missing_required_fields": {
            key: sum(row.get("_source") == "agent_tool_trace" and key not in row for row in rows)
            for key in required_trace
        },
        "unresolved_brace_placeholders": sum(
            row.get("_source") == "mainconf_increment"
            and ("{" in row.get("scenario_text", "") or "}" in row.get("scenario_text", ""))
            for row in rows
        ),
        "required_increment_fields": required_increment,
        "required_trace_fields": required_trace,
    }

    return {
        "schema_version": "scenarios_mainconf_manifest_v2",
        "n_total": len(rows),
        "sources": dict(source_counts),
        "tool_counts": dict(tool_counts),
        "trace_type_counts": dict(trace_types),
        "effect_positive_counts": dict(effect_counts),
        "cell_counts": cell_counts,
        "schema_checks": schema_checks,
        "notes": [
            "v2 preserves source in both source and _source fields.",
            "Existing scenarios_mainconf_v1 embeddings/results are not valid for this v2 file.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="data/scenarios_merged.jsonl")
    parser.add_argument("--increment", default="data/scenarios_mainconf_increment_v2.jsonl")
    parser.add_argument("--traces", default="data/agent_tool_traces_mainconf_v2.jsonl")
    parser.add_argument("--output", default="data/scenarios_mainconf_v2.jsonl")
    parser.add_argument("--manifest", default="analysis/scenarios_mainconf_v2_manifest.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    merged: list[dict[str, Any]] = []
    for source_name, path_str in [
        ("scenarios_merged", args.base),
        ("mainconf_increment", args.increment),
        ("agent_tool_trace", args.traces),
    ]:
        rows = read_jsonl(root / path_str)
        for idx, row in enumerate(rows):
            merged.append(normalize_row(row, source_name, idx))

    output = root / args.output
    manifest_path = root / args.manifest
    write_jsonl(output, merged)
    manifest = build_manifest(merged)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(merged)} rows to {output}")
    print(f"Wrote manifest to {manifest_path}")
    print(f"Schema checks: {manifest['schema_checks']}")


if __name__ == "__main__":
    main()
