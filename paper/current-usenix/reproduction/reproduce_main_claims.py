#!/usr/bin/env python3
"""Fail-fast reproduction index for the active USENIX main-paper claims."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
OUT = PAPER / "reproduction"


def read_json(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.exists():
        raise FileNotFoundError(relative)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {relative}")
    return value


def read_jsonl(relative: str) -> list[dict[str, Any]]:
    path = ROOT / relative
    if not path.exists():
        raise FileNotFoundError(relative)
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"expected JSON object at {relative}:{line_number}")
        rows.append(value)
    return rows


def get(value: Any, key: str) -> Any:
    current = value
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"missing {key!r} at {part!r}")
        current = current[part]
    return current


def add(
    rows: list[dict[str, Any]], claim_id: str, value: Any, source: str, key: str,
    location: str, generator: str, numerator: int | None = None,
    denominator: int | None = None,
) -> None:
    rows.append(
        {
            "claim_id": claim_id,
            "paper_location": location,
            "value": value,
            "numerator": numerator,
            "denominator": denominator,
            "source": source,
            "key": key,
            "generator": generator,
            "status": "verified",
        }
    )


def indexed(payload: dict[str, Any], outer: str, field: str, value: str) -> dict[str, Any]:
    for row in payload[outer]:
        if row[field] == value:
            return row
    raise KeyError(f"missing {outer}[{field}={value}]")


def require_table_snippets(table: str, snippets: list[str]) -> None:
    text = (PAPER / "tables" / table).read_text(encoding="utf-8")
    missing = [snippet for snippet in snippets if snippet not in text]
    if missing:
        raise ValueError(f"{table} differs from reproduced values: {missing}")


def add_rate_metric(
    rows: list[dict[str, Any]], claim_id: str, metric: dict[str, Any], source: str,
    key: str, location: str, generator: str,
) -> None:
    """Record a rate together with the exact numerator and denominator."""
    add(
        rows, claim_id, metric["rate"], source, f"{key}.rate", location, generator,
        metric.get("successes"), metric.get("total"),
    )


def add_protocol_separated_authority_claims(rows: list[dict[str, Any]]) -> None:
    source = (
        "experiments/human-authority-and-causal-validation/results/"
        "protocol-separated-authority-representation/report.json"
    )
    generator = "shared/compatibility/scripts/independent_authority_benchmark/run_experiment.py"
    payload = read_json(source)
    decisions_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "protocol-separated-authority-representation/authorization-decisions.jsonl"
    )
    decisions = read_jsonl(decisions_source)
    if payload.get("status") != "passed" or not all(payload.get("acceptance_gates", {}).values()):
        raise ValueError("protocol-separated authority experiment did not pass")

    registration = payload["registration"]
    for suffix, key in (
        ("CONTEXTS", "n_contexts"),
        ("PAIRS", "n_pairs"),
        ("SENSITIVE-PAIRS", "effective_sensitive_pairs"),
        ("INVARIANT-PAIRS", "surface_invariant_pairs"),
    ):
        add(
            rows, f"AUTHORITY-REGISTRATION-{suffix}", registration[key], source,
            f"registration.{key}", "Evaluation and Results / explicit authority", generator,
        )

    evaluation = payload["evaluation"]
    for suffix, key in (
        ("DOMAINS", "n_domains"),
        ("TOOLS", "n_tools"),
        ("CONTEXTS", "n_contexts"),
        ("EXACT-MATCHES", "descriptor_exact_matches"),
    ):
        add(
            rows, f"AUTHORITY-EVALUATION-{suffix}", evaluation[key], source,
            f"evaluation.{key}", "Evaluation and Results / explicit authority", generator,
        )

    representations = (
        "tool_name",
        "canonical_raw_arguments",
        "common_effect_fields",
        "validated_typed_effects",
    )
    for representation in representations:
        row = next(
            item for item in payload["direct_metrics"]
            if item["representation"] == representation and item["stratum"] == "all"
        )
        for suffix, key in (
            ("UPA", "unsafe_pre_allow"),
            ("COVERAGE", "coverage"),
            ("EXACT", "decision_accuracy"),
        ):
            add(
                rows, f"AUTHORITY-{representation.upper()}-{suffix}", row[key], source,
                f"direct_metrics[representation={representation},stratum=all].{key}",
                "Results / explicit-authority table", generator,
            )

        representation_decisions = [
            item for item in decisions if item["representation"] == representation
        ]
        ideal_allows = [
            item for item in representation_decisions if item["ideal_decision"] == "ALLOW"
        ]
        withheld = sum(item["monitor_decision"] != "ALLOW" for item in ideal_allows)
        if len(representation_decisions) != evaluation["n_contexts"] or not ideal_allows:
            raise ValueError(f"incomplete authorization decisions for {representation}")
        add(
            rows, f"AUTHORITY-{representation.upper()}-AUTHORIZED-WITHHELD",
            withheld / len(ideal_allows), decisions_source,
            (
                f"rows[representation={representation},ideal_decision=ALLOW,"
                "monitor_decision!=ALLOW]"
            ),
            "Results / explicit-authority table", generator,
            withheld, len(ideal_allows),
        )

        collision = indexed(payload, "collision_metrics", "representation", representation)
        for suffix, key in (
            ("MIXED-CELLS", "n_mixed_cells"),
            ("ERROR-LOWER-BOUND", "minimum_unavoidable_errors"),
        ):
            add(
                rows, f"AUTHORITY-{representation.upper()}-{suffix}", collision[key], source,
                f"collision_metrics[representation={representation}].{key}",
                "Results / explicit-authority table", generator,
            )

        state = payload["state_dependent"]["representations"][representation]
        add(
            rows, f"AUTHORITY-{representation.upper()}-STATE-COLLISIONS",
            state["colliding_groups"], source,
            f"state_dependent.representations.{representation}.colliding_groups",
            "Results / state-dependent authorization", generator,
            state["colliding_groups"], state["total"],
        )

    require_table_snippets(
        "table_protocol_separated_authority.tex",
        [
            "Tool-name view & 0.0 & 100.0 & 0.0 & 0.0 & 4",
            "Raw-call view & 1.1 & 50.4 & 99.6 & 87.2 & 51",
            "Common-field view & 0.0 & 32.9 & 81.0 & 81.0 & 9",
            "Typed-effect interface & 0.0 & 0.0 & 100.0 & 100.0 & 0",
        ],
    )


def fixed_claims(rows: list[dict[str, Any]]) -> None:
    add_protocol_separated_authority_claims(rows)
    prevalence_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "agentdojo-tool-effect-prevalence/agentdojo-tool-effect-prevalence-report.json"
    )
    prevalence = read_json(prevalence_source)
    prevalence_rows = (
        ("EFFECTFUL", "n_effectful_calls", "effectful_call_rate_all_calls", prevalence["n_official_calls"]),
        ("COMPOUND", "n_compound_calls", "compound_rate_effectful_calls", prevalence["prevalence"]["n_effectful_calls"]),
        ("HETEROGENEOUS", "n_heterogeneous_compound_calls", "heterogeneous_rate_effectful_calls", prevalence["prevalence"]["n_effectful_calls"]),
        ("MULTI-TARGET", "n_multi_target_calls", "multi_target_rate_effectful_calls", prevalence["prevalence"]["n_effectful_calls"]),
        ("CROSS-SUBSYSTEM", "n_cross_namespace_calls", "cross_namespace_rate_effectful_calls", prevalence["prevalence"]["n_effectful_calls"]),
    )
    for suffix, count_key, rate_key, denominator in prevalence_rows:
        add(
            rows, f"PREVALENCE-{suffix}", prevalence["prevalence"][rate_key],
            prevalence_source, f"prevalence.{rate_key}", "Results / prevalence table",
            "run_agentdojo_tool_effect_prevalence.py",
            prevalence["prevalence"][count_key], denominator,
        )
    require_table_snippets(
        "table_agentdojo_effect_prevalence.tex",
        ["Effectful calls & 29.5\\%", "Compound effects & 17.0\\%", "Heterogeneous effects & 13.0\\%", "Multiple targets & 7.0\\%"],
    )

    binding_source = (
        "experiments/binding-failure-and-granularity/results/"
        "hard-guard-granularity-stress/same-core-comparisons.json"
    )
    binding = read_json(binding_source)
    binding_methods = {
        "TOOL-NAME": "tool_name_rule_proxy",
        "QWEN": "local_qwen_self_audit",
        "TS-GUARD": "ts_guard_official_counterfactual_stress",
        "SAFIRON": "safiron_official_counterfactual_stress",
    }
    binding_metrics = {
        "EFFECT": "effect_sensitivity",
        "AUTH": "authorization_sensitivity",
        "RESOURCE": "resource_awareness",
        "UPA": "unsafe_pre_allow",
    }
    for method_id, method in binding_methods.items():
        row = indexed(binding, "existing_e47_rows", "method", method)
        for metric_id, key in binding_metrics.items():
            add(
                rows, f"BINDING-{method_id}-{metric_id}", row[key], binding_source,
                f"existing_e47_rows[method={method}].{key}",
                "Results / binding-problem table", "run_hard_guard_robustness.py",
            )

    unified_source = (
        "experiments/binding-failure-and-granularity/results/"
        "hard-guard-granularity-stress/reproduced-e48-main-table.json"
    )
    resource_source = (
        "experiments/binding-failure-and-granularity/results/"
        "hard-guard-granularity-stress/resource-authorization-stress.json"
    )
    provenance_source = (
        "experiments/binding-failure-and-granularity/results/"
        "hard-guard-granularity-stress/control-provenance-stress.json"
    )
    stress_specs = (
        ("UNIFIED", read_json(unified_source), unified_source, "effect_binding_guard_full", 822),
        ("RESOURCE-AUTH", read_json(resource_source), resource_source, "effect_binding_guard_full", 240),
        ("NO-RESOURCE", read_json(resource_source), resource_source, "full_without_resource_match", 240),
        ("NO-AUTH", read_json(resource_source), resource_source, "full_without_authorization_match", 240),
        ("PROVENANCE", read_json(provenance_source), provenance_source, "effect_binding_guard_full", 336),
    )
    for stress_id, payload, source, method, expected_rows in stress_specs:
        metric = payload["methods"][method]["overall"]
        if metric["n_rows"] != expected_rows:
            raise ValueError(f"wrong row count for {stress_id}")
        add(rows, f"STRESS-{stress_id}-ROWS", expected_rows, source,
            f"methods.{method}.overall.n_rows", "Results / binding-problem table",
            "run_hard_guard_robustness.py")
        for metric_id, key in (("UPA", "unsafe_pre_allow"), ("FD", "safe_false_deny"), ("COVERAGE", "coverage")):
            add_rate_metric(
                rows, f"STRESS-{stress_id}-{metric_id}", metric[key], source,
                f"methods.{method}.overall.{key}", "Appendix / controlled monitor stresses",
                "run_hard_guard_robustness.py",
            )
    require_table_snippets(
        "table_binding_problem_characterization.tex",
        [
            "Tool-name proxy & 0.0\\% & 0.0\\% & 0.0\\% & 29.2\\%",
            "Qwen self-audit & 66.7\\% & 56.5\\% & 29.2\\% & 0.4\\%",
            "TS-Guard & 62.5\\% & 76.4\\% & 83.3\\% & 15.9\\%",
            "Safiron & 100.0\\% & 8.8\\% & 16.7\\% & 54.5\\%",
            "Unified suite & 822 & 3.6\\% & 6.5\\% & 91.7\\%",
            "Resource/auth. & 240 & 38.3\\% & 0.0\\% & 92.1\\%",
            "w/o resource & 240 & 61.7\\% & 0.0\\% & 93.8\\%",
            "w/o authorization & 240 & 89.2\\% & 0.0\\% & 92.1\\%",
            "Provenance & 336 & 0.0\\% & 18.8\\% & 54.5\\%",
        ],
    )

    collision_source = (
        "experiments/binding-failure-and-granularity/results/"
        "authorization-separating-collision-audit/collision-audit-report.json"
    )
    collision = read_json(collision_source)
    if collision.get("status") != "passed":
        raise ValueError("authorization-separating collision audit did not pass")
    collision_specs = (
        ("UNIFIED", "E48-explicit-authority-subset", "tool_name"),
        ("UNIFIED", "E48-explicit-authority-subset", "ideal_effect"),
        ("UNIFIED", "E48-explicit-authority-subset", "ideal_effect_resource"),
        ("UNIFIED", "E48-explicit-authority-subset", "rule_extracted_effect_resource"),
        ("UNIFIED", "E48-explicit-authority-subset", "full_guard_decision_representation"),
        ("REPAIRED", "E50-repaired-resource-authorization", "tool_name"),
        ("REPAIRED", "E50-repaired-resource-authorization", "ideal_effect"),
        ("REPAIRED", "E50-repaired-resource-authorization", "ideal_effect_resource"),
        ("REPAIRED", "E50-repaired-resource-authorization", "rule_extracted_effect_resource"),
        ("REPAIRED", "E50-repaired-resource-authorization", "full_guard_decision_representation"),
    )
    for suite, dataset_name, representation in collision_specs:
        dataset = indexed(collision, "datasets", "dataset", dataset_name)
        row = indexed(dataset, "representations", "representation_name", representation)
        for suffix, key in (("MIXED", "n_mixed_authorization_cells"), ("ERROR-LB", "unit_cost_collision_lower_bound")):
            add(
                rows, f"COLLISION-{suite}-{representation.upper()}-{suffix}", row[key],
                collision_source,
                f"datasets[dataset={dataset_name}].representations[representation_name={representation}].{key}",
                "Results / representation-collision table", "run_authorization_collision_audit.py",
            )

    finite_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "finite-domain-effect-binding-validation/finite-domain-validation-report.json"
    )
    finite = read_json(finite_source)
    if finite.get("status") != "passed" or finite.get("n_contexts") != 56:
        raise ValueError("finite-domain effect validation is not final")
    for representation in (
        "tool_name", "source_effect_only", "source_common_fields", "source_full_effect",
    ):
        row = indexed(finite, "representations", "representation", representation)
        for suffix, key in (("MIXED", "authorization_collision_cells"), ("PAIRS", "authorization_separating_pairs")):
            add(
                rows, f"FINITE-{representation.upper()}-{suffix}", row[key], finite_source,
                f"representations[representation={representation}].{key}",
                "Results / representation-collision table", "run_finite_domain_effect_binding_validation.py",
            )
    require_table_snippets(
        "table_representation_collisions.tex",
        [
            "Tool name & 5 & 564", "Effect-only view & 6 & 548",
            "Common-field view & 5 & 118", "Typed-effect interface & 0 & 0",
            "Full source effect & 0 & 0",
        ],
    )

    refinement_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "refinement-monotonicity-check/refinement-monotonicity-report.json"
    )
    refinement = read_json(refinement_source)
    if refinement.get("status") != "passed":
        raise ValueError("refinement monotonicity check did not pass")
    trajectory = refinement["trajectory"]
    observed_pairs = [row["separating_pairs"] for row in trajectory]
    if observed_pairs != [124, 60, 28, 12, 4, 0]:
        raise ValueError(f"unexpected refinement trajectory: {observed_pairs}")
    add(
        rows,
        "REFINEMENT-TRAJECTORY",
        "124,60,28,12,4,0",
        refinement_source,
        "trajectory[*].separating_pairs",
        "Results / refinement paragraph",
        "run_refinement_monotonicity_check.py",
    )
    add(
        rows,
        "REFINEMENT-LATTICE-VIOLATIONS",
        refinement["lattice"]["refinement_violations"],
        refinement_source,
        "lattice.refinement_violations",
        "Results / refinement paragraph",
        "run_refinement_monotonicity_check.py",
    )
    for suffix, key in (("VERTICES", "vertices"), ("COMPARABLE-EDGES", "comparable_pairs")):
        add(
            rows, f"REFINEMENT-{suffix}", refinement["lattice"][key], refinement_source,
            f"lattice.{key}", "Results / refinement paragraph",
            "run_refinement_monotonicity_check.py",
        )

    sanitized_source = "paper/current-usenix/reproduction/sanitized_fixed_support.json"
    sanitized = read_json(sanitized_source)
    if sanitized.get("status") != "passed" or len(sanitized.get("source_hashes", {})) != 2:
        raise ValueError("sanitized fixed-support extract is not bound to both raw sources")
    common_projection = sanitized["projection_validation"]["eight_field_projection"]
    for suffix, key in (("CASES", "n_cases"), ("GAPS", "mediation_gaps")):
        add(
            rows, f"PROJECTION-COMMON-{suffix}", common_projection[key], sanitized_source,
            f"projection_validation.eight_field_projection.{key}",
            "Results / counterfactual-registration paragraph",
            "extract_sanitized_fixed_support.py",
        )

    descriptor = sanitized["descriptor_registration"]
    for suffix, key in (
        ("TOOLS", "n_registered_tools"),
        ("FIELDS", "n_security_fields"),
        ("CHANGED", "sandbox_counterfactual_status_counts.effect_changed"),
        ("INVARIANT", "sandbox_counterfactual_status_counts.effect_invariant"),
        ("EXTERNAL-DESTINATION", "sandbox_counterfactual_status_counts.external_request_destination_changes"),
        ("UNRESOLVED", "sandbox_counterfactual_status_counts.unresolved_fail_closed"),
        ("MULTI-STATUS-FIELDS", "n_multi_status_fields"),
    ):
        add(
            rows, f"INITIAL-DESCRIPTOR-{suffix}", get(descriptor, key), sanitized_source,
            f"descriptor_registration.{key}", "Method / offline registration",
            "extract_sanitized_fixed_support.py",
        )

    held_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "heldout-toolsandbox-effect-binding-validation/heldout-validation-report.json"
    )
    held = read_json(held_source)
    if held.get("status") != "passed" or held.get("n_contexts") != 32:
        raise ValueError("ToolSandbox held-out result is not final")
    for representation in ("tool_name", "common_fields", "typed_contract", "source_full_effect"):
        row = indexed(held, "representations", "representation", representation)
        for suffix, key in (
            ("CELLS", "n_cells"), ("COLLISIONS", "authorization_collision_cells"),
            ("PAIRS", "authorization_separating_pairs"), ("OVERPARTITION", "overpartition_pairs"),
        ):
            add(
                rows, f"TOOLSANDBOX-{representation.upper()}-{suffix}", row[key], held_source,
                f"representations[representation={representation}].{key}",
                "Results / ToolSandbox table", "run_toolsandbox_heldout_validation.py",
            )
    add(
        rows, "TOOLSANDBOX-WITNESS-CELLS", held["n_witness_cells"], held_source,
        "n_witness_cells", "Results / ToolSandbox paragraph",
        "run_toolsandbox_heldout_validation.py",
    )
    require_table_snippets(
        "table_toolsandbox_heldout.tex",
        ["Tool name & 5 & 5 & 88 & 16", "Common-field view & 11 & 4 & 41 & 0", "Typed-effect interface & 25 & 0 & 0 & 0", "Source effect & 25 & 0 & 0 & 0"],
    )

    registration_source = (
        "experiments/intent-bound-runtime-guard/results/"
        "counterfactual-atom-envelope-guard/registration_sufficiency_audit_v2.json"
    )
    registration = read_json(registration_source)
    if registration.get("status") != "passed":
        raise ValueError("registration sufficiency audit did not pass")
    field_rows = registration["field_rows"]
    committed = sum(row["committed_effect_changed"] for row in field_rows)
    output_only = sum(row["output_only_changed"] for row in field_rows)
    invariant = sum(row["effect_invariant"] for row in field_rows)
    invalid = registration["n_attempts"] - registration["n_valid"]
    no_valid_mutation = sum(row["valid"] == 0 for row in field_rows)
    registration_claims = (
        ("RETAINED", registration["descriptor_security_fields"], "descriptor_security_fields", registration["descriptor_security_fields"], registration["descriptor_total_fields"]),
        ("SUITE-FIELDS", registration["n_fields"], "n_fields", None, None),
        ("FIVE-VALID", registration["n_fields_with_five_valid_distinct_intervention_kinds"], "n_fields_with_five_valid_distinct_intervention_kinds", registration["n_fields_with_five_valid_distinct_intervention_kinds"], registration["n_fields"]),
        ("WITNESSED", registration["n_fields_with_committed_effect_witness"], "n_fields_with_committed_effect_witness", registration["n_fields_with_committed_effect_witness"], registration["n_fields"]),
        ("VALID", registration["n_valid"] / registration["n_attempts"], "n_valid / n_attempts", registration["n_valid"], registration["n_attempts"]),
        ("COMMITTED", committed, "sum(field_rows[*].committed_effect_changed)", None, None),
        ("OUTPUT-ONLY", output_only, "sum(field_rows[*].output_only_changed)", None, None),
        ("INVARIANT", invariant, "sum(field_rows[*].effect_invariant)", None, None),
        ("INVALID", invalid, "n_attempts - n_valid", None, None),
        ("NO-VALID-MUTATION", no_valid_mutation, "count(field_rows[*].valid == 0)", None, None),
    )
    for suffix, value, key, numerator, denominator in registration_claims:
        add(
            rows, f"REGISTRATION-{suffix}", value, registration_source, key,
            "Method / Results / registration table", "run_registration_sufficiency_audit_v2.py",
            numerator, denominator,
        )
    require_table_snippets(
        "table_registration_sufficiency.tex",
        ["100.0\\%", "50.7\\%", "88.0\\%", "76.8\\%", "73.3\\%", "23.2\\%"],
    )

    final_source = (
        "experiments/intent-bound-runtime-guard/results/"
        "counterfactual-atom-envelope-guard/deepseek_same_model_strong_baselines.json"
    )
    final = read_json(final_source)
    if final.get("status") != "passed":
        raise ValueError("C1f frozen evidence did not pass")
    for method in ("no_guard", "repeat_user_prompt", "spotlighting", "c1f"):
        method_row = final["methods"][method]
        successes = sum(method_row["benign"]["successes"])
        benign_denominator = 97 * method_row["benign"]["repetitions"]
        add(
            rows, f"DEEPSEEK-{method.upper()}-BU", method_row["benign"]["mean_utility"],
            final_source, f"methods.{method}.benign.mean_utility", "Results / DeepSeek table",
            "analyze_deepseek_strong_baselines.py", successes, benign_denominator,
        )
        for suffix, key in (("AU", "utility_successes"), ("ASR", "attack_successes")):
            attack = method_row["official_attack"]
            add(
                rows, f"DEEPSEEK-{method.upper()}-{suffix}", attack[key] / attack["n"],
                final_source, f"methods.{method}.official_attack.{key}", "Results / DeepSeek table",
                "analyze_deepseek_strong_baselines.py", attack[key], attack["n"],
            )
    audit_source = (
        "experiments/intent-bound-runtime-guard/results/"
        "counterfactual-atom-envelope-guard/final_guard_repair_report_2026-08-08.json"
    )
    audit = read_json(audit_source)
    scope_n = get(audit, "security.scope_aligned_confirmation_n")
    if scope_n != 608:
        raise ValueError(f"unexpected scope-aligned denominator: {scope_n}")
    for method in ("no_guard", "c1f"):
        key = f"security.scope_aligned_{method}_attack_successes"
        successes = get(audit, key)
        add(
            rows, f"DEEPSEEK-SCOPE-{method.upper()}-ASR", successes / scope_n,
            audit_source, key,
            "Results / DeepSeek table", "reproduce_deepseek_guard_repair.py",
            successes, scope_n,
        )
    add(
        rows, "DEEPSEEK-SCOPE-P", get(audit, "security.scope_aligned_exact_one_sided_mcnemar_p"),
        audit_source, "security.scope_aligned_exact_one_sided_mcnemar_p",
        "Results / DeepSeek table", "reproduce_deepseek_guard_repair.py",
    )
    require_table_snippets(
        "table_deepseek_runtime.tex",
        ["76.3\\% & 1.0\\%", "75.8\\% & 0.0\\%", "72.0\\% & 0.0\\%", "Scope aligned: no guard 1.0\\%"],
    )

    for claim_id, key in (
        ("DEEPSEEK-CHECKS", "security.c1f_precommit_checks"),
        ("DEEPSEEK-DENIES", "security.c1f_denies"),
        ("DEEPSEEK-ABSTAINS", "security.c1f_abstains"),
        ("DEEPSEEK-UNMEDIATED", "security.executed_without_allow"),
    ):
        add(rows, claim_id, get(audit, key), audit_source, key, "Results / runtime audit", "reproduce_deepseek_guard_repair.py")
    add(
        rows, "DEEPSEEK-ALLOWS",
        get(audit, "security.c1f_precommit_checks")
        - get(audit, "security.c1f_denies")
        - get(audit, "security.c1f_abstains"),
        audit_source, "security.c1f_precommit_checks - security.c1f_denies - security.c1f_abstains",
        "Results / runtime audit", "reproduce_deepseek_guard_repair.py",
    )
    churn = final["methods"]["c1f"]["paired_attack_utility_vs_no_guard"]
    for suffix, key in (("NO-GUARD-ONLY", "no_guard_only_successes"), ("C1F-ONLY", "method_only_successes")):
        add(
            rows, f"DEEPSEEK-UTILITY-CHURN-{suffix}", churn[key], final_source,
            f"methods.c1f.paired_attack_utility_vs_no_guard.{key}",
            "Results / utility churn", "analyze_deepseek_strong_baselines.py",
        )

    attribution_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "representation-closed-loop-attribution/closed-loop-attribution-report.json"
    )
    attribution = read_json(attribution_source)
    if attribution.get("status") != "passed":
        raise ValueError("representation attribution result did not pass")
    for variant in ("atom_field", "tool_call"):
        row = indexed(attribution, "aggregates", "variant", variant)
        for suffix, key, denominator_key in (
            ("BU", "benign_utility", "benign_n"), ("AU", "attack_utility", "attack_n"),
            ("ASR", "attack_success_rate", "attack_n"),
        ):
            denominator = row[denominator_key]
            numerator = row["attack_successes"] if suffix == "ASR" else round(row[key] * denominator)
            add(
                rows, f"ATTRIBUTION-{variant.upper()}-{suffix}", row[key], attribution_source,
                f"aggregates[variant={variant}].{key}", "Appendix / historical two-view attribution",
                "run_representation_closed_loop_attribution.py", numerator, denominator,
            )

    transfer_specs = (
        ("NO-GUARD", "experiments/long-horizon-transfer/results/long-horizon-cross-environment-transfer/agentlab-saved-transfer-no-guard-results.json"),
        ("OLDER-PROFILE", "experiments/long-horizon-transfer/results/long-horizon-cross-environment-transfer/agentlab-saved-transfer-e77-results.json"),
    )
    for transfer_id, source in transfer_specs:
        transfer = read_json(source)
        if transfer.get("status") != "passed" or transfer["metrics"].get("n") != 303:
            raise ValueError(f"incomplete legacy transfer row: {transfer_id}")
        for suffix, key in (("AU", "utility_successes"), ("ASR", "attack_successes")):
            add(
                rows, f"TRANSFER-{transfer_id}-{suffix}", transfer["metrics"][key] / 303,
                source, f"metrics.{key}", "Appendix / historical transfer comparison",
                "run_e79_agentlab_saved_transfer.py", transfer["metrics"][key], 303,
            )
        if transfer_id == "OLDER-PROFILE":
            add(
                rows, "TRANSFER-OLDER-PROFILE-PRECOMMIT-CHECKS",
                transfer["precommit_mediation"]["precommit_checks"], source,
                "precommit_mediation.precommit_checks",
                "Results / legacy saved-transfer paragraph",
                "finalize_e79_agentlab_saved_transfer.py",
            )
    view_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "runtime-policy-view-ablation/runtime-policy-view-report.json"
    )
    views = read_json(view_source)
    if views.get("status") != "passed" or views.get("n_cases") != 726:
        raise ValueError("runtime policy-view diagnostic did not pass")
    for variant in (
        "no_guard",
        "whole_call_provenance",
        "effect_only",
        "registered_field_c1f",
    ):
        row = indexed(views, "aggregates", "variant", variant)
        add(
            rows,
            f"POLICY-VIEW-{variant.upper()}-INTERCEPTED",
            row["successful_attack_trajectories_intercepted"],
            view_source,
            f"aggregates[variant={variant}].successful_attack_trajectories_intercepted",
            "Results / policy-view diagnostic",
            "run_runtime_policy_view_ablation.py",
            row["successful_attack_trajectories_intercepted"],
            row["official_attack_successes"],
        )
        add(
            rows,
            f"POLICY-VIEW-{variant.upper()}-TOUCHED",
            row["all_attack_trajectories_would_block"],
            view_source,
            f"aggregates[variant={variant}].all_attack_trajectories_would_block",
            "Results / policy-view diagnostic",
            "run_runtime_policy_view_ablation.py",
            row["all_attack_trajectories_would_block"],
            row["attack_n"],
        )
    if any(row["benign_trajectories_would_block"] != 0 for row in views["aggregates"]):
        raise ValueError("policy-view diagnostic unexpectedly touches a benign trajectory")
    add(
        rows, "POLICY-VIEW-BENIGN-TOUCHED", 0, view_source,
        "all(aggregates[*].benign_trajectories_would_block == 0)",
        "Results / policy-view diagnostic", "run_runtime_policy_view_ablation.py", 0, 97,
    )


def add_deepseek_repeated_claims(
    rows: list[dict[str, Any]], payload: dict[str, Any], source: str, generator: str
) -> None:
    if payload.get("benchmark") != "AgentDojo v1.1.2 benign tasks":
        raise ValueError("unexpected DeepSeek repeated-benign benchmark")
    for condition in ("no_guard", "spotlighting", "c1f"):
        row = indexed(payload, "aggregates", "condition", condition)
        if row.get("runs") != 4 or row.get("task_evaluations") != 388:
            raise ValueError(f"incomplete repeated-benign aggregate: {condition}")
        add(
            rows,
            f"DEEPSEEK-REPEATED-{condition.upper()}-UTILITY",
            row["mean_utility_rate"],
            source,
            f"aggregates[condition={condition}].mean_utility_rate",
            "Final Results / repeated benign utility",
            generator,
            row["utility_successes"],
            row["task_evaluations"],
        )
    bootstrap = payload["task_cluster_bootstrap"]
    for claim_id, key in (
        ("DEEPSEEK-REPEATED-C1F-DIFFERENCE", "difference_c1f_minus_no_guard"),
        ("DEEPSEEK-REPEATED-C1F-LOWER-BOUND", "one_sided_95_lower_bound"),
        ("DEEPSEEK-REPEATED-C1F-NONINFERIOR", "noninferior"),
    ):
        add(
            rows,
            claim_id,
            bootstrap[key],
            source,
            f"task_cluster_bootstrap.{key}",
            "Final Results / repeated benign utility",
            generator,
        )


def add_qwen_claims(
    rows: list[dict[str, Any]], payload: dict[str, Any], source: str, generator: str
) -> None:
    if payload.get("case_keys_per_condition") != 726:
        raise ValueError("Qwen matched comparison has the wrong case denominator")
    for condition in ("no_guard", "spotlighting", "c1f"):
        row = indexed(payload, "metrics", "condition", condition)
        if row.get("n_benign") != 97 or row.get("n_attack") != 629 or row.get("errors") != 0:
            raise ValueError(f"incomplete Qwen aggregate: {condition}")
        for suffix, value_key, denominator_key in (
            ("BENIGN-UTILITY", "benign_utility_successes", "n_benign"),
            ("ATTACK-UTILITY", "attack_utility_successes", "n_attack"),
            ("ASR", "attack_successes", "n_attack"),
        ):
            add(
                rows,
                f"QWEN32-{condition.upper()}-{suffix}",
                row[value_key] / row[denominator_key],
                source,
                f"metrics[condition={condition}].{value_key}",
                "Appendix / prior three-method second-model comparison",
                generator,
                row[value_key],
                row[denominator_key],
            )


def add_heldout_claims(
    rows: list[dict[str, Any]], payload: dict[str, Any], source: str, generator: str
) -> None:
    if (
        payload.get("benchmark") != "AgentDojo v1.1.2"
        or payload.get("official_validator") is not True
        or payload.get("real_external_side_effects") is not False
        or len(payload.get("manifest_sha256", "")) != 64
        or len(payload.get("frozen_c1f_source_hashes", {})) < 2
        or payload.get("failures") != []
    ):
        raise ValueError("held-out protocol or freeze metadata is incomplete")
    for method in ("no_guard", "spotlighting", "c1f"):
        row = indexed(payload, "summaries", "method", method)
        if row.get("n") != 320 or row.get("expected") != 320 or row.get("errors") != 0:
            raise ValueError(f"incomplete held-out aggregate: {method}")
        for suffix, key in (("ASR", "attack_successes"), ("UTILITY", "utility_successes")):
            add(
                rows,
                f"HELDOUT-{method.upper()}-{suffix}",
                row[key] / 320,
                source,
                f"summaries[method={method}].{key}",
                "Final Results / frozen held-out attacks",
                generator,
                row[key],
                320,
            )


def add_agentlab_claims(
    rows: list[dict[str, Any]], payload: dict[str, Any], source: str, generator: str
) -> None:
    metrics = payload["metrics"]
    if (
        payload.get("experiment") != "agentlab_saved_transfer_current_c1f_pair"
        or payload.get("method") != "c1f"
        or payload.get("expected_case_keys") != 303
        or metrics.get("n") != 303
        or metrics.get("evaluable") is not True
        or payload.get("official_validator") is not True
        or payload.get("real_external_side_effects") is not False
        or len(payload.get("model_sha256", "")) != 64
        or len(payload.get("case_manifest_sha256", "")) != 64
        or len(payload.get("c1f_source_hashes", {})) < 2
    ):
        raise ValueError("current-profile AgentLAB transfer is incomplete")
    comparison = {
        row["condition"]: row for row in payload.get("comparison_metrics", [])
    }
    if set(comparison) != {"no_guard", "c1f"} or any(
        row.get("n") != 303 or row.get("evaluable") is not True
        for row in comparison.values()
    ):
        raise ValueError("matched AgentLAB comparison is incomplete")
    for suffix, key in (("ASR", "attack_successes"), ("UTILITY", "utility_successes")):
        row = comparison["no_guard"]
        add(
            rows,
            f"AGENTLAB-NO-GUARD-{suffix}",
            row[key] / 303,
            source,
            f"comparison_metrics[condition=no_guard].{key}",
            "Final Results / saved-transfer comparison",
            generator,
            row[key],
            303,
        )
    for suffix, key in (("ASR", "attack_successes"), ("UTILITY", "utility_successes")):
        add(
            rows,
            f"AGENTLAB-C1F-{suffix}",
            metrics[key] / 303,
            source,
            f"metrics.{key}",
            "Final Results / saved-transfer comparison",
            generator,
            metrics[key],
            303,
        )
    mediation = payload["precommit_mediation"]
    if mediation.get("signature_multiset_exact_match") is not True:
        raise ValueError("AgentLAB pre-commit reconciliation failed")
    for suffix, key in (
        ("EXECUTED-CALLS", "executed_tool_result_calls"),
        ("PRECOMMIT-CHECKS", "precommit_checks"),
        ("MISSING-CHECKS", "missing_check_occurrences"),
    ):
        add(
            rows,
            f"AGENTLAB-C1F-{suffix}",
            mediation[key],
            source,
            f"precommit_mediation.{key}",
            "Final Results / saved-transfer comparison",
            generator,
        )
    require_table_snippets(
        "table_granularity_and_transfer.tex",
        ["61.1\\% & 31.4\\%", "43.6\\% & 0.3\\%"],
    )


def add_four_view_claims(
    rows: list[dict[str, Any]], payload: dict[str, Any], source: str, generator: str
) -> None:
    if (
        payload.get("experiment") != "current_c1f_closed_loop_four_view"
        or payload.get("n_cases") != 321
        or payload.get("selection_conditioned") is not True
        or not all(payload.get("gates", {}).values())
    ):
        raise ValueError("current-C1f four-view closed-loop result is incomplete")
    for variant in (
        "no_guard",
        "whole_call_provenance",
        "effect_only",
        "registered_field_c1f",
    ):
        row = indexed(payload, "aggregates", "variant", variant)
        if row.get("n_cases") != 321 or row.get("benign_n") != 48 or row.get("attack_n") != 273:
            raise ValueError(f"wrong four-view denominator: {variant}")
        for suffix, key, denominator in (
            ("BENIGN-UTILITY", "benign_utility_successes", 48),
            ("ATTACK-UTILITY", "attack_utility_successes", 273),
            ("ASR", "attack_successes", 273),
        ):
            add(
                rows,
                f"C1F-FOUR-VIEW-{variant.upper()}-{suffix}",
                row[key] / denominator,
                source,
                f"aggregates[variant={variant}].{key}",
                "Final Results / current-C1f mechanism attribution",
                generator,
                row[key],
                denominator,
            )
        audit = row.get("precommit_audit")
        if variant in {"whole_call_provenance", "effect_only"}:
            if not audit or audit.get("precommit_checks", 0) <= 0 or audit.get("executed_without_allow") != 0:
                raise ValueError(f"four-view pre-commit audit failed: {variant}")


def add_bounded_adaptive_claims(
    rows: list[dict[str, Any]], payload: dict[str, Any], source: str, generator: str
) -> None:
    if (
        payload.get("experiment") != "bounded_public_family_search_current_c1f"
        or payload.get("locked_cases") != 40
        or payload.get("variant_rows") != 320
        or len(payload.get("current_c1f_source_hashes", {})) < 2
        or len(payload.get("no_guard_source_hashes", {})) < 5
        or len(payload.get("model_sha256", "")) != 64
        or len(payload.get("locked_manifest_sha256", "")) != 64
    ):
        raise ValueError("current-C1f bounded adaptive result is incomplete")
    for method in ("no_guard", "ours_e77_effect_diff_runtime"):
        row = indexed(payload, "search_metrics", "method", method)
        if row.get("n") != 40:
            raise ValueError(f"wrong bounded-search denominator: {method}")
        for suffix, key in (("ASR", "attack_successes"), ("UTILITY", "terminal_user_utility_successes")):
            add(
                rows,
                f"BOUNDED-CURRENT-{method.upper()}-{suffix}",
                row[key] / 40,
                source,
                f"search_metrics[method={method}].{key}",
                "Final Results / bounded public-family diagnostic",
                generator,
                row[key],
                40,
            )
    add(
        rows,
        "BOUNDED-CURRENT-ASR-MCNEMAR-P",
        payload["paired_statistics"]["attack_success"]["exact_mcnemar_two_sided_p"],
        source,
        "paired_statistics.attack_success.exact_mcnemar_two_sided_p",
        "Final Results / bounded public-family diagnostic",
        generator,
    )


def add_raw_field_attribution_claims(
    rows: list[dict[str, Any]], payload: dict[str, Any], source: str, generator: str
) -> None:
    if (
        payload.get("experiment") != "current_c1f_raw_field_attribution"
        or payload.get("n_cases") != 321
        or payload.get("selection_conditioned") is not True
        or not all(payload.get("gates", {}).values())
    ):
        raise ValueError("raw-field attribution result is incomplete")
    raw = indexed(payload, "aggregates", "variant", "raw_field_taint")
    if raw.get("n_cases") != 321 or raw.get("benign_n") != 48 or raw.get("attack_n") != 273:
        raise ValueError("wrong raw-field attribution denominator")
    audit = raw.get("precommit_audit")
    if not audit or audit.get("precommit_checks", 0) <= 0 or audit.get("executed_without_allow") != 0:
        raise ValueError("raw-field pre-commit audit failed")
    for suffix, key, denominator in (
        ("BENIGN-UTILITY", "benign_utility_successes", 48),
        ("ATTACK-UTILITY", "attack_utility_successes", 273),
        ("ASR", "attack_successes", 273),
    ):
        add(
            rows,
            f"RAW-FIELD-CLOSED-LOOP-{suffix}",
            raw[key] / denominator,
            source,
            f"aggregates[variant=raw_field_taint].{key}",
            "Final Results / raw-field attribution",
            generator,
            raw[key],
            denominator,
        )
    retrospective = payload["retrospective_same_call"]
    call_denominator = retrospective["n_effectful_call_checks"]
    for suffix, key, denominator in (
        ("DECISION-DISAGREEMENTS", "decision_disagreements", call_denominator),
        ("RAW-ALLOW-ATOM-DENY", "raw_allow_atom_deny", call_denominator),
        ("RAW-DENY-ATOM-ALLOW", "raw_deny_atom_allow", call_denominator),
        ("TRAJECTORIES-WITH-DISAGREEMENT", "trajectories_with_disagreement", 726),
    ):
        add(
            rows,
            f"RAW-FIELD-RETROSPECTIVE-{suffix}",
            retrospective[key] / denominator,
            source,
            f"retrospective_same_call.{key}",
            "Final Results / paired representation attribution",
            generator,
            retrospective[key],
            denominator,
        )
    require_table_snippets(
        "table_granularity_and_transfer.tex",
        [
            "No blocking & 62.5\\% & 56.0\\% & 13.9\\%",
            "Whole-call provenance & 81.3\\% & 21.2\\% & 4.0\\%",
            "Effect only & 77.1\\% & 53.8\\% & 7.7\\%",
            "Raw-field taint & 81.3\\% & 59.3\\% & 3.7\\%",
            "Registered fields & 64.6\\% & 54.2\\% & 2.6\\%",
        ],
    )


def add_current_strong_baseline_claims(
    rows: list[dict[str, Any]], payload: dict[str, Any], source: str, generator: str
) -> None:
    expected = {
        "no_guard",
        "spotlighting",
        "prompt_sandwiching",
        "promptarmor_local",
        "c1f",
    }
    metrics = {row["method"]: row for row in payload.get("metrics", [])}
    if (
        payload.get("experiment") != "current_c1f_qwen32_strong_baseline_rerun"
        or set(metrics) != expected
        or not all(payload.get("gates", {}).values())
        or any(row.get("n_benign") != 97 or row.get("n_attack") != 629 for row in metrics.values())
    ):
        raise ValueError("current-C1f strong-baseline rerun is incomplete")
    for method, row in metrics.items():
        for suffix, key, denominator in (
            ("BENIGN-UTILITY", "benign_utility_successes", 97),
            ("ATTACK-UTILITY", "attack_utility_successes", 629),
            ("ASR", "attack_successes", 629),
        ):
            add(
                rows,
                f"CURRENT-STRONG-{method.upper()}-{suffix}",
                row[key] / denominator,
                source,
                f"metrics[method={method}].{key}",
                "Final Results / frozen strong-baseline comparison",
                generator,
                row[key],
                denominator,
            )
    audit = payload["c1f_precommit_audit"]
    for suffix, key in (
        ("PRECOMMIT-CHECKS", "precommit_checks"),
        ("EXECUTED-WITHOUT-ALLOW", "executed_without_allow"),
        ("RUNTIME-LLM-CALLS", "runtime_llm_calls"),
    ):
        add(
            rows,
            f"CURRENT-STRONG-C1F-{suffix}",
            audit[key],
            source,
            f"c1f_precommit_audit.{key}",
            "Final Results / frozen strong-baseline comparison",
            generator,
        )


def add_concrete_atom_authorizer_claims(
    rows: list[dict[str, Any]], payload: dict[str, Any], source: str, generator: str
) -> None:
    expected_methods = {
        "whole_call_tool_name",
        "raw_arguments_exact",
        "common_effect_atoms",
        "concrete_effect_atoms",
        "source_effect_oracle",
    }
    metrics = {row["method"]: row for row in payload.get("metrics", [])}
    if (
        payload.get("experiment") != "toolsandbox_concrete_atom_authorizer_mechanism"
        or payload.get("mode") != "full"
        or payload.get("n_tools") != 5
        or payload.get("n_contexts") != 32
        or payload.get("n_queries") != 232
        or set(metrics) != expected_methods
        or not all(payload.get("gates", {}).values())
    ):
        raise ValueError("concrete-atom authorizer mechanism result is incomplete")
    for suffix, key in (
        ("TOOLS", "n_tools"),
        ("CONTEXTS", "n_contexts"),
        ("QUERIES", "n_queries"),
    ):
        add(
            rows,
            f"CONCRETE-AUTHORIZER-{suffix}",
            payload[key],
            source,
            key,
            "Results / concrete-atom authorizer mechanism",
            generator,
        )
    for decision in ("ALLOW", "DENY"):
        add(
            rows,
            f"CONCRETE-AUTHORIZER-IDEAL-{decision}",
            payload["ideal_decisions"][decision],
            source,
            f"ideal_decisions.{decision}",
            "Results / concrete-atom authorizer mechanism",
            generator,
        )
    for method, row in metrics.items():
        for suffix, key in (
            ("UPA", "unsafe_pre_allow"),
            ("FD", "safe_false_deny"),
            ("COVERAGE", "coverage"),
            ("ACCURACY", "decision_accuracy"),
        ):
            add_rate_metric(
                rows,
                f"CONCRETE-AUTHORIZER-{method.upper()}-{suffix}",
                row[key],
                source,
                f"metrics[method={method}].{key}",
                "Results / concrete-atom authorizer mechanism",
                generator,
            )
    require_table_snippets(
        "table_concrete_atom_authorizer.tex",
        [
            "Tool name",
            "Exact raw args",
            "Common-field view",
            "Concrete atoms",
            "Source oracle",
        ],
    )


def add_new_interface_validation_claims(rows: list[dict[str, Any]]) -> None:
    state_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "state-aware-authority-interface/report.json"
    )
    state_generator = "shared/compatibility/scripts/state_aware_authority_baseline.py"
    state = read_json(state_source)
    state_reproduction = read_json(
        "experiments/human-authority-and-causal-validation/results/"
        "state-aware-authority-interface/reproduction-status.json"
    )
    if (state.get("status") != "passed" or state_reproduction.get("status") != "passed"
            or not all(state.get("acceptance_gates", {}).values())):
        raise ValueError("state-aware authority baseline did not pass all integrity gates")
    collision = indexed(state, "collision_metrics", "representation", "state_aware_raw_call")
    direct = next(item for item in state["direct_metrics"]
                  if item["representation"] == "state_aware_raw_call" and item["stratum"] == "all")
    for suffix, value, key in (
        ("CONTEXTS", direct["n"], "direct_metrics[state_aware_raw_call,all].n"),
        ("CELLS", collision["n_cells"], "collision_metrics[state_aware_raw_call].n_cells"),
        ("MIXED", collision["n_mixed_cells"], "collision_metrics[state_aware_raw_call].n_mixed_cells"),
        ("PAIRS", collision["authorization_separating_pairs"], "collision_metrics[state_aware_raw_call].authorization_separating_pairs"),
        ("OVERPARTITION", collision["overpartition_pairs"], "collision_metrics[state_aware_raw_call].overpartition_pairs"),
        ("MEDIAN-BYTES", collision["serialized_bytes"]["median"], "collision_metrics[state_aware_raw_call].serialized_bytes.median"),
        ("UPA", direct["unsafe_pre_allow"], "direct_metrics[state_aware_raw_call,all].unsafe_pre_allow"),
        ("COVERAGE", direct["coverage"], "direct_metrics[state_aware_raw_call,all].coverage"),
        ("EXACT", direct["decision_accuracy"], "direct_metrics[state_aware_raw_call,all].decision_accuracy"),
        ("STATE-COLLISIONS", state["state_dependent"]["representations"]["state_aware_raw_call"]["colliding_groups"],
         "state_dependent.representations.state_aware_raw_call.colliding_groups"),
    ):
        add(rows, f"STATE-AWARE-{suffix}", value, state_source, key,
            "Results / explicit authority", state_generator)
    require_table_snippets(
        "table_protocol_separated_authority.tex",
        ["State-aware request$^\\dagger$ & 0.0 & 0.0 & 100.0 & 100.0 & 0"],
    )

    certificate_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "executable-failure-certificates/report.json"
    )
    certificate_rows_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "executable-failure-certificates/failure-certificates.jsonl"
    )
    certificate_generator = "shared/compatibility/scripts/extract_executable_failure_certificates.py"
    certificate_report = read_json(certificate_source)
    certificates = read_jsonl(certificate_rows_source)
    if certificate_report.get("status") != "passed" or len(certificates) != 6 or len({item["certificate_id"] for item in certificates}) != 6:
        raise ValueError("failure certificate artifact incomplete")
    add(rows, "FAILURE-CERTIFICATES-N", 6, certificate_source, "n_certificates",
        "Results / executable certificates", certificate_generator)
    for item in certificates:
        valid = (
            item["source_effect_u"] != item["source_effect_v"]
            and item["ideal_decision_u"] != item["ideal_decision_v"]
            and item["coarse_representation_u"] == item["coarse_representation_v"]
            and item["refined_representation_u"] != item["refined_representation_v"]
        )
        if not valid:
            raise ValueError(f"invalid executable failure certificate: {item['certificate_id']}")
        add(rows, f"FAILURE-{item['category'].upper()}-VALID", True, certificate_rows_source,
            f"rows[certificate_id={item['certificate_id']}]", "Results / executable certificates",
            certificate_generator)
    require_table_snippets(
        "table_failure_certificates.tex",
        ["Compound effect & Raw call", "State dependence & Raw call"],
    )

    third_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "third-party-authorization-interface-validation/third_party_validation_report.json"
    )
    third_rows_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "third-party-authorization-interface-validation/post_freeze_authorization_rows.jsonl"
    )
    registration_rows_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "third-party-authorization-interface-validation/registration_source_executions.jsonl"
    )
    third_generator = "shared/compatibility/scripts/run_third_party_authorization_interface_validation.py"
    third = read_json(third_source)
    third_protocol = read_json(
        "experiments/human-authority-and-causal-validation/evaluation/"
        "third-party-authorization-interface-validation/protocol_manifest.json"
    )
    third_sources = read_json(
        "experiments/human-authority-and-causal-validation/evaluation/"
        "third-party-authorization-interface-validation/source_manifest.json"
    )
    post_rows = read_jsonl(third_rows_source)
    registration_rows = read_jsonl(registration_rows_source)
    if (
        third.get("status") != "passed" or third_protocol.get("protocol") != "third-party-authorization-interface-validation-v3"
        or len(third_protocol.get("harness_source_hashes", {})) != 10
        or third_sources.get("all_preflight_passed") is not True
        or len(post_rows) != 264 or len(registration_rows) != 264
        or len({item["case_id"] for item in post_rows}) != 264
        or len({item["case_id"] for item in registration_rows}) != 264
        or any(item.get("execution_error") or item.get("source_oracle_error") for item in post_rows + registration_rows)
    ):
        raise ValueError("third-party execution or row-integrity gate failed")
    for suffix, key in (
        ("TOOLS", "n_tools"), ("REGISTRATION", "n_registration_executions"),
        ("EVALUATION", "n_post_freeze_contexts"), ("REGISTRATION-FAILURES", "registration_descriptor_failures"),
        ("POST-FREEZE-FAILURES", "post_freeze_descriptor_failures"),
        ("EXACT", "descriptor_exact_match_rate"),
    ):
        add(rows, f"THIRD-PARTY-{suffix}", third[key], third_source, key,
            "Results / third-party validation", third_generator)
    for representation in ("tool_name", "raw_call", "state_aware_raw_call", "common_field", "typed_effect"):
        metric = indexed(third, "collision_metrics", "representation", representation)
        for suffix, key in (("MIXED", "mixed_cells"), ("PAIRS", "separating_pairs")):
            add(rows, f"THIRD-PARTY-{representation.upper()}-{suffix}", metric[key], third_source,
                f"collision_metrics[representation={representation}].{key}",
                "Results / third-party validation", third_generator)
    require_table_snippets(
        "table_third_party_validation.tex",
        ["Tool name & 11 & 11 & 1,552", "Raw call & 155 & 5 & 100",
         "State-aware request & 161 & 0 & 0", "Common fields & 126 & 12 & 200",
         "Typed effects & 138 & 0 & 0"],
    )
    for representation in ("state_aware_raw_call", "typed_effect"):
        metric = indexed(third, "authorization_metrics", "representation", representation)
        for suffix, key in (("COVERAGE", "coverage"), ("EXACT", "decision_accuracy")):
            add(rows, f"THIRD-PARTY-{representation.upper()}-{suffix}", metric[key], third_source,
                f"authorization_metrics[representation={representation}].{key}",
                "Results / third-party validation", third_generator)

    economy_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "authorization-interface-economy/interface_economy_report.json"
    )
    economy_protocol_source = (
        "experiments/human-authority-and-causal-validation/evaluation/"
        "authorization-interface-economy/protocol_manifest.json"
    )
    economy_generator = "shared/compatibility/scripts/run_authorization_interface_economy_audit.py"
    economy = read_json(economy_source)
    economy_protocol = read_json(economy_protocol_source)
    economy_metrics = economy.get("metrics", [])
    if (
        economy.get("status") != "passed" or economy.get("all_outcomes_retained") is not True
        or economy_protocol.get("timed_batches") != 30 or len(economy_metrics) != 4
        or {(item["domain"], item["interface"]) for item in economy_metrics} != {
            ("explicit_authority_1024", "typed_effect"),
            ("explicit_authority_1024", "state_aware_request"),
            ("third_party_mcp_264", "typed_effect"),
            ("third_party_mcp_264", "state_aware_request"),
        }
        or any(item["mixed_cells"] != 0 or item["decision_agreement"] != 1.0 for item in economy_metrics)
        or any(item["timing"]["end_to_end"]["timed_batches"] != 30 for item in economy_metrics)
    ):
        raise ValueError("authorization-interface economy audit incomplete")
    for relative, expected in economy_protocol.get("source_hashes", {}).items():
        path = ROOT / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"economy audit source drift: {relative}")
    for item in economy_metrics:
        prefix = f"ECONOMY-{item['domain'].upper()}-{item['interface'].upper()}"
        for suffix, value, key in (
            ("MIXED", item["mixed_cells"], "mixed_cells"),
            ("OVERPARTITION", item["overpartition_pairs"], "overpartition_pairs"),
            ("STATE-BYTES", item["raw_trusted_state_bytes"]["median"], "raw_trusted_state_bytes.median"),
            ("AST-STATEMENTS", item["runtime_code"]["ast_statements"], "runtime_code.ast_statements"),
            ("DECISION-AGREEMENT", item["decision_agreement"], "decision_agreement"),
            ("MEDIAN-LATENCY-US", item["timing"]["end_to_end"]["median"], "timing.end_to_end.median"),
        ):
            add(rows, f"{prefix}-{suffix}", value, economy_source,
                f"metrics[domain={item['domain']},interface={item['interface']}].{key}",
                "Results and Appendix / interface economy", economy_generator)
    economy_index = {(item["domain"], item["interface"]): item for item in economy_metrics}
    e_auth_typed = economy_index[("explicit_authority_1024", "typed_effect")]
    e_auth_state = economy_index[("explicit_authority_1024", "state_aware_request")]
    e_mcp_typed = economy_index[("third_party_mcp_264", "typed_effect")]
    e_mcp_state = economy_index[("third_party_mcp_264", "state_aware_request")]
    require_table_snippets(
        "table_interface_economy.tex",
        [
            f"Explicit authority (1,024) & Typed effect & 297 & 0 & 241 & 0 & 132 & {e_auth_typed['timing']['end_to_end']['median']:.1f}",
            f"& State-aware request & 669 & 3,252 & 537 & 9 & 143 & {e_auth_state['timing']['end_to_end']['median']:.1f}",
            f"Third-party MCP (264) & Typed effect & 138 & 0 & 203 & 0 & 102 & {e_mcp_typed['timing']['end_to_end']['median']:.1f}",
            f"& State-aware request & 161 & 90 & 271 & 4 & 83 & {e_mcp_state['timing']['end_to_end']['median']:.1f}",
        ],
    )

    native_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "native-delta-mechanical-validation/native_delta_validation_report.json"
    )
    native_rows_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "native-delta-mechanical-validation/native_decision_rows.jsonl"
    )
    mutant_rows_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "native-delta-mechanical-validation/mutant_results.jsonl"
    )
    native_generator = "shared/compatibility/scripts/run_native_delta_mechanical_validation.py"
    native = read_json(native_source)
    native_protocol = read_json(
        "experiments/human-authority-and-causal-validation/evaluation/"
        "native-delta-mechanical-validation/protocol_manifest.json"
    )
    mutation_manifest_payload = read_json(
        "experiments/human-authority-and-causal-validation/evaluation/"
        "native-delta-mechanical-validation/mutation_manifest.json"
    )
    native_rows = read_jsonl(native_rows_source)
    mutant_rows = read_jsonl(mutant_rows_source)
    mutation_manifest = mutation_manifest_payload.get("mutants", [])
    mutation_hash = hashlib.sha256(
        json.dumps(mutation_manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    if (
        native.get("status") != "passed" or native.get("all_rows_retained") is not True
        or native.get("protocol_hash") != native_protocol.get("protocol_hash")
        or mutation_manifest_payload.get("sha256") != mutation_hash
        or native_protocol.get("mutation_manifest_sha256") != mutation_hash
        or native.get("registration_contexts") != 264 or native.get("evaluation_contexts") != 264
        or native.get("registration_decision_agreement") != 1.0
        or native.get("evaluation_decision_agreement") != 1.0
        or native.get("compile_failures") != 0 or any(native.get("mechanical_isolation", {}).values())
        or len(native_rows) != 528 or len({item["case_id"] + ":" + item["phase"] for item in native_rows}) != 528
        or not all(item["decision_match"] for item in native_rows)
        or len(mutant_rows) != native.get("n_mutants")
        or {item["mutant_id"] for item in mutation_manifest} != {item["mutant_id"] for item in mutant_rows}
        or len({item["mutant_id"] for item in mutant_rows}) != len(mutant_rows)
        or sum(native.get("mutation_outcomes", {}).values()) != len(mutant_rows)
    ):
        raise ValueError("native-delta mechanical validation incomplete")
    for relative, expected in native_protocol.get("source_hashes", {}).items():
        path = ROOT / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"native-delta source drift: {relative}")
    for suffix, value, key in (
        ("REGISTRATION", native["registration_contexts"], "registration_contexts"),
        ("EVALUATION", native["evaluation_contexts"], "evaluation_contexts"),
        ("REGISTRATION-AGREEMENT", native["registration_decision_agreement"], "registration_decision_agreement"),
        ("EVALUATION-AGREEMENT", native["evaluation_decision_agreement"], "evaluation_decision_agreement"),
        ("COMPILE-FAILURES", native["compile_failures"], "compile_failures"),
        ("MUTANTS", native["n_mutants"], "n_mutants"),
        ("KILLED-REGISTRATION", native["mutation_outcomes"]["killed_registration"], "mutation_outcomes.killed_registration"),
        ("ESCAPED-HELDOUT", native["mutation_outcomes"]["escaped_to_heldout"], "mutation_outcomes.escaped_to_heldout"),
        ("EQUIVALENT-FROZEN", native["mutation_outcomes"]["equivalent_in_frozen_domain"], "mutation_outcomes.equivalent_in_frozen_domain"),
    ):
        add(rows, f"NATIVE-DELTA-{suffix}", value, native_source, key,
            "Results and Appendix / native-delta validation", native_generator)


def add_small_runtime_case_study_claims(
    rows: list[dict[str, Any]], payload: dict[str, Any], source: str, generator: str
) -> None:
    rows_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "small-typed-effect-runtime-case-study/runtime_trajectories.jsonl"
    )
    trajectories = read_jsonl(rows_source)
    protocol = read_json(
        "experiments/human-authority-and-causal-validation/evaluation/"
        "small-typed-effect-runtime-case-study/protocol_manifest.json"
    )
    if (
        payload.get("status") != "passed" or payload.get("n_cases") != 30 or len(trajectories) != 30
        or protocol.get("protocol") != "small-typed-effect-runtime-case-study-v2"
        or protocol.get("n_cases") != 30 or protocol.get("runtime_llm_calls") != 0
        or len(protocol.get("harness_source_hashes", {})) != 4
        or len({item["case_id"] for item in trajectories}) != 30
        or payload.get("check_use_failures") != 0 or payload.get("reconciliation_failures") != 0
        or any(item.get("executed_call") is not None and item.get("checked_call") != item.get("executed_call") for item in trajectories)
    ):
        raise ValueError("small runtime case study failed row-level integrity checks")
    for suffix, value, key in (
        ("CASES", payload["n_cases"], "n_cases"),
        ("COMMITS", payload["n_committed"], "n_committed"),
        ("PARSE-FAILURES", payload["parse_failures"], "parse_failures"),
        ("CHECK-USE-FAILURES", payload["check_use_failures"], "check_use_failures"),
        ("RECONCILIATION-FAILURES", payload["reconciliation_failures"], "reconciliation_failures"),
        ("ALLOW", payload["decision_counts"].get("ALLOW", 0), "decision_counts.ALLOW"),
        ("DENY", payload["decision_counts"].get("DENY", 0), "decision_counts.DENY"),
        ("ABSTAIN", payload["decision_counts"].get("ABSTAIN", 0), "decision_counts.ABSTAIN"),
    ):
        add(rows, f"SMALL-RUNTIME-{suffix}", value, source, key,
            "Results / integration case study", generator)


def pending_claims(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    required = [
        (
            "deepseek_repeated_benign",
            "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/deepseek_benign_interleaved_results.json",
            "finalize_deepseek_benign_interleaved.py",
        ),
        (
            "qwen32_matched_full",
            "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/qwen32_matched_results.json",
            "finalize_qwen32_matched.py",
        ),
        (
            "deepseek_locked_heldout",
            "experiments/adaptive-injection-benchmark/results/usenix-heldout-public-families/results.json",
            "run_deepseek_heldout.py",
        ),
        (
            "agentlab_c1f_transfer",
            "analysis/results/e79_agentlab_saved_transfer_current_pair_results.json",
            "run_e79_agentlab_c1f_pn_qwen32_queue.py",
        ),
        (
            "current_c1f_closed_loop_four_view",
            "experiments/security-analysis-ablation-and-overhead/results/"
            "c1f-closed-loop-four-view/closed-loop-four-view-report.json",
            "run_c1f_closed_loop_four_view_extension.py",
        ),
        (
            "current_c1f_bounded_adaptive",
            "experiments/adaptive-injection-benchmark/results/"
            "bounded-public-family-search-current-c1f/results.json",
            "run_current_c1f_bounded_adaptive.py",
        ),
        (
            "current_c1f_raw_field_attribution",
            "experiments/security-analysis-ablation-and-overhead/results/"
            "c1f-raw-field-attribution/raw-field-attribution-report.json",
            "run_c1f_raw_field_attribution.py",
        ),
        (
            "current_c1f_qwen32_strong_baselines",
            "experiments/unified-agent-security-baselines/results/"
            "current-c1f-strong-baseline-rerun/results.json",
            "run_current_c1f_qwen32_strong_baseline_rerun.py",
        ),
        (
            "toolsandbox_concrete_atom_authorizer",
            "experiments/human-authority-and-causal-validation/results/"
            "concrete-atom-authorizer-mechanism/concrete-atom-authorizer-report.json",
            "run_toolsandbox_concrete_atom_authorizer.py",
        ),
        (
            "small_typed_effect_runtime_case_study",
            "experiments/human-authority-and-causal-validation/results/"
            "small-typed-effect-runtime-case-study/runtime_case_study_report.json",
            "shared/compatibility/scripts/run_small_typed_effect_runtime_case_study.py",
        ),
    ]
    pending = []
    for name, source, generator in required:
        path = ROOT / source
        if not path.exists():
            pending.append({"artifact": name, "source": source, "reason": "missing"})
            continue
        payload = read_json(source)
        if payload.get("status") != "passed":
            pending.append({"artifact": name, "source": source, "reason": f"status={payload.get('status')}"})
            continue
        if name == "deepseek_repeated_benign":
            add_deepseek_repeated_claims(rows, payload, source, generator)
        elif name == "qwen32_matched_full":
            add_qwen_claims(rows, payload, source, generator)
        elif name == "deepseek_locked_heldout":
            add_heldout_claims(rows, payload, source, generator)
        elif name == "agentlab_c1f_transfer":
            add_agentlab_claims(rows, payload, source, generator)
        elif name == "current_c1f_closed_loop_four_view":
            add_four_view_claims(rows, payload, source, generator)
        elif name == "current_c1f_bounded_adaptive":
            add_bounded_adaptive_claims(rows, payload, source, generator)
        elif name == "current_c1f_raw_field_attribution":
            add_raw_field_attribution_claims(rows, payload, source, generator)
        elif name == "current_c1f_qwen32_strong_baselines":
            add_current_strong_baseline_claims(rows, payload, source, generator)
        elif name == "toolsandbox_concrete_atom_authorizer":
            add_concrete_atom_authorizer_claims(rows, payload, source, generator)
        elif name == "small_typed_effect_runtime_case_study":
            add_small_runtime_case_study_claims(rows, payload, source, generator)
        else:
            raise AssertionError(name)
    return pending


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    rows: list[dict[str, Any]] = []
    fixed_claims(rows)
    add_new_interface_validation_claims(rows)
    pending = pending_claims(rows)
    claim_ids = [row["claim_id"] for row in rows]
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("duplicate claim IDs in active reproduction ledger")
    if not pending and len(rows) != 360:
        raise ValueError(f"complete reproduction ledger must contain 360 rows, observed {len(rows)}")
    status = "passed" if not pending else "pending_required_artifacts"
    payload = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_paper": "paper/current-usenix/main.tex",
        "n_claim_rows": len(rows),
        "rows": rows,
        "pending": pending,
        "claim_boundary": "Executable falsification and bounded conformance of authorization observation interfaces, plus a provenance-origin integration case study.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "main_claims.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fields = ["claim_id", "paper_location", "value", "numerator", "denominator", "source", "key", "generator", "status"]
    with (OUT / "main_claims.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Active USENIX Main-Claim Reproduction", "", f"Status: `{status}`.", "", "| Claim | Value | Source |", "|---|---:|---|"]
    lines.extend(f"| `{row['claim_id']}` | {row['value']} | `{row['source']}::{row['key']}` |" for row in rows)
    if pending:
        lines.extend(["", "## Pending", ""])
        lines.extend(f"- `{row['artifact']}`: {row['reason']} at `{row['source']}`." for row in pending)
    lines.append("")
    (OUT / "main_claims.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "reproduction_status.json").write_text(
        json.dumps({"status": status, "n_claim_rows": len(rows), "pending": pending}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "n_claim_rows": len(rows), "pending": pending}, indent=2))
    if pending and not args.allow_pending:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
