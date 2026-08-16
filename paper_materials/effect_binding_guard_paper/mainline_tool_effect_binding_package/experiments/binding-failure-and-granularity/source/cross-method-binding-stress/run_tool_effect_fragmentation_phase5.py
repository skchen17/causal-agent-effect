from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .io_utils import read_jsonl, write_json
from .phase5_camel import build_camel_structural_counterfactuals, validate_camel_cases
from .phase5_ipiguard import build_ipiguard_counterfactuals, validate_ipiguard_cases
from .phase5_metrics import summarize_camel_component, summarize_ipiguard_component, summarize_pipeline


SUMMARY = Path("analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase5_summary.md")
UNIFIED = Path("analysis/results/tool_effect_fragmentation_phase5_unified")
IPIGUARD_RESULT = Path("analysis/results/tool_effect_fragmentation_ipiguard_phase5")
CAMEL_RESULT = Path("analysis/results/tool_effect_fragmentation_camel_phase5")
FAILURES = Path("analysis/results/tool_effect_fragmentation_phase5_failure_examples")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build/summarize E47 Phase 5 IPIGuard and CaMeL experiments.")
    parser.add_argument("--bootstrap-iters", type=int, default=2000)
    parser.add_argument("--run-camel-component", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    ipiguard_cases = build_ipiguard_counterfactuals(read_jsonl(root / "data/agentdojo_effect_verifier_t122_core.jsonl"))
    camel_cases = build_camel_structural_counterfactuals()
    if args.run_camel_component:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "src.experiments.tool_effect_fragmentation.phase5_camel_component_worker",
            ],
            cwd=root,
            check=True,
        )
    reproduction = load_json(root / "analysis/results/tool_effect_fragmentation_phase5_reproduction.json")
    ipiguard_traces = read_jsonl(root / "data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl")
    camel_traces = read_jsonl(root / "data/tool_effect_fragmentation/camel_phase5_traces.jsonl")
    camel_component = read_jsonl(root / "analysis/results/tool_effect_fragmentation_camel_component_phase5.jsonl")
    ipiguard_component = read_jsonl(root / "analysis/results/tool_effect_fragmentation_ipiguard_component_phase5.jsonl")
    ipiguard_component = enrich_ipiguard_component(ipiguard_component, ipiguard_cases)
    ipiguard_component_summary = (
        summarize_ipiguard_component(ipiguard_component, bootstrap_iters=args.bootstrap_iters)
        if ipiguard_component
        else {"status": "core_built_pending_original_component_inference", "n_cases": len(ipiguard_cases)}
    )
    camel_component_summary = (
        summarize_camel_component(camel_component, bootstrap_iters=args.bootstrap_iters)
        if camel_component
        else {"status": "not_run"}
    )
    payload = {
        "schema_version": "tool_effect_fragmentation_phase5_unified_v1",
        "counterfactual_validation": {
            "ipiguard": validate_ipiguard_cases(ipiguard_cases),
            "camel": validate_camel_cases(camel_cases),
        },
        "original_pipeline_local_model": {
            "ipiguard": summarize_pipeline(ipiguard_traces),
            "camel": summarize_pipeline(camel_traces),
        },
        "original_component_custom_stress": {
            "camel_security_policy": camel_component_summary,
            "ipiguard_dag_counterfactual": ipiguard_component_summary,
        },
        "reproduction_audit": reproduction,
        "acceptance_gates": acceptance_gates(
            ipiguard_cases,
            camel_cases,
            ipiguard_traces,
            camel_traces,
            ipiguard_component,
            camel_component,
        ),
        "claim_boundary": [
            "Local GGUF pipeline results are original-pipeline/local-model evidence, not original-paper numeric reproduction.",
            "IPIGuard custom stress uses the released DAG construction prompt/parser, not the full construct-traverse-execute pipeline.",
            "IPIGuard DAG outputs do not expose realized-effect labels, so planned-effect coverage is not identifiable without an external effect mapper.",
            "CaMeL component stress uses the original generic policy engine but not the full generated-code pipeline.",
            "AgentDojo tools execute only inside simulated environments; real_side_effects is always false.",
            "Pipeline/model compatibility failures are reproduction failures, not evidence that the safety method fails.",
        ],
    }
    write_json(root / UNIFIED.with_suffix(".json"), payload)
    text = markdown(payload)
    (root / UNIFIED.with_suffix(".md")).write_text(text, encoding="utf-8")
    write_system_result(
        root,
        IPIGUARD_RESULT,
        "IPIGuard",
        payload["original_pipeline_local_model"]["ipiguard"],
        ipiguard_component_summary,
        payload["claim_boundary"],
    )
    write_system_result(
        root,
        CAMEL_RESULT,
        "CaMeL",
        payload["original_pipeline_local_model"]["camel"],
        camel_component_summary,
        payload["claim_boundary"],
    )
    failure_payload = {
        "ipiguard": ipiguard_component_summary.get("failure_examples", []),
        "camel": camel_failure_examples(camel_component),
        "claim_boundary": payload["claim_boundary"],
    }
    write_json(root / FAILURES.with_suffix(".json"), failure_payload)
    (root / FAILURES.with_suffix(".md")).write_text(failure_markdown(failure_payload), encoding="utf-8")
    (root / SUMMARY).parent.mkdir(parents=True, exist_ok=True)
    (root / SUMMARY).write_text(text, encoding="utf-8")


