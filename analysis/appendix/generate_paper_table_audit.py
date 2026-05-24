#!/usr/bin/env python3
"""Generate paper-facing result tables and source-audit notes.

This script intentionally does not rerun experiments. It reads existing JSON
outputs and writes a Markdown audit file so manuscript numbers can be traced
back to concrete result files.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
LEXICAL_SCRIPT = ROOT / "lexical_control_experiment.py"
LEXICAL_MANIFEST = ANALYSIS / "lexical_control_manifest.json"
LEXICAL_RESULT = ANALYSIS / "lexical_control_qwen3-8b_scenarios_merged_lexical_control.json"
PIIA_RAW = ANALYSIS / "iia_true_raw_qwen3-8b_scenarios_merged.jsonl"
PIIA_BOOT = ANALYSIS / "iia_true_bootstrap_qwen3-8b_scenarios_merged.json"


SOURCES = {
    "baseline": ANALYSIS / "baseline_comparison_qwen3-8b_scenarios_merged.json",
    "fnr_frag": ANALYSIS / "fnr_frag_qwen3-8b_scenarios_merged.json",
    "piia": ANALYSIS / "iia_true_qwen3-8b_scenarios_merged.json",
    "contrastive": ANALYSIS / "contrastive_qwen3-8b_scenarios_merged.json",
    "ablation": ANALYSIS / "ablation_qwen3-8b_scenarios_merged.json",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fmt(x: Any, ndigits: int = 3) -> str:
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if math.isnan(x):
            return "nan"
        return f"{x:.{ndigits}f}"
    return str(x)


def wilson_interval(p_hat: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson interval for a binomial proportion.

    p_hat is the reported proportion. We infer the nearest integer count from
    p_hat * n because the JSON stores rates rather than confusion matrices.
    """
    if n <= 0:
        return (float("nan"), float("nan"))
    k = int(round(p_hat * n))
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) / n) + z**2 / (4 * n**2)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def representative_loto_rows(loto_table: dict[str, Any]) -> list[list[str]]:
    """Use the same representative rows as the current manuscript table.

    For most effects, choose the held-out tool with highest heldout_FNR. For
    content_fetched, include both held-out forms because the paper discusses
    both. For tool_error, include web_search to show negative Delta FNR / zero
    ToolProxyGap. "Within FNR" is held-out-tool internal CV, while "Heldout
    FNR" is all-but-heldout LOTO.
    """
    rows: list[list[str]] = []
    for effect, by_tool in loto_table.items():
        if effect == "content_fetched":
            tools = ["terminal", "web_fetch"]
        elif effect == "tool_error":
            tools = ["web_search"]
        else:
            tools = [max(by_tool.items(), key=lambda item: item[1]["heldout_FNR"])[0]]

        for heldout_tool in tools:
            item = by_tool[heldout_tool]
            delta = item["heldout_FNR"] - item["within_FNR"]
            rows.append(
                [
                    effect,
                    "all-but-" + heldout_tool,
                    str(item["n_pos"]),
                    heldout_tool,
                    fmt(item["within_FNR"]),
                    fmt(item["heldout_FNR"]),
                    fmt(delta),
                    fmt(max(0.0, delta)),
                    "[" + ", ".join(fmt(v) for v in wilson_interval(item["heldout_FNR"], item["n_pos"])) + "]",
                ]
            )
    return rows


