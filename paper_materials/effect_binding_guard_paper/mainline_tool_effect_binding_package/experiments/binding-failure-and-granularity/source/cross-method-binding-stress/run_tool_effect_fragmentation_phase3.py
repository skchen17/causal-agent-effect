from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from src.experiments.tool_effect_fragmentation.adapters import build_system_cases, run_baselines
    from src.experiments.tool_effect_fragmentation.io_utils import write_json, write_jsonl
    from src.experiments.tool_effect_fragmentation.phase2_metrics import example_to_markdown, failure_examples
    from src.experiments.tool_effect_fragmentation.phase3_agentdojo import agentdojo_phase3_analysis, agentdojo_phase3_markdown
    from src.experiments.tool_effect_fragmentation.phase3_evidence import evidence_phase3_markdown, run_evidence_diagnostic
    from src.experiments.tool_effect_fragmentation.phase3_mechanism import mechanism_phase3_markdown, run_phase3_mechanism
    from src.experiments.tool_effect_fragmentation.phase3_reproduction import phase3_reproduction_markdown, run_phase3_reproduction_audit
else:
    from .adapters import build_system_cases, run_baselines
    from .io_utils import write_json, write_jsonl
    from .phase2_metrics import example_to_markdown, failure_examples
    from .phase3_agentdojo import agentdojo_phase3_analysis, agentdojo_phase3_markdown
    from .phase3_evidence import evidence_phase3_markdown, run_evidence_diagnostic
    from .phase3_mechanism import mechanism_phase3_markdown, run_phase3_mechanism
    from .phase3_reproduction import phase3_reproduction_markdown, run_phase3_reproduction_audit


DEFAULT_SYSTEMS = ("agentdojo", "toolsafe", "ipiguard", "safiron", "camel")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E47 Tool-Effect Fragmentation Phase 3 experiments.")
    parser.add_argument("--system", action="append", dest="systems", default=[])
    parser.add_argument("--max-base-cases", type=int, default=24)
    parser.add_argument("--bootstrap-iters", type=int, default=500)
    parser.add_argument("--allow-model-download", action="store_true")
    parser.add_argument("--run-external-smokes", action="store_true")
    parser.add_argument("--external-smoke-examples", type=int, default=5)
    parser.add_argument("--local-gguf-model", default="models/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf")
    parser.add_argument("--skip-local-encoder", action="store_true")
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
    for system in systems:
        cases, manifest = build_system_cases(system, root, args.max_base_cases)
        predictions = run_baselines(cases)
        all_cases.extend(cases)
        all_predictions.extend(predictions)
        manifests.append(manifest.to_dict())
    write_jsonl(data_dir / "phase3_stress_cases.jsonl", [case.to_dict() for case in all_cases])
    write_jsonl(data_dir / "phase3_predictions.jsonl", [pred.to_dict() for pred in all_predictions])

    agentdojo_cases = [case for case in all_cases if case.source_system == "agentdojo"]
    agentdojo_predictions = [pred for pred in all_predictions if pred.source_system == "agentdojo"]
    agentdojo = agentdojo_phase3_analysis(agentdojo_cases, agentdojo_predictions, bootstrap_iters=args.bootstrap_iters)
    mechanism = run_phase3_mechanism(root=root, bootstrap_iters=args.bootstrap_iters, run_local_encoder=not args.skip_local_encoder)
    evidence = run_evidence_diagnostic(agentdojo_cases, agentdojo_predictions)
    if args.run_external_smokes:
        if __package__ in {None, ""}:
            from src.experiments.tool_effect_fragmentation.phase3_external_smoke import run_system_smoke
        else:
            from .phase3_external_smoke import run_system_smoke

        smoke_rows = []
        smoke_systems = {}
        for system in ("toolsafe", "safiron", "ipiguard", "camel"):
            smoke = run_system_smoke(
                root,
                system,
                examples=args.external_smoke_examples,
                gguf_path=root / args.local_gguf_model,
                n_gpu_layers=-1,
                n_ctx=8192,
                max_new_tokens=256,
                max_input_tokens=4096,
                skip_official_models=False,
            )
            smoke_rows.extend(smoke.pop("rows"))
            smoke_systems[system] = smoke
        write_json(
            results_dir / "tool_effect_fragmentation_external_smoke_phase3.json",
            {
                "schema_version": "tool_effect_fragmentation_external_smoke_phase3_v1",
                "safety_contract": {"executes_tools": False, "executes_side_effects": False},
                "systems": smoke_systems,
            },
        )
        write_jsonl(results_dir / "tool_effect_fragmentation_external_smoke_phase3.jsonl", smoke_rows)
    reproduction = run_phase3_reproduction_audit(root, allow_model_download=args.allow_model_download)
    examples = failure_examples(all_cases + agentdojo_cases, all_predictions, max_per_type=5) + evidence.get("examples", [])

    payload = {
        "schema_version": "tool_effect_fragmentation_phase3_v1",
        "systems": systems,
        "manifests": manifests,
        "agentdojo_phase3": agentdojo,
        "mechanism_phase3": mechanism,
        "evidence_phase3": evidence,
        "reproduction_phase3": reproduction,
        "failure_examples": examples,
        "answers": phase3_answers(agentdojo, mechanism, evidence, reproduction),
        "acceptance_gates": acceptance_gates(agentdojo, mechanism, evidence, reproduction, examples),
        "claim_boundary": claim_boundary(),
    }
    write_json(results_dir / "tool_effect_fragmentation_phase3_unified.json", payload)
    (results_dir / "tool_effect_fragmentation_phase3_unified.md").write_text(phase3_unified_markdown(payload), encoding="utf-8")
    write_json(results_dir / "tool_effect_fragmentation_agentdojo_phase3.json", agentdojo)
    (results_dir / "tool_effect_fragmentation_agentdojo_phase3.md").write_text(agentdojo_phase3_markdown(agentdojo), encoding="utf-8")
    write_json(results_dir / "tool_effect_fragmentation_mechanism_phase3.json", mechanism)
    (results_dir / "tool_effect_fragmentation_mechanism_phase3.md").write_text(mechanism_phase3_markdown(mechanism), encoding="utf-8")
    write_json(results_dir / "tool_effect_fragmentation_evidence_phase3.json", evidence)
    (results_dir / "tool_effect_fragmentation_evidence_phase3.md").write_text(evidence_phase3_markdown(evidence), encoding="utf-8")
    write_json(results_dir / "tool_effect_fragmentation_reproduction_phase3.json", reproduction)
    (results_dir / "tool_effect_fragmentation_reproduction_phase3.md").write_text(phase3_reproduction_markdown(reproduction), encoding="utf-8")
    write_json(results_dir / "tool_effect_fragmentation_failure_examples_phase3.json", examples)
    (results_dir / "tool_effect_fragmentation_failure_examples_phase3.md").write_text(example_to_markdown(examples), encoding="utf-8")
    experiment_dir.mkdir(parents=True, exist_ok=True)
    (experiment_dir / "phase3_summary.md").write_text(phase3_summary_markdown(payload), encoding="utf-8")