def acceptance_gates(
    ipiguard_cases: list[dict[str, Any]],
    camel_cases: list[dict[str, Any]],
    ipiguard_traces: list[dict[str, Any]],
    camel_traces: list[dict[str, Any]],
    ipiguard_component: list[dict[str, Any]],
    camel_component: list[dict[str, Any]],
) -> dict[str, bool]:
    ipiguard_four_suite = four_suite_complete(ipiguard_traces, "ipiguard")
    camel_four_suite = four_suite_complete(camel_traces, "camel")
    gates = {
        "ipiguard_counterfactual_core_valid": not validate_ipiguard_cases(ipiguard_cases)["errors"],
        "camel_structural_core_valid": not validate_camel_cases(camel_cases)["errors"],
        "ipiguard_original_dag_component_complete": len(ipiguard_component) == len(ipiguard_cases),
        "camel_original_policy_component_complete": len(camel_component) == len(camel_cases),
        "ipiguard_original_pipeline_smoke_complete": len(ipiguard_traces) > 0,
        "camel_original_pipeline_smoke_complete": len(camel_traces) > 0,
        "ipiguard_four_suite_complete": ipiguard_four_suite,
        "camel_four_suite_complete": camel_four_suite,
        "real_side_effects_absent": not any(
            bool(row.get("real_side_effects")) for row in [*ipiguard_traces, *camel_traces, *camel_component]
        ),
        "paper_evidence_gate": False,
    }
    gates["both_mechanism_counterfactual_stresses_complete"] = (
        gates["ipiguard_original_dag_component_complete"] and gates["camel_original_policy_component_complete"]
    )
    gates["paper_evidence_gate"] = (
        gates["both_mechanism_counterfactual_stresses_complete"]
        and (ipiguard_four_suite or camel_four_suite)
        and gates["real_side_effects_absent"]
    )
    return gates


def four_suite_complete(rows: list[dict[str, Any]], system: str) -> bool:
    suites = {"workspace", "slack", "travel", "banking"}
    policies = {"none", "normal"} if system == "ipiguard" else {"none", "normal", "strict"}
    expected = {
        (suite, mode, policy)
        for suite in suites
        for mode in {"benign", "attack"}
        for policy in policies
    }
    observed = {
        (str(row.get("suite")), str(row.get("mode")), str(row.get("policy_mode")))
        for row in rows
        if row.get("case_protocol") == "full_cross_product"
    }
    return expected.issubset(observed)