def safety_rows(fnr_frag: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    alpha_source = fnr_frag.get("alpha_loto", fnr_frag.get("alpha", {}))
    for effect, by_tool in fnr_frag["loto_fnrs"].items():
        for tool, beta in by_tool.items():
            alpha = alpha_source.get(effect, {}).get(tool)
            if alpha is None:
                continue
            rows.append([effect, tool, fmt(beta), fmt(alpha), fmt(max(0.0, beta - alpha))])
    rows.sort(key=lambda row: float(row[4]), reverse=True)
    return rows


def deployed_rows(fnr_frag: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for effect, by_tool in fnr_frag["deployed_fnrs"].items():
        for tool, fnr in by_tool.items():
            fpr = fnr_frag["fpr"].get(effect, {}).get(tool, "NA")
            rows.append([effect, tool, fmt(fnr), fmt(fpr) if isinstance(fpr, float) else fpr])
    return rows


def baseline_rows(baselines: dict[str, Any]) -> list[list[str]]:
    rows = []
    for effect, item in baselines.items():
        rows.append(
            [
                effect,
                fmt(item["pooled_worstFNR"]),
                fmt(item["balanced_worstFNR"]),
                fmt(item["tool_cond_worstFNR"]),
                fmt(item.get("group_reweight_worstFNR", item.get("group_dro_worstFNR"))),
            ]
        )
    return rows


def piia_rows(piia: list[dict[str, Any]], piia_boot: dict[str, Any] | None = None) -> list[list[str]]:
    rows = []
    for item in piia:
        boot_item = (piia_boot or {}).get("effects", {}).get(item["effect"], {})
        drop_ci = boot_item.get("piia_drop_ci95")
        rows.append(
            [
                item["effect"],
                fmt(item["iia_within"]),
                fmt(item["iia_cross"]),
                fmt(item["iia_within"] - item["iia_cross"]),
                "[" + ", ".join(fmt(v) for v in drop_ci) + "]" if drop_ci else "NA",
                str(item["n_pairs"]),
            ]
        )
    return rows


def contrastive_rows(contrastive: dict[str, Any], ablation: dict[str, Any]) -> tuple[list[list[str]], list[str]]:
    rows = []
    notes = []
    dim64 = ablation.get("dim_ablation", {})
    for effect, by_tool in contrastive.items():
        max_pre = max(item["pre"] for item in by_tool.values())
        max_post = max(item["post"] for item in by_tool.values())
        dim64_post = dim64.get(effect, {}).get("64", {}).get("max_post")
        rows.append(
            [
                effect,
                fmt(max_pre),
                fmt(max_post),
                fmt(max_pre - max_post),
                fmt(dim64_post) if dim64_post is not None else "NA",
            ]
        )
        if dim64_post is not None and abs(max_post - dim64_post) > 1e-4:
            notes.append(
                f"- `{effect}` has contrastive max post-FNR {fmt(max_post)} but dim-ablation k=64 max post-FNR {fmt(dim64_post)}."
            )
    return rows, notes


def main() -> None:
    baseline = load_json(SOURCES["baseline"])
    fnr_frag = load_json(SOURCES["fnr_frag"])
    piia = load_json(SOURCES["piia"])
    piia_boot = load_json(PIIA_BOOT) if PIIA_BOOT.exists() else None
    contrastive = load_json(SOURCES["contrastive"])
    ablation = load_json(SOURCES["ablation"])

    contrastive_table, contrastive_notes = contrastive_rows(contrastive, ablation)
    if PIIA_BOOT.exists():
        piia_note = f"Source-cluster bootstrap CIs are available at `{PIIA_BOOT.relative_to(ROOT)}` and use raw outcomes from `{PIIA_RAW.relative_to(ROOT)}`."
    elif PIIA_RAW.exists():
        piia_note = f"Raw intervention outcomes are available at `{PIIA_RAW.relative_to(ROOT)}`; run `analysis/bootstrap_iia_raw.py` to create source-cluster bootstrap CIs."
    else:
        piia_note = "The pIIA rows are descriptive diagnostics. Raw intervention outcomes are not present yet; run `interchange_intervention_true.py` without `--no-save-raw` to create JSONL for bootstrap CIs."

    parts = [
        "# Paper Table Audit",
        "",
        "> Generated by `analysis/generate_paper_table_audit.py`. This file traces manuscript-facing numbers to existing JSON outputs. It does not rerun experiments.",
        "",
        "## Sources",
        "",
        table(["Alias", "Path"], [[alias, str(path.relative_to(ROOT))] for alias, path in SOURCES.items()]),
        "",
        "## Deployed FNR/FPR Point Estimates",
        "",
        "These are point estimates for fully covered probes. They are not statistical SafeInv certificates without confidence upper bounds.",
        "",
        table(["Effect", "Tool", "Deploy FNR", "Deploy FPR"], deployed_rows(fnr_frag)),
        "",
        "## Representative LOTO Stress-Test FNR",
        "",
        "Wilson intervals are approximate and infer integer miss counts from stored rates.",
        "",
        table(
            [
                "Effect",
                "Training source",
                "Heldout N+",
                "Heldout",
                "Heldout within FNR",
                "Heldout FNR",
                "Delta FNR",
                "ToolProxyGap",
                "Heldout FNR 95% Wilson CI",
            ],
            representative_loto_rows(baseline["loto_table"]),
        ),
        "",
        "## LOTO Counterfactual Safety Lower Bound",
        "",
        table(["Effect", "Heldout tool", "beta_LOTO", "alpha_LOTO", "[beta-alpha]_+"], safety_rows(fnr_frag)),
        "",
        "## Baseline Worst-Tool FNR",
        "",
        table(["Effect", "Pooled", "Balanced", "Tool-cond", "Group reweight"], baseline_rows(baseline["baselines"])),
        "",
        "## pIIA Diagnostic",
        "",
        piia_note,
        "",
        table(["Effect", "pIIA-within", "pIIA-cross", "pIIA-Drop", "pIIA-Drop 95% CI", "Pair count"], piia_rows(piia, piia_boot)),
        "",
        "## Contrastive Projection",
        "",
        table(["Effect", "Max pre-FNR", "Max post-FNR", "Delta", "Dim-ablation k=64 max post-FNR"], contrastive_table),
        "",
        "## Audit Notes",
        "",
    ]
    if contrastive_notes:
        parts.extend(contrastive_notes)
    else:
        parts.append("- No contrastive-vs-ablation max post-FNR discrepancies found.")
    if LEXICAL_RESULT.exists():
        parts.append(f"- Lexical normalization/control result JSON found at `{LEXICAL_RESULT.relative_to(ROOT)}`.")
    elif LEXICAL_SCRIPT.exists() and LEXICAL_MANIFEST.exists():
        parts.append(
            f"- Lexical-control dataset generation is scripted in `{LEXICAL_SCRIPT.relative_to(ROOT)}` and documented by `{LEXICAL_MANIFEST.relative_to(ROOT)}`, but the embedding-backed result JSON is still missing."
        )
    else:
        parts.append(
            "- Lexical normalization/control numbers currently appear in `paper/main.tex`, but no dedicated script/result JSON was found during audit. P1 should either add that output or move the claim out of the main paper."
        )
    if PIIA_RAW.exists():
        parts.append(f"- pIIA raw outcomes found at `{PIIA_RAW.relative_to(ROOT)}`; CI reporting can now be audited from intervention-level records.")
    else:
        parts.append("- pIIA uncertainty cannot be audited from aggregate JSON alone; retain descriptive wording unless raw intervention outcomes are saved.")
    if PIIA_BOOT.exists():
        parts.append(f"- pIIA source-cluster bootstrap intervals found at `{PIIA_BOOT.relative_to(ROOT)}`.")

    output = ANALYSIS / "paper_table_audit.md"
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