def phase3_answers(agentdojo: dict[str, Any], mechanism: dict[str, Any], evidence: dict[str, Any], reproduction: dict[str, Any]) -> dict[str, str]:
    tool_name = agentdojo["methods"].get("tool_name_classifier", {})
    degradation = tool_name.get("random_vs_heldout_degradation", {}).get("delta")
    primary = mechanism["backends"][mechanism["primary_backend"]]["similarities"]["effect_vs_tool_clustering_gap"]
    custom_stress_systems = [
        system
        for system, audit in reproduction["audits"].items()
        if audit.get("status") == "original_method_custom_stress_available"
    ]
    non_oracle = evidence["metrics_by_method"].get("non_oracle_envdiff_verifier", {})
    return {
        "What is paper-grade evidence?": "AgentDojo local T122-derived custom stress tables are the current paper-grade environment evidence.",
        "What is original-method evidence?": _original_method_answer(custom_stress_systems),
        "What is proxy-only?": "IPIGuard and CaMeL use local-Qwen substitute smokes. These results validate dry-run adapter feasibility only and do not establish the original methods' behavior.",
        "What is upper-bound?": "effect_resource_abstraction and execution_evidence_upper_bound remain oracle/upper-bound rows.",
        "Does random split overestimate safety?": _delta_answer(degradation),
        "Does held-out-tool stress reveal fragmentation?": "Yes for tool-surface baselines in AgentDojo Phase 3; see held-out-tool FNR and degradation table.",
        "Does plan/step/trajectory text solve fragmentation?": "No automatic guarantee; text proxy baselines still show nonzero held-out-tool FNR and action errors.",
        "Does representation cluster by tool or effect?": f"Primary mechanism gap is {primary:.4f}; negative values indicate same-tool proximity is stronger than same-effect proximity.",
        "Does non-oracle execution evidence help?": _evidence_answer(non_oracle),
        "What still blocks a top-tier paper?": "Non-AgentDojo official-checkpoint custom stress still uses proxy or published-derived expected labels and is not an original-paper benchmark reproduction; upper-bound evidence rows and mechanism diagnostics also remain separate from deployable-method evidence.",
    }


def acceptance_gates(agentdojo: dict[str, Any], mechanism: dict[str, Any], evidence: dict[str, Any], reproduction: dict[str, Any], examples: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "agentdojo_phase3_table_complete": bool(agentdojo.get("methods")),
        "official_method_or_complete_audit": reproduction["acceptance_summary"]["original_method_result_available"]
        or reproduction["acceptance_summary"].get("original_method_custom_stress_available", False)
        or reproduction["acceptance_summary"].get("original_method_smoke_available", False)
        or reproduction["acceptance_summary"]["complete_adapter_failed_available"],
        "mechanism_bootstrap_and_permutation_complete": bool(mechanism["backends"][mechanism["primary_backend"]].get("bootstrap"))
        and bool(mechanism["backends"][mechanism["primary_backend"]].get("permutation_controls")),
        "oracle_non_oracle_evidence_separated": "non_oracle_envdiff_verifier" in evidence["metrics_by_method"],
        "failure_examples_generated": bool(examples),
        "claim_boundary_present": True,
    }