def markdown(payload: dict[str, Any]) -> str:
    gates = payload["acceptance_gates"]
    camel = payload["original_component_custom_stress"]["camel_security_policy"]
    lines = [
        "# E47 Phase 5 IPIGuard and CaMeL Evaluation",
        "",
        "## Status",
        "",
        f"- IPIGuard counterfactual core: `{payload['counterfactual_validation']['ipiguard']['n_cases']}` cases.",
        f"- CaMeL structural core: `{payload['counterfactual_validation']['camel']['n_cases']}` cases.",
        f"- IPIGuard original-pipeline trace rows: `{payload['original_pipeline_local_model']['ipiguard']['n_rows']}`.",
        f"- CaMeL original-pipeline trace rows: `{payload['original_pipeline_local_model']['camel']['n_rows']}`.",
        "",
        "## CaMeL Original Policy Component",
        "",
    ]
    if camel.get("n_rows"):
        lines.extend(
            [
                f"- Rows: `{camel['n_rows']}`",
                f"- Overall accuracy: `{fmt(camel['overall_accuracy'])}`",
                f"- Unsafe blocked: `{fmt(camel['unsafe_execution_blocked'])}`",
                f"- Safe false denial: `{fmt(camel['safe_false_denial'])}`",
                f"- Structural invariance: `{fmt(camel['structural_invariance'])}`",
            ]
        )
    else:
        lines.append("- Not run.")
    lines.extend(["", "## Original Pipeline Local-Model Evaluation", ""])
    for system, summary in payload["original_pipeline_local_model"].items():
        lines.append(f"### {system}")
        lines.append("")
        for component, metrics in summary.get("by_component", {}).items():
            lines.append(
                f"- `{component}`: rows `{metrics['n_rows']}`, runtime errors `{fmt(metrics['runtime_error_rate'])}`, "
                f"policy denials `{fmt(metrics['policy_denial_rate'])}`, "
                f"benign utility `{fmt(metrics['utility_benign'])}`, attack utility `{fmt(metrics['utility_under_attack'])}`, "
                f"attack success `{fmt(metrics['attack_success_rate'])}`, DAG valid `{fmt(metrics['dag_parse_valid_rate'])}`."
            )
        lines.append("")
    ipiguard = payload["original_component_custom_stress"]["ipiguard_dag_counterfactual"]
    lines.extend(["## IPIGuard Original DAG Component Stress", ""])
    if ipiguard.get("n_rows"):
        lines.extend(
            [
                f"- Rows: `{ipiguard['n_rows']}`",
                f"- Parse-valid: `{fmt(ipiguard['parse_valid_rate'])}`",
                f"- Normalized-effect prompt leakage excluding explicit effect graph: "
                f"`{fmt(ipiguard['normalized_effect_prompt_leak_rate_excluding_explicit_effect_graph'])}`",
                f"- Planned tool-surface coverage: `{fmt(ipiguard['planned_tool_surface_coverage'])}`",
                f"- Planned effect coverage: `{ipiguard['planned_effect_coverage']['status']}`",
                f"- Same-effect topology consistency: `{fmt(ipiguard['same_effect_topology_consistency'])}`",
                f"- Same-effect exact-DAG consistency: `{fmt(ipiguard['same_effect_exact_dag_consistency'])}`",
                f"- Same-effect normalized-DAG consistency: `{fmt(ipiguard['same_effect_normalized_dag_consistency'])}`",
                f"- Tool-surface full-DAG change rate: `{fmt(ipiguard['tool_surface_full_dag_change_rate'])}`",
                f"- Same-tool different-effect topology sensitivity: `{fmt(ipiguard['same_tool_different_effect_topology_sensitivity'])}`",
                f"- Same-tool different-effect content sensitivity: `{fmt(ipiguard['same_tool_different_effect_content_sensitivity'])}`",
            ]
        )
        lines.extend(["", "### IPIGuard Consistency by Variant", ""])
        for variant, metrics in ipiguard.get("counterfactual_consistency_by_variant", {}).items():
            lines.append(
                f"- `{variant}`: topology `{fmt(metrics['topology_consistency'])}`, "
                f"exact DAG `{fmt(metrics['exact_dag_consistency'])}`, "
                f"normalized DAG `{fmt(metrics['normalized_dag_consistency'])}`."
            )
        wrapper = ipiguard.get("counterfactual_consistency_by_variant", {}).get("wrapper_tool", {})
        schema = ipiguard.get("counterfactual_consistency_by_variant", {}).get("arg_schema_change", {})
        rename = ipiguard.get("counterfactual_consistency_by_variant", {}).get("tool_rename", {})
        lines.extend(
            [
                "",
                "## Reviewer Interpretation",
                "",
                f"- IPIGuard tool rename is stable after the known alias map (`{fmt(rename.get('normalized_dag_consistency', {}))}`), "
                f"but wrapper and argument-schema shifts remain less stable after known-map normalization "
                f"(`{fmt(wrapper.get('normalized_dag_consistency', {}))}` and `{fmt(schema.get('normalized_dag_consistency', {}))}`).",
                "- IPIGuard topology remains unchanged even when the visible effect changes; topology-only metrics therefore miss content-level effect sensitivity.",
                "- CaMeL is stable under synchronized structural rewrites, but the custom policy component blocks only part of the weak-labeled unsafe structural cases.",
                "- Original-pipeline rates cover all four native suites with a local non-paper model. Low no-defense attack success and utility sharply limit defense-effectiveness conclusions.",
                f"- The current four-suite paper-evidence gate is `{gates['paper_evidence_gate']}` under the implemented completion criteria; this is an artifact-completion gate, not an acceptance or safety gate.",
            ]
        )
    else:
        lines.append(f"- Status: `{ipiguard.get('status', 'not_run')}`")
    lines.extend(["", "## Acceptance Gates", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in gates.items())
    lines.extend(["", "## Claim Boundary", ""])
    lines.extend(f"- {item}" for item in payload["claim_boundary"])
    return "\n".join(lines) + "\n"


def fmt(metric: dict[str, Any]) -> str:
    if metric.get("rate") is None:
        return "NA"
    return f"{metric['rate']:.4f} [{metric['ci_low']:.4f}, {metric['ci_high']:.4f}]"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "not_run"}


