#!/usr/bin/env python3
"""Measure semantic placement and prototype costs of two sufficient interfaces."""

from __future__ import annotations

import ast
import csv
import gc
import hashlib
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.compatibility.scripts.independent_authority_benchmark import (
    authority_model, descriptor_runtime, run_experiment as authority_base,
    state_aware_request_adapter, state_aware_view,
)
from shared.compatibility.scripts.third_party_authorization_interface_validation.descriptor_compiler import (
    compile_descriptor as compile_third_party, initial_descriptors,
)
from shared.compatibility.scripts.third_party_authorization_interface_validation.policy import authorize_all as authorize_third_party
from shared.compatibility.scripts.third_party_authorization_interface_validation.state_aware_adapter import (
    build_view as build_third_party_state_view,
    requests as third_party_state_requests,
)


ROOT = REPO_ROOT
EVAL = ROOT / "experiments/human-authority-and-causal-validation/evaluation/authorization-interface-economy"
RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/authorization-interface-economy"
AUTH_RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface"
THIRD_EVAL = ROOT / "experiments/human-authority-and-causal-validation/evaluation/third-party-authorization-interface-validation"
THIRD_RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation"
WARMUP_BATCHES = 3
TIMED_BATCHES = 30


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def scalar_leaves(value: Any) -> int:
    if isinstance(value, dict):
        return sum(scalar_leaves(item) for item in value.values())
    if isinstance(value, list):
        return sum(scalar_leaves(item) for item in value)
    return 1


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def distribution(values: list[float]) -> dict[str, float]:
    return {"median": statistics.median(values), "p95": quantile(values, 0.95),
            "min": min(values), "max": max(values)}


def code_metrics(paths: list[Path], tool_names: set[str]) -> dict[str, Any]:
    statements = branches = 0
    referenced_tools = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        statements += sum(isinstance(node, ast.stmt) for node in ast.walk(tree))
        branches += sum(isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.IfExp, ast.Match))
                        for node in ast.walk(tree))
        referenced_tools.update(
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in tool_names
        )
    return {
        "python_files": [str(path.relative_to(ROOT)) for path in paths],
        "source_bytes": sum(path.stat().st_size for path in paths),
        "ast_statements": statements, "branch_nodes": branches,
        "tool_names_in_executable_code": sorted(referenced_tools),
        "n_tool_names_in_executable_code": len(referenced_tools),
    }


def overpartition(rows: list[dict[str, Any]], source_key: Callable[[dict[str, Any]], str],
                  representation_key: Callable[[dict[str, Any]], str]) -> int:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[source_key(row)].append(row)
    return sum(
        representation_key(left) != representation_key(right)
        for values in groups.values() for left, right in combinations(values, 2)
    )


