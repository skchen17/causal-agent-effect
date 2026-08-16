#!/usr/bin/env python3
"""Multi-base source-executed descriptor audit with explicit omission tests."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import (
    SIDE_EFFECT_TO_EFFECT,
)
from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.agentdojo_effect_diff_worker import (
    execute,
    observed_calls,
)
from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.registration_sufficiency_audit import (
    classify_pair,
    effect_signature,
    jsonable,
    mutation_candidates,
)


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "paper").is_dir() and (parent / "experiments").is_dir()
)
OUT = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard"
DESCRIPTORS = (
    ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)
SOURCE_LOGDIR = (
    ROOT
    / "runs/e76_agentdojo_official_v112_llm_descriptor_runtime_strict_20260711_142954_e76_strict_cap4096_ctx65536_gpu1"
)
KINDS = (
    "observed_alternative",
    "typed_alternative",
    "boundary_alternative",
    "expansion_alternative",
    "surface_alternative",
    "omission_default",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(value: Any) -> str:
    return json.dumps(jsonable(value), sort_keys=True, default=str)


def unique_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for call in calls:
        key = signature(call)
        if key not in seen:
            seen.add(key)
            result.append(copy.deepcopy(call))
    return result


def main() -> int:
    descriptors = {
        row["tool_name"]: row
        for row in (
            json.loads(line)
            for line in DESCRIPTORS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    calls = observed_calls(SOURCE_LOGDIR)
    rows: list[dict[str, Any]] = []
    field_metadata: dict[tuple[str, str, str], dict[str, Any]] = {}

    for suite_name in ("workspace", "slack", "travel", "banking"):
        suite = get_suite("v1.1.2", suite_name)
        runtime = FunctionsRuntime(suite.tools)
        for tool in suite.tools:
            if tool.name not in SIDE_EFFECT_TO_EFFECT:
                continue
            schema = tool.parameters.model_json_schema()
            required = set(schema.get("required", []))
            tool_calls = unique_calls(calls.get((suite_name, tool.name), []))
            valid_bases: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for candidate in tool_calls:
                result = execute(suite, runtime, tool.name, candidate)
                if not result.get("error"):
                    valid_bases.append((candidate, result))
                if len(valid_bases) >= 8:
                    break

            for field in sorted(schema.get("properties", {})):
                key = (suite_name, tool.name, field)
                eligible = [(args, result) for args, result in valid_bases if field in args]
                if not eligible:
                    eligible = valid_bases[:1]
                field_metadata[key] = {
                    "suite": suite_name,
                    "tool_name": tool.name,
                    "field": field,
                    "required": field in required,
                    "n_observed_calls": len(tool_calls),
                    "n_valid_base_calls": len(valid_bases),
                }
                observed = [call[field] for call in tool_calls if field in call]
                for base_index, (base_args, base_result) in enumerate(eligible[:5]):
                    base_value = base_args.get(field)
                    mutations = mutation_candidates(base_value, observed, field)
                    if field not in required:
                        mutations.append(("omission_default", None))
                    for mutation_index, (kind, candidate) in enumerate(mutations):
                        mutated_args = copy.deepcopy(base_args)
                        if kind == "omission_default":
                            mutated_args.pop(field, None)
                        else:
                            mutated_args[field] = candidate
                        mutated_result = execute(suite, runtime, tool.name, mutated_args)
                        descriptor = descriptors.get(tool.name, {})
                        rows.append(
                            {
                                **field_metadata[key],
                                "base_index": base_index,
                                "mutation_index": mutation_index,
                                "mutation_kind": kind,
                                "registered_security_relevant": field
                                in descriptor.get("security_fields", []),
                                "registered_role": descriptor.get("field_roles", {}).get(field),
                                "base_value": jsonable(base_value),
                                "mutated_value": (
                                    "__OMITTED__" if kind == "omission_default" else jsonable(candidate)
                                ),
                                "base_error": base_result.get("error"),
                                "mutated_error": mutated_result.get("error"),
                                "base_state_delta_paths": list(
                                    effect_signature(base_result.get("before"), base_result.get("after"))
                                ),
                                "mutated_state_delta_paths": list(
                                    effect_signature(mutated_result.get("before"), mutated_result.get("after"))
                                ),
                                "classification": classify_pair(base_result, mutated_result),
                            }
                        )

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["suite"], row["tool_name"], row["field"])].append(row)
    summaries = []
    for key, items in sorted(grouped.items()):
        valid = [row for row in items if row["classification"] != "invalid_or_unresolved"]
        valid_kinds = sorted({row["mutation_kind"] for row in valid})
        committed = [row for row in valid if row["classification"] == "committed_effect_changed"]
        summaries.append(
            {
                **field_metadata[key],
                "attempted": len(items),
                "valid": len(valid),
                "valid_mutation_kinds": "|".join(valid_kinds),
                "n_valid_mutation_kinds": len(valid_kinds),
                "five_valid_distinct_intervention_kinds": len(valid_kinds) >= 5,
                "committed_effect_changed": len(committed),
                "output_only_changed": sum(
                    row["classification"] == "output_only_changed" for row in valid
                ),
                "effect_invariant": sum(
                    row["classification"] == "effect_invariant" for row in valid
                ),
                "committed_effect_witness": bool(committed),
            }
        )

    report = {
        "experiment": "AgentDojo multi-base registration sufficiency audit",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agentdojo_version": "v1.1.2",
        "descriptor_sha256": sha256(DESCRIPTORS),
        "descriptor_security_fields": sum(
            len(row.get("security_fields", [])) for row in descriptors.values()
        ),
        "descriptor_total_fields": sum(
            len(row.get("tool_fields", [])) for row in descriptors.values()
        ),
        "descriptor_non_security_fields": sum(
            len(row.get("non_security_fields", [])) for row in descriptors.values()
        ),
        "mutation_kinds": list(KINDS),
        "n_fields": len(summaries),
        "n_attempts": len(rows),
        "n_valid": sum(row["valid"] for row in summaries),
        "classification_counts": dict(
            sorted(Counter(row["classification"] for row in rows).items())
        ),
        "n_fields_with_valid_base": sum(row["n_valid_base_calls"] > 0 for row in summaries),
        "n_fields_with_five_valid_distinct_intervention_kinds": sum(
            row["five_valid_distinct_intervention_kinds"] for row in summaries
        ),
        "n_fields_with_committed_effect_witness": sum(
            row["committed_effect_witness"] for row in summaries
        ),
        "field_rows": summaries,
        "claim_boundary": (
            "This post-freeze audit searches multiple observed base calls and adds an explicit "
            "omission/default intervention. It does not alter the C1f registry. Invalid rows are "
            "retained, and five valid mutation kinds are still a coverage measure rather than "
            "a proof of global field necessity or atom minimality."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "registration_sufficiency_counterfactual_rows_v2.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )
    (OUT / "registration_sufficiency_audit_v2.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (OUT / "registration_sufficiency_field_summary_v2.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    md = f"""# Multi-Base Registration Sufficiency Audit

- Fields: `{report['n_fields']}`.
- Fields with at least one valid base call: `{report['n_fields_with_valid_base']}/{report['n_fields']}`.
- Fields with five valid distinct intervention kinds: `{report['n_fields_with_five_valid_distinct_intervention_kinds']}/{report['n_fields']}`.
- Fields with a committed-effect witness: `{report['n_fields_with_committed_effect_witness']}/{report['n_fields']}`.
- Valid executions: `{report['n_valid']}/{report['n_attempts']}`.

{report['claim_boundary']}
"""
    (OUT / "registration_sufficiency_audit_v2.md").write_text(md, encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "status", "n_fields", "n_attempts", "n_valid", "n_fields_with_valid_base",
        "n_fields_with_five_valid_distinct_intervention_kinds",
        "n_fields_with_committed_effect_witness",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
