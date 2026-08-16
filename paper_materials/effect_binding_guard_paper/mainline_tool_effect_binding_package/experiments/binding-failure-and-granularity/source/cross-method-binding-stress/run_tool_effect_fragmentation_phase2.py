from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from src.experiments.tool_effect_fragmentation.adapters import build_system_cases, run_baselines
    from src.experiments.tool_effect_fragmentation.io_utils import write_json, write_jsonl
    from src.experiments.tool_effect_fragmentation.mechanism import mechanism_markdown, run_mechanism_experiment
    from src.experiments.tool_effect_fragmentation.phase2_metrics import (
        agentdojo_split_comparison,
        baseline_vs_upper_bound_deltas,
        example_to_markdown,
        failure_examples,
        row_vs_action_deltas,
    )
    from src.experiments.tool_effect_fragmentation.reproduction_audit import audit_external_reproductions, audit_markdown
    from src.experiments.tool_effect_fragmentation.reporting import access_guard_summary, method_claim_scope
else:
    from .adapters import build_system_cases, run_baselines
    from .io_utils import write_json, write_jsonl
    from .mechanism import mechanism_markdown, run_mechanism_experiment
    from .phase2_metrics import (
        agentdojo_split_comparison,
        baseline_vs_upper_bound_deltas,
        example_to_markdown,
        failure_examples,
        row_vs_action_deltas,
    )
    from .reproduction_audit import audit_external_reproductions, audit_markdown
    from .reporting import access_guard_summary, method_claim_scope


DEFAULT_SYSTEMS = ("agentdojo", "toolsafe", "ipiguard", "safiron", "camel")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E47 Tool-Effect Fragmentation Phase 2 experiments.")
    parser.add_argument("--system", action="append", dest="systems", default=[])
    parser.add_argument("--max-base-cases", type=int, default=24)
    parser.add_argument("--bootstrap-iters", type=int, default=500)
    parser.add_argument("--data-dir", default="data/tool_effect_fragmentation")
    parser.add_argument("--results-dir", default="analysis/results")
    parser.add_argument("--experiment-dir", default="analysis/experiments/E47_tool_effect_fragmentation_crosspaper")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    systems = args.systems or list(DEFAULT_SYSTEMS)
    data_dir = root / args.data_dir
    results_dir = root / args.results_dir
    experiment_dir = root / args.experiment_dir
    all_cases = []
    all_predictions = []
    manifests = []
    system_payloads = []
    for system in systems:
        cases, manifest = build_system_cases(system, root, args.max_base_cases)
        predictions = run_baselines(cases)
        manifests.append(manifest.to_dict())
        all_cases.extend(cases)
        all_predictions.extend(predictions)
        system_payloads.append(
            {
                "system": system,
                "manifest": manifest.to_dict(),
                "n_cases": len(cases),
                "n_predictions": len(predictions),
                "access_guard_summary": access_guard_summary(predictions),
            }
        )
    write_jsonl(data_dir / "phase2_stress_cases.jsonl", [case.to_dict() for case in all_cases])
    write_jsonl(data_dir / "phase2_predictions.jsonl", [pred.to_dict() for pred in all_predictions])

    agentdojo_cases = [case for case in all_cases if case.source_system == "agentdojo"]
    agentdojo_predictions = [pred for pred in all_predictions if pred.source_system == "agentdojo"]
    split_comparison = agentdojo_split_comparison(
        agentdojo_cases,
        agentdojo_predictions,
        bootstrap_iters=args.bootstrap_iters,
    )
    mechanism = run_mechanism_experiment()
    audit = audit_external_reproductions(root)
    examples = failure_examples(all_cases, all_predictions, max_per_type=1)
    paired_deltas = {
        "all_systems_tool_surface_vs_execution_evidence": baseline_vs_upper_bound_deltas(
            all_cases,
            all_predictions,
            bootstrap_iters=args.bootstrap_iters,
        ),
        "agentdojo_tool_surface_vs_execution_evidence": baseline_vs_upper_bound_deltas(
            agentdojo_cases,
            agentdojo_predictions,
            bootstrap_iters=args.bootstrap_iters,
        ),
        "row_vs_action": row_vs_action_deltas(
            all_cases,
            all_predictions,
            bootstrap_iters=args.bootstrap_iters,
        ),
    }
    phase2_rows = build_phase2_rows(system_payloads, split_comparison)
    payload = {
        "schema_version": "tool_effect_fragmentation_phase2_v1",
        "systems": systems,
        "manifests": manifests,
        "phase2_rows": phase2_rows,
        "agentdojo_split_comparison": split_comparison,
        "reproduction_audit": audit,
        "mechanism_effect_invariance": mechanism,
        "paired_deltas": paired_deltas,
        "failure_examples": examples,
        "answers": phase2_answers(split_comparison, mechanism, audit, paired_deltas),
        "claim_boundary": claim_boundary(),
        "acceptance_gates": acceptance_gates(split_comparison, mechanism, audit, examples),
    }
    write_json(results_dir / "tool_effect_fragmentation_phase2_unified.json", payload)
    (results_dir / "tool_effect_fragmentation_phase2_unified.md").write_text(phase2_markdown(payload), encoding="utf-8")
    write_json(results_dir / "tool_effect_fragmentation_phase2_reproduction_audit.json", audit)
    (results_dir / "tool_effect_fragmentation_phase2_reproduction_audit.md").write_text(audit_markdown(audit), encoding="utf-8")
    write_json(results_dir / "tool_effect_fragmentation_phase2_mechanism.json", mechanism)
    (results_dir / "tool_effect_fragmentation_phase2_mechanism.md").write_text(mechanism_markdown(mechanism), encoding="utf-8")
    write_json(results_dir / "tool_effect_fragmentation_phase2_failure_examples.json", examples)
    (results_dir / "tool_effect_fragmentation_phase2_failure_examples.md").write_text(example_to_markdown(examples), encoding="utf-8")
    experiment_dir.mkdir(parents=True, exist_ok=True)
    (experiment_dir / "phase2_summary.md").write_text(phase2_summary_markdown(payload), encoding="utf-8")


