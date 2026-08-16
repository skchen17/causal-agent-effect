#!/usr/bin/env python3
"""Run the finite E85 causal-mediation contract validation suite."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.experiments.effect_binding_guard.e85_causal_effect_contract_validation.controlled_suite import (
    atom_policy,
    atomizer_for,
    concrete_policy,
    execute,
    intervention_cases,
)
from src.experiments.effect_binding_guard.e85_causal_effect_contract_validation.evaluator import (
    evaluate_contract,
    summarize_rows,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT_JSON = ROOT / "analysis/results/e85_causal_mediation_report.json"
RESULT_MD = ROOT / "analysis/results/e85_causal_mediation_report.md"
ROWS_JSONL = ROOT / "analysis/results/e85_causal_mediation_rows.jsonl"
METRICS_CSV = ROOT / "analysis/results/e85_causal_mediation_metrics.csv"


CONTRACTS = (
    "none",
    "omit_target",
    "collapse_multi_resource",
    "omit_default_effect",
    "omit_compound_effect",
    "include_placebo",
)


def run() -> dict:
    all_rows = []
    summaries = {}
    cases = intervention_cases()
    for contract_id in CONTRACTS:
        rows = evaluate_contract(
            contract_id=contract_id,
            cases=cases,
            execute=execute,
            atomize=atomizer_for(contract_id),
            concrete_policy=concrete_policy,
            atom_policy=atom_policy,
        )
        all_rows.extend(rows)
        summaries[contract_id] = summarize_rows(rows)

    good = summaries["none"]
    required_failures = {
        "omit_target": summaries["omit_target"]["relation_counts"].get("mediation_gap", 0) >= 1,
        "collapse_multi_resource": summaries["collapse_multi_resource"]["relation_counts"].get(
            "mediation_gap", 0
        )
        >= 1,
        "omit_default_effect": summaries["omit_default_effect"]["relation_counts"].get("mediation_gap", 0)
        >= 1,
        "omit_compound_effect": summaries["omit_compound_effect"]["relation_counts"].get("mediation_gap", 0)
        >= 1,
        "include_placebo": summaries["include_placebo"]["relation_counts"].get("over_sensitive", 0) >= 1,
    }
    status = "passed_bounded_finite_model" if (
        good["atom_mediation_recall"] == 1.0
        and good["atom_mediation_precision"] == 1.0
        and good["surface_invariance_rate"] == 1.0
        and good["authorization_flip_agreement"] == 1.0
        and all(required_failures.values())
    ) else "failed"
    report = {
        "status": status,
        "scope": "finite controlled state-transition model; not AgentDojo or open-domain certification",
        "n_intervention_cases": len(cases),
        "n_contract_variants": len(CONTRACTS),
        "n_rows": len(all_rows),
        "intervention_axes": sorted({case.axis for case in cases}),
        "contract_summaries": summaries,
        "required_ablation_detection": required_failures,
        "claim_boundary": (
            "E85 validates the causal-mediation metric implementation on a finite controlled tool model. "
            "It shows that the checks accept a complete contract and expose target, multi-resource, default, "
            "compound-effect, and placebo failures. It does not establish soundness for AgentDojo or external tools."
        ),
    }

    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ROWS_JSONL.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in all_rows), encoding="utf-8"
    )
    with METRICS_CSV.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "contract_id",
            "n_cases",
            "atom_mediation_recall",
            "atom_mediation_precision",
            "mediation_gap_rate",
            "effect_change_miss_rate",
            "over_sensitivity_rate",
            "surface_invariance_rate",
            "interaction_mediation_rate",
            "authorization_flip_agreement",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for contract_id in CONTRACTS:
            writer.writerow({"contract_id": contract_id, **{key: summaries[contract_id][key] for key in fieldnames[1:]}})
    lines = [
        "# E85 Causal-Mediation Contract Validation",
        "",
        f"- Status: `{status}`",
        f"- Controlled intervention cases: `{len(cases)}`",
        f"- Contract variants: `{len(CONTRACTS)}`",
        "",
        "| Contract | Mediation recall | Mediation precision | Gap rate | Over-sensitivity | Flip agreement |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for contract_id in CONTRACTS:
        item = summaries[contract_id]
        fmt = lambda value: "n/a" if value is None else f"{value:.3f}"
        lines.append(
            f"| {contract_id} | {fmt(item['atom_mediation_recall'])} | "
            f"{fmt(item['atom_mediation_precision'])} | {fmt(item['mediation_gap_rate'])} | "
            f"{fmt(item['over_sensitivity_rate'])} | {fmt(item['authorization_flip_agreement'])} |"
        )
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    RESULT_MD.write_text("\n".join(lines), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
