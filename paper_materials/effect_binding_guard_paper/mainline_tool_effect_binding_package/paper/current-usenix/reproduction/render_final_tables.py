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


def pct(numerator: int, denominator: int) -> str:
    return f"{100 * numerator / denominator:.1f}\\%"


def main() -> int:
    deepseek = load(
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "deepseek_benign_interleaved_results.json"
    )
    qwen = load(
        "experiments/unified-agent-security-baselines/results/"
        "current-c1f-strong-baseline-rerun/results.json"
    )
    heldout = load(
        "experiments/adaptive-injection-benchmark/results/usenix-heldout-public-families/results.json"
    )
    concrete_authorizer = load(
        "experiments/human-authority-and-causal-validation/results/"
        "concrete-atom-authorizer-mechanism/concrete-atom-authorizer-report.json"
    )

    matched = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{5pt}",
        r"\caption{Matched runtime comparison. DeepSeek benign utility uses four interleaved repetitions ($N=388$ per method). Qwen3-32B uses the same checkpoint and exact 97 benign and 629 attack keys for every method. Spotlighting denotes AgentDojo's built-in paper-defined defense; daggered methods are comparable local adapters, not original-paper reproductions.}",
        r"\label{tab:final-matched-validation}",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Model / evaluation & Method & Benign utility & Attack utility & Attack success & Runs \\",
        r"\midrule",
    ]
    for condition, label in (("no_guard", "No guard"), ("spotlighting", "Spotlighting"), ("c1f", r"\sys{}")):
        row = indexed(deepseek, "aggregates", "condition", condition)
        matched.append(
            f"DeepSeek benign & {label} & {pct(row['utility_successes'], 388)} & -- & -- & 4 \\\\"
        )
    matched.append(r"\midrule")
    for method, label in (
        ("no_guard", "No guard"),
        ("spotlighting", "Spotlighting"),
        ("prompt_sandwiching", r"Prompt Sandwiching$^{\dagger}$"),
        ("promptarmor_local", r"PromptArmor-style$^{\dagger}$"),
        ("c1f", r"\sys{}"),
    ):
        row = indexed(qwen, "metrics", "method", method)
        matched.append(
            f"Qwen3-32B & {label} & {pct(row['benign_utility_successes'], 97)} & "
            f"{pct(row['attack_utility_successes'], 629)} & {pct(row['attack_successes'], 629)} & 1 \\\\"
        )
    matched.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2pt}\parbox{\textwidth}{\footnotesize "
            r"$^{\dagger}$Comparable local prompting adapters implemented for this paper under the common-input protocol, not reproductions of any original-paper evaluation.}",
            r"\end{table*}",
            "",
        ]
    )
    (PAPER / "tables/table_final_matched_validation.tex").write_text("\n".join(matched), encoding="utf-8")

    external = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Frozen public-family result under one DeepSeek protocol ($N=320$ per method).}",
        r"\label{tab:final-heldout}",
        r"\begin{tabular}{lrr}",
        r"\toprule",
        r"Method & Utility & Attack success \\",
        r"\midrule",
    ]
    for method, label in (("no_guard", "No guard"), ("spotlighting", "Spotlighting"), ("c1f", r"\sys{}")):
        row = indexed(heldout, "summaries", "method", method)
        external.append(
            f"{label} & {pct(row['utility_successes'], 320)} & {pct(row['attack_successes'], 320)} \\\\"
        )
    external.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )
    (PAPER / "tables/table_final_heldout.tex").write_text(
        "\n".join(external), encoding="utf-8"
    )

    authorizer = [
        r"\begin{table}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\caption{Finite ToolSandbox authorizer check. UPA is unsafe pre-allow; FD is false denial.}",
        r"\label{tab:concrete-atom-authorizer}",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"View & UPA & FD & Coverage & Accuracy \\",
        r"\midrule",
    ]
    labels = {
        "whole_call_tool_name": "Tool name",
        "raw_arguments_exact": "Exact raw args",
        "common_effect_atoms": "Common-field view",
        "concrete_effect_atoms": "Concrete atoms",
        "source_effect_oracle": "Source oracle",
    }
    for method in labels:
        row = indexed(concrete_authorizer, "metrics", "method", method)
        authorizer.append(
            f"{labels[method]} & {100 * row['unsafe_pre_allow']['rate']:.1f}\\% & "
            f"{100 * row['safe_false_deny']['rate']:.1f}\\% & {100 * row['coverage']['rate']:.1f}\\% & "
            f"{100 * row['decision_accuracy']['rate']:.1f}\\% \\\\"
        )
    authorizer.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2pt}\parbox{0.98\linewidth}{\footnotesize All 232 ordered queries use one executed context as the allowed effect multiset and check another context of the same tool.}",
            r"\end{table}",
            "",
        ]
    )
    (PAPER / "tables/table_concrete_atom_authorizer.tex").write_text(
        "\n".join(authorizer), encoding="utf-8"
    )
    print(json.dumps({"status": "passed", "tables": 3}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
