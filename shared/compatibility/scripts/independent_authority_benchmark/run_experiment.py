#!/usr/bin/env python3
"""Freeze and run the protocol-separated authority representation benchmark."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import authority_model, context_generator, descriptor_runtime, sandbox, specs, transition_oracle


ROOT = Path(__file__).resolve().parents[4]
EVAL = ROOT / "experiments/human-authority-and-causal-validation/evaluation/protocol-separated-authority-representation"
RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/protocol-separated-authority-representation"
AUTHORITY = EVAL / "authority-state.json"
GENERATOR = EVAL / "generator-config.json"
CANDIDATES = EVAL / "descriptor-candidates.json"
FROZEN = EVAL / "frozen-executable-descriptors.json"
REGISTRATION = EVAL / "registration-contexts.jsonl"
EVALUATION = EVAL / "descriptor-blind-evaluation-contexts.jsonl"
PROTOCOL = EVAL / "protocol-lock.json"

REPRESENTATIONS = ("tool_name", "canonical_raw_arguments", "common_effect_fields", "validated_typed_effects")


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _typed_transition(atom: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": atom["operation"], "resource_type": atom["resource_type"], "resource_id": atom["resource_id"],
        "target_principal": atom.get("target_principal"), "attributes": atom.get("qualifiers", {}),
        "commit_mode": atom.get("commit_mode", "commit"),
    }


def evaluate_context(row: dict[str, Any], descriptors: dict[str, dict[str, Any]], authority: dict[str, Any]) -> dict[str, Any]:
    before_hash = hashlib.sha256(canonical(row["pre_state"]).encode()).hexdigest()
    after = sandbox.execute(row)
    if hashlib.sha256(canonical(row["pre_state"]).encode()).hexdigest() != before_hash:
        raise AssertionError(f"pre-state mutated: {row['case_id']}")
    transitions = transition_oracle.derive(row["pre_state"], after, row["tool_name"])
    concrete_requests = [authority_model.transition_request(item, row["authority_context"]) for item in transitions]
    ideal, ideal_reasons = authority_model.authorize_all(concrete_requests, authority, row["authority_context"], partial=False)
    compile_error = None
    try:
        atoms = descriptor_runtime.compile_descriptor(descriptors[row["tool_name"]], row)
    except Exception as exc:  # fail closed and retain the row
        atoms, compile_error = [], f"{type(exc).__name__}:{exc}"
    typed_transitions = [_typed_transition(item) for item in atoms]
    return {
        **row,
        "pre_state_sha256": before_hash,
        "post_state_sha256": hashlib.sha256(canonical(after).encode()).hexdigest(),
        "source_transitions": transitions,
        "typed_effects": atoms,
        "descriptor_compile_error": compile_error,
        "descriptor_exact_transition_match": compile_error is None and transitions == typed_transitions,
        "ideal_decision": ideal,
        "ideal_reasons": ideal_reasons,
    }


def validate_registration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exact = sum(row["descriptor_exact_transition_match"] for row in rows)
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pair[row["counterfactual_pair_id"]].append(row)
    pairs = []
    for pair_id, members in sorted(by_pair.items()):
        if len(members) != 2:
            raise AssertionError(pair_id)
        source_changed = members[0]["source_transitions"] != members[1]["source_transitions"]
        typed_changed = members[0]["typed_effects"] != members[1]["typed_effects"]
        axis = members[0]["mutation_axis"]
        expected_changed = axis != "surface"
        pairs.append({
            "pair_id": pair_id, "domain": members[0]["domain"], "axis": axis,
            "source_changed": source_changed, "typed_changed": typed_changed,
            "expected_changed": expected_changed,
            "passed": all(row["descriptor_exact_transition_match"] for row in members)
                      and source_changed == expected_changed and typed_changed == expected_changed,
        })
    return {
        "n_contexts": len(rows), "n_pairs": len(pairs), "exact_matches": exact,
        "exact_match_rate": exact / len(rows), "relation_passes": sum(item["passed"] for item in pairs),
        "relation_accuracy": sum(item["passed"] for item in pairs) / len(pairs),
        "effective_sensitive_pairs": sum(item["source_changed"] and item["axis"] != "surface" for item in pairs),
        "surface_invariant_pairs": sum(not item["source_changed"] and item["axis"] == "surface" for item in pairs),
        "axes": dict(Counter(item["axis"] for item in pairs)), "pair_rows": pairs,
    }


def freeze_protocol(force: bool) -> dict[str, Any]:
    if PROTOCOL.exists() and not force:
        raise FileExistsError(f"protocol already frozen: {PROTOCOL}")
    EVAL.mkdir(parents=True, exist_ok=True)
    authority = authority_model.authority_state()
    config = context_generator.generator_config()
    candidates = specs.descriptor_candidates()
    write_json(AUTHORITY, authority)
    write_json(GENERATOR, config)
    write_json(CANDIDATES, candidates)
    registration = context_generator.generate_registration(config)
    write_jsonl(REGISTRATION, registration)

    descriptor_map = {item["tool_name"]: item for item in candidates["descriptors"]}
    evaluated_registration = [evaluate_context(row, descriptor_map, authority) for row in registration]
    registration_report = validate_registration(evaluated_registration)
    if registration_report["exact_match_rate"] != 1.0 or registration_report["relation_accuracy"] != 1.0:
        raise RuntimeError("descriptor registration gates failed")

    frozen_at = datetime.now(timezone.utc).isoformat()
    frozen = copy.deepcopy(candidates)
    frozen["freeze_metadata"] = {
        "frozen_at": frozen_at, "registration_status": "passed",
        "registration_contexts_sha256": sha256(REGISTRATION),
        "registration_exact_match_rate": registration_report["exact_match_rate"],
        "registration_relation_accuracy": registration_report["relation_accuracy"],
    }
    write_json(FROZEN, frozen)

    # Evaluation contexts are materialized only after executable descriptors freeze.
    evaluation = context_generator.generate_evaluation(config)
    write_jsonl(EVALUATION, evaluation)
    generated_at = datetime.now(timezone.utc).isoformat()
    protocol = {
        "experiment": "protocol_separated_authority_representation",
        "status": "frozen_before_evaluation_execution",
        "sequence": [
            {"event": "authority_and_generator_frozen", "at": frozen_at},
            {"event": "descriptor_frozen_after_registration", "at": frozen_at},
            {"event": "descriptor_blind_evaluation_materialized", "at": generated_at},
        ],
        "design": {
            "domains": config["domains"], "n_registration_contexts": len(registration),
            "n_evaluation_contexts": len(evaluation), "representations": list(REPRESENTATIONS),
            "evaluation_label_balancing": False, "post_result_case_deletion": False,
            "pair_selection": "none before execution; mixed cells discovered after authority labels",
            "runtime_descriptor_source": FROZEN.relative_to(ROOT).as_posix(),
        },
        "registration_report": {key: value for key, value in registration_report.items() if key != "pair_rows"},
        "hashes": {
            "authority_state": sha256(AUTHORITY), "generator_config": sha256(GENERATOR),
            "descriptor_candidates": sha256(CANDIDATES), "frozen_descriptors": sha256(FROZEN),
            "registration_contexts": sha256(REGISTRATION), "evaluation_contexts": sha256(EVALUATION),
            "sandbox_module": sha256(Path(sandbox.__file__)), "oracle_module": sha256(Path(transition_oracle.__file__)),
            "authority_module": sha256(Path(authority_model.__file__)), "descriptor_runtime_module": sha256(Path(descriptor_runtime.__file__)),
            "generator_module": sha256(Path(context_generator.__file__)), "specs_module": sha256(Path(specs.__file__)),
            "runner_module": sha256(Path(__file__)),
        },
        "claim_boundary": "Protocol-separated controlled benchmark; not independently authored and not a production prevalence estimate.",
    }
    write_json(PROTOCOL, protocol)
    return protocol


def verify_protocol() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    observed = {
        "authority_state": sha256(AUTHORITY), "generator_config": sha256(GENERATOR),
        "descriptor_candidates": sha256(CANDIDATES), "frozen_descriptors": sha256(FROZEN),
        "registration_contexts": sha256(REGISTRATION), "evaluation_contexts": sha256(EVALUATION),
        "sandbox_module": sha256(Path(sandbox.__file__)), "oracle_module": sha256(Path(transition_oracle.__file__)),
        "authority_module": sha256(Path(authority_model.__file__)), "descriptor_runtime_module": sha256(Path(descriptor_runtime.__file__)),
        "generator_module": sha256(Path(context_generator.__file__)), "specs_module": sha256(Path(specs.__file__)),
        "runner_module": sha256(Path(__file__)),
    }
    if observed != protocol["hashes"]:
        raise RuntimeError({key: {"expected": protocol["hashes"].get(key), "observed": value}
                            for key, value in observed.items() if protocol["hashes"].get(key) != value})
    return protocol


def _raw_atoms(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Best-effort tool-call-level adapter over explicit arguments only."""
    args, tool = row["arguments"], row["tool_name"]
    mode = args.get("commit_mode", "commit")
    atoms: list[dict[str, Any]] = []
    def add(operation: str, kind: str, resource: str, target: str | None = None, attrs: dict[str, Any] | None = None) -> None:
        atoms.append({"effect": operation, "operation": operation, "resource_type": kind, "resource_id": resource,
                      "target_principal": target, "qualifiers": attrs or {}, "commit_mode": mode})
    if tool == "schedule_meeting":
        operation = "calendar.draft.save" if mode == "draft" else "calendar.event.schedule" if mode == "scheduled" else "calendar.event.upsert"
        attrs = {key: args[key] for key in ("visibility", "recurrence") if key in args}
        add(operation, "calendar", args["calendar_ref"], attrs=attrs)
        if mode == "commit":
            for person in args.get("participants", []): add("calendar.participant.invite", "calendar", args["calendar_ref"], person)
    elif tool == "share_document":
        operation = "document.share.draft" if mode == "draft" else "document.share.revoke" if args.get("operation") == "revoke" else "document.share.grant"
        refs = args.get("doc_refs", [args["doc_ref"]])
        for ref in refs:
            if mode == "draft": add(operation, "document", ref)
            else:
                for person in args.get("recipients", []): add(operation, "document", ref, person, {"permission": args["permission"]})
                if "visibility" in args: add("document.visibility.set", "document", ref, attrs={"visibility": args["visibility"]})
    elif tool == "post_message":
        operation = "message.draft.save" if mode == "draft" else "message.schedule" if mode == "scheduled" else "message.post"
        for ref in args.get("channel_refs", [args["channel_ref"]]):
            add(operation, "channel", ref, attrs={"payload_class": args["payload_class"]} if mode == "commit" else {})
            if mode == "commit":
                for person in args.get("recipients", []): add("message.notify", "channel", ref, person)
    elif tool == "transfer_funds":
        operation = "bank.transfer.draft" if mode == "draft" else "bank.transfer.schedule" if mode == "scheduled" else "bank.transfer.commit"
        add(operation, "bank_account", args["account_ref"], args["payee_ref"], {"amount": args["amount"], "currency": args["currency"]})
    return atoms