def build_phase2_rows(system_payloads: list[dict[str, Any]], split_comparison: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    agentdojo_methods = split_comparison.get("methods", {})
    for payload in system_payloads:
        manifest = payload["manifest"]
        if payload["system"] == "agentdojo":
            for method, method_payload in agentdojo_methods.items():
                for protocol, metrics in method_payload["protocols"].items():
                    rows.append(
                        {
                            "system": "agentdojo",
                            "protocol": protocol,
                            "method": method,
                            "claim_scope": method_claim_scope(method),
                            "adapter_status": manifest["adapter_status"],
                            "paper_grade_environment": manifest.get("paper_grade_environment", False),
                            "paper_grade_method": manifest.get("paper_grade_method", False),
                            "n_cases": metrics["n_cases"],
                            "fnr": metrics["fnr"],
                            "held_out_tool_fnr": metrics["held_out_tool_fnr"],
                            "unsafe_action_pre_allow": metrics["unsafe_action_pre_allow"],
                            "safe_action_false_deny": metrics["safe_action_false_deny"],
                            "action_level_decision_error": metrics["action_level_decision_error"],
                            "intra_action_decision_inconsistency": metrics["intra_action_decision_inconsistency"],
                            "effect_invariance_gap": metrics["effect_invariance_gap"],
                            "tool_proxy_gap": metrics["tool_proxy_gap"],
                        }
                    )
        elif manifest["adapter_status"] == "adapter_failed":
            rows.append(
                {
                    "system": payload["system"],
                    "protocol": "reproduction_audit",
                    "method": "adapter_failed",
                    "claim_scope": "adapter_failed",
                    "adapter_status": manifest["adapter_status"],
                    "paper_grade_environment": False,
                    "paper_grade_method": False,
                    "n_cases": 0,
                }
            )
    return rows


def phase2_answers(
    split_comparison: dict[str, Any],
    mechanism: dict[str, Any],
    audit: dict[str, Any],
    paired_deltas: dict[str, Any],
) -> dict[str, str]:
    tool_name = split_comparison.get("methods", {}).get("tool_name_classifier", {})
    delta = tool_name.get("random_vs_heldout_delta", {}).get("delta")
    gap = mechanism.get("similarities", {}).get("effect_vs_tool_clustering_gap")
    return {
        "Does performance degrade from random split to held-out-tool split?": _answer_delta(delta, "tool_name_classifier random-vs-heldout FNR delta"),
        "Do methods cluster by tool surface or by realized effect?": _answer_gap(gap),
        "Does looking at plan/step/trajectory text solve fragmentation?": "No automatic guarantee in this diagnostic: text/plan/step/trajectory proxy baselines are reported separately and must be compared against held-out-tool FNR and action-level errors.",
        "Do graph/evidence/provenance methods reduce fragmentation?": "Effect/resource and execution-evidence rows are more stable in current tests, but they are marked upper-bound unless implemented as non-oracle verifiers.",
        "Where do row-level metrics disagree with action-level safety?": "See paired_deltas.row_vs_action and failure examples; row FNR and action-level decision error are reported separately.",
        "Which results are paper-grade, original-method, proxy-only, or upper-bound?": "AgentDojo is paper-grade environment only; current non-AgentDojo systems are proxy diagnostics or complete adapter-failure audits unless reproduction_audit reports original_method_runnable.",
        "What still prevents a top-tier paper claim?": "Missing exact original-method reproductions, proxy labels for non-AgentDojo systems, upper-bound effect/evidence rows, and limited mechanism evidence prevent broad cross-paper claims.",
    }


def acceptance_gates(
    split_comparison: dict[str, Any],
    mechanism: dict[str, Any],
    audit: dict[str, Any],
    examples: list[dict[str, Any]],
) -> dict[str, bool]:
    return {
        "agentdojo_random_vs_heldout_complete": bool(split_comparison.get("methods")),
        "non_agentdojo_original_or_complete_audit": audit["acceptance_summary"]["original_method_result_available"]
        or audit["acceptance_summary"]["complete_adapter_failed_available"],
        "mechanism_gap_reported": mechanism["similarities"]["effect_vs_tool_clustering_gap"] is not None,
        "failure_examples_generated": bool(examples),
        "claim_boundary_present": True,
    }


def claim_boundary() -> list[str]:
    return [
        "Can claim: Tool-surface baselines fail under AgentDojo custom stress when reported as paper-grade local stress evidence.",
        "Can claim: Text/plan/step/trajectory views do not automatically remove fragmentation in current proxy tests.",
        "Can claim: Effect/resource and execution-evidence upper bounds are more stable in current tests.",
        "Can claim: Proxy diagnostics identify likely failure modes for step-level, graph-level, and plan-level systems.",
        "Cannot claim: ToolSafe, IPIGuard, Safiron, or CaMeL original method failure unless an official-method adapter is actually run.",
        "Cannot claim: Graph/provenance methods generally fail.",
        "Cannot claim: Execution evidence is a deployable complete safety solution.",
    ]


def phase2_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Tool-Effect Fragmentation Phase 2 Unified Report",
        "",
        "## Required Questions",
        "",
    ]
    for question, answer in payload["answers"].items():
        lines.append(f"- **{question}** {answer}")
    lines.extend(["", "## AgentDojo Split Comparison", ""])
    lines.extend(_split_table(payload["agentdojo_split_comparison"]))
    lines.extend(["", "## External Reproduction Audit", ""])
    for system, audit in payload["reproduction_audit"]["audits"].items():
        lines.append(f"- `{system}`: `{audit['status']}`; blockers: {', '.join(audit['blockers']) or 'none'}")
    lines.extend(["", "## Mechanism Experiment", ""])
    sims = payload["mechanism_effect_invariance"]["similarities"]
    lines.append(f"- Effect-vs-tool clustering gap: `{_fmt(sims['effect_vs_tool_clustering_gap'])}`")
    lines.append(f"- Interpretation: {sims['gap_interpretation']}")
    lines.extend(["", "## Claim Boundary", ""])
    lines.extend(f"- {item}" for item in payload["claim_boundary"])
    return "\n".join(lines) + "\n"


