#!/usr/bin/env python3
"""Overlay the frozen authority benchmark with a state-aware request view."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

from shared.compatibility.scripts.independent_authority_benchmark import (
    authority_model,
    run_experiment as base,
    state_aware_request_adapter,
    state_aware_view,
)


ROOT = Path(__file__).resolve().parents[3]
EVAL = ROOT / "experiments/human-authority-and-causal-validation/evaluation/state-aware-authority-interface"
RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface"
VIEW_CONTRACT = EVAL / "view-contract.json"
ADAPTER_CONTRACT = EVAL / "request-adapter-contract.json"
PROTOCOL = EVAL / "protocol-lock.json"
REPRESENTATIONS = (*base.REPRESENTATIONS, "state_aware_raw_call")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def freeze(force: bool = False) -> dict[str, Any]:
    base.verify_protocol()
    if PROTOCOL.exists() and not force:
        raise FileExistsError(f"protocol already frozen: {PROTOCOL}")
    EVAL.mkdir(parents=True, exist_ok=True)
    write_json(VIEW_CONTRACT, state_aware_view.contract())
    write_json(ADAPTER_CONTRACT, state_aware_request_adapter.contract())
    protocol = {
        "experiment": "state_aware_authority_interface",
        "status": "frozen",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "base_experiment": "protocol_separated_authority_representation",
        "base_protocol_sha256": sha256(base.PROTOCOL),
        "expected_contexts": 1024,
        "representations": list(REPRESENTATIONS),
        "tracks": {
            "representation_only": "collision, state collision, overpartition, and size over the effect-free view",
            "request_adapter_diagnostic": "direct authority metrics using a separately disclosed tool-specific adapter",
        },
        "hashes": {
            "base_contexts": sha256(base.EVALUATION),
            "base_authority": sha256(base.AUTHORITY),
            "base_descriptors": sha256(base.FROZEN),
            "view_contract": sha256(VIEW_CONTRACT),
            "adapter_contract": sha256(ADAPTER_CONTRACT),
            "view_module": sha256(Path(state_aware_view.__file__)),
            "adapter_module": sha256(Path(state_aware_request_adapter.__file__)),
            "runner_module": sha256(Path(__file__)),
        },
        "outcome_independent_acceptance": True,
        "claim_boundary": (
            "The state-aware view is effect-free. Direct authorization metrics additionally depend on a "
            "frozen tool-specific request adapter and are reported as a separate diagnostic."
        ),
    }
    write_json(PROTOCOL, protocol)
    return protocol


def verify() -> dict[str, Any]:
    base.verify_protocol()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    observed = {
        "base_contexts": sha256(base.EVALUATION),
        "base_authority": sha256(base.AUTHORITY),
        "base_descriptors": sha256(base.FROZEN),
        "view_contract": sha256(VIEW_CONTRACT),
        "adapter_contract": sha256(ADAPTER_CONTRACT),
        "view_module": sha256(Path(state_aware_view.__file__)),
        "adapter_module": sha256(Path(state_aware_request_adapter.__file__)),
        "runner_module": sha256(Path(__file__)),
    }
    if observed != protocol["hashes"]:
        raise RuntimeError({key: {"expected": protocol["hashes"].get(key), "observed": value}
                            for key, value in observed.items() if protocol["hashes"].get(key) != value})
    return protocol


def _state_decision(row: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    view = state_aware_view.build_view(row)
    atoms = state_aware_request_adapter.requests(view)
    requests = [authority_model.atom_request(atom, row["authority_context"]) for atom in atoms]
    decision, reasons = authority_model.authorize_all(
        requests, authority, row["authority_context"], partial=True, inventory_complete=True,
    )
    encoded = canonical(view)
    return {
        "case_id": row["case_id"], "domain": row["domain"], "stratum": row["stratum"],
        "argument_group_id": row["argument_group_id"], "representation": "state_aware_raw_call",
        "representation_key": encoded, "representation_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "monitor_decision": decision, "monitor_reasons": reasons,
        "ideal_decision": row["ideal_decision"],
        "descriptor_exact_transition_match": row["descriptor_exact_transition_match"],
        "state_aware_view": view, "adapter_requests": atoms,
    }


def _scalar_leaves(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_scalar_leaves(item) for item in value.values())
    if isinstance(value, list):
        return sum(_scalar_leaves(item) for item in value)
    return 1


def _percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def _representation_diagnostics(evaluated: list[dict[str, Any]], decisions: list[dict[str, Any]],
                                representation: str) -> dict[str, Any]:
    rows = [row for row in decisions if row["representation"] == representation]
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_by_case = {row["case_id"]: canonical(row["source_transitions"]) for row in evaluated}
    for row in rows:
        by_source[source_by_case[row["case_id"]]].append(row)
    overpartition = 0
    for members in by_source.values():
        total = len(members) * (len(members) - 1) // 2
        by_key = Counter(row["representation_key"] for row in members)
        same = sum(n * (n - 1) // 2 for n in by_key.values())
        overpartition += total - same

    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_key[row["representation_key"]].append(row)
    separating_pairs = 0
    for members in by_key.values():
        labels = Counter(row["ideal_decision"] for row in members)
        separating_pairs += labels["ALLOW"] * labels["DENY"]

    sizes = [len(row["representation_key"].encode()) for row in rows]
    scalars = [_scalar_leaves(row.get("state_aware_view", json.loads(row["representation_key"]))) for row in rows]
    return {
        "representation": representation,
        "authorization_separating_pairs": separating_pairs,
        "overpartition_pairs": overpartition,
        "serialized_bytes": {"median": statistics.median(sizes), "p95": _percentile(sizes, 0.95), "max": max(sizes)},
        "scalar_leaves": {"median": statistics.median(scalars), "p95": _percentile(scalars, 0.95), "max": max(scalars)},
    }


def _state_collision_audit(evaluated: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> dict[str, Any]:
    labels: dict[str, set[str]] = defaultdict(set)
    for row in evaluated:
        labels[row["argument_group_id"]].add(row["ideal_decision"])
    separating = {group for group, values in labels.items() if len(values) > 1}
    result = {"n_argument_groups": len(labels), "n_state_policy_separating_groups": len(separating), "representations": {}}
    for representation in REPRESENTATIONS:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in decisions:
            if row["representation"] == representation and row["argument_group_id"] in separating:
                groups[row["argument_group_id"]].append(row)
        collisions = sum(len({row["representation_key"] for row in members}) == 1 for members in groups.values())
        result["representations"][representation] = {
            "colliding_groups": collisions, "total": len(separating),
            "rate": collisions / len(separating) if separating else None,
        }
    return result


def _taxonomy(evaluated: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evaluated_by_id = {row["case_id"]: row for row in evaluated}
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        if row["representation"] == "state_aware_raw_call":
            cells[row["representation_key"]].append(row)
    output = []
    for key, members in sorted(cells.items()):
        allows = sorted((row for row in members if row["ideal_decision"] == "ALLOW"), key=lambda row: row["case_id"])
        denies = sorted((row for row in members if row["ideal_decision"] == "DENY"), key=lambda row: row["case_id"])
        if not allows or not denies:
            continue
        for allow, deny in combinations([allows[0], denies[0]], 2):
            first, second = evaluated_by_id[allow["case_id"]], evaluated_by_id[deny["case_id"]]
            operations = {item["operation"] for item in first["source_transitions"] + second["source_transitions"]}
            category = "state_transition_not_represented"
            if any("participant" in item or "notify" in item or "share" in item for item in operations):
                category = "compound_or_target_expansion"
            elif any("visibility" in item or "recurrence" in item for item in operations):
                category = "default_or_qualifier_semantics"
            elif any("fee" in item or "balance" in item or "compliance" in item for item in operations):
                category = "state_dependent_compound_effect"
            output.append({
                "cell_sha256": hashlib.sha256(key.encode()).hexdigest(),
                "allow_case_id": allow["case_id"], "deny_case_id": deny["case_id"],
                "cause": category, "allow_source_transitions": first["source_transitions"],
                "deny_source_transitions": second["source_transitions"],
            })
    return output


def _old_results_unchanged(direct: list[dict[str, Any]], collisions: list[dict[str, Any]]) -> bool:
    old = json.loads((base.RESULTS / "report.json").read_text(encoding="utf-8"))
    old_direct = {(row["representation"], row["stratum"]): row for row in old["direct_metrics"]}
    old_collisions = {row["representation"]: row for row in old["collision_metrics"]}
    direct_unchanged = all(
        row == old_direct[(row["representation"], row["stratum"])]
        for row in direct if row["representation"] in base.REPRESENTATIONS
    )
    collision_keys = {
        "representation", "n_cells", "n_mixed_cells", "rows_in_mixed_cells",
        "minimum_unavoidable_errors",
    }
    collisions_unchanged = all(
        {key: row[key] for key in collision_keys} == old_collisions[row["representation"]]
        for row in collisions if row["representation"] in base.REPRESENTATIONS
    )
    return direct_unchanged and collisions_unchanged


def run() -> dict[str, Any]:
    protocol = verify()
    authority = json.loads(base.AUTHORITY.read_text(encoding="utf-8"))
    descriptors = base.descriptor_runtime.load_descriptors(str(base.FROZEN))
    contexts = base.read_jsonl(base.EVALUATION)
    if len(contexts) != protocol["expected_contexts"]:
        raise RuntimeError("base context count changed")
    evaluated = [base.evaluate_context(row, descriptors, authority) for row in contexts]
    decisions = base.monitor_decisions(evaluated, authority)
    decisions.extend(_state_decision(row, authority) for row in evaluated)
    direct = [base.metric(decisions, representation, stratum) for representation in REPRESENTATIONS for stratum in ("all", "routine", "boundary")]
    collision_metrics, collision_rows = [], []
    for representation in REPRESENTATIONS:
        summary, rows = base.collision_audit(decisions, representation)
        summary.update(_representation_diagnostics(evaluated, decisions, representation))
        collision_metrics.append(summary)
        collision_rows.extend(rows)
    taxonomy = _taxonomy(evaluated, decisions)
    state_dependent = _state_collision_audit(evaluated, decisions)
    gates = {
        "base_protocol_verified": True,
        "all_1024_contexts_retained": len(evaluated) == 1024,
        "five_rows_per_context": len(decisions) == 5 * len(evaluated),
        "case_ids_unique": len({row["case_id"] for row in evaluated}) == len(evaluated),
        "old_four_representation_results_unchanged": _old_results_unchanged(direct, collision_metrics),
        "state_views_complete": all("state_aware_view" in row for row in decisions if row["representation"] == "state_aware_raw_call"),
        "no_silent_adapter_failure": all(row["monitor_decision"] in {"ALLOW", "DENY", "ABSTAIN"} for row in decisions),
    }
    report = {
        "experiment": "state_aware_authority_interface", "status": "passed" if all(gates.values()) else "failed",
        "n_contexts": len(evaluated), "representations": list(REPRESENTATIONS),
        "direct_metrics": direct, "collision_metrics": collision_metrics,
        "state_dependent": state_dependent, "state_aware_failure_taxonomy_count": len(taxonomy),
        "acceptance_gates": gates, "protocol_sha256": sha256(PROTOCOL),
        "interpretation": {
            "representation_track": "Collision results use only the effect-free state-aware view.",
            "direct_track": "Direct metrics also use the frozen tool-specific request adapter.",
            "outcome_rule": "A tie or state-aware success is accepted; scientific status does not depend on typed effects winning.",
        },
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_jsonl(RESULTS / "source-executions.jsonl", evaluated)
    write_jsonl(RESULTS / "representation-rows.jsonl", decisions)
    write_jsonl(RESULTS / "collision-witnesses.jsonl", collision_rows)
    write_jsonl(RESULTS / "state-aware-failure-taxonomy.jsonl", taxonomy)
    write_json(RESULTS / "state-dependent-collisions.json", state_dependent)
    write_json(RESULTS / "report.json", report)
    write_json(RESULTS / "reproduction-status.json", {"status": report["status"], "acceptance_gates": gates, "protocol_sha256": sha256(PROTOCOL)})
    with (RESULTS / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["representation", "stratum", "n", "unsafe_pre_allow", "false_denial", "abstain", "coverage", "decision_accuracy", "covered_accuracy", "ideal_allow", "ideal_deny"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(direct)
    with (RESULTS / "collision-metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["representation", "n_cells", "n_mixed_cells", "rows_in_mixed_cells", "minimum_unavoidable_errors", "authorization_separating_pairs", "overpartition_pairs", "serialized_bytes", "scalar_leaves"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(collision_metrics)
    lines = ["# State-Aware Authorization Interface", "", f"Status: **{report['status']}**", "", "## Direct adapter diagnostic", "", "| Interface | Coverage | UPA | Withheld | Exact | Mixed |", "|---|---:|---:|---:|---:|---:|"]
    collision_by_rep = {row["representation"]: row for row in collision_metrics}
    for row in direct:
        if row["stratum"] != "all": continue
        withheld = sum(item["monitor_decision"] != "ALLOW" for item in decisions if item["representation"] == row["representation"] and item["ideal_decision"] == "ALLOW") / row["ideal_allow"]
        lines.append(f"| {row['representation']} | {100*row['coverage']:.1f}% | {100*row['unsafe_pre_allow']:.1f}% | {100*withheld:.1f}% | {100*row['decision_accuracy']:.1f}% | {collision_by_rep[row['representation']]['n_mixed_cells']} |")
    lines += ["", "The state-aware collision key is effect-free. Its direct metrics additionally use the disclosed frozen request adapter.", ""]
    (RESULTS / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--force-freeze", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.freeze or args.force_freeze:
        freeze(force=args.force_freeze)
    if args.run or not (args.freeze or args.force_freeze):
        print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
