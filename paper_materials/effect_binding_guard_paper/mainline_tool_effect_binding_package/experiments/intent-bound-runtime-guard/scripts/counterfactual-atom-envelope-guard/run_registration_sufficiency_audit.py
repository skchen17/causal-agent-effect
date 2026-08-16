#!/usr/bin/env python3
"""Run repeated source-executed interventions without changing descriptors."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from collections import defaultdict
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
    aggregate_rows,
    classify_pair,
    effect_signature,
    jsonable,
    mutation_candidates,
)


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "paper").is_dir() and (parent / "experiments").is_dir()
)
OUT = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard"
DESCRIPTORS = (
    ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)
SOURCE_LOGDIR = ROOT / "runs/e76_agentdojo_official_v112_llm_descriptor_runtime_strict_20260711_142954_e76_strict_cap4096_ctx65536_gpu1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    descriptors = {
        row["tool_name"]: row
        for row in (
            json.loads(line) for line in DESCRIPTORS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    OUT.mkdir(parents=True, exist_ok=True)
    protocol_path = OUT / "registration_sufficiency_protocol.json"
    protocol = {
        "status": "frozen_before_execution",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "descriptor_sha256": sha256(DESCRIPTORS),
        "mutation_classes": [
            "observed_alternative",
            "typed_alternative",
            "boundary_alternative",
            "expansion_alternative",
            "surface_alternative",
        ],
        "classification": [
            "committed_effect_changed",
            "output_only_changed",
            "effect_invariant",
            "invalid_or_unresolved",
        ],
        "retain_all_failures": True,
    }
    if protocol_path.exists():
        existing = json.loads(protocol_path.read_text(encoding="utf-8"))
        if existing.get("descriptor_sha256") != protocol["descriptor_sha256"]:
            raise RuntimeError("descriptor changed after registration audit protocol freeze")
        protocol = existing
    else:
        protocol_path.write_text(
            json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    calls = observed_calls(SOURCE_LOGDIR)
    rows: list[dict[str, Any]] = []
    for suite_name in ("workspace", "slack", "travel", "banking"):
        suite = get_suite("v1.1.2", suite_name)
        runtime = FunctionsRuntime(suite.tools)
        for tool in suite.tools:
            if tool.name not in SIDE_EFFECT_TO_EFFECT:
                continue
            schema = tool.parameters.model_json_schema()
            tool_calls = calls.get((suite_name, tool.name), [])
            for field in sorted(schema.get("properties", {})):
                candidates_with_field = [call for call in tool_calls if field in call]
                base_args = copy.deepcopy(candidates_with_field[0]) if candidates_with_field else (
                    copy.deepcopy(tool_calls[0]) if tool_calls else {}
                )
                base_value = base_args.get(field)
                observed = [call[field] for call in candidates_with_field]
                mutations = mutation_candidates(base_value, observed, field)
                if not mutations:
                    mutations = [("unsupported", base_value)]
                base_result = execute(suite, runtime, tool.name, base_args)
                for index, (kind, candidate) in enumerate(mutations):
                    mutated_args = copy.deepcopy(base_args)
                    mutated_args[field] = candidate
                    mutated_result = execute(suite, runtime, tool.name, mutated_args)
                    descriptor = descriptors.get(tool.name, {})
                    rows.append(
                        {
                            "suite": suite_name,
                            "tool_name": tool.name,
                            "field": field,
                            "mutation_index": index,
                            "mutation_kind": kind,
                            "required": field in set(schema.get("required", [])),
                            "registered_security_relevant": field in descriptor.get("security_fields", []),
                            "registered_role": descriptor.get("field_roles", {}).get(field),
                            "registered_role_evidence": "lexical_heuristic_not_source_validated",
                            "base_value": jsonable(base_value),
                            "mutated_value": jsonable(candidate),
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

    aggregate = aggregate_rows(rows)
    report = {
        "experiment": "AgentDojo descriptor registration sufficiency audit",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agentdojo_version": "v1.1.2",
        "descriptor_sha256": sha256(DESCRIPTORS),
        "descriptor_security_fields": sum(len(row.get("security_fields", [])) for row in descriptors.values()),
        "descriptor_total_fields": sum(len(row.get("tool_fields", [])) for row in descriptors.values()),
        "descriptor_non_security_fields": sum(len(row.get("non_security_fields", [])) for row in descriptors.values()),
        **{key: value for key, value in aggregate.items() if key != "field_rows"},
        "field_rows": aggregate["field_rows"],
        "claim_boundary": (
            "This repeated source-execution audit does not modify the frozen C1f descriptors. "
            "A committed-effect witness shows necessity only for the executed intervention family. "
            "Absence of a witness is not proof of irrelevance. Registered field roles remain lexical "
            "heuristics unless separately validated. The 67/67 conservative field set must not be "
            "described as successful automatic field elimination."
        ),
    }
    rows_path = OUT / "registration_sufficiency_counterfactual_rows.jsonl"
    rows_path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )
    (OUT / "registration_sufficiency_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (OUT / "registration_sufficiency_field_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregate["field_rows"][0]))
        writer.writeheader()
        writer.writerows(aggregate["field_rows"])
    md = f"""# Registration Sufficiency Audit

- Frozen descriptor fields marked security-relevant: `{report['descriptor_security_fields']}/{report['descriptor_total_fields']}`.
- Frozen descriptor fields marked non-security: `{report['descriptor_non_security_fields']}`.
- Fields audited: `{report['n_fields']}`.
- Fields with five valid perturbations: `{report['n_fields_with_five_valid_perturbations']}/{report['n_fields']}`.
- Fields with at least one committed-effect witness: `{report['n_fields_with_committed_effect_witness']}/{report['n_fields']}`.
- Valid source executions: `{report['n_valid']}/{report['n_attempts']}`.

## Interpretation

{report['claim_boundary']}
"""
    (OUT / "registration_sufficiency_audit.md").write_text(md, encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "status", "n_fields", "n_fields_with_five_valid_perturbations",
        "n_fields_with_committed_effect_witness", "n_attempts", "n_valid"
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