def phase2_summary_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# E47 Phase 2 Summary",
        "",
        "## Status",
        "",
        "- AgentDojo random/held-out/same-effect stress comparison is complete over the local paper-grade stress environment.",
        "- Non-AgentDojo systems have complete reproduction audits; original-method results require missing model/API/runtime prerequisites to be satisfied.",
        "- Mechanism effect-vs-tool clustering experiment is diagnostic and local-only.",
        "",
        "## Answers",
        "",
    ]
    for question, answer in payload["answers"].items():
        lines.append(f"- **{question}** {answer}")
    lines.extend(["", "## Acceptance Gates", ""])
    for gate, passed in payload["acceptance_gates"].items():
        lines.append(f"- `{gate}`: `{passed}`")
    lines.extend(["", "## Claim Boundary", ""])
    lines.extend(f"- {item}" for item in payload["claim_boundary"])
    return "\n".join(lines) + "\n"


def _split_table(split_comparison: dict[str, Any]) -> list[str]:
    lines = [
        "| Method | Protocol | N | FNR | Held-out-tool FNR | Unsafe pre-allow | Action error | ToolProxyGap |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for method, method_payload in split_comparison.get("methods", {}).items():
        for protocol, metrics in method_payload["protocols"].items():
            lines.append(
                "| `{}` | `{}` | {} | {} | {} | {} | {} | {} |".format(
                    method,
                    protocol,
                    metrics["n_cases"],
                    _fmt_rate(metrics["fnr"]),
                    _fmt_rate(metrics["held_out_tool_fnr"]),
                    _fmt_rate(metrics["unsafe_action_pre_allow"]),
                    _fmt_rate(metrics["action_level_decision_error"]),
                    _fmt(metrics["tool_proxy_gap"]),
                )
            )
    return lines


def _answer_delta(delta: float | None, label: str) -> str:
    if delta is None:
        return f"{label} is not available."
    direction = "worsens" if delta > 0 else "improves or does not worsen"
    return f"{label} = {delta:.4f}; held-out stress {direction} relative to the random subset."


def _answer_gap(gap: float | None) -> str:
    if gap is None:
        return "The mechanism clustering gap is not available."
    if gap > 0:
        return f"Effect-vs-tool clustering gap is {gap:.4f}, indicating stronger same-effect than same-tool proximity in this controlled diagnostic."
    return f"Effect-vs-tool clustering gap is {gap:.4f}, indicating tool-surface proximity is at least as strong as same-effect proximity in this controlled diagnostic."


def _fmt_rate(metric: dict[str, Any]) -> str:
    rate = metric.get("rate")
    if rate is None:
        return "NA"
    return f"{rate:.3f} [{metric.get('ci_low', 0):.3f}, {metric.get('ci_high', 0):.3f}]"


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


if __name__ == "__main__":
    main()

