#!/usr/bin/env python3
"""Render final validation tables from passed result JSONs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]


def load(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(relative)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "passed":
        raise RuntimeError(f"result is not passed: {relative}")
    return payload


def indexed(payload: dict[str, Any], outer: str, field: str, value: str) -> dict[str, Any]:
    for row in payload[outer]:
        if row[field] == value:
            return row
    raise KeyError(f"{outer}[{field}={value}]")


def main() -> int:
    deepseek = load(
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "deepseek_benign_interleaved_results.json"
    )
    qwen = load(
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "qwen32_matched_results.json"
    )
    heldout = load(
        "experiments/adaptive-injection-benchmark/results/usenix-heldout-public-families/results.json"
    )
    transfer = load("analysis/results/e79_agentlab_saved_transfer_current_pair_results.json")
    four_view = load(
        "experiments/security-analysis-ablation-and-overhead/results/"
        "c1f-closed-loop-four-view/closed-loop-four-view-report.json"
    )

    matched = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{5pt}",
        r"\caption{Frozen final validation. DeepSeek benign utility is aggregated over four interleaved repetitions. Qwen uses the same checkpoint and exact 97 benign and 629 attack keys for every method.}",
        r"\label{tab:final-matched-validation}",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Model / evaluation & Method & Benign utility & Attack utility & Attack success & Runs \\",
        r"\midrule",
    ]
    for condition, label in (("no_guard", "No guard"), ("spotlighting", "Spotlighting"), ("c1f", r"\sys{}")):
        row = indexed(deepseek, "aggregates", "condition", condition)
        matched.append(
            f"DeepSeek benign & {label} & {row['utility_successes']}/388 & -- & -- & 4 \\\\"
        )
    matched.append(r"\midrule")
    for condition, label in (("no_guard", "No guard"), ("spotlighting", "Spotlighting"), ("c1f", r"\sys{}")):
        row = indexed(qwen, "metrics", "condition", condition)
        matched.append(
            f"Qwen3-32B & {label} & {row['benign_utility_successes']}/97 & "
            f"{row['attack_utility_successes']}/629 & {row['attack_successes']}/629 & 1 \\\\"
        )
    matched.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""])
    (PAPER / "tables/table_final_matched_validation.tex").write_text("\n".join(matched), encoding="utf-8")

    external = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Frozen held-out and saved-transfer results. The 320-case set compares methods under one DeepSeek protocol. AgentLAB is a fixed 303-case saved replay, not adaptive attack generation.}",
        r"\label{tab:final-heldout-transfer}",
        r"\begin{tabular}{llrr}",
        r"\toprule",
        r"Evaluation & Method & Utility & Attack success \\",
        r"\midrule",
    ]
    for method, label in (("no_guard", "No guard"), ("spotlighting", "Spotlighting"), ("c1f", r"\sys{}")):
        row = indexed(heldout, "summaries", "method", method)
        external.append(
            f"Locked families & {label} & {row['utility_successes']}/320 & {row['attack_successes']}/320 \\\\"
        )
    transfer_rows = {
        row["condition"]: row for row in transfer["comparison_metrics"]
    }
    external.extend(
        [
            r"\midrule",
            f"AgentLAB saved & No guard & {transfer_rows['no_guard']['utility_successes']}/303 & {transfer_rows['no_guard']['attack_successes']}/303 \\\\ ",
            f"AgentLAB saved & \\sys{{}} & {transfer_rows['c1f']['utility_successes']}/303 & {transfer_rows['c1f']['attack_successes']}/303 \\\\ ",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )
    (PAPER / "tables/table_final_heldout_transfer.tex").write_text("\n".join(external), encoding="utf-8")

    mechanism = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{4pt}",
        r"\caption{Current-C1f closed-loop mechanism comparison on the frozen 321-case applicability subset. Rates are selection-conditioned, not benchmark-wide estimates.}",
        r"\label{tab:final-four-view}",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Monitor view & Benign util. & Attack util. & Attack success \\",
        r"\midrule",
    ]
    for variant, label in (
        ("no_guard", "No guard"),
        ("whole_call_provenance", "Whole-call provenance"),
        ("effect_only", "Effect only"),
        ("registered_field_c1f", "Registered fields"),
    ):
        row = indexed(four_view, "aggregates", "variant", variant)
        mechanism.append(
            f"{label} & {row['benign_utility_successes']}/48 & "
            f"{row['attack_utility_successes']}/273 & {row['attack_successes']}/273 \\\\"
        )
    mechanism.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    (PAPER / "tables/table_final_four_view.tex").write_text(
        "\n".join(mechanism), encoding="utf-8"
    )
    print(json.dumps({"status": "passed", "tables": 3}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
