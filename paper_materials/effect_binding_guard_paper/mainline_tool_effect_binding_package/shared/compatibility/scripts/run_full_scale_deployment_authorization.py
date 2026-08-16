#!/usr/bin/env python3
"""Run the full-scale typed-effect authorization conformance experiment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import full_scale_deployment_authorization_core as core


def find_root(path: Path) -> Path:
    for candidate in (path.resolve(), *path.resolve().parents):
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
EVAL = ROOT / "experiments/human-authority-and-causal-validation/evaluation/full-scale-deployment-authorization"
RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/full-scale-deployment-authorization"
POLICIES = EVAL / "policy-manifests.json"
DESCRIPTORS = EVAL / "frozen-descriptor-manifest.json"
REGISTRATION = EVAL / "registration-counterfactuals.jsonl"
CONTEXTS = EVAL / "heldout-authorization-contexts.jsonl"
PROTOCOL = EVAL / "protocol.json"
CORE_PATH = Path(core.__file__).resolve()


def ratio(successes: int, total: int) -> dict[str, Any]:
    return {"successes": successes, "total": total, "rate": successes / total if total else 0.0}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def freeze_inputs(force: bool = False) -> dict[str, Any]:
    EVAL.mkdir(parents=True, exist_ok=True)
    if PROTOCOL.exists() and not force:
        raise FileExistsError(f"frozen protocol already exists: {PROTOCOL}; pass --force-freeze to replace")

    policies = core.policy_manifests()
    descriptors = core.descriptor_manifest()
    registration = core.build_contexts("registration")
    contexts = core.build_contexts("evaluation")
    POLICIES.write_text(json.dumps(policies, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DESCRIPTORS.write_text(json.dumps(descriptors, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_jsonl(REGISTRATION, registration)
    write_jsonl(CONTEXTS, contexts)

    protocol = {
        "experiment": "full_scale_deployment_authorization_representation",
        "status": "frozen_before_full_run",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "design": {
            "n_domains": len(core.DOMAINS),
            "n_tools": len(core.TOOL_NAMES),
            "n_registration_contexts": len(registration),
            "n_registration_pairs": len(registration) // 2,
            "n_heldout_contexts": len(contexts),
            "n_heldout_policy_separating_pairs": len(contexts) // 2,
            "representations": list(core.REPRESENTATIONS),
            "same_policy_engine": "authorize_observation for all direct decisions; one cell consumer for all representation-capacity diagnostics",
            "source_execution": "domain-specific copied in-memory sandbox; no external side effects",
            "registration_evaluation_split": "disjoint case IDs and concrete held-out values; registration has eight sensitive axes plus one surface-invariant pair per tool",
            "post_result_case_deletion": False,
        },
        "input_hashes": {
            "policy_manifests_sha256": sha256(POLICIES),
            "descriptor_manifest_sha256": sha256(DESCRIPTORS),
            "registration_counterfactuals_sha256": sha256(REGISTRATION),
            "heldout_contexts_sha256": sha256(CONTEXTS),
            "core_sha256": sha256(CORE_PATH),
            "runner_sha256": sha256(Path(__file__).resolve()),
        },
        "acceptance_gates": {
            "registration_descriptor_exact_set_match": 1.0,
            "registration_relation_accuracy": 1.0,
            "heldout_descriptor_exact_set_match": 1.0,
            "heldout_typed_direct_accuracy": 1.0,
            "heldout_typed_unsafe_pre_allow": 0.0,
            "heldout_typed_false_denial": 0.0,
            "heldout_typed_coverage": 1.0,
            "typed_policy_mixed_cells": 0,
            "each_coarse_view_has_policy_mixed_cells": True,
            "raw_arguments_have_state_dependent_collisions": True,
            "all_cases_retained": True,
        },
        "claim_boundary": (
            "Controlled eight-tool copied-sandbox authorization experiment over frozen ACL, "
            "capability, and delegation policies. It measures representation sufficiency on "
            "the enumerated intervention and policy families; it does not establish open-world "
            "descriptor soundness, policy correctness, deployment prevalence, or production safety."
        ),
    }
    PROTOCOL.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return protocol


def verify_frozen_inputs() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    expected = protocol["input_hashes"]
    observed = {
        "policy_manifests_sha256": sha256(POLICIES),
        "descriptor_manifest_sha256": sha256(DESCRIPTORS),
        "registration_counterfactuals_sha256": sha256(REGISTRATION),
        "heldout_contexts_sha256": sha256(CONTEXTS),
        "core_sha256": sha256(CORE_PATH),
        "runner_sha256": sha256(Path(__file__).resolve()),
    }
    if observed != expected:
        differences = {key: {"expected": expected.get(key), "observed": value} for key, value in observed.items() if expected.get(key) != value}
        raise RuntimeError(f"frozen input mismatch: {json.dumps(differences, sort_keys=True)}")
    return protocol


def evaluate_rows(rows: list[dict[str, Any]], policies: dict[str, Any]) -> list[dict[str, Any]]:
    evaluated: list[dict[str, Any]] = []
    for row in rows:
        before_hash = hashlib.sha256(core.canonical(row["pre_state"]).encode()).hexdigest()
        after = core.execute_tool(row)
        if hashlib.sha256(core.canonical(row["pre_state"]).encode()).hexdigest() != before_hash:
            raise AssertionError(f"source execution mutated frozen pre-state: {row['case_id']}")
        source = core.source_effects(row, after)
        typed = core.instantiate_descriptor(row)
        ideal = core.ideal_decision(source, policies[row["policy_id"]])
        evaluated.append({
            **row,
            "pre_state_sha256": before_hash,
            "post_state_sha256": hashlib.sha256(core.canonical(after).encode()).hexdigest(),
            "source_effects": source,
            "typed_effects": typed,
            "descriptor_exact_set_match": source == typed,
            "ideal_decision": ideal,
        })
    return evaluated


def validate_registration(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pair[row["pair_id"]].append(row)
    pair_rows: list[dict[str, Any]] = []
    for pair_id, pair in sorted(by_pair.items()):
        if len(pair) != 2:
            raise AssertionError(f"registration pair size: {pair_id}")
        left, right = pair
        expected = left["expected_relation"]
        source_changed = left["source_effects"] != right["source_effects"]
        typed_changed = left["typed_effects"] != right["typed_effects"]
        ideal_changed = left["ideal_decision"] != right["ideal_decision"]
        passed = (
            all(item["descriptor_exact_set_match"] for item in pair)
            and source_changed == typed_changed
            and ((source_changed and ideal_changed) if expected == "sensitive" else (not source_changed and not ideal_changed))
        )
        pair_rows.append({
            "pair_id": pair_id,
            "domain": left["domain"],
            "tool_name": left["tool_name"],
            "axis": left["axis"],
            "expected_relation": expected,
            "source_changed": source_changed,
            "typed_changed": typed_changed,
            "ideal_decision_changed": ideal_changed,
            "passed": passed,
            "case_ids": [item["case_id"] for item in pair],
        })
    exact = sum(row["descriptor_exact_set_match"] for row in rows)
    relation = sum(row["passed"] for row in pair_rows)
    report = {
        "n_contexts": len(rows),
        "n_pairs": len(pair_rows),
        "n_tools": len({row["tool_name"] for row in rows}),
        "n_domains": len({row["domain"] for row in rows}),
        "descriptor_exact_set_match": ratio(exact, len(rows)),
        "counterfactual_relation_accuracy": ratio(relation, len(pair_rows)),
        "sensitive_pairs": sum(row["expected_relation"] == "sensitive" for row in pair_rows),
        "surface_invariant_pairs": sum(row["expected_relation"] == "invariant" for row in pair_rows),
        "axes": dict(Counter(row["axis"] for row in pair_rows)),
        "registered_tools": sorted({row["tool_name"] for row in rows if all(item["passed"] for item in pair_rows if item["tool_name"] == row["tool_name"])}),
    }
    return report, pair_rows


def direct_decisions(rows: list[dict[str, Any]], policies: dict[str, Any]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for row in rows:
        for name in core.REPRESENTATIONS:
            view = core.observation(row, name)
            decision, reasons = core.authorize_observation(view, policies[row["policy_id"]])
            decisions.append({
                "case_id": row["case_id"],
                "pair_id": row["pair_id"],
                "domain": row["domain"],
                "axis": row["axis"],
                "state_dependent": row["state_dependent"],
                "representation": name,
                "representation_sha256": hashlib.sha256(core.canonical(view).encode()).hexdigest(),
                "monitor_decision": decision,
                "reasons": reasons,
                "ideal_decision": row["ideal_decision"],
            })
    return decisions


def decision_metrics(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    subset = [row for row in rows if row["representation"] == name]
    denied = [row for row in subset if row["ideal_decision"] == "DENY"]
    allowed = [row for row in subset if row["ideal_decision"] == "ALLOW"]
    covered = [row for row in subset if row["monitor_decision"] != "ABSTAIN"]
    return {
        "representation": name,
        "n": len(subset),
        "unsafe_pre_allow": ratio(sum(row["monitor_decision"] == "ALLOW" for row in denied), len(denied)),
        "false_denial": ratio(sum(row["monitor_decision"] == "DENY" for row in allowed), len(allowed)),
        "abstain": ratio(sum(row["monitor_decision"] == "ABSTAIN" for row in subset), len(subset)),
        "coverage": ratio(len(covered), len(subset)),
        "decision_accuracy": ratio(sum(row["monitor_decision"] == row["ideal_decision"] for row in subset), len(subset)),
        "covered_accuracy": ratio(sum(row["monitor_decision"] == row["ideal_decision"] for row in covered), len(covered)),
    }


def collision_audit(rows: list[dict[str, Any]], name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        cells[core.representation_key(row, name)].append(row)
    mixed: list[dict[str, Any]] = []
    for key, members in sorted(cells.items()):
        counts = Counter(row["ideal_decision"] for row in members)
        if len(counts) > 1:
            mixed.append({
                "representation": name,
                "cell_sha256": hashlib.sha256(key.encode()).hexdigest(),
                "n": len(members),
                "allow": counts["ALLOW"],
                "deny": counts["DENY"],
                "minimum_unavoidable_errors": min(counts["ALLOW"], counts["DENY"]),
                "case_ids": [row["case_id"] for row in members],
                "domains": sorted({row["domain"] for row in members}),
                "axes": sorted({row["axis"] for row in members}),
            })
    summary = {
        "representation": name,
        "n_cells": len(cells),
        "n_mixed_cells": len(mixed),
        "n_rows_in_mixed_cells": sum(row["n"] for row in mixed),
        "minimum_unavoidable_row_errors": sum(row["minimum_unavoidable_errors"] for row in mixed),
    }
    return summary, mixed


def cell_decisions(rows: list[dict[str, Any]], name: str, mixed_resolution: str) -> list[dict[str, Any]]:
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        cells[core.representation_key(row, name)].append(row)
    output: list[dict[str, Any]] = []
    for members in cells.values():
        decisions = {row["ideal_decision"] for row in members}
        decision = next(iter(decisions)) if len(decisions) == 1 else mixed_resolution
        for row in members:
            output.append({"case_id": row["case_id"], "representation": name, "monitor_decision": decision, "ideal_decision": row["ideal_decision"]})
    return output


def simple_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    denied = [row for row in rows if row["ideal_decision"] == "DENY"]
    allowed = [row for row in rows if row["ideal_decision"] == "ALLOW"]
    covered = [row for row in rows if row["monitor_decision"] != "ABSTAIN"]
    return {
        "unsafe_pre_allow": ratio(sum(row["monitor_decision"] == "ALLOW" for row in denied), len(denied)),
        "false_denial": ratio(sum(row["monitor_decision"] == "DENY" for row in allowed), len(allowed)),
        "abstain": ratio(sum(row["monitor_decision"] == "ABSTAIN" for row in rows), len(rows)),
        "coverage": ratio(len(covered), len(rows)),
        "decision_accuracy": ratio(sum(row["monitor_decision"] == row["ideal_decision"] for row in rows), len(rows)),
    }


def pair_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pair[row["pair_id"]].append(row)
    output = []
    for pair_id, pair in sorted(by_pair.items()):
        if len(pair) != 2:
            raise AssertionError(pair_id)
        record = {
            "pair_id": pair_id,
            "domain": pair[0]["domain"],
            "axis": pair[0]["axis"],
            "state_dependent": pair[0]["state_dependent"],
            "case_ids": [row["case_id"] for row in pair],
            "ideal_decisions": [row["ideal_decision"] for row in pair],
            "representations": {},
        }
        for name in core.REPRESENTATIONS:
            left, right = (core.representation_key(row, name) for row in pair)
            record["representations"][name] = {"collision": left == right}
        output.append(record)
    return output


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "# Full-Scale Deployment-Style Authorization Experiment",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Scope",
        "",
        f"The frozen evaluation contains {report['evaluation']['n_contexts']} contexts, "
        f"{report['evaluation']['n_pairs']} policy-separating pairs, "
        f"{report['evaluation']['n_tools']} tools, and {report['evaluation']['n_domains']} domains. "
        "Every tool call executes only in a copied in-memory sandbox.",
        "",
        "The candidate descriptors were validated before evaluation on "
        f"{report['registration']['n_contexts']} registration contexts and "
        f"{report['registration']['n_pairs']} counterfactual pairs. Registration and held-out "
        "evaluation use disjoint case IDs and concrete values.",
        "",
        "## Registration",
        "",
        f"- Descriptor/source exact-set match: {report['registration']['descriptor_exact_set_match']['successes']}/{report['registration']['descriptor_exact_set_match']['total']}.",
        f"- Counterfactual relation accuracy: {report['registration']['counterfactual_relation_accuracy']['successes']}/{report['registration']['counterfactual_relation_accuracy']['total']}.",
        f"- Sensitive pairs: {report['registration']['sensitive_pairs']}; surface-invariant pairs: {report['registration']['surface_invariant_pairs']}.",
        "",
        "## Direct Policy Decisions",
        "",
        "All representations are passed to the same tri-state policy engine. Opaque or incomplete effect inventories produce ABSTAIN; known unauthorized facts produce DENY.",
        "",
        "| Representation | UPA | False denial | Abstain | Coverage | Accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["direct_policy_metrics"]:
        lines.append(f"| {row['representation']} | {100*row['unsafe_pre_allow']['rate']:.1f}% | {100*row['false_denial']['rate']:.1f}% | {100*row['abstain']['rate']:.1f}% | {100*row['coverage']['rate']:.1f}% | {100*row['decision_accuracy']['rate']:.1f}% |")
    lines.extend([
        "",
        "## Representation-Capacity Diagnostics",
        "",
        "Mixed cells contain calls that look identical under one representation but require different ideal authorization decisions. The lower bound is the minority count in each mixed cell.",
        "",
        "| Representation | Cells | Mixed cells | Rows in mixed cells | Error lower bound | Fail-open UPA | Fail-closed false denial |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for row in report["representation_capacity"]:
        lines.append(f"| {row['representation']} | {row['n_cells']} | {row['n_mixed_cells']} | {row['n_rows_in_mixed_cells']} | {row['minimum_unavoidable_row_errors']} | {100*row['fail_open']['unsafe_pre_allow']['rate']:.1f}% | {100*row['fail_closed']['false_denial']['rate']:.1f}% |")
    state = report["state_dependent_subset"]
    lines.extend([
        "",
        "## State-Dependent Authorization",
        "",
        f"The held-out set contains {state['n_pairs']} same-argument, different-pre-state pairs. "
        f"Raw arguments collide on {state['raw_argument_collisions']}/{state['n_pairs']} pairs; "
        f"typed effects collide on {state['typed_effect_collisions']}/{state['n_pairs']}.",
        "",
        "## Interpretation",
        "",
        "1. Coarse views contain constructive policy-separating collisions under the frozen deployment-style policies. Any deterministic completion of a mixed cell must either allow an unauthorized effect or withhold authorized work.",
        "2. The counterfactually validated typed representation exposes the concrete resource, operation, target, qualifier, commit mode, and state-dependent effects needed by the same policy engine on this bounded domain.",
        "3. These results establish bounded representation sufficiency, not open-world descriptor soundness or production safety.",
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
    ])
    return "\n".join(lines)


def render_table(report: dict[str, Any]) -> str:
    names = {"tool_name": "Tool name", "canonical_raw_arguments": "Raw arguments", "common_effect_fields": "Common fields", "validated_typed_effects": "Validated typed effects"}
    capacity = {row["representation"]: row for row in report["representation_capacity"]}
    direct = {row["representation"]: row for row in report["direct_policy_metrics"]}
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        "\\caption{Authorization sufficiency on 192 held-out copied-sandbox contexts. UPA and false denial use the common direct policy engine; mixed cells and the error lower bound measure representation capacity.}",
        "\\label{tab:full-deployment-authz}",
        "\\begin{tabular}{lrrrrr}",
        "\\toprule",
        "Representation & UPA & FDeny & Coverage & Mixed & Lower bound \\\\",
        "\\midrule",
    ]
    for name in core.REPRESENTATIONS:
        d, c = direct[name], capacity[name]
        lines.append(f"{names[name]} & {100*d['unsafe_pre_allow']['rate']:.1f}\\% & {100*d['false_denial']['rate']:.1f}\\% & {100*d['coverage']['rate']:.1f}\\% & {c['n_mixed_cells']} & {c['minimum_unavoidable_row_errors']} \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    return "\n".join(lines)


def run(mode: str, output_dir: Path | None = None) -> dict[str, Any]:
    protocol = verify_frozen_inputs()
    policies = json.loads(POLICIES.read_text(encoding="utf-8"))
    registration_input = read_jsonl(REGISTRATION)
    evaluation_input = read_jsonl(CONTEXTS)
    if mode == "smoke":
        registration_input = registration_input[:18]
        evaluation_input = evaluation_input[:24]

    registration_rows = evaluate_rows(registration_input, policies)
    registration_report, registration_pairs = validate_registration(registration_rows)
    evaluation_rows = evaluate_rows(evaluation_input, policies)
    direct = direct_decisions(evaluation_rows, policies)
    direct_metrics = [decision_metrics(direct, name) for name in core.REPRESENTATIONS]

    capacity = []
    all_witnesses: list[dict[str, Any]] = []
    for name in core.REPRESENTATIONS:
        summary, witnesses = collision_audit(evaluation_rows, name)
        summary["primary"] = simple_metrics(cell_decisions(evaluation_rows, name, "ABSTAIN"))
        summary["fail_open"] = simple_metrics(cell_decisions(evaluation_rows, name, "ALLOW"))
        summary["fail_closed"] = simple_metrics(cell_decisions(evaluation_rows, name, "DENY"))
        capacity.append(summary)
        all_witnesses.extend(witnesses)

    pairs = pair_audit(evaluation_rows)
    state_pairs = [row for row in pairs if row["state_dependent"]]
    state_summary = {
        "n_pairs": len(state_pairs),
        "raw_argument_collisions": sum(row["representations"]["canonical_raw_arguments"]["collision"] for row in state_pairs),
        "common_field_collisions": sum(row["representations"]["common_effect_fields"]["collision"] for row in state_pairs),
        "typed_effect_collisions": sum(row["representations"]["validated_typed_effects"]["collision"] for row in state_pairs),
    }

    typed_direct = next(row for row in direct_metrics if row["representation"] == "validated_typed_effects")
    typed_capacity = next(row for row in capacity if row["representation"] == "validated_typed_effects")
    coarse = [row for row in capacity if row["representation"] != "validated_typed_effects"]
    expected_n = 24 if mode == "smoke" else 192
    gates = {
        "frozen_inputs_match": True,
        "all_evaluation_contexts_retained": len(evaluation_rows) == expected_n,
        "all_source_calls_execute_in_copied_state": True,
        "registration_descriptor_exact_set_match": registration_report["descriptor_exact_set_match"]["rate"] == 1.0,
        "registration_relation_accuracy": registration_report["counterfactual_relation_accuracy"]["rate"] == 1.0,
        "heldout_descriptor_exact_set_match": all(row["descriptor_exact_set_match"] for row in evaluation_rows),
        "heldout_policy_pairs_are_separating": all(set(row["ideal_decisions"]) == {"ALLOW", "DENY"} for row in pairs),
        "typed_direct_zero_unsafe_pre_allow": typed_direct["unsafe_pre_allow"]["rate"] == 0,
        "typed_direct_zero_false_denial": typed_direct["false_denial"]["rate"] == 0,
        "typed_direct_full_coverage": typed_direct["coverage"]["rate"] == 1.0,
        "typed_direct_full_accuracy": typed_direct["decision_accuracy"]["rate"] == 1.0,
        "typed_has_no_policy_mixed_cells": typed_capacity["n_mixed_cells"] == 0,
        "coarse_views_have_policy_mixed_cells": all(row["n_mixed_cells"] > 0 for row in coarse) if mode == "full" else True,
        "raw_arguments_have_state_dependent_collisions": state_summary["raw_argument_collisions"] > 0 if mode == "full" else True,
        "typed_resolves_state_dependent_pairs": state_summary["typed_effect_collisions"] == 0,
        "no_silent_decision_drops": len(direct) == len(evaluation_rows) * len(core.REPRESENTATIONS),
    }

    per_domain = []
    for domain in core.DOMAINS:
        domain_rows = [row for row in evaluation_rows if row["domain"] == domain]
        if not domain_rows:
            continue
        domain_direct = [row for row in direct if row["domain"] == domain]
        per_domain.append({
            "domain": domain,
            "n": len(domain_rows),
            "ideal_decisions": dict(Counter(row["ideal_decision"] for row in domain_rows)),
            "common_effect_fields": decision_metrics(domain_direct, "common_effect_fields"),
            "validated_typed_effects": decision_metrics(domain_direct, "validated_typed_effects"),
        })

    report = {
        "status": "passed" if all(gates.values()) else "failed",
        "experiment": "full_scale_deployment_authorization_representation",
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registration": registration_report,
        "evaluation": {
            "n_contexts": len(evaluation_rows),
            "n_pairs": len(pairs),
            "n_domains": len({row["domain"] for row in evaluation_rows}),
            "n_tools": len({row["tool_name"] for row in evaluation_rows}),
            "ideal_decisions": dict(Counter(row["ideal_decision"] for row in evaluation_rows)),
            "descriptor_exact_set_match": ratio(sum(row["descriptor_exact_set_match"] for row in evaluation_rows), len(evaluation_rows)),
        },
        "direct_policy_metrics": direct_metrics,
        "representation_capacity": capacity,
        "state_dependent_subset": state_summary,
        "per_domain": per_domain,
        "gates": gates,
        "input_hashes": protocol["input_hashes"],
        "claim_boundary": protocol["claim_boundary"],
    }

    target = output_dir or (RESULTS / "smoke" if mode == "smoke" else RESULTS)
    target.mkdir(parents=True, exist_ok=True)
    write_jsonl(target / "registration-source-executions.jsonl", registration_rows)
    write_jsonl(target / "registration-pair-validation.jsonl", registration_pairs)
    write_jsonl(target / "heldout-source-executions.jsonl", evaluation_rows)
    write_jsonl(target / "authorization-decisions.jsonl", direct)
    write_jsonl(target / "representation-collision-witnesses.jsonl", all_witnesses)
    write_jsonl(target / "policy-separating-pair-audit.jsonl", pairs)
    (target / "full-scale-authorization-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target / "full-scale-authorization-report.md").write_text(render_report(report), encoding="utf-8")
    (target / "table_full_scale_deployment_authorization.tex").write_text(render_table(report), encoding="utf-8")
    (target / "claim-boundary.md").write_text("# Claim Boundary\n\n" + report["claim_boundary"] + "\n", encoding="utf-8")

    with (target / "direct-policy-metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["representation", "unsafe_pre_allow", "false_denial", "abstain", "coverage", "decision_accuracy", "covered_accuracy"])
        for row in direct_metrics:
            writer.writerow([row["representation"], row["unsafe_pre_allow"]["rate"], row["false_denial"]["rate"], row["abstain"]["rate"], row["coverage"]["rate"], row["decision_accuracy"]["rate"], row["covered_accuracy"]["rate"]])
    with (target / "representation-capacity.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["representation", "n_cells", "n_mixed_cells", "n_rows_in_mixed_cells", "minimum_unavoidable_row_errors", "fail_open_upa", "fail_closed_false_denial"])
        for row in capacity:
            writer.writerow([row["representation"], row["n_cells"], row["n_mixed_cells"], row["n_rows_in_mixed_cells"], row["minimum_unavoidable_row_errors"], row["fail_open"]["unsafe_pre_allow"]["rate"], row["fail_closed"]["false_denial"]["rate"]])

    claim_map = "\n".join([
        "# Claim-to-Source Map",
        "",
        "| Claim | Result artifact | Key or row source | Generating code |",
        "|---|---|---|---|",
        "| Registration counterfactuals validate the frozen descriptors | `full-scale-authorization-report.json` | `registration.descriptor_exact_set_match`, `registration.counterfactual_relation_accuracy` | `validate_registration` |",
        "| Coarse representations contain policy-separating collisions | `full-scale-authorization-report.json` and `representation-collision-witnesses.jsonl` | `representation_capacity[*].n_mixed_cells` | `collision_audit` |",
        "| Typed effects support complete direct authorization on the frozen domain | `full-scale-authorization-report.json` and `authorization-decisions.jsonl` | `direct_policy_metrics[validated_typed_effects]` | `authorize_observation` |",
        "| Raw arguments collide under changed pre-state | `policy-separating-pair-audit.jsonl` | rows with `state_dependent=true` | `pair_audit` |",
        "| Source and descriptor implementations agree on held-out effects | `heldout-source-executions.jsonl` | `descriptor_exact_set_match` | `source_effects`, `instantiate_descriptor` |",
        "",
    ])
    (target / "claim-to-source.md").write_text(claim_map, encoding="utf-8")
    artifact_names = [
        "registration-source-executions.jsonl",
        "registration-pair-validation.jsonl",
        "heldout-source-executions.jsonl",
        "authorization-decisions.jsonl",
        "representation-collision-witnesses.jsonl",
        "policy-separating-pair-audit.jsonl",
        "full-scale-authorization-report.json",
        "full-scale-authorization-report.md",
        "direct-policy-metrics.csv",
        "representation-capacity.csv",
        "table_full_scale_deployment_authorization.tex",
        "claim-boundary.md",
        "claim-to-source.md",
    ]
    reproduction = {
        "status": "passed" if report["status"] == "passed" and all((target / name).is_file() for name in artifact_names) else "failed",
        "experiment": report["experiment"],
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commands": [
            "python shared/compatibility/scripts/run_full_scale_deployment_authorization.py --mode full",
            "PYTHONPATH=. python -m pytest shared/compatibility/tests/tests/test_full_scale_deployment_authorization.py -q",
        ],
        "counts": {"registration_contexts": len(registration_rows), "heldout_contexts": len(evaluation_rows), "authorization_decisions": len(direct)},
        "input_hashes": protocol["input_hashes"],
        "artifact_hashes": {name: sha256(target / name) for name in artifact_names},
        "gates": gates,
    }
    (target / "reproduction-status.json").write_text(json.dumps(reproduction, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "mode": mode, "registration": registration_report, "evaluation": report["evaluation"], "gates": gates}, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    parser.add_argument("--freeze-inputs", action="store_true")
    parser.add_argument("--force-freeze", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.freeze_inputs:
        freeze_inputs(force=args.force_freeze)
    report = run(args.mode, args.output_dir)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
