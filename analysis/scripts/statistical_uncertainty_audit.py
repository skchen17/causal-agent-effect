"""Build a statistical uncertainty audit for the current paper results.

The script reads existing JSON/JSONL artifacts and writes:

- analysis/statistical_uncertainty_audit.json
- analysis/statistical_uncertainty_audit.md

It is intentionally an audit layer. It does not rerun probes or change any
paper results. Proportion intervals are reconstructed from stored rates and
positive counts, so they should be treated as review-facing diagnostics rather
than a replacement for raw prediction-level intervals.
"""

from __future__ import annotations

import json
import math
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
DATA = ROOT / "data"

MAIN_DATA = DATA / "scenarios_merged.jsonl"
CHAIN_DATA = DATA / "causal_chain_conditioning_v2.jsonl"

LOTO_PATH = ANALYSIS / "baseline_comparison_qwen3-8b_scenarios_merged.json"
FNR_FRAG_PATH = ANALYSIS / "fnr_frag_qwen3-8b_scenarios_merged.json"
STRICT_PATH = ANALYSIS / "contrastive_strict_lopo_qwen3-8b_scenarios_merged.json"
MULTISEED_PATH = ANALYSIS / "contrastive_multiseed_qwen3-8b_scenarios_merged.json"
CHAIN_PATH = ANALYSIS / "causal_chain_mechanism_qwen3-8b_causal_chain_conditioning_v2.json"
PIIA_BOOT_PATH = ANALYSIS / "iia_true_bootstrap_qwen3-8b_scenarios_merged.json"

OUT_JSON = ANALYSIS / "statistical_uncertainty_audit.json"
OUT_MD = ANALYSIS / "statistical_uncertainty_audit.md"
PRIMARY_DATASET = "scenarios_merged"


def resolve_data_name(model: str, data: str) -> str:
    if data.startswith(f"{model}_"):
        return data
    return f"{model}_{data}"


def output_suffix(data: str) -> str:
    if data == "scenarios_merged":
        return ""
    return "_" + data.removeprefix("scenarios_")


def configure_paths(data: str, model: str) -> None:
    global MAIN_DATA, LOTO_PATH, FNR_FRAG_PATH, STRICT_PATH, MULTISEED_PATH
    global PIIA_BOOT_PATH, OUT_JSON, OUT_MD, PRIMARY_DATASET

    PRIMARY_DATASET = data
    model_data = resolve_data_name(model, data)
    suffix = output_suffix(data)

    MAIN_DATA = DATA / f"{data}.jsonl"
    LOTO_PATH = ANALYSIS / f"baseline_comparison_{model_data}.json"
    FNR_FRAG_PATH = ANALYSIS / f"fnr_frag_{model_data}.json"
    STRICT_PATH = ANALYSIS / f"contrastive_strict_lopo_{model_data}.json"
    MULTISEED_PATH = ANALYSIS / f"contrastive_multiseed_{model_data}.json"
    PIIA_BOOT_PATH = ANALYSIS / f"iia_true_bootstrap_{model_data}.json"
    OUT_JSON = ANALYSIS / f"statistical_uncertainty_audit{suffix}.json"
    OUT_MD = ANALYSIS / f"statistical_uncertainty_audit{suffix}.md"


def missing_section(path: Path, kind: str) -> dict[str, Any]:
    return {
        "available": False,
        "source": str(path.relative_to(ROOT)),
        "missing_reason": f"{kind} artifact not found for dataset `{PRIMARY_DATASET}`.",
        "summary": {},
        "rows": [],
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def rnd(x: float | None, digits: int = 4) -> float | None:
    if x is None:
        return None
    return round(float(x), digits)


def wilson_ci_from_k(k: int, n: int, z: float = 1.96) -> list[float | None]:
    if n <= 0:
        return [None, None]
    phat = k / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def wilson_ci_from_rate(rate: float | None, n_pos: int | None) -> dict[str, Any]:
    if rate is None or n_pos is None or n_pos <= 0:
        return {"n_positive": n_pos, "estimated_false_negatives": None, "ci95": [None, None]}
    k = int(round(float(rate) * int(n_pos)))
    k = max(0, min(k, int(n_pos)))
    return {
        "n_positive": int(n_pos),
        "estimated_false_negatives": k,
        "ci95": wilson_ci_from_k(k, int(n_pos)),
        "note": "Wilson CI reconstructed from stored rounded rate and n_positive.",
    }


def mean_ci(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "std": None, "ci95_mean": [None, None]}
    n = len(values)
    m = mean(values)
    if n == 1:
        return {"n": 1, "mean": rnd(m), "std": 0.0, "ci95_mean": [rnd(m), rnd(m)]}
    sd = pstdev(values)
    se = sd / math.sqrt(n)
    tcrit_by_df = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
    }
    tcrit = tcrit_by_df.get(n - 1, 1.96)
    half = tcrit * se
    return {
        "n": n,
        "mean": rnd(m),
        "std": rnd(sd),
        "ci95_mean": [rnd(max(0.0, m - half)), rnd(min(1.0, m + half))],
        "note": "Mean CI uses sample values in the result file; with five seeds this remains descriptive.",
    }