def enrich_ipiguard_component(
    rows: list[dict[str, Any]],
    cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {case["case_id"]: case for case in cases}
    enriched = []
    for row in rows:
        case = by_id.get(row.get("case_id"), {})
        candidate_nodes = case.get("candidate_dag", {}).get("nodes", [])
        candidate = candidate_nodes[0] if candidate_nodes else {}
        enriched.append(
            {
                **row,
                "candidate_tool_name": candidate.get("tool_name"),
                "candidate_arguments": candidate.get("arguments"),
                "resource": case.get("resource"),
                "counterfactual_axis": case.get("counterfactual_axis"),
            }
        )
    return enriched


def write_system_result(
    root: Path,
    output: Path,
    system: str,
    pipeline: dict[str, Any],
    component: dict[str, Any],
    claim_boundary: list[str],
) -> None:
    payload = {
        "system": system,
        "original_pipeline_local_model": pipeline,
        "original_component_custom_stress": component,
        "claim_boundary": claim_boundary,
    }
    write_json(root / output.with_suffix(".json"), payload)
    lines = [f"# E47 Phase 5 {system}", "", "## Original Pipeline Local-Model Evaluation", ""]
    lines.append(f"- Rows: `{pipeline.get('n_rows', 0)}`")
    for name, metrics in pipeline.get("by_component", {}).items():
        lines.append(
            f"- `{name}`: runtime errors `{fmt(metrics['runtime_error_rate'])}`, "
            f"policy denials `{fmt(metrics['policy_denial_rate'])}`, benign utility `{fmt(metrics['utility_benign'])}`, "
            f"attack utility `{fmt(metrics['utility_under_attack'])}`, attack success `{fmt(metrics['attack_success_rate'])}`."
        )
    lines.extend(["", "## Original Component Custom Stress", "", f"```json\n{json.dumps(component, indent=2)}\n```"])
    lines.extend(["", "## Claim Boundary", *[f"- {item}" for item in claim_boundary]])
    (root / output.with_suffix(".md")).write_text("\n".join(lines) + "\n", encoding="utf-8")


def camel_failure_examples(rows: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "failure_type": "policy_decision_error",
            "case_id": row["case_id"],
            "counterfactual_group_id": row["counterfactual_group_id"],
            "variant": row["variant"],
            "expected_decision": row["expected_decision"],
            "predicted_decision": row["predicted_decision"],
            "policy_reason": row.get("policy_reason", ""),
        }
        for row in rows
        if row.get("predicted_decision") != row.get("expected_decision")
    ][:limit]


def failure_markdown(payload: dict[str, Any]) -> str:
    lines = ["# E47 Phase 5 Failure Examples", ""]
    for system in ("ipiguard", "camel"):
        lines.extend([f"## {system}", ""])
        examples = payload.get(system, [])
        if not examples:
            lines.append("- No examples available.")
        for example in examples:
            lines.append(f"- `{example.get('failure_type')}`: `{example.get('case_id') or example.get('variant_case_id')}`")
        lines.append("")
    lines.extend(["## Claim Boundary", *[f"- {item}" for item in payload["claim_boundary"]]])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