def time_path(rows: list[dict[str, Any]], function: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    for _ in range(WARMUP_BATCHES):
        for row in rows:
            function(row)
    batches = []
    gc_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(TIMED_BATCHES):
            started = time.perf_counter_ns()
            for row in rows:
                function(row)
            batches.append((time.perf_counter_ns() - started) / len(rows) / 1000.0)
    finally:
        if gc_enabled:
            gc.enable()
    return {"unit": "microseconds_per_context", "warmup_batches": WARMUP_BATCHES,
            "timed_batches": TIMED_BATCHES, **distribution(batches)}


def stage_timings(rows: list[dict[str, Any]], construct: Callable[[Any], Any],
                  adapt: Callable[[Any], Any], authorize: Callable[[Any], Any]) -> dict[str, Any]:
    constructed = [construct(row) for row in rows]
    adapted = [adapt(item) for item in constructed]
    return {
        "view_construction": time_path(rows, construct),
        "semantic_adaptation": time_path(constructed, adapt),
        "authorization": time_path(adapted, authorize),
        "end_to_end": time_path(rows, lambda row: authorize(adapt(construct(row)))),
    }


def authority_domain() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = read_jsonl(authority_base.RESULTS / "source-executions-and-typed-effects.jsonl")
    descriptors = descriptor_runtime.load_descriptors(str(authority_base.FROZEN))
    state = json.loads(authority_base.AUTHORITY.read_text(encoding="utf-8"))

    def typed_construct(row: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return descriptor_runtime.compile_descriptor(descriptors[row["tool_name"]], row), row["authority_context"]

    def typed_adapt(value: tuple[list[dict[str, Any]], dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return value

    def state_construct(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        return state_aware_view.build_view(row), row["authority_context"]

    def state_adapt(value: tuple[dict[str, Any], dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        view, context = value
        return state_aware_request_adapter.requests(view), context

    def decide(value: tuple[list[dict[str, Any]], dict[str, Any]]) -> tuple[str, list[str]]:
        atoms, context = value
        requests = [authority_model.atom_request(atom, context) for atom in atoms]
        return authority_model.authorize_all(requests, state, context, partial=True, inventory_complete=True)

    views = [state_aware_view.build_view(row) for row in rows]
    exposure = [{"resolved_defaults": view["resolved_defaults"],
                 "referenced_resources": view["referenced_resources"]} for view in views]
    typed_keys = [canonical(row["typed_effects"]) for row in rows]
    state_keys = [canonical(view) for view in views]
    report = json.loads((AUTH_RESULTS / "report.json").read_text(encoding="utf-8"))
    collision = {item["representation"]: item for item in report["collision_metrics"]}
    tool_names = {row["tool_name"] for row in rows}
    typed_code = code_metrics([ROOT / "shared/compatibility/scripts/independent_authority_benchmark/descriptor_runtime.py"], tool_names)
    state_code = code_metrics([
        ROOT / "shared/compatibility/scripts/independent_authority_benchmark/state_aware_view.py",
        ROOT / "shared/compatibility/scripts/independent_authority_benchmark/state_aware_request_adapter.py",
    ], tool_names)
    descriptor_bytes = authority_base.FROZEN.stat().st_size
    metrics = []
    for name, keys, raw_exposure, code, construct, adapt in (
        ("typed_effect", typed_keys, [{} for _ in rows], typed_code, typed_construct, typed_adapt),
        ("state_aware_request", state_keys, exposure, state_code, state_construct, state_adapt),
    ):
        collision_row = collision["validated_typed_effects" if name == "typed_effect" else "state_aware_raw_call"]
        metrics.append({
            "domain": "explicit_authority_1024", "interface": name, "n_contexts": len(rows),
            "n_cells": collision_row["n_cells"], "mixed_cells": collision_row["n_mixed_cells"],
            "overpartition_pairs": collision_row["overpartition_pairs"],
            "serialized_bytes": distribution([len(key.encode()) for key in keys]),
            "scalar_leaves": distribution([scalar_leaves(json.loads(key)) for key in keys]),
            "raw_trusted_state_bytes": distribution([len(canonical(item).encode()) for item in raw_exposure]),
            "raw_trusted_state_leaves": distribution([scalar_leaves(item) if item else 0 for item in raw_exposure]),
            "runtime_code": code, "declarative_descriptor_bytes": descriptor_bytes if name == "typed_effect" else 0,
            "semantic_placement": {
                "descriptor_entries": len(descriptors) if name == "typed_effect" else 0,
                "tool_specific_executable_adapter": name == "state_aware_request",
                "new_tool_requires_executable_dispatch_change": name == "state_aware_request",
                "new_tool_requires_declarative_entry": name == "typed_effect",
                "note": ("generic descriptor interpreter" if name == "typed_effect"
                         else "tool-specific view construction and request adaptation"),
            },
            "decision_agreement": sum(decide(adapt(construct(row)))[0] == row["ideal_decision"] for row in rows) / len(rows),
            "timing": stage_timings(rows, construct, adapt, decide),
        })
    return metrics, {}


def third_party_domain() -> list[dict[str, Any]]:
    rows = read_jsonl(THIRD_RESULTS / "post_freeze_authorization_rows.jsonl")
    descriptors_list = initial_descriptors()
    descriptors = {item["tool_name"]: item for item in descriptors_list}
    manifest = json.loads((THIRD_EVAL / "authority_manifest.json").read_text(encoding="utf-8"))

    def typed_construct(row: dict[str, Any]) -> list[dict[str, Any]]:
        return compile_third_party(descriptors[row["tool_name"]], row)

    def state_construct(row: dict[str, Any]) -> dict[str, Any]:
        return build_third_party_state_view(row)

    def decide(requests: list[dict[str, Any]]) -> tuple[str, list[str]]:
        return authorize_third_party(requests, manifest, partial=False, inventory_complete=True)

    typed_keys = [row["representation_keys"]["typed_effect"] for row in rows]
    state_keys = [row["representation_keys"]["state_aware_raw_call"] for row in rows]
    exposures = [build_third_party_state_view(row)["referenced_state"] for row in rows]
    tool_names = {row["tool_name"] for row in rows}
    typed_code = code_metrics([ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/descriptor_compiler.py"], tool_names)
    state_code = code_metrics([ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/state_aware_adapter.py"], tool_names)
    collision_report = json.loads((THIRD_RESULTS / "third_party_validation_report.json").read_text(encoding="utf-8"))
    collisions = {item["representation"]: item for item in collision_report["collision_metrics"]}
    output = []
    for name, keys, raw_exposure, code, construct, adapt, source_rep in (
        ("typed_effect", typed_keys, [{} for _ in rows], typed_code, typed_construct, lambda value: value, "typed_effect"),
        ("state_aware_request", state_keys, exposures, state_code, state_construct, third_party_state_requests, "state_aware_raw_call"),
    ):
        collision = collisions[source_rep]
        output.append({
            "domain": "third_party_mcp_264", "interface": name, "n_contexts": len(rows),
            "n_cells": collision["n_cells"], "mixed_cells": collision["mixed_cells"],
            "overpartition_pairs": overpartition(rows,
                lambda row: row["representation_keys"]["source_effect_oracle"],
                lambda row, rep=source_rep: row["representation_keys"][rep]),
            "serialized_bytes": distribution([len(key.encode()) for key in keys]),
            "scalar_leaves": distribution([scalar_leaves(json.loads(key)) for key in keys]),
            "raw_trusted_state_bytes": distribution([len(canonical(item).encode()) for item in raw_exposure]),
            "raw_trusted_state_leaves": distribution([scalar_leaves(item) if item else 0 for item in raw_exposure]),
            "runtime_code": code,
            "declarative_descriptor_bytes": len(canonical(descriptors_list).encode()) if name == "typed_effect" else 0,
            "semantic_placement": {
                "descriptor_entries": len(descriptors_list) if name == "typed_effect" else 0,
                "tool_specific_executable_adapter": True,
                "new_tool_requires_executable_dispatch_change": True,
                "new_tool_requires_declarative_entry": name == "typed_effect",
                "note": ("prototype descriptor plus tool-specific compiler"
                         if name == "typed_effect" else "tool-specific state-aware request adapter"),
            },
            "decision_agreement": sum(decide(adapt(construct(row)))[0] == row["ideal_decision"] for row in rows) / len(rows),
            "timing": stage_timings(rows, construct, adapt, decide),
        })
    return output


def main() -> int:
    EVAL.mkdir(parents=True, exist_ok=True); RESULTS.mkdir(parents=True, exist_ok=True)
    authority_metrics, _ = authority_domain()
    third_metrics = third_party_domain()
    metrics = authority_metrics + third_metrics
    sources = [
        AUTH_RESULTS / "report.json", authority_base.RESULTS / "source-executions-and-typed-effects.jsonl",
        THIRD_RESULTS / "third_party_validation_report.json", THIRD_RESULTS / "post_freeze_authorization_rows.jsonl",
        ROOT / "shared/compatibility/scripts/independent_authority_benchmark/descriptor_runtime.py",
        ROOT / "shared/compatibility/scripts/independent_authority_benchmark/state_aware_view.py",
        ROOT / "shared/compatibility/scripts/independent_authority_benchmark/state_aware_request_adapter.py",
        ROOT / "shared/compatibility/scripts/independent_authority_benchmark/authority_model.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/descriptor_compiler.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/state_aware_adapter.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/policy.py",
        Path(__file__),
    ]
    protocol = {
        "protocol": "authorization-interface-economy-v1", "warmup_batches": WARMUP_BATCHES,
        "timed_batches": TIMED_BATCHES, "source_hashes": {str(path.relative_to(ROOT)): sha(path) for path in sources},
        "measurement_scope": "prototype implementation only; not production TCB or deployment latency",
        "outcome_rule": "all outcomes retained; typed interface need not win",
    }
    protocol["protocol_hash"] = hashlib.sha256(canonical(protocol).encode()).hexdigest()
    (EVAL / "protocol_manifest.json").write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (RESULTS / "interface_economy_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    flat = []
    for row in metrics:
        flat.append({
            "domain": row["domain"], "interface": row["interface"], "cells": row["n_cells"],
            "mixed": row["mixed_cells"], "overpartition_pairs": row["overpartition_pairs"],
            "median_bytes": row["serialized_bytes"]["median"], "p95_bytes": row["serialized_bytes"]["p95"],
            "median_state_bytes": row["raw_trusted_state_bytes"]["median"],
            "ast_statements": row["runtime_code"]["ast_statements"],
            "tool_names_in_code": row["runtime_code"]["n_tool_names_in_executable_code"],
            "decision_agreement": row["decision_agreement"],
            "view_us": row["timing"]["view_construction"]["median"],
            "adapt_us": row["timing"]["semantic_adaptation"]["median"],
            "authorize_us": row["timing"]["authorization"]["median"],
            "median_latency_us": row["timing"]["end_to_end"]["median"],
            "p95_latency_us": row["timing"]["end_to_end"]["p95"],
        })
    with (RESULTS / "interface_economy_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0])); writer.writeheader(); writer.writerows(flat)
    report = {"status": "passed", "protocol_hash": protocol["protocol_hash"], "metrics": metrics,
              "all_outcomes_retained": True, "claim_boundary": protocol["measurement_scope"]}
    (RESULTS / "interface_economy_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Authorization Interface Economy", "", "| Domain | Interface | Cells | Mixed | Overpartition | Median bytes | Median state bytes | AST stmts | Tool names in code | Median us |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    lines += [f"| {r['domain']} | {r['interface']} | {r['cells']} | {r['mixed']} | {r['overpartition_pairs']} | "
              f"{r['median_bytes']:.1f} | {r['median_state_bytes']:.1f} | {r['ast_statements']} | "
              f"{r['tool_names_in_code']} | {r['median_latency_us']:.2f} |" for r in flat]
    lines += ["", "Measurements describe this prototype only; a state-aware success is accepted.", ""]
    (RESULTS / "interface_economy_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
