#!/usr/bin/env python3
"""Regenerate the evidence rows for claims currently admitted to the PDF."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
OUTPUT = PAPER / "reproduction"


def read_json(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {relative}")
    return value


def resolve(value: Any, key: str) -> Any:
    current = value
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"missing key {key!r} at {part!r}")
        current = current[part]
    return current


def add(
    rows: list[dict[str, Any]],
    claim_id: str,
    metric: str,
    value: Any,
    source: str,
    key: str,
    paper_location: str,
) -> None:
    rows.append(
        {
            "claim_id": claim_id,
            "metric": metric,
            "value": value,
            "source": source,
            "key": key,
            "paper_location": paper_location,
            "status": "verified",
        }
    )


def main() -> int:
    rows: list[dict[str, Any]] = []

    e47_source = (
        "experiments/binding-failure-and-granularity/results/"
        "cross-method-binding-stress/"
        "tool-effect-fragmentation-capability-matrix-phase6.json"
    )
    e47 = read_json(e47_source)
    e47_rows = {row["method"]: row for row in e47["main_matrix"]}
    e47_methods = {
        "TOOL": "tool_name_rule_proxy",
        "QWEN": "local_qwen_self_audit",
        "TSGUARD": "ts_guard_official_counterfactual_stress",
        "SAFIRON": "safiron_official_counterfactual_stress",
    }
    for short, method_id in e47_methods.items():
        row = e47_rows[method_id]
        for metric in (
            "effect_sensitivity",
            "authorization_sensitivity",
            "resource_awareness",
            "unsafe_pre_allow",
            "safe_false_deny",
        ):
            add(
                rows,
                f"E47-{short}-{metric.upper()}",
                metric,
                row[metric],
                e47_source,
                f"main_matrix[method={method_id}].{metric}",
                "Results / controlled problem characterization table",
            )
    for method_id in (
        "ts_guard_official_counterfactual_stress",
        "safiron_official_counterfactual_stress",
    ):
        if e47_rows[method_id]["claim_scope"] != "original_method_custom_stress":
            raise ValueError(f"E47 {method_id} lost its custom-stress claim boundary")

    e48_source = (
        "experiments/binding-failure-and-granularity/results/"
        "effect-resource-tuple-guard/tuple-guard-results.json"
    )
    e48 = read_json(e48_source)
    if e48["manifest"]["n_rows"] != 822 or e48["manifest"]["n_pairs"] != 6840:
        raise ValueError("E48 row or relation count changed")
    if e48["manifest"]["deployable_input_leakage_violations"]:
        raise ValueError("E48 deployable input leakage violations are nonzero")
    e48_overall = e48["methods"]["effect_binding_guard_full"]["overall"]
    for metric in ("unsafe_pre_allow", "safe_false_deny", "coverage"):
        add(
            rows,
            f"E48-FULL-{metric.upper()}",
            metric,
            e48_overall[metric]["rate"],
            e48_source,
            f"methods.effect_binding_guard_full.overall.{metric}.rate",
            "Experimental Setup / Results / controlled problem characterization table",
        )
    e48_pair = e48["methods"]["effect_binding_guard_full"]["pair_metrics"][
        "pair_relation_accuracy"
    ]
    if e48_pair["n_groups"] != 30:
        raise ValueError("E48 pairwise statistical unit changed")
    add(
        rows,
        "E48-PAIR-RELATION",
        "group_bootstrap_pair_relation_accuracy",
        e48_pair["rate"],
        e48_source,
        "methods.effect_binding_guard_full.pair_metrics.pair_relation_accuracy.rate",
        "Experimental Setup",
    )

    e50_source = (
        "experiments/binding-failure-and-granularity/results/"
        "hard-guard-granularity-stress/hard-guard-robustness-results.json"
    )
    e50 = read_json(e50_source)
    if not all(e50["acceptance_gates"].values()):
        raise ValueError("one or more E50 acceptance gates failed")
    if not e50["leakage_audit"]["leakage_free"]:
        raise ValueError("E50 leakage audit failed")
    e50_variants = {
        "RA-FULL": (
            "resource_authorization_stress",
            "effect_binding_guard_full",
        ),
        "RA-NO-RESOURCE": (
            "resource_authorization_stress",
            "full_without_resource_match",
        ),
        "RA-NO-AUTH": (
            "resource_authorization_stress",
            "full_without_authorization_match",
        ),
        "PROVENANCE-FULL": (
            "control_provenance_stress",
            "effect_binding_guard_full",
        ),
    }
    for short, (stress, method) in e50_variants.items():
        overall = e50[stress]["methods"][method]["overall"]
        expected_rows = 240 if stress == "resource_authorization_stress" else 336
        if overall["n_rows"] != expected_rows:
            raise ValueError(f"E50 {short} row count changed")
        for metric in ("unsafe_pre_allow", "safe_false_deny", "coverage"):
            add(
                rows,
                f"E50-{short}-{metric.upper()}",
                metric,
                overall[metric]["rate"],
                e50_source,
                f"{stress}.methods.{method}.overall.{metric}.rate",
                "Experimental Setup / Results / controlled problem characterization table",
            )
    for axis, expected in (
        ("near_alias_resource", (20, 24)),
        ("out_of_scope_resource", (20, 24)),
        ("same_resource_different_effect", (6, 24)),
        ("authorization_missing", (0, 24)),
        ("commit_not_authorized", (0, 24)),
    ):
        metric = e50["resource_authorization_stress"]["by_axis"][axis][
            "effect_binding_guard_full"
        ]["overall"]["unsafe_pre_allow"]
        if (metric["successes"], metric["total"]) != expected:
            raise ValueError(f"E50 {axis} unsafe-pre-allow count changed")
        add(
            rows,
            f"E50-{axis.upper()}-UPA",
            "unsafe_pre_allow_count",
            f"{metric['successes']}/{metric['total']}",
            e50_source,
            (
                f"resource_authorization_stress.by_axis.{axis}."
                "effect_binding_guard_full.overall.unsafe_pre_allow"
            ),
            "Results",
        )

    e78_source = "analysis/results/e78_capacity_matched_comparison.json"
    e78 = read_json(e78_source)
    if e78["status"] != "passed_with_non_evaluable_rows":
        raise ValueError("E78 capacity-matched comparison status changed")
    if e78["targeted_results"] != 60 or e78["targeted_non_evaluable"] != 9:
        raise ValueError("E78 targeted result accounting changed")
    e78_methods = {row["method_id"]: row for row in e78["metrics"]}
    method_ids = {
        "NOGUARD": "agentdojo_live_local_no_guard",
        "MELON": "agentdojo_live_melon_local",
        "OURS": "agentdojo_live_ours_e77_effect_diff_runtime",
        "SANDWICH": "agentdojo_live_prompt_sandwiching",
        "PROMPTARMOR": "agentdojo_live_promptarmor_local",
        "SPOTLIGHT": "agentdojo_live_spotlighting_with_delimiting",
    }
    metrics = {
        "BU": "benign_utility_rate",
        "UA": "attack_utility_rate",
        "ASR": "attack_success_rate",
    }
    for short, method_id in method_ids.items():
        row = e78_methods[method_id]
        if row["n_total"] != 726:
            raise ValueError(f"E78 {method_id} does not cover 726 rows")
        for metric_short, key in metrics.items():
            add(
                rows,
                f"E78-{short}-{metric_short}",
                key,
                row[key],
                e78_source,
                f"metrics[method_id={method_id}].{key}",
                "Abstract / Results / common-checkpoint baseline table",
            )
        add(
            rows,
            f"E78-{short}-BENIGN-EVALUABLE",
            "n_benign_evaluable",
            row["n_benign_evaluable"],
            e78_source,
            f"metrics[method_id={method_id}].n_benign_evaluable",
            "Baseline table / Limitations",
        )
        add(
            rows,
            f"E78-{short}-ATTACK-EVALUABLE",
            "n_attack_evaluable",
            row["n_attack_evaluable"],
            e78_source,
            f"metrics[method_id={method_id}].n_attack_evaluable",
            "Baseline table / Limitations",
        )
    add(
        rows,
        "E78-NON-EVALUABLE",
        "targeted_non_evaluable",
        e78["targeted_non_evaluable"],
        e78_source,
        "targeted_non_evaluable",
        "Experimental Setup / Results / Limitations",
    )

    e78_stats_source = "analysis/results/e78_capacity_matched_statistics.json"
    e78_stats = read_json(e78_stats_source)["comparisons"][
        "agentdojo_live_ours_e77_effect_diff_runtime"
    ]
    for metric, short in (
        ("attack_success", "ASR"),
        ("benign_utility", "BU"),
        ("attack_utility", "UA"),
    ):
        comparison = e78_stats[metric]
        add(
            rows,
            f"E78-OURS-{short}-N-PAIRED",
            "n_paired",
            comparison["n_paired"],
            e78_stats_source,
            (
                "comparisons.agentdojo_live_ours_e77_effect_diff_runtime."
                f"{metric}.n_paired"
            ),
            "Results",
        )
        for key in (
            "no_guard_successes",
            "method_successes",
            "holm_adjusted_p",
        ):
            add(
                rows,
                f"E78-OURS-{short}-{key}".upper(),
                key,
                comparison[key],
                e78_stats_source,
                (
                    "comparisons.agentdojo_live_ours_e77_effect_diff_runtime."
                    f"{metric}.{key}"
                ),
                "Abstract / Introduction / Results",
            )
        add(
            rows,
            f"E78-OURS-{short}-DELTA",
            f"{metric}_difference",
            comparison["paired_bootstrap"][
                "difference_method_minus_no_guard"
            ],
            e78_stats_source,
            (
                "comparisons.agentdojo_live_ours_e77_effect_diff_runtime."
                f"{metric}.paired_bootstrap.difference_method_minus_no_guard"
            ),
            "Results",
        )

    attribution_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "representation-closed-loop-attribution/"
        "closed-loop-attribution-report.json"
    )
    attribution = read_json(attribution_source)
    if attribution["status"] != "passed":
        raise ValueError("closed-loop attribution did not pass")
    attribution_rows = {
        row["variant"]: row for row in attribution["aggregates"]
    }
    for short, variant in (
        ("ATOM", "atom_field"),
        ("CALL", "tool_call"),
    ):
        row = attribution_rows[variant]
        if row["n_cases"] != 321:
            raise ValueError("closed-loop attribution denominator changed")
        for key in (
            "benign_utility",
            "attack_utility",
            "attack_successes",
            "attack_success_rate",
        ):
            add(
                rows,
                f"ATTRIBUTION-{short}-{key}".upper(),
                key,
                row[key],
                attribution_source,
                f"aggregates[variant={variant}].{key}",
                "Results / granularity-transfer table",
            )

    e79_sources = {
        "NOGUARD": (
            "experiments/long-horizon-transfer/results/"
            "long-horizon-cross-environment-transfer/"
            "agentlab-saved-transfer-no-guard-results.json"
        ),
        "OURS": (
            "experiments/long-horizon-transfer/results/"
            "long-horizon-cross-environment-transfer/"
            "agentlab-saved-transfer-e77-results.json"
        ),
    }
    for short, source in e79_sources.items():
        payload = read_json(source)
        if payload["status"] != "passed" or payload["metrics"]["n"] != 303:
            raise ValueError(f"E79 {short} result is not final")
        for key in (
            "attack_successes",
            "attack_success_rate",
            "utility_successes",
            "utility_rate",
        ):
            add(
                rows,
                f"E79-{short}-{key}".upper(),
                key,
                payload["metrics"][key],
                source,
                f"metrics.{key}",
                "Abstract / Introduction / Results / transfer table",
            )
        if short == "OURS":
            mediation = payload["precommit_mediation"]
            if (
                mediation["executed_tool_result_calls"],
                mediation["precommit_checks"],
                mediation["signature_multiset_exact_match"],
            ) != (1439, 1439, True):
                raise ValueError("E79 mediation accounting changed")
            add(
                rows,
                "E79-OURS-PRECOMMIT-EXACT",
                "signature_multiset_exact_match",
                mediation["signature_multiset_exact_match"],
                source,
                "precommit_mediation.signature_multiset_exact_match",
                "Abstract / Results",
            )

    overhead_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "runtime-overhead-measurement/observed-trajectory-overhead-and-recovery.json"
    )
    overhead = read_json(overhead_source)
    if overhead["status"] != "passed_with_observational_timing_caveat":
        raise ValueError("observed trajectory overhead report did not pass")
    if overhead["protocol"]["paired_case_keys"] != 726:
        raise ValueError("observed trajectory overhead does not cover 726 paired keys")
    overhead_expected = {
        "duration.all.no_guard.median_seconds": 53.272162079811096,
        "duration.all.ours.median_seconds": 85.54312837123871,
        "duration.all.paired.median_ratio": 1.3604710145852188,
        "recovery.precommit_checks": 2930,
        "recovery.revision_llm_calls": 738,
        "recovery.checks_transitioned_to_allow": 32,
    }
    for key, expected in overhead_expected.items():
        observed = resolve(overhead, key)
        if observed != expected:
            raise ValueError(
                f"observed trajectory/recovery metric changed at {key}: "
                f"expected {expected!r}, observed {observed!r}"
            )
        add(
            rows,
            f"E78-OBSERVED-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            observed,
            overhead_source,
            key,
            "Experimental Setup / Results",
        )

    e84_review_source = (
        "experiments/human-authority-and-causal-validation/evaluation/"
        "authority-manifest-human-review/summary.json"
    )
    e84_review = read_json(e84_review_source)
    add(rows, "E84-REVIEWED", "reviewed_rows", e84_review["reviewed_rows"], e84_review_source, "reviewed_rows", "Experimental Setup / authority-burden table")
    add(rows, "E84-ACCEPTED", "compiled_trusted_manifests", e84_review["compiled_trusted_manifests"], e84_review_source, "compiled_trusted_manifests", "Experimental Setup / authority-burden table")
    add(rows, "E84-BINDING-APPROVE", "binding_approvals", e84_review["binding_decision_counts"]["APPROVE"], e84_review_source, "binding_decision_counts.APPROVE", "authority-burden table")
    add(rows, "E84-BINDING-REJECT", "binding_rejections", e84_review["binding_decision_counts"]["REJECT"], e84_review_source, "binding_decision_counts.REJECT", "authority-burden table")

    e84_repair_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "runtime-mechanism-ablation/e84-resolver-repair-validation.json"
    )
    e84_repair = read_json(e84_repair_source)
    add(rows, "E84-RUNTIME-READY", "runtime_ready_manifests", e84_repair["runtime_ready_trusted_manifests_after_full_review"], e84_repair_source, "runtime_ready_trusted_manifests_after_full_review", "Experimental Setup / Results / authority-burden table")
    for decision in ("APPROVE", "REJECT"):
        add(rows, f"E84-RESOLVER-{decision}", f"resolver_{decision.lower()}", e84_repair["decision_counts"][decision], e84_repair_source, f"decision_counts.{decision}", "Results / authority-burden table")

    e84_result_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "runtime-mechanism-ablation/"
        "e84-qwen32-reviewed-authority-strong-baselines-full-results.json"
    )
    e84_payload = read_json(e84_result_source)
    e84_result = e84_payload["metrics"]
    for short, method_id in (
        ("NOGUARD", "agentdojo_live_local_no_guard"),
        ("SANDWICH", "agentdojo_live_prompt_sandwiching"),
        ("PROMPTARMOR", "agentdojo_live_promptarmor_local"),
        ("OURS", "agentdojo_live_ours_e84_reviewed_authority"),
    ):
        row = e84_result[method_id]
        if row["n_total"] != 195:
            raise ValueError(f"E84 {method_id} does not cover 195 rows")
        for metric_short, key in metrics.items():
            result_key = (
                "attack_user_utility_rate"
                if key == "attack_utility_rate"
                else key
            )
            add(
                rows,
                f"E84-{short}-{metric_short}",
                result_key,
                row[result_key],
                e84_result_source,
                f"metrics.{method_id}.{result_key}",
                "Results / reviewed-authority table",
            )
    e84_stats = e84_payload["paired_statistics"]["comparisons"][
        "agentdojo_live_ours_e84_reviewed_authority"
    ]
    for metric, short in (
        ("attack_success", "ASR"),
        ("benign_utility", "BU"),
        ("attack_utility", "UA"),
    ):
        add(
            rows,
            f"E84-OURS-{short}-DELTA",
            f"{metric}_difference",
            e84_stats[metric]["paired_bootstrap"]["difference_method_minus_reference"],
            e84_result_source,
            (
                "paired_statistics.comparisons."
                f"agentdojo_live_ours_e84_reviewed_authority.{metric}."
                "paired_bootstrap.difference_method_minus_reference"
            ),
            "Results",
        )
        add(
            rows,
            f"E84-OURS-{short}-HOLM-P",
            f"{metric}_holm_adjusted_p",
            e84_stats[metric]["holm_adjusted_p"],
            e84_result_source,
            (
                "paired_statistics.comparisons."
                f"agentdojo_live_ours_e84_reviewed_authority.{metric}."
                "holm_adjusted_p"
            ),
            "Results",
        )
    add(
        rows,
        "E84-PRECOMMIT-CHECKS",
        "precommit_checks",
        e84_payload["runtime_audit"]["precommit_checks"],
        e84_result_source,
        "runtime_audit.precommit_checks",
        "Abstract / Results",
    )
    add(
        rows,
        "E84-BLOCKED-EXECUTED",
        "blocked_calls_executed",
        e84_payload["runtime_audit"]["blocked_calls_executed"],
        e84_result_source,
        "runtime_audit.blocked_calls_executed",
        "Abstract / Results",
    )
    residual = e84_payload["residual_e84_official_attack_successes"]
    if len(residual) != 1:
        raise ValueError(f"expected one E84 residual official attack success, observed {len(residual)}")
    for key in ("runtime_feedback_executed_false", "runtime_feedback_executed_true"):
        add(
            rows,
            f"E84-RESIDUAL-{key.upper()}",
            key,
            residual[0][key],
            e84_result_source,
            f"residual_e84_official_attack_successes[0].{key}",
            "Results",
        )

    joint_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "joint-effect-authority-diagnostic/four-cell-results.json"
    )
    joint = read_json(joint_source)
    if joint["status"] != "passed" or not all(joint["verification_gates"].values()):
        raise ValueError("joint effect-authority diagnostic did not pass")
    joint_expected = {
        "common_support_case_count": 180,
        "factorial_deltas_on_common_support.source_contract_minus_current_at_reviewed_authority": 0,
        "factorial_deltas_on_common_support.official_oracle_minus_reviewed_at_current_contract": 0,
        "authority_agreement_audit.same_fixed_trace_admissibility": 195,
        "authority_agreement_audit.official_oracle_admissible_successful_benign_traces": 19,
        "authority_agreement_audit.reviewed_authority_retained_official_admissible_benign_traces": 19,
        "authority_agreement_audit.utility_success_with_extra_unofficial_effect": 1,
        "successful_attack_scope_audit.blocked_by_reviewed_authority": 4,
        "successful_attack_scope_audit.with_privileged_calls": 4,
        "successful_attack_scope_audit.without_privileged_calls": 1,
    }
    for key, expected in joint_expected.items():
        observed = resolve(joint, key)
        if observed != expected:
            raise ValueError(
                f"joint effect-authority diagnostic changed at {key}: "
                f"expected {expected!r}, observed {observed!r}"
            )
        add(
            rows,
            f"JOINT-DIAGNOSTIC-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            observed,
            joint_source,
            key,
            "Results / Additional Results appendix",
        )

    utility_audit_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "benign-utility-causal-audit/benign-utility-causal-audit.json"
    )
    utility_audit = read_json(utility_audit_source)
    if utility_audit["status"] != "passed":
        raise ValueError("E84 benign utility causal audit did not pass")
    utility_audit_expected = {
        "discordant_case_count": 7,
        "official_utility_on_discordant_cases.net_e84_minus_no_guard": -5,
        "visible_answer_only_sensitivity_on_discordant_cases.net_e84_minus_no_guard": -3,
        "interpretation.net_gap_attributable_to_reasoning_sensitive_scoring": -2,
        "interpretation.visible_answer_model_variation_losses": 3,
        "direct_guard_denial_or_abstention_losses": 0,
    }
    for key, expected in utility_audit_expected.items():
        observed = resolve(utility_audit, key)
        if observed != expected:
            raise ValueError(
                f"E84 benign utility audit changed at {key}: "
                f"expected {expected!r}, observed {observed!r}"
            )
        add(
            rows,
            f"E84-UTILITY-AUDIT-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            observed,
            utility_audit_source,
            key,
            "Results / Limitations / Additional Results appendix",
        )

    headline_utility_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "headline-benign-utility-pathway-audit/"
        "headline-benign-utility-pathway-audit.json"
    )
    headline_utility = read_json(headline_utility_source)
    if headline_utility["status"] != "passed":
        raise ValueError("E78 headline benign-utility pathway audit did not pass")
    headline_utility_expected = {
        "overall.no_guard_successes": 63,
        "overall.ours_successes": 33,
        "overall.net_ours_minus_no_guard": -30,
        "feedback_stratum.cases": 47,
        "feedback_stratum.net_ours_minus_no_guard": -31,
        "no_feedback_stratum.cases": 50,
        "no_feedback_stratum.net_ours_minus_no_guard": 1,
        "discordant.losses": 37,
        "discordant.losses_with_runtime_feedback": 32,
        "runtime_feedback_loss_anatomy.plan_construction_cases": 16,
        "runtime_feedback_loss_anatomy.binding_or_evidence_cases": 22,
        "runtime_feedback_loss_anatomy.overlap_plan_and_binding_cases": 6,
        "literal_grounding_probe.resolver_check_count": 85,
        (
            "literal_grounding_probe."
            "loss_cases_with_a_resolver_value_seen_in_prior_tool_output"
        ): 12,
    }
    for key, expected in headline_utility_expected.items():
        observed = resolve(headline_utility, key)
        if observed != expected:
            raise ValueError(
                f"E78 headline benign-utility pathway audit changed at {key}: "
                f"expected {expected!r}, observed {observed!r}"
            )
        add(
            rows,
            f"E78-UTILITY-PATHWAY-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            observed,
            headline_utility_source,
            key,
            "Results / Limitations / Additional Results appendix",
        )

    source_relation_probe_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "headline-benign-utility-pathway-audit/"
        "source-relation-mechanism-probe.json"
    )
    source_relation_probe = read_json(source_relation_probe_source)
    if source_relation_probe["status"] != "passed":
        raise ValueError("E78 source-relation mechanism probe did not pass")
    source_relation_expected = {
        "cases.correct_source_unconstrained_fields.decision": "ALLOW",
        "cases.correct_source_semantic_fields.decision": "ALLOW",
        "cases.wrong_source_name.decision": "NEEDS_REPLAN",
        "cases.ambiguous_prior_result.decision": "NEEDS_REPLAN",
    }
    for key, expected in source_relation_expected.items():
        observed = resolve(source_relation_probe, key)
        if observed != expected:
            raise ValueError(
                f"E78 source-relation mechanism probe changed at {key}: "
                f"expected {expected!r}, observed {observed!r}"
            )
        add(
            rows,
            f"E78-SOURCE-RELATION-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            observed,
            source_relation_probe_source,
            key,
            "Additional Results appendix",
        )

    call_revision_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "headline-benign-utility-pathway-audit/"
        "call-revision-routing-v5-smoke.json"
    )
    call_revision = read_json(call_revision_source)
    call_revision_expected = {
        "status": "passed",
        "outcomes.benign_utility": False,
        "outcomes.attack_goal_achieved": False,
        "routing_check.call_revision_feedback_rows": 2,
        "routing_check.permission_plan_revision_rows_for_same_call": 0,
        "routing_check.runtime_llm_calls_for_call_only_mismatch": 0,
    }
    for key, expected in call_revision_expected.items():
        observed = resolve(call_revision, key)
        if observed != expected:
            raise ValueError(
                f"E78 call-revision smoke changed at {key}: "
                f"expected {expected!r}, observed {observed!r}"
            )
        add(
            rows,
            f"E78-CALL-REVISION-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            observed,
            call_revision_source,
            key,
            "Internal mechanism audit / future appendix",
        )

    relation_planner_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "headline-benign-utility-pathway-audit/"
        "registered-relation-planner-model-pilot.json"
    )
    relation_planner = read_json(relation_planner_source)
    relation_planner_expected = {
        "status": "passed",
        "parse_valid": True,
        "validation_passed": True,
        "expected_relations_selected": True,
        "model_calls": 1,
        "tool_executions": 0,
    }
    for key, expected in relation_planner_expected.items():
        observed = resolve(relation_planner, key)
        if observed != expected:
            raise ValueError(
                f"registered-relation planner pilot changed at {key}: "
                f"expected {expected!r}, observed {observed!r}"
            )
        add(
            rows,
            f"E78-RELATION-PLANNER-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            observed,
            relation_planner_source,
            key,
            "Internal mechanism audit / future appendix",
        )

    bounded_relation_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "headline-benign-utility-pathway-audit/"
        "bounded-relation-v8-end-to-end-smoke.json"
    )
    bounded_relation = read_json(bounded_relation_source)
    bounded_relation_expected = {
        "status": "passed",
        "outcomes.benign_utility": True,
        "outcomes.attack_goal_achieved": False,
        "benign_recovery.attempts": 2,
        "benign_recovery.final_decision": "ALLOW",
        "benign_recovery.final_execution_attempted": True,
        "benign_recovery.runtime_llm_calls_for_call_revision": 0,
        "projection_isolation.benign_registered_projection_values": 1,
        "projection_isolation.paired_attack_registered_projection_values": 0,
        "projection_isolation.paired_attack_send_money_execution_attempts": 0,
    }
    for key, expected in bounded_relation_expected.items():
        observed = resolve(bounded_relation, key)
        if observed != expected:
            raise ValueError(
                f"bounded-relation smoke changed at {key}: "
                f"expected {expected!r}, observed {observed!r}"
            )
        add(
            rows,
            f"E78-BOUNDED-RELATION-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            observed,
            bounded_relation_source,
            key,
            "Internal mechanism audit / future appendix",
        )

    relation_pilot_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "headline-benign-utility-pathway-audit/"
        "registered-relation-benign-pilot-v8.json"
    )
    relation_pilot = read_json(relation_pilot_source)
    relation_pilot_expected = {
        "status": "passed_fixed_denominator_outcomes_retained",
        "v8_outcomes.target.cases": 12,
        "v8_outcomes.target.utility_successes": 1,
        "v8_outcomes.target.utility_failures": 11,
        "v8_outcomes.target.errors": 0,
        "v8_outcomes.control.cases": 4,
        "v8_outcomes.control.utility_successes": 4,
        "v8_outcomes.control.errors": 0,
        "v8_outcomes.overall.cases": 16,
        "v8_outcomes.overall.utility_successes": 5,
        "v8_outcomes.overall.errors": 0,
        "runtime_audit.executed_non_allow_checks": 0,
        "failure_anatomy.runtime_relation_failure_case_count": 7,
        "failure_anatomy.plan_construction_failure_case_count": 4,
    }
    for key, expected in relation_pilot_expected.items():
        observed = resolve(relation_pilot, key)
        if observed != expected:
            raise ValueError(
                f"registered-relation benign pilot changed at {key}: "
                f"expected {expected!r}, observed {observed!r}"
            )
        add(
            rows,
            f"E78-RELATION-PILOT-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            observed,
            relation_pilot_source,
            key,
            "Internal mechanism audit / future appendix",
        )

    relation_gap_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "headline-benign-utility-pathway-audit/"
        "registered-relation-onboarding-gap-audit.json"
    )
    relation_gap = read_json(relation_gap_source)
    relation_gap_expected = {
        "status": "passed",
        "counts.target_cases": 12,
        "counts.exact_source_target_field_groups": 14,
        "counts.groups_observed_in_recovered_cases": 2,
        "counts.groups_observed_in_failed_cases": 12,
        "counts.relation_case_rows": 17,
        "counts.runtime_relation_failure_cases": 7,
        "counts.plan_construction_failure_cases": 4,
    }
    for key, expected in relation_gap_expected.items():
        observed = resolve(relation_gap, key)
        if observed != expected:
            raise ValueError(
                f"registered-relation onboarding audit changed at {key}: "
                f"expected {expected!r}, observed {observed!r}"
            )
        add(
            rows,
            f"E78-RELATION-GAP-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            observed,
            relation_gap_source,
            key,
            "Internal mechanism audit / future appendix",
        )

    full_benign_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "full-benign-runtime-guard-validation/full-benign-report.json"
    )
    full_benign = read_json(full_benign_source)
    expected_full_benign = {
        "status": "failed",
        "n_expected": 97,
        "n_observed": 97,
        "fixed_denominator_gate_passed": True,
        "utility_successes": 26,
        "precommit_checks": 426,
        "unsafe_unmanifested_effect_allows": 0,
        "utility_gate_minimum": 50,
        "utility_gate_passed": False,
        "official_labels_exposed_to_runtime": False,
        "human_review_claimed": False,
    }
    for key, expected in expected_full_benign.items():
        if full_benign[key] != expected:
            raise ValueError(
                f"full-benign result changed at {key}: "
                f"expected {expected!r}, observed {full_benign[key]!r}"
            )
        add(
            rows,
            f"FULL-BENIGN-{key.upper()}",
            key,
            full_benign[key],
            full_benign_source,
            key,
            "Results / Limitations",
        )
    for decision, expected in (("ALLOW", 270), ("ABSTAIN", 152), ("DENY", 4)):
        observed = full_benign["precommit_decision_counts"][decision]
        if observed != expected:
            raise ValueError(f"full-benign {decision} count changed")
        add(
            rows,
            f"FULL-BENIGN-{decision}",
            f"{decision.lower()}_checks",
            observed,
            full_benign_source,
            f"precommit_decision_counts.{decision}",
            "Results / Limitations",
        )
    add(
        rows,
        "FULL-BENIGN-UTILITY-RATE",
        "utility_rate",
        full_benign["utility_rate"],
        full_benign_source,
        "utility_rate",
        "Results / Limitations",
    )

    root_cause_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "full-benign-runtime-guard-validation/"
        "full-benign-abstain-root-cause.json"
    )
    root_cause = read_json(root_cause_source)
    if (
        root_cause["status"],
        root_cause["n_tasks"],
        root_cause["precommit_checks"],
    ) != ("passed", 97, 426):
        raise ValueError("full-benign root-cause audit status or denominator changed")
    reason_expected = {
        "authority_manifest_unavailable": 107,
        "resolver_value_unproven": 43,
        "security_field_unbound": 3,
        "tool_outside_bounded_plan": 2,
        "outside_exact_authority": 4,
    }
    for reason, expected in reason_expected.items():
        observed = root_cause["reason_family_check_incidence"][reason]
        if observed != expected:
            raise ValueError(f"full-benign root-cause count changed for {reason}")
        add(
            rows,
            f"FULL-BENIGN-ROOT-{reason.upper()}",
            f"{reason}_check_incidence",
            observed,
            root_cause_source,
            f"reason_family_check_incidence.{reason}",
            "Results / Limitations",
        )
    task_utility_expected = {
        "guard_successes": 26,
        "no_guard_successes": 64,
    }
    for key, expected in task_utility_expected.items():
        observed = root_cause["task_utility"][key]
        if observed != expected:
            raise ValueError(f"full-benign paired utility changed at {key}")
        add(
            rows,
            f"FULL-BENIGN-ROOT-{key.upper()}",
            key,
            observed,
            root_cause_source,
            f"task_utility.{key}",
            "Results / Limitations",
        )
    contingency_expected = {
        "guard_failure__no_guard_failure": 27,
        "guard_failure__no_guard_success": 44,
        "guard_success__no_guard_failure": 6,
        "guard_success__no_guard_success": 20,
    }
    for key, expected in contingency_expected.items():
        observed = root_cause["task_utility"]["paired_contingency"][key]
        if observed != expected:
            raise ValueError(f"full-benign contingency changed at {key}")
        add(
            rows,
            f"FULL-BENIGN-ROOT-{key.upper()}",
            key,
            observed,
            root_cause_source,
            f"task_utility.paired_contingency.{key}",
            "Results",
        )
    if any(root_cause["privacy_gate"].values()):
        raise ValueError("full-benign root-cause audit emitted sensitive content")
    for key, observed in root_cause["privacy_gate"].items():
        add(
            rows,
            f"FULL-BENIGN-PRIVACY-{key.upper()}",
            key,
            observed,
            root_cause_source,
            f"privacy_gate.{key}",
            "Artifact only",
        )

    e81_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "runtime-mechanism-ablation/"
        "e81-qwen32-runtime-ablation-full-results.json"
    )
    e81 = read_json(e81_source)
    if e81["status"] != "passed_with_nonapplicable_a13":
        raise ValueError(f"unexpected E81 status: {e81['status']}")
    for row_id, count in e81["row_case_counts"].items():
        if count != 195:
            raise ValueError(f"E81 {row_id} does not cover 195 rows")
    e81_metrics = {
        "BU": "benign_utility_rate",
        "UA": "attack_user_utility_rate",
        "ASR": "attack_success_rate",
    }
    for row_id in ("A0", "A1", "A2", "A7", "A9", "A11", "A12", "A13", "A15"):
        row = e81["metrics"][row_id]
        for metric_short, key in e81_metrics.items():
            add(
                rows,
                f"E81-{row_id}-{metric_short}",
                key,
                row[key],
                e81_source,
                f"metrics.{row_id}.{key}",
                "Results / runtime-mechanism ablation table",
            )
    for row_id, audit in e81["runtime_audit"].items():
        if audit["blocked_calls_executed"] != 0:
            raise ValueError(f"E81 {row_id} executed a blocked call")
        add(
            rows,
            f"E81-{row_id}-BLOCKED-EXECUTED",
            "blocked_calls_executed",
            audit["blocked_calls_executed"],
            e81_source,
            f"runtime_audit.{row_id}.blocked_calls_executed",
            "Results",
        )
    for row_id, metric in (
        ("A9", "attack_utility"),
        ("A11", "attack_success"),
        ("A12", "attack_utility"),
    ):
        comparison = e81["paired_statistics"]["comparisons"][row_id][metric]
        add(
            rows,
            f"E81-{row_id}-{metric.upper()}-DELTA",
            f"{metric}_difference",
            comparison["paired_bootstrap"]["difference_ablation_minus_a1"],
            e81_source,
            (
                f"paired_statistics.comparisons.{row_id}.{metric}."
                "paired_bootstrap.difference_ablation_minus_a1"
            ),
            "Results",
        )
        add(
            rows,
            f"E81-{row_id}-{metric.upper()}-CI95",
            f"{metric}_bootstrap_ci95",
            comparison["paired_bootstrap"]["ci95"],
            e81_source,
            (
                f"paired_statistics.comparisons.{row_id}.{metric}."
                "paired_bootstrap.ci95"
            ),
            "Results",
        )
        add(
            rows,
            f"E81-{row_id}-{metric.upper()}-HOLM-P",
            f"{metric}_holm_adjusted_p",
            comparison["holm_adjusted_p"],
            e81_source,
            (
                f"paired_statistics.comparisons.{row_id}.{metric}."
                "holm_adjusted_p"
            ),
            "Results",
        )
    a13 = e81["static_applicability_audit"]["rows"]["A13"]
    if a13["claim_eligible"] or a13["applicable_dynamic_security_defaults"] != 0:
        raise ValueError("E81 A13 must remain nonapplicable")
    add(
        rows,
        "E81-A13-APPLICABLE-DEFAULTS",
        "applicable_dynamic_security_defaults",
        a13["applicable_dynamic_security_defaults"],
        e81_source,
        (
            "static_applicability_audit.rows.A13."
            "applicable_dynamic_security_defaults"
        ),
        "Results / Limitations",
    )

    static_rows = [
        ("E80-O3-EXEC", "valid_calls_reaching_executor", 3173, "analysis/results/e80_e77_implementation_obligation_audit.json", "logs.valid_calls_reaching_executor", "Security Analysis / Results / obligation table"),
        ("E80-O3-CHECK", "official_checks", 3173, "analysis/results/e80_e77_implementation_obligation_audit.json", "precommit_audit.official_checks", "Security Analysis / Results / obligation table"),
        ("E80-EMITTED", "valid_structured_calls_emitted", 3235, "analysis/results/e80_e77_implementation_obligation_audit.json", "logs.valid_structured_calls_emitted", "Results"),
        ("E80-UNEXEC", "valid_calls_without_tool_result", 62, "analysis/results/e80_e77_implementation_obligation_audit.json", "logs.valid_calls_without_tool_result", "Results"),
        ("E85-PAIRS", "controlled_intervention_cases", 9, "analysis/results/e85_causal_mediation_report.json", "n_intervention_cases", "Experimental Setup / Security Analysis"),
        ("E85-CONTRACTS", "controlled_contract_variants", 6, "analysis/results/e85_causal_mediation_report.json", "n_contract_variants", "Experimental Setup / Security Analysis"),
        ("E82-BASE", "selected_base_attack_keys", 40, "evaluation/e82_adaptive_attacks/case_manifest_summary.json", "selected_base_attack_keys", "Evaluation Methodology"),
        ("E82-STRATEGIES", "adaptive_strategies", 12, "evaluation/e82_adaptive_attacks/case_manifest_summary.json", "adaptive_strategies", "Evaluation Methodology"),
        ("E82-PAIRS", "materialized_strategy_case_pairs", 480, "evaluation/e82_adaptive_attacks/case_manifest_summary.json", "materialized_strategy_case_pairs", "Evaluation Methodology"),
        ("E79-SAVED-N", "saved_attack_cases", 303, "evaluation/e79_long_horizon/agentlab_saved_attack_manifest.json", "n_cases", "Experimental Setup"),
        ("E83-MICRO-N", "measured_decisions", 36000, "analysis/results/e83_runtime_microbenchmark.json", "configurations*iterations_per_configuration", "Results"),
        ("E83-MICRO-LLM", "runtime_llm_calls", 0, "analysis/results/e83_runtime_microbenchmark.json", "correctness.runtime_llm_calls", "Results"),
    ]
    for values in static_rows:
        claim_id, _, expected, source, key, _ = values
        source_json = read_json(source)
        if key == "configurations*iterations_per_configuration":
            actual = (
                source_json["configurations"]
                * source_json["iterations_per_configuration"]
            )
        else:
            actual = resolve(source_json, key)
        if actual != expected:
            raise ValueError(
                f"{claim_id} source mismatch: expected {expected!r}, observed {actual!r}"
            )
        add(rows, *values)

    bounded_adaptive_source = (
        "experiments/adaptive-injection-benchmark/results/"
        "bounded-public-family-search/bounded-search-report.json"
    )
    bounded_adaptive = read_json(bounded_adaptive_source)
    if (
        bounded_adaptive["status"],
        bounded_adaptive["locked_cases"],
        bounded_adaptive["variant_rows"],
    ) != ("passed", 40, 320):
        raise ValueError("bounded adaptive search status or denominator changed")
    for key in ("locked_cases", "variant_rows"):
        add(
            rows,
            f"BOUNDED-ADAPTIVE-{key.upper()}",
            key,
            bounded_adaptive[key],
            bounded_adaptive_source,
            key,
            "Results / Limitations",
        )
    bounded_rows = {
        row["method"]: row for row in bounded_adaptive["search_metrics"]
    }
    bounded_expected = {
        "no_guard": {
            "n": 40,
            "attack_successes": 4,
            "attack_success_rate": 0.1,
            "terminal_user_utility_successes": 18,
            "terminal_user_utility_rate": 0.45,
            "evaluated_variants": 149,
        },
        "ours_e77_effect_diff_runtime": {
            "n": 40,
            "attack_successes": 1,
            "attack_success_rate": 0.025,
            "terminal_user_utility_successes": 12,
            "terminal_user_utility_rate": 0.3,
            "evaluated_variants": 160,
        },
    }
    for method, expected in bounded_expected.items():
        row = bounded_rows[method]
        for key, value in expected.items():
            if row[key] != value:
                raise ValueError(
                    f"bounded adaptive result changed for {method}/{key}"
                )
            add(
                rows,
                f"BOUNDED-ADAPTIVE-{method}-{key}".upper(),
                key,
                row[key],
                bounded_adaptive_source,
                f"search_metrics[method={method}].{key}",
                "Results / Limitations",
            )
    paired_expected = {
        "attack_success": {
            "reference_only": 4,
            "method_only": 1,
            "discordant_pairs": 5,
            "exact_mcnemar_two_sided_p": 0.375,
        },
        "terminal_user_utility": {
            "reference_only": 7,
            "method_only": 1,
            "discordant_pairs": 8,
            "exact_mcnemar_two_sided_p": 0.0703125,
        },
    }
    for metric, expected in paired_expected.items():
        for key, value in expected.items():
            observed = bounded_adaptive["paired_statistics"][metric][key]
            if observed != value:
                raise ValueError(
                    f"bounded adaptive paired statistic changed for {metric}/{key}"
                )
            add(
                rows,
                f"BOUNDED-ADAPTIVE-{metric}-{key}".upper(),
                key,
                observed,
                bounded_adaptive_source,
                f"paired_statistics.{metric}.{key}",
                "Results / Limitations",
            )

    e85_projection_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "causal-effect-projection-validation/"
        "agentdojo-projection-intervention-report.json"
    )
    e85_projection = read_json(e85_projection_source)
    if e85_projection["status"] != "passed_with_projection_gaps":
        raise ValueError("E85 source-grounded intervention status changed")
    for key, expected in (
        ("n_reviewed_tool_instances", 16),
        ("n_source_verified_tool_instances", 16),
        ("n_base_calls_executed", 16),
    ):
        if e85_projection[key] != expected:
            raise ValueError(f"E85 projection {key} changed")
        add(
            rows,
            f"E85-PROJECTION-{key.upper()}",
            key,
            e85_projection[key],
            e85_projection_source,
            key,
            "Experimental Setup / Results",
        )
    if e85_projection["source_integrity_errors"]:
        raise ValueError("E85 source integrity errors are nonempty")
    expected_aggregates = {
        "eight_field_projection": {
            "n_cases": 80,
            "n_passed": 65,
            "mediation_gaps": 15,
            "over_sensitive": 0,
            "unsupported": 0,
        },
        "typed_qualifier_projection": {
            "n_cases": 80,
            "n_passed": 80,
            "mediation_gaps": 0,
            "over_sensitive": 0,
            "unsupported": 0,
        },
    }
    for variant, expected in expected_aggregates.items():
        aggregate = e85_projection["aggregate_by_contract_variant"][variant]
        for key, value in expected.items():
            if aggregate[key] != value:
                raise ValueError(f"E85 {variant} {key} changed")
            add(
                rows,
                f"E85-{variant.upper()}-{key.upper()}",
                key,
                aggregate[key],
                e85_projection_source,
                f"aggregate_by_contract_variant.{variant}.{key}",
                "Experimental Setup / Results / Limitations",
            )

    collision_source = (
        "experiments/binding-failure-and-granularity/results/"
        "authorization-separating-collision-audit/collision-audit-report.json"
    )
    collision = read_json(collision_source)
    if collision["status"] != "passed" or collision["n_witness_cells"] != 288:
        raise ValueError("authorization collision audit status or witness count changed")
    collision_expected = {
        "E48-explicit-authority-subset": {
            "tool_name": (45, 96),
            "ideal_effect": (35, 48),
            "ideal_effect_resource": (0, 0),
            "rule_extracted_effect_resource": (30, 43),
            "full_guard_decision_representation": (14, 18),
        },
        "E50-repaired-resource-authorization": {
            "tool_name": (23, 72),
            "ideal_effect": (22, 45),
            "ideal_effect_resource": (0, 0),
            "rule_extracted_effect_resource": (8, 10),
            "full_guard_decision_representation": (8, 11),
        },
    }
    collision_rows = {
        (dataset["dataset"], row["representation_name"]): row
        for dataset in collision["datasets"]
        for row in dataset["representations"]
    }
    for dataset, representations in collision_expected.items():
        for representation, (mixed, lower_bound) in representations.items():
            row = collision_rows[(dataset, representation)]
            if (
                row["n_mixed_authorization_cells"],
                row["unit_cost_collision_lower_bound"],
            ) != (mixed, lower_bound):
                raise ValueError(
                    f"collision audit changed for {dataset}/{representation}"
                )
            for metric, value in (
                ("n_mixed_authorization_cells", mixed),
                ("unit_cost_collision_lower_bound", lower_bound),
            ):
                add(
                    rows,
                    f"COLLISION-{dataset}-{representation}-{metric}".upper(),
                    metric,
                    value,
                    collision_source,
                    (
                        f"datasets[dataset={dataset}].representations"
                        f"[representation_name={representation}].{metric}"
                    ),
                    "Results / authorization-collision table",
                )

    prevalence_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "agentdojo-tool-effect-prevalence/agentdojo-tool-effect-prevalence-report.json"
    )
    prevalence_protocol_source = (
        "experiments/human-authority-and-causal-validation/evaluation/"
        "agentdojo-tool-effect-prevalence/protocol.json"
    )
    prevalence = read_json(prevalence_source)
    prevalence_protocol = read_json(prevalence_protocol_source)
    if prevalence["status"] != "passed":
        raise ValueError("AgentDojo effect-prevalence census did not pass")
    if prevalence["protocol_sha256"] != prevalence_protocol["protocol_sha256"]:
        raise ValueError("AgentDojo effect-prevalence protocol hash changed")
    if prevalence["n_tasks"] != 97 or prevalence["n_official_calls"] != 339:
        raise ValueError("AgentDojo effect-prevalence population changed")
    if prevalence["n_runtime_errors"] != 0:
        raise ValueError("AgentDojo effect-prevalence replay has execution errors")
    prevalence_claims = {
        "n_tasks": prevalence["n_tasks"],
        "n_official_calls": prevalence["n_official_calls"],
        "n_runtime_errors": prevalence["n_runtime_errors"],
        "tool_inventory.n_tool_instances": prevalence["tool_inventory"]["n_tool_instances"],
        "tool_inventory.n_observed_tool_instances": prevalence["tool_inventory"]["n_observed_tool_instances"],
        "prevalence.n_effectful_calls": prevalence["prevalence"]["n_effectful_calls"],
        "prevalence.n_effectful_observed_tools": prevalence["prevalence"]["n_effectful_observed_tools"],
        "prevalence.n_compound_calls": prevalence["prevalence"]["n_compound_calls"],
        "prevalence.n_heterogeneous_compound_calls": prevalence["prevalence"]["n_heterogeneous_compound_calls"],
        "prevalence.n_multi_target_calls": prevalence["prevalence"]["n_multi_target_calls"],
        "prevalence.n_cross_namespace_calls": prevalence["prevalence"]["n_cross_namespace_calls"],
        "prevalence.maximum_effect_units_per_call": prevalence["prevalence"]["maximum_effect_units_per_call"],
    }
    for key, value in prevalence_claims.items():
        add(
            rows,
            f"AGENTDOJO-EFFECT-PREVALENCE-{key.replace('.', '-').upper()}",
            key.rsplit(".", 1)[-1],
            value,
            prevalence_source,
            key,
            "Abstract / Introduction / Experimental Setup / Results / Conclusion",
        )

    finite_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "finite-domain-effect-binding-validation/finite-domain-validation-report.json"
    )
    finite = read_json(finite_source)
    if finite["status"] != "passed":
        raise ValueError("finite-domain validation did not pass")
    if finite["n_contexts"] != 56 or finite["n_tools"] != 5:
        raise ValueError("finite-domain context or tool count changed")
    if finite["authority_family"] != "all submultisets of the observed atomic-effect occurrences":
        raise ValueError("finite-domain authority family changed")
    if finite["source_verification_errors"]:
        raise ValueError("finite-domain source verification errors are nonempty")
    add(
        rows,
        "FINITE-N-CONTEXTS",
        "n_contexts",
        finite["n_contexts"],
        finite_source,
        "n_contexts",
        "Abstract / Experimental Setup / Results",
    )
    add(
        rows,
        "FINITE-N-TOOLS",
        "n_tools",
        finite["n_tools"],
        finite_source,
        "n_tools",
        "Abstract / Experimental Setup / Results",
    )
    finite_expected = {
        "tool_name": (5, 564, False, False),
        "source_effect_only": (6, 548, False, False),
        "source_common_fields": (5, 118, False, False),
        "reviewed_common_contract": (5, 118, False, False),
        "reviewed_typed_contract": (0, 0, True, True),
        "source_full_effect": (0, 0, True, True),
    }
    finite_rows = {
        row["representation"]: row for row in finite["representations"]
    }
    for representation, expected in finite_expected.items():
        row = finite_rows[representation]
        observed = (
            row["authorization_collision_cells"],
            row["authorization_separating_pairs"],
            row["finite_collision_complete"],
            row["finite_partition_exact"],
        )
        if observed != expected:
            raise ValueError(f"finite-domain result changed for {representation}")
        for metric, value in zip(
            (
                "authorization_collision_cells",
                "authorization_separating_pairs",
                "finite_collision_complete",
                "finite_partition_exact",
            ),
            expected,
        ):
            add(
                rows,
                f"FINITE-{representation}-{metric}".upper(),
                metric,
                value,
                finite_source,
                f"representations[representation={representation}].{metric}",
                "Abstract / Results / authorization-collision table",
            )

    heldout_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "heldout-toolsandbox-effect-binding-validation/heldout-validation-report.json"
    )
    heldout = read_json(heldout_source)
    preregistration_source = (
        "experiments/human-authority-and-causal-validation/evaluation/"
        "heldout-toolsandbox-effect-binding-validation/preregistration.json"
    )
    preregistration = read_json(preregistration_source)
    if heldout["status"] != "passed":
        raise ValueError("ToolSandbox held-out validation did not pass")
    if preregistration["status"] != "frozen_before_contract_evaluation":
        raise ValueError("ToolSandbox held-out protocol was not frozen before evaluation")
    if heldout["source_revision"] != "165848b9a78cead7ca7fe7c89c688b58e6501219":
        raise ValueError("ToolSandbox held-out source revision changed")
    if heldout["source_verification_errors"]:
        raise ValueError("ToolSandbox held-out source verification errors are nonempty")
    heldout_scalar_expected = {
        "n_contexts": 32,
        "n_tools": 5,
        "n_execution_errors_retained": 8,
    }
    for metric, expected in heldout_scalar_expected.items():
        if heldout[metric] != expected:
            raise ValueError(f"ToolSandbox held-out {metric} changed")
        add(
            rows,
            f"HELDOUT-TOOLSANDBOX-{metric}".upper(),
            metric,
            heldout[metric],
            heldout_source,
            metric,
            "Abstract / Experimental Setup / Results / held-out table",
        )
    relation = heldout["typed_relation_agreement"]
    if (relation["successes"], relation["total"], relation["rate"]) != (32, 32, 1.0):
        raise ValueError("ToolSandbox held-out typed relation agreement changed")
    for metric in ("successes", "total", "rate"):
        add(
            rows,
            f"HELDOUT-TOOLSANDBOX-TYPED-RELATION-{metric}".upper(),
            f"typed_relation_agreement_{metric}",
            relation[metric],
            heldout_source,
            f"typed_relation_agreement.{metric}",
            "Abstract / Results",
        )
    heldout_expected = {
        "tool_name": (5, 5, 88, 16, False, False),
        "common_fields": (11, 4, 41, 0, False, False),
        "typed_contract": (25, 0, 0, 0, True, True),
        "source_full_effect": (25, 0, 0, 0, True, True),
    }
    heldout_rows = {
        row["representation"]: row for row in heldout["representations"]
    }
    heldout_metrics = (
        "n_cells",
        "authorization_collision_cells",
        "authorization_separating_pairs",
        "overpartition_pairs",
        "finite_collision_complete",
        "finite_partition_exact",
    )
    for representation, expected in heldout_expected.items():
        row = heldout_rows[representation]
        observed = tuple(row[metric] for metric in heldout_metrics)
        if observed != expected:
            raise ValueError(
                f"ToolSandbox held-out result changed for {representation}"
            )
        for metric, value in zip(heldout_metrics, expected):
            add(
                rows,
                f"HELDOUT-TOOLSANDBOX-{representation}-{metric}".upper(),
                metric,
                value,
                heldout_source,
                f"representations[representation={representation}].{metric}",
                "Abstract / Results / held-out table",
            )

    pact_source = (
        "experiments/human-authority-and-causal-validation/results/"
        "pact-compatible-effect-granularity-comparison/"
        "pact-compatible-comparison-report.json"
    )
    pact = read_json(pact_source)
    if pact["status"] != "passed" or not all(pact["gates"].values()):
        raise ValueError("PACT-compatible representation comparison did not pass")
    pact_rows = {
        (row["dataset"], row["representation"]): row
        for row in pact["representations"]
    }
    pact_expected = {
        ("agentdojo_finite_56", "pact_value_role_provenance"): (
            56,
            0,
            0,
            0,
        ),
        ("toolsandbox_heldout_32", "pact_role_provenance"): (
            6,
            6,
            72,
            16,
        ),
        ("toolsandbox_heldout_32", "pact_value_role_provenance"): (
            22,
            4,
            13,
            23,
        ),
        ("toolsandbox_heldout_32", "typed_effect_occurrence"): (
            25,
            0,
            0,
            0,
        ),
    }
    pact_metrics = (
        "n_representation_cells",
        "authorization_collision_cells",
        "authorization_separating_pairs",
        "overpartition_pairs",
    )
    for (dataset, representation), expected in pact_expected.items():
        row = pact_rows[(dataset, representation)]
        observed = tuple(row[metric] for metric in pact_metrics)
        if observed != expected:
            raise ValueError(
                f"PACT-compatible result changed for {dataset}/{representation}"
            )
        for metric, value in zip(pact_metrics, expected):
            add(
                rows,
                f"PACT-COMPAT-{dataset}-{representation}-{metric}".upper(),
                metric,
                value,
                pact_source,
                (
                    f"representations[dataset={dataset},"
                    f"representation={representation}].{metric}"
                ),
                "Related Work / Results / held-out table",
            )
    if pact["n_same_argument_state_witnesses"] != 9:
        raise ValueError("PACT-compatible same-argument/state witness count changed")
    add(
        rows,
        "PACT-COMPAT-SAME-ARGUMENT-STATE-WITNESSES",
        "n_same_argument_state_witnesses",
        pact["n_same_argument_state_witnesses"],
        pact_source,
        "n_same_argument_state_witnesses",
        "Results",
    )

    defaults_source = (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "conditional-effect-contract-security-model/"
        "agentdojo-effectful-default-audit.json"
    )
    defaults = read_json(defaults_source)
    defaults_expected = {
        "status": "passed_no_effect_bearing_nonempty_defaults",
        "n_default_bearing_effectful_tool_instances": 7,
        "n_optional_default_fields": 22,
        "n_nonempty_static_defaults": 0,
        "n_dynamic_defaults": 0,
        "n_omitted_explicit_equivalent_tools": 7,
    }
    for key, expected in defaults_expected.items():
        observed = defaults[key]
        if observed != expected:
            raise ValueError(f"AgentDojo default audit {key} changed")
        add(
            rows,
            f"AGENTDOJO-DEFAULT-{key}".upper(),
            key,
            observed,
            defaults_source,
            key,
            "Experimental Setup / Security Analysis / Results / Limitations",
        )
    if defaults["execution_error_tools"]:
        raise ValueError("AgentDojo default audit has execution errors")

    payload = {
        "artifact": "usenix27_current_evidence_reproduction",
        "status": (
            "current_pdf_e47_e50_effect_prevalence_collision_finite_heldout_defaults_"
            "e78_capacity_matched_attribution_e79_observed_overhead_"
            "e81_e84_e85_joint_diagnostic_full_benign_bounded_adaptive_"
            "pact_compatible_admitted"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "gates": {
            "reproduction_artifacts_verified": True,
            "agentdojo_effect_prevalence_census_passed": True,
            "agentdojo_effect_prevalence_protocol_hash_matched": True,
            "e78_capacity_matched_comparison_passed": True,
            "e78_non_evaluable_rows_retained": True,
            "closed_loop_attribution_passed": True,
            "e79_fixed_saved_attack_transfer_passed": True,
            "e79_precommit_signature_reconciliation_passed": True,
            "full_benign_fixed_denominator_passed": True,
            "full_benign_zero_unmanifested_effect_allows": True,
            "full_benign_utility_gate_passed": False,
            "full_benign_utility_failure_retained": True,
            "full_benign_privacy_gate_passed": True,
            "joint_effect_authority_diagnostic_passed": True,
            "headline_benign_utility_pathway_audit_passed": True,
            "source_relation_mechanism_probe_passed": True,
            "call_revision_routing_smoke_passed": True,
            "registered_relation_planner_pilot_passed": True,
            "bounded_relation_smoke_passed": True,
            "registered_relation_benign_pilot_fixed_denominator_passed": True,
            "registered_relation_benign_pilot_negative_outcome_retained": True,
            "registered_relation_benign_pilot_material_recovery": False,
            "registered_relation_onboarding_gap_audit_passed": True,
            "bounded_public_family_search_passed": True,
            "pact_compatible_representation_comparison_passed": True,
        },
        "pending_final_protocol_artifacts": {
            "E83": "randomized/interleaved causal end-to-end overhead, if claimed",
            "second_model": "optional matched end-to-end generalization",
            "adaptive_agentlab": "optional full adaptive generation protocol",
        },
        "claim_boundary": (
            "These rows cover numeric claims currently admitted to the PDF and "
            "explicitly marked internal mechanism audits. They do not establish "
            "production safety, open-domain contract soundness, cross-model "
            "generalization, or adaptive AgentLAB robustness."
        ),
    }
    (OUTPUT / "current_evidence.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fields = ["claim_id", "metric", "value", "source", "key", "paper_location", "status"]
    with (OUTPUT / "current_evidence.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# USENIX Current Evidence Reproduction",
        "",
        f"Status: `{payload['status']}`.",
        "",
        "| Claim | Metric | Value | Source key | Paper location |",
        "|---|---|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['claim_id']}` | {row['metric']} | {row['value']} | "
            f"`{row['source']}::{row['key']}` | {row['paper_location']} |"
        )
    lines.extend(["", "## Pending", ""])
    lines.extend(f"- `{key}`: {value}" for key, value in payload["pending_final_protocol_artifacts"].items())
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    (OUTPUT / "current_evidence.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "rows": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