def observation(row: dict[str, Any], representation: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if representation == "tool_name":
        atom = {"effect": "tool.invoke", "operation": "tool.invoke", "resource_type": None, "resource_id": None,
                "target_principal": None, "qualifiers": {}, "commit_mode": None}
        return [atom], {"tool_name": row["tool_name"]}
    if representation == "canonical_raw_arguments":
        return _raw_atoms(row), {"tool_name": row["tool_name"], "arguments": row["arguments"]}
    if representation == "common_effect_fields":
        atoms = [{**atom, "qualifiers": {}} for atom in row["typed_effects"]]
        return atoms, atoms
    if representation == "validated_typed_effects":
        return row["typed_effects"], row["typed_effects"]
    raise ValueError(representation)


def monitor_decisions(rows: list[dict[str, Any]], authority: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        for representation in REPRESENTATIONS:
            atoms, key_value = observation(row, representation)
            requests = [authority_model.atom_request(atom, row["authority_context"]) for atom in atoms]
            decision, reasons = authority_model.authorize_all(
                requests, authority, row["authority_context"], partial=True,
                inventory_complete=representation in {"common_effect_fields", "validated_typed_effects"} or bool(atoms),
            )
            output.append({
                "case_id": row["case_id"], "domain": row["domain"], "stratum": row["stratum"],
                "argument_group_id": row["argument_group_id"], "representation": representation,
                "representation_key": canonical(key_value), "monitor_decision": decision, "monitor_reasons": reasons,
                "ideal_decision": row["ideal_decision"], "descriptor_exact_transition_match": row["descriptor_exact_transition_match"],
            })
    return output


def metric(rows: list[dict[str, Any]], representation: str, stratum: str = "all") -> dict[str, Any]:
    subset = [row for row in rows if row["representation"] == representation and (stratum == "all" or row["stratum"] == stratum)]
    denied, allowed = [row for row in subset if row["ideal_decision"] == "DENY"], [row for row in subset if row["ideal_decision"] == "ALLOW"]
    covered = [row for row in subset if row["monitor_decision"] != "ABSTAIN"]
    ratio = lambda n, d: n / d if d else None
    return {
        "representation": representation, "stratum": stratum, "n": len(subset),
        "unsafe_pre_allow": ratio(sum(row["monitor_decision"] == "ALLOW" for row in denied), len(denied)),
        "false_denial": ratio(sum(row["monitor_decision"] == "DENY" for row in allowed), len(allowed)),
        "abstain": ratio(sum(row["monitor_decision"] == "ABSTAIN" for row in subset), len(subset)),
        "coverage": ratio(len(covered), len(subset)),
        "decision_accuracy": ratio(sum(row["monitor_decision"] == row["ideal_decision"] for row in subset), len(subset)),
        "covered_accuracy": ratio(sum(row["monitor_decision"] == row["ideal_decision"] for row in covered), len(covered)),
        "ideal_allow": len(allowed), "ideal_deny": len(denied),
    }


def collision_audit(decisions: list[dict[str, Any]], representation: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        if row["representation"] == representation:
            cells[row["representation_key"]].append(row)
    mixed = []
    for key, members in cells.items():
        labels = Counter(row["ideal_decision"] for row in members)
        if len(labels) > 1:
            mixed.append({
                "representation": representation, "cell_sha256": hashlib.sha256(key.encode()).hexdigest(),
                "n": len(members), "allow": labels["ALLOW"], "deny": labels["DENY"],
                "minimum_unavoidable_errors": min(labels["ALLOW"], labels["DENY"]),
                "case_ids": [row["case_id"] for row in members],
            })
    return {
        "representation": representation, "n_cells": len(cells), "n_mixed_cells": len(mixed),
        "rows_in_mixed_cells": sum(item["n"] for item in mixed),
        "minimum_unavoidable_errors": sum(item["minimum_unavoidable_errors"] for item in mixed),
    }, mixed


def state_collision_audit(evaluated: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> dict[str, Any]:
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
        result["representations"][representation] = {"colliding_groups": collisions, "total": len(separating), "rate": collisions / len(separating) if separating else None}
    return result


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Protocol-Separated Authority Representation Benchmark", "", f"Status: **{report['status']}**", "",
        "## Protocol", "",
        f"The experiment uses {report['evaluation']['n_contexts']} descriptor-blind contexts across four copied-sandbox domains. "
        "Policies are explicit ACL, capability, and delegation authority state. Evaluation contexts are generated without labels and mixed cells are discovered only after execution.",
        "", "## Registration", "",
        f"Executable JSON descriptors matched the independent transition oracle on {report['registration']['exact_matches']}/{report['registration']['n_contexts']} registration contexts and passed {report['registration']['relation_passes']}/{report['registration']['n_pairs']} counterfactual relation checks.",
        "", "## Direct authorization", "",
        "| Representation | Coverage | UPA | False denial | Accuracy |", "|---|---:|---:|---:|---:|",
    ]
    for row in report["direct_metrics"]:
        if row["stratum"] != "all": continue
        pct = lambda value: "n/a" if value is None else f"{100*value:.1f}%"
        lines.append(f"| {row['representation']} | {pct(row['coverage'])} | {pct(row['unsafe_pre_allow'])} | {pct(row['false_denial'])} | {pct(row['decision_accuracy'])} |")
    lines += ["", "## Representation collisions", "", "| Representation | Mixed cells | Minimum unavoidable errors |", "|---|---:|---:|"]
    for row in report["collision_metrics"]:
        lines.append(f"| {row['representation']} | {row['n_mixed_cells']} | {row['minimum_unavoidable_errors']} |")
    lines += ["", "## Claim boundary", "", report["claim_boundary"], ""]
    return "\n".join(lines)


def render_latex(report: dict[str, Any]) -> str:
    collisions = {row["representation"]: row for row in report["collision_metrics"]}
    labels = {
        "tool_name": "Tool name", "canonical_raw_arguments": "Raw arguments",
        "common_effect_fields": "Common fields", "validated_typed_effects": "Validated typed effects",
    }
    rows = []
    for metric_row in report["direct_metrics"]:
        if metric_row["stratum"] != "all":
            continue
        collision = collisions[metric_row["representation"]]
        pct = lambda value: "--" if value is None else f"{100 * value:.1f}"
        rows.append(
            f"{labels[metric_row['representation']]} & {pct(metric_row['unsafe_pre_allow'])} & "
            f"{pct(metric_row['false_denial'])} & {pct(metric_row['coverage'])} & "
            f"{pct(metric_row['decision_accuracy'])} & {collision['n_mixed_cells']} \\\\"
        )
    return "\n".join([
        "\\begin{table}[t]", "\\centering", "\\small",
        "\\caption{Authorization correctness under a shared authority engine (percent except mixed cells).}",
        "\\label{tab:protocol-separated-authorization}",
        "\\begin{tabular}{lrrrrr}", "\\toprule",
        "Representation & UPA & FDeny & Coverage & Accuracy & Mixed \\\\", "\\midrule",
        *rows, "\\bottomrule", "\\end{tabular}", "\\end{table}", "",
    ])


def run() -> dict[str, Any]:
    protocol = verify_protocol()
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    descriptors = descriptor_runtime.load_descriptors(str(FROZEN))
    registration_rows = [evaluate_context(row, descriptors, authority) for row in read_jsonl(REGISTRATION)]
    registration = validate_registration(registration_rows)
    evaluation_rows = [evaluate_context(row, descriptors, authority) for row in read_jsonl(EVALUATION)]
    decisions = monitor_decisions(evaluation_rows, authority)
    direct_metrics = [metric(decisions, representation, stratum) for representation in REPRESENTATIONS for stratum in ("all", "routine", "boundary")]
    collision_metrics, collision_rows = [], []
    for representation in REPRESENTATIONS:
        summary, rows = collision_audit(decisions, representation)
        collision_metrics.append(summary); collision_rows.extend(rows)
    exact = sum(row["descriptor_exact_transition_match"] for row in evaluation_rows)
    typed_metric = next(row for row in direct_metrics if row["representation"] == "validated_typed_effects" and row["stratum"] == "all")
    typed_collision = next(row for row in collision_metrics if row["representation"] == "validated_typed_effects")
    coarse_collisions = [row for row in collision_metrics if row["representation"] != "validated_typed_effects"]
    gates = {
        "all_rows_retained": len(evaluation_rows) == protocol["design"]["n_evaluation_contexts"],
        "registration_exact": registration["exact_match_rate"] == 1.0,
        "registration_relations": registration["relation_accuracy"] == 1.0,
        "evaluation_descriptor_exact": exact == len(evaluation_rows),
        "zero_compile_failures": all(row["descriptor_compile_error"] is None for row in evaluation_rows),
        "typed_zero_unsafe_pre_allow": typed_metric["unsafe_pre_allow"] == 0.0,
        "typed_zero_false_denial": typed_metric["false_denial"] == 0.0,
        "typed_full_coverage": typed_metric["coverage"] == 1.0,
        "typed_zero_mixed_cells": typed_collision["n_mixed_cells"] == 0,
        "each_coarse_view_has_mixed_cells": all(row["n_mixed_cells"] > 0 for row in coarse_collisions),
    }
    report = {
        "experiment": "protocol_separated_authority_representation", "status": "passed" if all(gates.values()) else "failed",
        "registration": {key: value for key, value in registration.items() if key != "pair_rows"},
        "evaluation": {
            "n_contexts": len(evaluation_rows), "n_domains": len({row["domain"] for row in evaluation_rows}),
            "n_tools": len({row["tool_name"] for row in evaluation_rows}), "ideal_labels": dict(Counter(row["ideal_decision"] for row in evaluation_rows)),
            "descriptor_exact_matches": exact, "descriptor_exact_match_rate": exact / len(evaluation_rows),
            "compile_failures": sum(row["descriptor_compile_error"] is not None for row in evaluation_rows),
        },
        "direct_metrics": direct_metrics, "collision_metrics": collision_metrics,
        "state_dependent": state_collision_audit(evaluation_rows, decisions),
        "acceptance_gates": gates,
        "protocol_hash": sha256(PROTOCOL),
        "claim_boundary": (
            "This controlled, protocol-separated benchmark establishes representation sufficiency only for the frozen tool, intervention, and authority families. "
            "It is not independently authored, does not estimate production prevalence, and does not establish open-world descriptor soundness or production safety."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_jsonl(RESULTS / "source-executions-and-typed-effects.jsonl", evaluation_rows)
    write_jsonl(RESULTS / "authorization-decisions.jsonl", decisions)
    write_jsonl(RESULTS / "representation-collision-witnesses.jsonl", collision_rows)
    write_jsonl(RESULTS / "registration-pair-audit.jsonl", registration["pair_rows"])
    write_json(RESULTS / "report.json", report)
    (RESULTS / "report.md").write_text(render_markdown(report), encoding="utf-8")
    (RESULTS / "table_protocol_separated_authority.tex").write_text(render_latex(report), encoding="utf-8")
    with (RESULTS / "direct-metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(direct_metrics[0])); writer.writeheader(); writer.writerows(direct_metrics)
    with (RESULTS / "collision-metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(collision_metrics[0])); writer.writeheader(); writer.writerows(collision_metrics)
    write_json(RESULTS / "reproduction-status.json", {
        "status": report["status"], "n_evaluation_rows": len(evaluation_rows), "n_decision_rows": len(decisions),
        "all_rows_retained": len(evaluation_rows) == protocol["design"]["n_evaluation_contexts"],
        "protocol_hash_verified": True, "acceptance_gates": gates,
    })
    (RESULTS / "claim-boundary.md").write_text("# Claim Boundary\n\n" + report["claim_boundary"] + "\n", encoding="utf-8")
    (RESULTS / "claim-to-source.md").write_text("\n".join([
        "# Claim-to-Source Map", "",
        "| Claim | Result key | Source rows |", "|---|---|---|",
        "| Registration validates executable descriptors | `registration.*` | `registration-pair-audit.jsonl` |",
        "| Typed effects match concrete transitions | `evaluation.descriptor_exact_match_rate` | `source-executions-and-typed-effects.jsonl` |",
        "| Direct authorization metrics | `direct_metrics[]` | `authorization-decisions.jsonl` |",
        "| Coarse views contain mixed cells | `collision_metrics[]` | `representation-collision-witnesses.jsonl` |",
        "| Raw arguments collide under changed pre-state | `state_dependent.*` | evaluation rows grouped by `argument_group_id` |", "",
    ]), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--force-freeze", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.freeze or args.force_freeze:
        freeze_protocol(args.force_freeze)
    if args.run or not (args.freeze or args.force_freeze):
        report = run()
        print(json.dumps({"status": report["status"], "evaluation": report["evaluation"], "direct_metrics": [r for r in report["direct_metrics"] if r["stratum"] == "all"], "collision_metrics": report["collision_metrics"], "state_dependent": report["state_dependent"]}, indent=2))


if __name__ == "__main__":
    main()