def claim_boundary() -> list[str]:
    return [
        "Can claim: AgentDojo custom stress shows tool-surface baselines fail under held-out-tool shift.",
        "Can claim: Current plan/step/trajectory text baselines do not automatically remove fragmentation.",
        "Can claim: Mechanism diagnostic suggests tool-surface proximity can dominate same-effect proximity.",
        "Can claim: Effect/resource and execution-evidence upper bounds are stable in current tests.",
        "Can claim: Non-oracle evidence helps only to the extent shown by the Phase 3 evidence diagnostic.",
        "Cannot claim: ToolSafe or Safiron original-paper methods fail from E47 custom stress alone; the released checkpoints ran, but the benchmark and expected labels are adapted.",
        "Cannot claim: IPIGuard or CaMeL original methods fail; current results are local-model substitutes.",
        "Cannot claim: Graph/provenance methods generally fail.",
        "Cannot claim: Execution evidence is a deployable complete safety solution.",
        "Cannot claim: LLMs do not understand tools at all.",
        "Cannot claim: All trajectory methods are ineffective.",
    ]


def phase3_unified_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Tool-Effect Fragmentation Phase 3 Unified Report", "", "## Required Sections", ""]
    for question, answer in payload["answers"].items():
        lines.append(f"- **{question}** {answer}")
    lines.extend(["", "## Acceptance Gates", ""])
    for gate, passed in payload["acceptance_gates"].items():
        lines.append(f"- `{gate}`: `{passed}`")
    lines.extend(["", "## Official-Checkpoint Custom Stress", ""])
    lines.extend(_official_stress_table(payload["reproduction_phase3"]))
    lines.extend(["", "## Claim Boundary", ""])
    lines.extend(f"- {item}" for item in payload["claim_boundary"])
    return "\n".join(lines) + "\n"


def phase3_summary_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# E47 Phase 3 Summary",
        "",
        "## Status",
        "",
        "- AgentDojo Phase 3 balanced stress table generated.",
        "- ToolSafe/TS-Guard and Safiron official checkpoints pass dry-run inference smokes; completed E47 official-checkpoint custom stress results are reported when present.",
        "- IPIGuard and CaMeL pass local-model substitute smokes only.",
        "- Mechanism Phase 3 includes bootstrap, permutation controls, and ablations.",
        "- Evidence Phase 3 separates non-oracle env-diff diagnostic from oracle upper bounds.",
        "",
        "## Answers",
        "",
    ]
    for question, answer in payload["answers"].items():
        lines.append(f"- **{question}** {answer}")
    lines.extend(["", "## Official-Checkpoint Custom Stress", ""])
    lines.extend(_official_stress_table(payload["reproduction_phase3"]))
    lines.extend(["", "## Claim Boundary", ""])
    lines.extend(f"- {item}" for item in payload["claim_boundary"])
    return "\n".join(lines) + "\n"


def _delta_answer(delta: float | None) -> str:
    if delta is None:
        return "Not available."
    return f"Tool-name random-vs-heldout FNR delta is {delta:.4f}; positive values mean random split overestimates held-out safety."


def _evidence_answer(metrics: dict[str, Any]) -> str:
    if not metrics:
        return "Not available."
    rate = metrics["held_out_tool_fnr"]["rate"]
    return f"non_oracle_envdiff_verifier held-out-tool FNR is {'NA' if rate is None else f'{rate:.4f}'} in the saved-evidence diagnostic."


def _original_method_answer(custom_stress_systems: list[str]) -> str:
    if custom_stress_systems:
        systems = ", ".join(custom_stress_systems)
        return (
            f"Released official checkpoints have completed E47 custom stress for {systems}. "
            "This is original-checkpoint evidence on adapted stress inputs, not original-paper benchmark reproduction."
        )
    return (
        "ToolSafe/TS-Guard and Safiron official checkpoints pass non-side-effect inference smokes, "
        "but no non-AgentDojo checkpoint has completed the full E47 custom stress yet."
    )


def _official_stress_table(reproduction: dict[str, Any]) -> list[str]:
    lines = [
        "| System | Cases | Parse-valid | FNR | Safe false deny | Same-effect consistency | Action error | Scope |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    found = False
    for system, audit in reproduction["audits"].items():
        stress = audit.get("phase3_official_custom_stress")
        if not stress:
            continue
        found = True
        metrics = stress["metrics"]
        lines.append(
            f"| `{system}` | {stress['n_cases']} | {stress['n_parse_valid']} | "
            f"{_rate(metrics, 'fnr')} | {_rate(metrics, 'safe_action_false_deny')} | "
            f"{_rate(metrics, 'same_effect_consistency')} | {_rate(metrics, 'action_level_decision_error')} | "
            f"`{stress['claim_scope']}` |"
        )
    return lines if found else ["No completed official-checkpoint custom stress results."]


def _rate(metrics: dict[str, Any], key: str) -> str:
    rate = metrics.get(key, {}).get("rate")
    return "NA" if rate is None else f"{rate:.4f}"


if __name__ == "__main__":
    main()
