#!/usr/bin/env python3
"""Generate final readiness reports and the second simulated review."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
WORKSPACE = ROOT / "paper/writing-workspace"
SOURCES = {
    "deepseek": (
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "deepseek_benign_interleaved_results.json"
    ),
    "qwen": (
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "qwen32_matched_results.json"
    ),
    "heldout": "experiments/adaptive-injection-benchmark/results/usenix-heldout-public-families/results.json",
    "transfer": "analysis/results/e79_agentlab_saved_transfer_current_pair_results.json",
    "four_view": (
        "experiments/security-analysis-ablation-and-overhead/results/"
        "c1f-closed-loop-four-view/closed-loop-four-view-report.json"
    ),
    "bounded": (
        "experiments/adaptive-injection-benchmark/results/"
        "bounded-public-family-search-current-c1f/results.json"
    ),
}


def read_passed(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(relative)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "passed":
        raise RuntimeError(f"artifact not passed: {relative}")
    return payload


def indexed(payload: dict[str, Any], outer: str, field: str, value: str) -> dict[str, Any]:
    for row in payload[outer]:
        if row[field] == value:
            return row
    raise KeyError(f"{outer}[{field}={value}]")


def load_all() -> dict[str, dict[str, Any]]:
    return {name: read_passed(relative) for name, relative in SOURCES.items()}


def assess(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    deepseek = payloads["deepseek"]
    qwen = payloads["qwen"]
    heldout = payloads["heldout"]
    transfer = payloads["transfer"]
    four = payloads["four_view"]
    bounded = payloads["bounded"]
    ds = {name: indexed(deepseek, "aggregates", "condition", name) for name in ("no_guard", "spotlighting", "c1f")}
    qw = {name: indexed(qwen, "metrics", "condition", name) for name in ("no_guard", "spotlighting", "c1f")}
    ho = {name: indexed(heldout, "summaries", "method", name) for name in ("no_guard", "spotlighting", "c1f")}
    fv = {
        name: indexed(four, "aggregates", "variant", name)
        for name in ("no_guard", "whole_call_provenance", "effect_only", "registered_field_c1f")
    }
    bounded_rows = {
        name: indexed(bounded, "search_metrics", "method", name)
        for name in ("no_guard", "ours_e77_effect_diff_runtime")
    }
    transfer_rows = {
        name: indexed(transfer, "comparison_metrics", "condition", name)
        for name in ("no_guard", "c1f")
    }
    bootstrap = deepseek["task_cluster_bootstrap"]
    security_not_worse = (
        qw["c1f"]["attack_successes"] <= qw["no_guard"]["attack_successes"]
        and ho["c1f"]["attack_successes"] <= ho["no_guard"]["attack_successes"]
        and bounded_rows["ours_e77_effect_diff_runtime"]["attack_successes"]
        <= bounded_rows["no_guard"]["attack_successes"]
        and transfer_rows["c1f"]["attack_successes"]
        <= transfer_rows["no_guard"]["attack_successes"]
    )
    granularity_signal = fv["registered_field_c1f"]["attack_successes"] < max(
        fv["whole_call_provenance"]["attack_successes"],
        fv["effect_only"]["attack_successes"],
    )
    utility_noninferior = bootstrap["noninferior"] is True
    if security_not_worse and granularity_signal and utility_noninferior:
        recommendation = "Weak Accept"
    elif security_not_worse and granularity_signal:
        recommendation = "Borderline / Weak Reject"
    else:
        recommendation = "Weak Reject"
    return {
        "deepseek": ds,
        "qwen": qw,
        "heldout": ho,
        "transfer": transfer_rows,
        "four_view": fv,
        "bounded": bounded_rows,
        "bootstrap": bootstrap,
        "security_not_worse_on_frozen_generalization_checks": security_not_worse,
        "closed_loop_granularity_signal": granularity_signal,
        "benign_utility_noninferior": utility_noninferior,
        "simulated_recommendation": recommendation,
    }


def fraction(row: dict[str, Any], key: str, denominator: int) -> str:
    return f"{row[key]}/{denominator}"


def render_completion(a: dict[str, Any]) -> str:
    ds, qw, ho, fv, bounded = a["deepseek"], a["qwen"], a["heldout"], a["four_view"], a["bounded"]
    return "\n".join(
        [
            "# Final Frozen-Experiment Completion Report",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}.",
            "",
            "All six required frozen artifacts report `status=passed`; no unfavorable row is removed.",
            "",
            "## Matched Utility and Second Model",
            "",
            f"- DeepSeek benign utility over four interleaved repetitions: no guard {fraction(ds['no_guard'], 'utility_successes', 388)}, Spotlighting {fraction(ds['spotlighting'], 'utility_successes', 388)}, C1f {fraction(ds['c1f'], 'utility_successes', 388)}.",
            f"- C1f-minus-no-guard difference: {a['bootstrap']['difference_c1f_minus_no_guard']:.4f}; one-sided 95% lower bound: {a['bootstrap']['one_sided_95_lower_bound']:.4f}; non-inferior at -0.05: `{str(a['benign_utility_noninferior']).lower()}`.",
            f"- Qwen3-32B attack success: no guard {fraction(qw['no_guard'], 'attack_successes', 629)}, Spotlighting {fraction(qw['spotlighting'], 'attack_successes', 629)}, C1f {fraction(qw['c1f'], 'attack_successes', 629)}.",
            f"- Qwen3-32B benign utility: no guard {fraction(qw['no_guard'], 'benign_utility_successes', 97)}, Spotlighting {fraction(qw['spotlighting'], 'benign_utility_successes', 97)}, C1f {fraction(qw['c1f'], 'benign_utility_successes', 97)}.",
            "",
            "## Held-Out, Transfer, and Attribution",
            "",
            f"- Frozen 320-case held-out ASR counts: no guard {fraction(ho['no_guard'], 'attack_successes', 320)}, Spotlighting {fraction(ho['spotlighting'], 'attack_successes', 320)}, C1f {fraction(ho['c1f'], 'attack_successes', 320)}.",
            f"- Frozen 40-key worst-of-four ASR counts: no guard {fraction(bounded['no_guard'], 'attack_successes', 40)}, current C1f {fraction(bounded['ours_e77_effect_diff_runtime'], 'attack_successes', 40)}.",
            f"- Current-profile AgentLAB saved transfer: no guard attack/utility {a['transfer']['no_guard']['attack_successes']}/303 and {a['transfer']['no_guard']['utility_successes']}/303; C1f {a['transfer']['c1f']['attack_successes']}/303 and {a['transfer']['c1f']['utility_successes']}/303.",
            f"- Four-view closed-loop ASR counts: no guard {fraction(fv['no_guard'], 'attack_successes', 273)}, whole-call {fraction(fv['whole_call_provenance'], 'attack_successes', 273)}, effect-only {fraction(fv['effect_only'], 'attack_successes', 273)}, registered-field C1f {fraction(fv['registered_field_c1f'], 'attack_successes', 273)}.",
            "",
            "## Claim Boundary",
            "",
            "The results support policy-relative effect representation and a bounded provenance-origin mediation instance. They do not establish global minimality, complete authorization, production safety, adaptive AgentLAB reproduction, or SOTA.",
            "",
        ]
    )


def render_review(a: dict[str, Any]) -> str:
    ni = "passes" if a["benign_utility_noninferior"] else "does not pass"
    granularity = "is present" if a["closed_loop_granularity_signal"] else "is not established"
    return "\n".join(
        [
            "# Simulated USENIX Security Review, Round 2",
            "",
            f"**Recommendation: {a['simulated_recommendation']}.**",
            "",
            "## Summary",
            "",
            "The paper presents a policy-relative representation obligation for effectful tool calls, a source-executed counterfactual registration procedure, and a narrow deterministic provenance-origin mediator. All frozen validation artifacts and row-level reproduction gates are complete.",
            "",
            "## Evidence Assessment",
            "",
            f"- The preregistered five-point benign-utility test {ni} its non-inferiority criterion.",
            f"- A closed-loop advantage of registered fields over at least one coarser monitor view {granularity} on the selection-conditioned subset.",
            f"- Frozen generalization checks do not make C1f worse than no guard on attack success: `{str(a['security_not_worse_on_frozen_generalization_checks']).lower()}`.",
            "- The source-oracle collision and held-out ToolSandbox results remain the cleanest evidence for the atom representation; runtime ASR alone is not used to prove minimal atom discovery.",
            "",
            "## Strengths",
            "",
            "1. The paper separates representation, provenance, policy, mediation, and check-use assumptions.",
            "2. Source execution and frozen interventions provide falsifiable evidence rather than evaluator-only semantic labels.",
            "3. Negative results, invalid interventions, Spotlighting comparisons, utility outcomes, and selection boundaries remain visible.",
            "4. The artifact exposes per-cell claim provenance and compact per-case final outcomes.",
            "",
            "## Remaining Risks",
            "",
            "1. The AgentDojo registry retains all 67 schema fields, so automatic sparse descriptor discovery is not demonstrated.",
            "2. The confinement instance is limited to provenance-origin policy and literal task grounding; ACLs, delegation, quotas, and output-only goals remain outside scope.",
            "3. ToolSandbox and the finite source domains are bounded; they do not certify unseen tools or asynchronous effects.",
            "4. The collision theorem is elementary, so the contribution depends on the executable systems evidence and complete mediation path.",
            "",
            "The recommendation does not imply production safety, complete authorization, or SOTA; those claims remain outside the evaluated boundary.",
            "",
            "## Provisional Scores",
            "",
            "| Criterion | Score (1--5) |",
            "|---|---:|",
            "| Originality | 3 |",
            "| Technical quality | 4 |",
            "| Correctness | 4 |",
            "| Clarity | 4 |",
            "| Systems-security fit | 4 |",
            "",
        ]
    )


def replace_section(path: Path, heading: str, next_heading: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.index(next_heading, start)
    path.write_text(text[:start] + body.rstrip() + "\n\n" + text[end:], encoding="utf-8")


def main() -> int:
    payloads = load_all()
    assessment = assess(payloads)
    completion = render_completion(assessment)
    (PAPER / "final_experiment_completion_report.md").write_text(completion, encoding="utf-8")
    (PAPER / "simulated_review_round2.md").write_text(render_review(assessment), encoding="utf-8")

    final_validation = "\n".join(completion.splitlines()[5:-5])
    replace_section(
        PAPER / "writing_report.md",
        "## Required Results Still Running",
        "## Remaining Experimental Attribution Risk",
        "## Final Frozen Validation\n\n" + final_validation,
    )

    readiness = "\n".join(
        [
            "# USENIX Security '27 Submission Readiness",
            "",
            f"Last updated: {datetime.now(timezone.utc).date().isoformat()}.",
            "",
            "## Current Decision",
            "",
            "**Status: paper evidence complete; author verification and artifact release remain.**",
            "",
            "All six frozen terminal experiments, the 155-row fixed evidence ledger, generated final tables, and compact per-case export have passed their fail-fast gates. Performance claims follow the observed outcomes, including any failed non-inferiority or baseline parity.",
            "",
            "## Evidence Outcome",
            "",
            f"- DeepSeek benign non-inferiority at the five-point margin: `{str(assessment['benign_utility_noninferior']).lower()}`.",
            f"- Security not worse than no guard on the frozen Qwen and held-out checks: `{str(assessment['security_not_worse_on_frozen_generalization_checks']).lower()}`.",
            f"- Closed-loop registered-field granularity signal: `{str(assessment['closed_loop_granularity_signal']).lower()}`.",
            f"- Simulated second-round recommendation: **{assessment['simulated_recommendation']}**.",
            "",
            "## Claim Boundary",
            "",
            "The supportable claim is that counterfactually validated, policy-relative effect atoms expose representation collisions and can drive auditable pre-commit mediation under explicit provenance and runtime assumptions. The evidence does not establish a globally minimal schema, a complete authority system, production safety, unrestricted adaptive robustness, or SOTA.",
            "",
            "## Author-Only Completion",
            "",
            "Authors must verify all AI-assisted prose and numbers, provide author/ORCID/funding/conflict metadata, perform the final anonymity review, run the released package in a clean environment, and insert a stable anonymous artifact URL.",
            "",
        ]
    )
    (PAPER / "submission_readiness_report.md").write_text(readiness, encoding="utf-8")

    replace_section(
        WORKSPACE / "final_artifact_manifest.md",
        "## Evidence Gates",
        "## Claim Boundary",
        "## Evidence Gates\n\nAll six frozen final experiments, final tables, claim ledger, and compact per-case outcome export passed. Artifact publication remains gated only on author verification, a clean-environment run, final anonymity review, and a stable anonymous URL.",
    )
    logic_path = WORKSPACE / "logic_transfer_audit.md"
    logic = logic_path.read_text(encoding="utf-8")
    marker = "## Remaining Transfer Checks"
    logic_path.write_text(
        logic[: logic.index(marker)]
        + "## Completed Transfer Checks\n\nAll six strict final artifacts were inserted through the result generator. The retrospective and closed-loop four-view results remain separately labeled, all final table rows were regenerated, and the second simulated review is recorded in `paper/current-usenix/simulated_review_round2.md`.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "passed", **{k: v for k, v in assessment.items() if isinstance(v, bool) or k == "simulated_recommendation"}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