def effect_names(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    return list(rows[0].get("effects", {}).keys())


def dataset_cell_audit(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    effects = effect_names(rows)
    tools = sorted({r.get("tool_name", "unknown") for r in rows})
    context_counts = Counter(str(r.get("context_type", "missing")) for r in rows)
    cells = []

    for effect in effects:
        for tool in tools:
            tool_rows = [r for r in rows if r.get("tool_name") == tool]
            n = len(tool_rows)
            n_pos = sum(1 for r in tool_rows if int(r.get("effects", {}).get(effect, 0)) == 1)
            n_neg = n - n_pos
            if n == 0:
                continue
            cells.append({
                "effect": effect,
                "tool": tool,
                "n": n,
                "n_positive": n_pos,
                "n_negative": n_neg,
                "positive_rate": rnd(n_pos / n if n else None),
                "loto_evaluable": bool(n_pos >= 5 and n_neg >= 5),
                "below_30_positive": bool(0 < n_pos < 30),
                "below_50_positive": bool(0 < n_pos < 50),
                "zero_positive": bool(n_pos == 0),
            })

    positive_cells = [c for c in cells if c["n_positive"] > 0]
    low_pos = [c for c in positive_cells if c["n_positive"] < 30]
    very_low_pos = [c for c in positive_cells if c["n_positive"] < 10]
    return {
        "name": name,
        "n_rows": len(rows),
        "n_tools": len(tools),
        "n_effects": len(effects),
        "tools": tools,
        "context_counts": dict(context_counts),
        "summary": {
            "n_cells": len(cells),
            "n_positive_cells": len(positive_cells),
            "n_zero_positive_cells": len([c for c in cells if c["n_positive"] == 0]),
            "n_positive_cells_below_30": len(low_pos),
            "n_positive_cells_below_50": len([c for c in positive_cells if c["n_positive"] < 50]),
            "n_positive_cells_below_10": len(very_low_pos),
            "min_positive_count": min((c["n_positive"] for c in positive_cells), default=0),
            "median_positive_count": median_int([c["n_positive"] for c in positive_cells]),
        },
        "low_positive_cells": sorted(low_pos, key=lambda c: (c["n_positive"], c["effect"], c["tool"])),
        "cells": cells,
    }


def median_int(values: list[int]) -> int | None:
    if not values:
        return None
    vals = sorted(values)
    mid = len(vals) // 2
    if len(vals) % 2:
        return int(vals[mid])
    return int(round((vals[mid - 1] + vals[mid]) / 2))


def loto_audit() -> dict[str, Any]:
    if not LOTO_PATH.exists():
        section = missing_section(LOTO_PATH, "LOTO/baseline")
        section.update({
            "summary": {
                "n_rows": 0,
                "n_small_n_rows_lt30": 0,
                "n_rows_lt50": 0,
                "max_heldout_fnr": None,
                "max_fnr_gap": None,
            },
            "top_high_fnr_rows": [],
            "small_n_high_fnr_rows": [],
        })
        return section
    data = load_json(LOTO_PATH)
    table = data["loto_table"]
    rows = []
    for effect, tools in sorted(table.items()):
        for tool, item in sorted(tools.items()):
            n_pos = int(item["n_pos"])
            n_neg = int(item["n_neg"])
            held = item.get("heldout_FNR")
            within = item.get("within_FNR")
            row = {
                "effect": effect,
                "tool": tool,
                "n_positive": n_pos,
                "n_negative": n_neg,
                "within_fnr": within,
                "within_fnr_ci95": wilson_ci_from_rate(within, n_pos)["ci95"],
                "heldout_fnr": held,
                "heldout_fnr_ci95": wilson_ci_from_rate(held, n_pos)["ci95"],
                "fnr_gap": item.get("FNR_gap"),
                "small_n_flag": bool(n_pos < 30),
                "main_conference_cell_flag": bool(n_pos < 50),
            }
            rows.append(row)

    return {
        "source": str(LOTO_PATH.relative_to(ROOT)),
        "methodology": {
            "training_split": "leave one tool out; train on all other tools for the target effect",
            "model": "sklearn LogisticRegression(C=1.0, class_weight='balanced')",
            "decision_rule": "predict(), equivalent to the classifier's default 0.5 binary decision threshold",
            "ci_method": "Wilson CI reconstructed from rounded FNR and n_positive",
        },
        "summary": {
            "n_rows": len(rows),
            "n_small_n_rows_lt30": len([r for r in rows if r["small_n_flag"]]),
            "n_rows_lt50": len([r for r in rows if r["main_conference_cell_flag"]]),
            "max_heldout_fnr": max((r["heldout_fnr"] for r in rows), default=None),
            "max_fnr_gap": max((r["fnr_gap"] for r in rows), default=None),
        },
        "top_high_fnr_rows": sorted(rows, key=lambda r: (-r["heldout_fnr"], r["n_positive"]))[:12],
        "small_n_high_fnr_rows": sorted(
            [r for r in rows if r["small_n_flag"]],
            key=lambda r: (-r["heldout_fnr"], r["n_positive"], r["effect"], r["tool"]),
        ),
        "rows": rows,
    }


def baseline_audit(loto_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not LOTO_PATH.exists():
        section = missing_section(LOTO_PATH, "baseline")
        section.update({
            "summary": {
                "n_rows": 0,
                "methods": [],
                "n_small_n_rows_lt30": 0,
                "contains_group_dro_alias": False,
            }
        })
        return section
    data = load_json(LOTO_PATH)
    baselines = data["baselines"]
    n_lookup = {(r["effect"], r["tool"]): r for r in loto_rows}
    rows = []
    for effect, item in sorted(baselines.items()):
        for key, value in sorted(item.items()):
            if not key.endswith("_worstFNR"):
                continue
            method = key.removesuffix("_worstFNR")
            if method == "group_dro":
                method_note = "Compatibility alias; current implementation is group reweighting, not true worst-group optimization."
            else:
                method_note = None
            tool = item.get(f"{method}_worstTool")
            lookup = n_lookup.get((effect, tool), {})
            rows.append({
                "effect": effect,
                "method": method,
                "worst_fnr": value,
                "worst_tool": tool,
                "n_positive_at_worst_tool": lookup.get("n_positive"),
                "ci95": wilson_ci_from_rate(value, lookup.get("n_positive")).get("ci95"),
                "small_n_flag": bool((lookup.get("n_positive") or 0) < 30),
                "note": method_note,
            })
    return {
        "source": str(LOTO_PATH.relative_to(ROOT)),
        "summary": {
            "n_rows": len(rows),
            "methods": sorted({r["method"] for r in rows}),
            "n_small_n_rows_lt30": len([r for r in rows if r["small_n_flag"]]),
            "contains_group_dro_alias": any(r["method"] == "group_dro" for r in rows),
        },
        "rows": rows,
    }


def strict_lopo_audit() -> dict[str, Any]:
    if not STRICT_PATH.exists():
        section = missing_section(STRICT_PATH, "strict LOPO")
        section.update({
            "reported_summary": {},
            "summary": {
                "n_evaluable_effects": 0,
                "n_not_evaluable_effects": 0,
                "n_tool_case_rows": 0,
                "n_small_n_rows_lt30": 0,
                "max_strict_post_fnr": None,
                "mean_delta_fnr": None,
            },
            "not_evaluable_effects": [],
            "top_remaining_post_fnr_rows": [],
        })
        return section
    data = load_json(STRICT_PATH)
    rows = []
    not_evaluable = []
    for effect, item in sorted(data["effects"].items()):
        if item.get("status") != "evaluable":
            not_evaluable.append({
                "effect": effect,
                "n_forms": item.get("n_forms"),
                "reason": item.get("reason"),
            })
            continue
        for pair in item.get("pairs", []):
            heldout_pair = pair.get("heldout_pair")
            for result in pair.get("tool_results", []):
                n_pos = int(result["n_positive"])
                raw_fnr = result.get("raw_fnr")
                post_fnr = result.get("strict_post_fnr")
                rows.append({
                    "effect": effect,
                    "heldout_pair": heldout_pair,
                    "tool": result.get("tool"),
                    "n_positive": n_pos,
                    "raw_fnr": raw_fnr,
                    "raw_fnr_ci95": wilson_ci_from_rate(raw_fnr, n_pos)["ci95"],
                    "strict_post_fnr": post_fnr,
                    "strict_post_fnr_ci95": wilson_ci_from_rate(post_fnr, n_pos)["ci95"],
                    "delta_fnr": result.get("delta_fnr"),
                    "small_n_flag": bool(n_pos < 30),
                })
    return {
        "source": str(STRICT_PATH.relative_to(ROOT)),
        "reported_summary": data.get("summary", {}),
        "methodology": {
            "training_split": "leave one positive tool-pair out from contrastive pairs, then evaluate affected tools",
            "seed_variance": "not available in current strict LOPO artifact",
            "ci_method": "Wilson CI reconstructed from rounded FNR and n_positive",
        },
        "summary": {
            "n_evaluable_effects": len([e for e, item in data["effects"].items() if item.get("status") == "evaluable"]),
            "n_not_evaluable_effects": len(not_evaluable),
            "n_tool_case_rows": len(rows),
            "n_small_n_rows_lt30": len([r for r in rows if r["small_n_flag"]]),
            "max_strict_post_fnr": max((r["strict_post_fnr"] for r in rows), default=None),
            "mean_delta_fnr": rnd(mean([r["delta_fnr"] for r in rows if r["delta_fnr"] is not None])) if rows else None,
        },
        "not_evaluable_effects": not_evaluable,
        "top_remaining_post_fnr_rows": sorted(rows, key=lambda r: (-r["strict_post_fnr"], r["n_positive"]))[:12],
        "rows": rows,
    }


def multiseed_audit() -> dict[str, Any]:
    if not MULTISEED_PATH.exists():
        section = missing_section(MULTISEED_PATH, "contrastive multiseed")
        section.update({
            "config": {},
            "summary": {
                "n_rows": 0,
                "n_seeds": 0,
                "max_mean_post_fnr": None,
                "max_population_std": None,
            },
            "top_post_fnr_rows": [],
        })
        return section
    data = load_json(MULTISEED_PATH)
    rows = []
    for effect, tools in sorted(data["results"].items()):
        for tool, item in sorted(tools.items()):
            values = [float(v) for v in item.get("values", [])]
            ci = mean_ci(values)
            rows.append({
                "effect": effect,
                "tool": tool,
                "n_seeds": ci["n"],
                "post_fnr_mean": item.get("post_fnr_mean"),
                "post_fnr_std_population": item.get("post_fnr_std"),
                "post_fnr_values": values,
                "post_fnr_ci95_mean": ci["ci95_mean"],
                "aggregation": item.get("aggregation"),
                "train_protocol": data.get("config", {}).get("train_protocol"),
                "note": "Full-training projection uses observed cross-form positive pairs; not strict coverage-missing evidence.",
            })
    return {
        "source": str(MULTISEED_PATH.relative_to(ROOT)),
        "config": data.get("config", {}),
        "summary": {
            "n_rows": len(rows),
            "n_seeds": len(data.get("config", {}).get("seeds", [])),
            "max_mean_post_fnr": max((r["post_fnr_mean"] for r in rows), default=None),
            "max_population_std": max((r["post_fnr_std_population"] for r in rows), default=None),
        },
        "top_post_fnr_rows": sorted(rows, key=lambda r: (-r["post_fnr_mean"], -r["post_fnr_std_population"]))[:12],
        "rows": rows,
    }


def causal_chain_audit() -> dict[str, Any]:
    if not CHAIN_PATH.exists():
        section = missing_section(CHAIN_PATH, "causal-chain")
        section.update({
            "reported_summary": {},
            "summary": {
                "n_group_rows": 0,
                "n_tool_rows": 0,
                "n_small_n_tool_rows_lt30": 0,
                "n_small_n_group_rows_lt30": 0,
                "max_held_fnr": None,
            },
            "small_n_high_fnr_rows": [],
            "group_rows": [],
        })
        return section
    data = load_json(CHAIN_PATH)
    rows = []
    group_rows = []
    for effect, groups in sorted(data["effects"].items()):
        for group, item in sorted(groups.items()):
            group_rows.append({
                "effect": effect,
                "group": group,
                "n_samples": item.get("n_samples"),
                "n_positive": item.get("n_positive"),
                "max_held_fnr": item.get("max_held_fnr"),
                "max_within_fnr": item.get("max_within_fnr"),
                "toolproxy_gap": item.get("toolproxy_gap"),
                "effect_probe_auc": item.get("effect_probe_auc"),
                "small_n_group_flag": bool((item.get("n_positive") or 0) < 30),
            })
            for result in item.get("tool_results", []):
                n_pos = int(result.get("n_positive") or 0)
                held = result.get("held_fnr")
                within = result.get("within_fnr")
                rows.append({
                    "effect": effect,
                    "group": group,
                    "tool": result.get("tool"),
                    "n": result.get("n"),
                    "n_positive": n_pos,
                    "held_fnr": held,
                    "held_fnr_ci95": wilson_ci_from_rate(held, n_pos)["ci95"],
                    "within_fnr": within,
                    "within_fnr_ci95": wilson_ci_from_rate(within, n_pos)["ci95"],
                    "toolproxy_gap": result.get("toolproxy_gap"),
                    "held_auc": result.get("held_auc"),
                    "small_n_flag": bool(0 < n_pos < 30),
                })
    return {
        "source": str(CHAIN_PATH.relative_to(ROOT)),
        "reported_summary": data.get("summary", {}),
        "methodology": {
            "training_split": "per condition/group leave-one-tool-out diagnostic",
            "focus_effects": sorted(data.get("effects", {}).keys()),
            "seed_variance": "not available in current causal-chain artifact",
            "ci_method": "Wilson CI reconstructed from rounded FNR and n_positive",
        },
        "summary": {
            "n_group_rows": len(group_rows),
            "n_tool_rows": len(rows),
            "n_small_n_tool_rows_lt30": len([r for r in rows if r["small_n_flag"]]),
            "n_small_n_group_rows_lt30": len([r for r in group_rows if r["small_n_group_flag"]]),
            "max_held_fnr": max((r["held_fnr"] for r in rows if r["held_fnr"] is not None), default=None),
        },
        "small_n_high_fnr_rows": sorted(
            [r for r in rows if r["small_n_flag"] and r["held_fnr"] is not None],
            key=lambda r: (-r["held_fnr"], r["n_positive"], r["effect"], r["group"], r["tool"]),
        )[:20],
        "group_rows": group_rows,
        "rows": rows,
    }


def piia_audit() -> dict[str, Any]:
    if not PIIA_BOOT_PATH.exists():
        section = missing_section(PIIA_BOOT_PATH, "pIIA bootstrap")
        section.update({
            "raw_path": None,
            "n_raw_outcomes": 0,
            "summary": {
                "n_effects": 0,
                "max_piia_drop": None,
                "max_piia_drop_ci_width": None,
            },
            "top_piia_drop_rows": [],
        })
        return section
    data = load_json(PIIA_BOOT_PATH)
    rows = []
    for effect, item in sorted(data["effects"].items()):
        rows.append({
            "effect": effect,
            "n_raw_outcomes": item.get("n_raw_outcomes"),
            "n_source_examples": item.get("n_source_examples"),
            "n_direction_pairs": item.get("n_direction_pairs"),
            "iia_within": item.get("iia_within"),
            "iia_within_ci95": item.get("iia_within_ci95"),
            "iia_cross": item.get("iia_cross"),
            "iia_cross_ci95": item.get("iia_cross_ci95"),
            "piia_drop": item.get("piia_drop"),
            "piia_drop_ci95": item.get("piia_drop_ci95"),
            "bootstrap_unit": item.get("bootstrap", {}).get("unit"),
        })
    return {
        "source": str(PIIA_BOOT_PATH.relative_to(ROOT)),
        "raw_path": data.get("raw_path"),
        "n_raw_outcomes": data.get("n_raw_outcomes"),
        "methodology": {
            "diagnostic": "probe-mediated IIA; not standard SCM-based IIA",
            "threshold": "raw outcomes include score_before <= 0.5 < score_after crossing",
            "ci_method": "source-index bootstrap from raw intervention outcomes",
        },
        "summary": {
            "n_effects": len(rows),
            "max_piia_drop": max((r["piia_drop"] for r in rows), default=None),
            "max_piia_drop_ci_width": max(
                (r["piia_drop_ci95"][1] - r["piia_drop_ci95"][0] for r in rows if r["piia_drop_ci95"]),
                default=None,
            ),
        },
        "top_piia_drop_rows": sorted(rows, key=lambda r: -r["piia_drop"])[:12],
        "rows": rows,
    }


def threshold_audit() -> list[dict[str, Any]]:
    return [
        {
            "component": "LOTO FNR, deployed FNR, baselines, contrastive post-FNR, causal-chain FNR",
            "source_scripts": [
                "experiment_fnr_frag.py",
                "experiment_baselines.py",
                "solution_contrastive.py",
                "run_contrastive_strict_lopo.py",
                "run_contrastive_multiseed.py",
                "analysis/analyze_causal_chain_mechanism.py",
            ],
            "classifier": "sklearn LogisticRegression(C=1.0, class_weight='balanced')",
            "decision_rule": "clf.predict(...), effectively the default 0.5 probability/logit decision boundary for binary classification",
            "audit_risk": "No threshold sweep or validation-selected threshold is recorded in current artifacts. FNR/FPR should be reported as default-threshold diagnostics, not calibrated deployment estimates.",
        },
        {
            "component": "pIIA raw intervention outcomes",
            "source_scripts": ["interchange_intervention_true.py", "analysis/bootstrap_iia_raw.py"],
            "decision_rule": "score_before <= 0.5 < score_after",
            "audit_risk": "This is a probe-threshold crossing diagnostic. It does not establish standard SCM-based interchange intervention validity.",
        },
    ]


def reviewer_actions(audit: dict[str, Any]) -> list[dict[str, str]]:
    actions = []
    loto_summary = audit["loto"]["summary"]
    if loto_summary.get("n_small_n_rows_lt30"):
        actions.append({
            "priority": "P0",
            "item": "Add row-level N+, N-, and Wilson CI to main or appendix LOTO tables.",
            "reason": f"{loto_summary['n_small_n_rows_lt30']} LOTO rows have N+ < 30.",
        })
    strict_summary = audit["contrastive_strict_lopo"]["summary"]
    if audit["contrastive_strict_lopo"].get("available", True) and strict_summary.get("n_evaluable_effects", 0) < 3:
        actions.append({
            "priority": "P0",
            "item": "Do not present strict LOPO as broad mitigation evidence.",
            "reason": f"Only {strict_summary['n_evaluable_effects']} effects are evaluable under strict transitive alignment.",
        })
    causal_summary = audit["causal_chain"]["summary"]
    if audit["causal_chain"].get("available", True) and causal_summary.get("n_small_n_tool_rows_lt30"):
        actions.append({
            "priority": "P0",
            "item": "Keep causal-chain conditioning as mechanism/stress diagnostic unless small-N rows are expanded.",
            "reason": f"{causal_summary['n_small_n_tool_rows_lt30']} causal-chain tool rows have 0 < N+ < 30.",
        })
    if not audit["loto"].get("available", True):
        actions.append({
            "priority": "P0",
            "item": "Run LOTO/baseline experiments before using this dataset in the paper.",
            "reason": audit["loto"].get("missing_reason", "LOTO artifact missing."),
        })
    if not audit["contrastive_strict_lopo"].get("available", True):
        actions.append({
            "priority": "P1",
            "item": "Run strict LOPO contrastive evaluation after embeddings are available.",
            "reason": audit["contrastive_strict_lopo"].get("missing_reason", "strict LOPO artifact missing."),
        })
    actions.append({
        "priority": "P1",
        "item": "Record threshold-selection rules in the paper and artifact appendix.",
        "reason": "Current artifacts mostly use default LogisticRegression.predict thresholds without calibration sweeps.",
    })
    actions.append({
        "priority": "P1",
        "item": "Add strict LOPO seed variance or explicitly mark strict LOPO as single-run descriptive evidence.",
        "reason": "Multiseed evidence exists for full-training projection, not for strict LOPO.",
    })
    actions.append({
        "priority": "P1",
        "item": "Remove or rename the group_dro compatibility field in paper-facing tables unless true worst-group optimization is implemented.",
        "reason": "The baseline artifact still carries a group_dro alias for group reweighting.",
    })
    return actions


def build_audit() -> dict[str, Any]:
    main_rows = load_jsonl(MAIN_DATA)
    datasets = {PRIMARY_DATASET: dataset_cell_audit(main_rows, PRIMARY_DATASET)}
    if CHAIN_DATA.exists():
        chain_rows = load_jsonl(CHAIN_DATA)
        datasets["causal_chain_conditioning_v2"] = dataset_cell_audit(chain_rows, "causal_chain_conditioning_v2")
    loto = loto_audit()
    audit = {
        "schema_version": "statistical_uncertainty_audit_v1",
        "generated_by": "analysis/statistical_uncertainty_audit.py",
        "primary_dataset": PRIMARY_DATASET,
        "scope": "Audit existing artifacts for cell counts, uncertainty intervals, threshold rules, and seed variance. Does not rerun probes.",
        "methodology_notes": [
            "Wilson intervals are reconstructed from stored rounded rates and n_positive when raw predictions are unavailable.",
            "Seed intervals are descriptive because current multiseed projection uses five seeds.",
            "Threshold audit is based on source-code decision rules and current result artifacts.",
        ],
        "datasets": datasets,
        "thresholds": threshold_audit(),
        "loto": loto,
        "baselines": baseline_audit(loto["rows"]),
        "contrastive_strict_lopo": strict_lopo_audit(),
        "contrastive_multiseed": multiseed_audit(),
        "causal_chain": causal_chain_audit(),
        "piia": piia_audit(),
    }
    audit["reviewer_actions"] = reviewer_actions(audit)
    return audit


def fmt_ci(ci: list[Any] | None) -> str:
    if not ci or ci[0] is None:
        return "NA"
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def write_md(audit: dict[str, Any]) -> None:
    lines = []
    lines.append("# Statistical Uncertainty Audit")
    lines.append("")
    lines.append("> Generated by `analysis/statistical_uncertainty_audit.py`. This audit reads existing artifacts and does not rerun probes.")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("- Proportion CIs are Wilson intervals reconstructed from stored rounded rates and N+.")
    lines.append("- They are review-facing diagnostics; final paper tables should prefer raw prediction-level intervals when available.")
    lines.append("- Current threshold rules mostly use default `LogisticRegression.predict` decisions, not validation-calibrated thresholds.")
    lines.append("")

    main = audit["datasets"][audit["primary_dataset"]]
    lines.append("## Dataset Cell Counts")
    lines.append("")
    lines.append(
        f"`{main['name']}`: {main['n_rows']} rows, {main['n_tools']} tools, "
        f"{main['n_effects']} effects. Positive cells below N+=30: "
        f"{main['summary']['n_positive_cells_below_30']} / {main['summary']['n_positive_cells']}."
    )
    low_rows = [
        [c["effect"], c["tool"], c["n_positive"], c["n_negative"], c["loto_evaluable"]]
        for c in main["low_positive_cells"][:20]
    ]
    lines.append("")
    lines.append(md_table(["Effect", "Tool", "N+", "N-", "LOTO evaluable"], low_rows))
    lines.append("")

    loto = audit["loto"]
    lines.append("## LOTO FNR Audit")
    lines.append("")
    if not loto.get("available", True):
        lines.append(f"Missing: {loto['missing_reason']}")
    else:
        lines.append(
            f"Rows: {loto['summary']['n_rows']}; rows with N+ < 30: "
            f"{loto['summary']['n_small_n_rows_lt30']}; max held-out FNR: "
            f"{loto['summary']['max_heldout_fnr']}."
        )
    loto_rows = [
        [
            r["effect"],
            r["tool"],
            r["n_positive"],
            r["heldout_fnr"],
            fmt_ci(r["heldout_fnr_ci95"]),
            r["fnr_gap"],
        ]
        for r in loto["top_high_fnr_rows"]
    ]
    lines.append("")
    lines.append(md_table(["Effect", "Tool", "N+", "Held FNR", "Held FNR CI95", "Gap"], loto_rows))
    lines.append("")

    strict = audit["contrastive_strict_lopo"]
    lines.append("## Strict Contrastive LOPO Audit")
    lines.append("")
    if not strict.get("available", True):
        lines.append(f"Missing: {strict['missing_reason']}")
    else:
        lines.append(
            f"Evaluable effects: {strict['summary']['n_evaluable_effects']}; "
            f"not evaluable effects: {strict['summary']['n_not_evaluable_effects']}; "
            f"tool-case rows: {strict['summary']['n_tool_case_rows']}; "
            f"rows with N+ < 30: {strict['summary']['n_small_n_rows_lt30']}."
        )
    strict_rows = [
        [
            r["effect"],
            "+".join(r["heldout_pair"]),
            r["tool"],
            r["n_positive"],
            r["strict_post_fnr"],
            fmt_ci(r["strict_post_fnr_ci95"]),
            r["delta_fnr"],
        ]
        for r in strict["top_remaining_post_fnr_rows"]
    ]
    lines.append("")
    lines.append(md_table(["Effect", "Held pair", "Tool", "N+", "Post FNR", "Post CI95", "Delta"], strict_rows))
    lines.append("")

    multi = audit["contrastive_multiseed"]
    lines.append("## Full-Training Contrastive Multiseed Audit")
    lines.append("")
    if not multi.get("available", True):
        lines.append(f"Missing: {multi['missing_reason']}")
    else:
        lines.append(
            f"Seeds: {multi['summary']['n_seeds']}; max mean post-FNR: "
            f"{multi['summary']['max_mean_post_fnr']}; max population std: "
            f"{multi['summary']['max_population_std']}."
        )
    multi_rows = [
        [
            r["effect"],
            r["tool"],
            r["n_seeds"],
            r["post_fnr_mean"],
            r["post_fnr_std_population"],
            fmt_ci(r["post_fnr_ci95_mean"]),
        ]
        for r in multi["top_post_fnr_rows"]
    ]
    lines.append("")
    lines.append(md_table(["Effect", "Tool", "Seeds", "Mean", "Std", "Mean CI95"], multi_rows))
    lines.append("")

    chain = audit["causal_chain"]
    lines.append("## Causal-Chain Diagnostic Audit")
    lines.append("")
    if not chain.get("available", True):
        lines.append(f"Missing: {chain['missing_reason']}")
    else:
        lines.append(
            f"Tool rows: {chain['summary']['n_tool_rows']}; small-N tool rows: "
            f"{chain['summary']['n_small_n_tool_rows_lt30']}; max held FNR: "
            f"{chain['summary']['max_held_fnr']}."
        )
    chain_rows = [
        [
            r["effect"],
            r["group"],
            r["tool"],
            r["n_positive"],
            r["held_fnr"],
            fmt_ci(r["held_fnr_ci95"]),
            r["toolproxy_gap"],
        ]
        for r in chain["small_n_high_fnr_rows"]
    ]
    lines.append("")
    lines.append(md_table(["Effect", "Group", "Tool", "N+", "Held FNR", "Held CI95", "Gap"], chain_rows))
    lines.append("")

    piia = audit["piia"]
    lines.append("## pIIA Bootstrap Audit")
    lines.append("")
    if not piia.get("available", True):
        lines.append(f"Missing: {piia['missing_reason']}")
    else:
        lines.append(
            f"Effects: {piia['summary']['n_effects']}; raw outcomes: {piia['n_raw_outcomes']}; "
            f"max pIIA-Drop: {piia['summary']['max_piia_drop']}."
        )
    piia_rows = [
        [
            r["effect"],
            r["n_raw_outcomes"],
            r["n_source_examples"],
            r["piia_drop"],
            fmt_ci(r["piia_drop_ci95"]),
        ]
        for r in piia["top_piia_drop_rows"]
    ]
    lines.append("")
    lines.append(md_table(["Effect", "Raw outcomes", "Sources", "pIIA-Drop", "Drop CI95"], piia_rows))
    lines.append("")

    lines.append("## Threshold Audit")
    lines.append("")
    for row in audit["thresholds"]:
        lines.append(f"- `{row['component']}`: {row['decision_rule']}")
        lines.append(f"  Risk: {row['audit_risk']}")
    lines.append("")

    lines.append("## Reviewer Actions")
    lines.append("")
    action_rows = [[a["priority"], a["item"], a["reason"]] for a in audit["reviewer_actions"]]
    lines.append(md_table(["Priority", "Action", "Reason"], action_rows))
    lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3-8b")
    parser.add_argument("--data", default="scenarios_merged")
    args = parser.parse_args()

    configure_paths(args.data, args.model)
    audit = build_audit()
    OUT_JSON.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    write_md(audit)
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
