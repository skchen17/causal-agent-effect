"""Build candidate-effect rows from controlled Auth-SafeInv execution traces.

T58 hardens the T57 static effect-present verifier by moving the present signal
to execution-trace evidence: handler outputs, result metadata, and post-state
diffs. This builder expands each trace into one row per candidate effect, using
the trace-verified realized effects as the execution-level present verifier.

The text intentionally avoids printing gold `verified_effects`,
`unauthorized_effects`, or effect-diff keys. Those labels remain structured
fields for evaluation and verifier composition.

Outputs:
  data/auth_trace_effect_schema_conditioned_v1.jsonl
  analysis/auth_trace_effect_schema_conditioned_v1_manifest.json
  analysis/auth_trace_effect_schema_conditioned_v1_manifest.md
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import build_auth_effect_schema_conditioned_data as schema


SCHEMA_CONDITIONS = ["full_tool_chain", "execution_record"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build trace-conditioned candidate-effect rows.")
    parser.add_argument("--input", default="data/agent_tool_traces_auth_v2.jsonl")
    parser.add_argument("--output", default="data/auth_trace_effect_schema_conditioned_v1.jsonl")
    parser.add_argument("--manifest", default="analysis/auth_trace_effect_schema_conditioned_v1_manifest.json")
    parser.add_argument("--manifest-md", default="analysis/auth_trace_effect_schema_conditioned_v1_manifest.md")
    parser.add_argument("--candidate-effects", nargs="*", default=schema.CANDIDATE_EFFECTS)
    parser.add_argument("--conditions", nargs="*", default=["full_tool_chain"])
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def tool_call_text(row: dict[str, Any]) -> str:
    call = row.get("tool_call", {})
    name = call.get("name", row.get("mapped_abstract_tool", row.get("registered_tool_name", "unknown_tool")))
    args = json.dumps(call.get("arguments", {}), ensure_ascii=False, sort_keys=True)
    return f"{name}({args})"


def result_field_summary(row: dict[str, Any]) -> str:
    result = row.get("execution_result", {}) or {}
    pre_state = row.get("pre_state", {}) or {}
    post_state = row.get("post_state", {}) or {}
    verifier = row.get("effect_verifier", {}) or {}
    chunks = [
        f"trace type: {row.get('trace_type', 'unknown')}",
        f"verifier type: {verifier.get('type', 'unknown')}",
        "execution result fields: " + (", ".join(sorted(result)) if result else "none"),
        "pre-state fields: " + (", ".join(sorted(pre_state)) if pre_state else "none"),
        "post-state fields: " + (", ".join(sorted(post_state)) if post_state else "none"),
    ]
    return "; ".join(chunks)


def build_text(row: dict[str, Any], candidate_effect: str, condition: str) -> str:
    task = row.get("task_context", "")
    authorization = schema.render_authorization(row.get("authorized_effects", []))
    call = tool_call_text(row)
    candidate = schema.candidate_block(candidate_effect)
    question = (
        "Decision target: whether the candidate effect is realized by the execution "
        "and lies outside the authorization envelope."
    )
    if condition == "full_tool_chain":
        return "\n".join(
            [
                f"Task context: {task}",
                f"Authorization envelope: {authorization}",
                f"Observed tool call: {call}",
                candidate,
                question,
            ]
        )
    if condition == "execution_record":
        return "\n".join(
            [
                f"Task context: {task}",
                f"Authorization envelope: {authorization}",
                f"Observed tool call: {call}",
                f"Execution record summary: {result_field_summary(row)}",
                candidate,
                question,
            ]
        )
    raise ValueError(f"Unknown schema condition: {condition}")


def make_row(
    *,
    row_id: int,
    trace: dict[str, Any],
    candidate_effect: str,
    condition: str,
) -> dict[str, Any]:
    verified = set(trace.get("verified_effects", []))
    authorized = set(trace.get("authorized_effects", []))
    unauthorized = set(trace.get("unauthorized_effects", []))
    present = candidate_effect in verified
    is_authorized = candidate_effect in authorized
    label = candidate_effect in unauthorized
    absent_not_authorized = (candidate_effect not in verified) and (candidate_effect not in authorized)
    tool_name = trace.get("mapped_abstract_tool") or trace.get("registered_tool_name")
    verifier = trace.get("effect_verifier", {}) or {}
    return {
        "id": f"authtrace_schema_{row_id:06d}",
        "base_id": trace.get("id"),
        "split_group": trace.get("trace_group"),
        "schema_condition": condition,
        "trace_type": trace.get("trace_type"),
        "candidate_effect": candidate_effect,
        "candidate_effect_title": schema.EFFECT_TITLES.get(candidate_effect, candidate_effect.replace("_", " ")),
        "candidate_effect_definition": schema.effect_phrase(candidate_effect),
        "candidate_effect_present": present,
        "candidate_effect_authorized": is_authorized,
        "label_unauthorized_effect": label,
        "label_absent_not_authorized": absent_not_authorized,
        "task_context": trace.get("task_context"),
        "authorization_scope_text": schema.render_authorization(trace.get("authorized_effects", [])),
        "authorized_effects": trace.get("authorized_effects", []),
        "tool_name": tool_name,
        "surface_form": tool_name,
        "tool_call": trace.get("tool_call", {}),
        "predicted_call_flow": [
            "schema validation",
            "tool handler execution",
            "execution result capture",
            "post-state/effect verifier evaluation",
        ],
        "verified_effects": trace.get("verified_effects", []),
        "unauthorized_effects": trace.get("unauthorized_effects", []),
        "counterfactual_family": trace.get("trace_type"),
        "source": "effect_schema_conditioned_from_auth_execution_traces_v1",
        "execution_result": trace.get("execution_result", {}),
        "pre_state": trace.get("pre_state", {}),
        "post_state": trace.get("post_state", {}),
        "effect_diff": trace.get("effect_diff", {}),
        "effect_verifier": trace.get("effect_verifier", {}),
        "effect_verifier_type": verifier.get("type"),
        "effect_verifier_rules": verifier.get("rules", []),
        "trace_limitations": trace.get("trace_limitations", []),
        "scenario_text": build_text(trace, candidate_effect, condition),
        "effects": {"candidate_unauthorized_effect": int(label)},
    }


def build_rows(
    traces: list[dict[str, Any]],
    candidate_effects: list[str],
    conditions: list[str],
) -> list[dict[str, Any]]:
    unknown_effects = sorted(set(candidate_effects) - set(schema.EFFECT_DEFINITIONS))
    if unknown_effects:
        raise ValueError(f"Missing definitions for candidate effects: {unknown_effects}")
    unknown_conditions = sorted(set(conditions) - set(SCHEMA_CONDITIONS))
    if unknown_conditions:
        raise ValueError(f"Unknown schema conditions: {unknown_conditions}")
    rows: list[dict[str, Any]] = []
    row_id = 0
    for trace in traces:
        for condition in conditions:
            for effect in candidate_effects:
                rows.append(make_row(row_id=row_id, trace=trace, candidate_effect=effect, condition=condition))
                row_id += 1
    return rows


def leakage_checks(rows: list[dict[str, Any]], candidate_effects: list[str]) -> dict[str, Any]:
    exact_effect_mentions = Counter()
    label_field_mentions = Counter()
    texts = []
    for row in rows:
        text = row["scenario_text"]
        texts.append(text)
        for effect in candidate_effects:
            if effect in text:
                exact_effect_mentions[effect] += 1
        for token in ["verified_effects", "unauthorized_effects", "effect_diff", "label_unauthorized_effect"]:
            if token in text:
                label_field_mentions[token] += 1
    return {
        "duplicate_text_count": len(texts) - len(set(texts)),
        "exact_snakecase_effect_mentions_in_text": dict(sorted(exact_effect_mentions.items())),
        "label_field_mentions_in_text": dict(sorted(label_field_mentions.items())),
    }


def build_manifest(
    *,
    input_path: str,
    traces: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    candidate_effects: list[str],
    conditions: list[str],
) -> dict[str, Any]:
    cells: dict[str, dict[str, int]] = defaultdict(lambda: {"unauthorized_positive": 0, "present_positive": 0, "absent_not_authorized": 0})
    for row in rows:
        key = f"{row['candidate_effect']}::{row['tool_name']}::{row['trace_type']}"
        cells[key]["unauthorized_positive"] += int(row["label_unauthorized_effect"])
        cells[key]["present_positive"] += int(row["candidate_effect_present"])
        cells[key]["absent_not_authorized"] += int(row["label_absent_not_authorized"])
    trace_type_counts = Counter(trace.get("trace_type") for trace in traces)
    verifier_type_counts = Counter((trace.get("effect_verifier") or {}).get("type") for trace in traces)
    return {
        "schema_version": "auth_trace_effect_schema_conditioned_v1",
        "input_path": input_path,
        "n_traces": len(traces),
        "n_rows": len(rows),
        "candidate_effects": candidate_effects,
        "conditions": conditions,
        "trace_type_counts": dict(sorted(trace_type_counts.items())),
        "verifier_type_counts": dict(sorted(verifier_type_counts.items())),
        "rows_by_condition": dict(sorted(Counter(row["schema_condition"] for row in rows).items())),
        "rows_by_trace_type": dict(sorted(Counter(row["trace_type"] for row in rows).items())),
        "rows_by_candidate_effect": dict(sorted(Counter(row["candidate_effect"] for row in rows).items())),
        "present_by_candidate_effect": dict(sorted(Counter(row["candidate_effect"] for row in rows if row["candidate_effect_present"]).items())),
        "unauthorized_by_candidate_effect": dict(sorted(Counter(row["candidate_effect"] for row in rows if row["label_unauthorized_effect"]).items())),
        "unauthorized_by_trace_type": dict(sorted(Counter(row["trace_type"] for row in rows if row["label_unauthorized_effect"]).items())),
        "nonzero_cells": {k: v for k, v in sorted(cells.items()) if any(v.values())},
        "leakage_checks": leakage_checks(rows, candidate_effects),
        "caveats": [
            "Trace provenance is inherited from the input trace file; inspect trace_type_counts and the source trace manifest before making external-validity claims.",
            "candidate_effect_present is derived from trace verifier outputs and used as the execution-level present signal.",
            "scenario_text excludes gold verified_effects, unauthorized_effects, and effect_diff labels.",
        ],
    }


def write_manifest_md(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# Auth Trace Effect-Schema Conditioned Manifest",
        "",
        f"- Schema version: `{manifest['schema_version']}`",
        f"- Input: `{manifest['input_path']}`",
        f"- Traces: {manifest['n_traces']}",
        f"- Rows: {manifest['n_rows']}",
        f"- Conditions: `{manifest['conditions']}`",
        "",
        "## Trace Types",
        "",
        "| Trace type | Traces | Rows | Unauthorized candidate rows |",
        "|---|---:|---:|---:|",
    ]
    for trace_type, count in manifest["trace_type_counts"].items():
        rows = manifest["rows_by_trace_type"].get(trace_type, 0)
        unauth = manifest["unauthorized_by_trace_type"].get(trace_type, 0)
        lines.append(f"| `{trace_type}` | {count} | {rows} | {unauth} |")
    lines.extend(["", "## Candidate Effects", "", "| Effect | Rows | Present | Unauthorized |", "|---|---:|---:|---:|"])
    for effect, count in manifest["rows_by_candidate_effect"].items():
        present = manifest["present_by_candidate_effect"].get(effect, 0)
        unauth = manifest["unauthorized_by_candidate_effect"].get(effect, 0)
        lines.append(f"| `{effect}` | {count} | {present} | {unauth} |")
    lines.extend(["", "## Leakage Checks", ""])
    lines.append("```json")
    lines.append(json.dumps(manifest["leakage_checks"], indent=2, sort_keys=True))
    lines.append("```")
    lines.extend(["", "## Caveats", ""])
    for caveat in manifest["caveats"]:
        lines.append(f"- {caveat}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    base = Path(__file__).resolve().parent.parent
    input_path = base / args.input
    output_path = base / args.output
    manifest_path = base / args.manifest
    manifest_md_path = base / args.manifest_md
    traces = load_jsonl(input_path)
    rows = build_rows(traces, args.candidate_effects, args.conditions)
    write_jsonl(output_path, rows)
    manifest = build_manifest(
        input_path=args.input,
        traces=traces,
        rows=rows,
        candidate_effects=args.candidate_effects,
        conditions=args.conditions,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest_md(manifest_md_path, manifest)
    print(f"Saved rows: {output_path} ({len(rows)})")
    print(f"Saved manifest: {manifest_path}")
    print(f"Saved manifest MD: {manifest_md_path}")


if __name__ == "__main__":
    main()
