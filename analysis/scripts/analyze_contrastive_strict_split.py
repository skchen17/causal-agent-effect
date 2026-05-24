"""Analyze contrastive multiseed results with strict two-form vs three-plus split.

Reads: analysis/contrastive_multiseed_qwen3-8b_scenarios_merged.json
Outputs: analysis/contrastive_strict_split_qwen3-8b_scenarios_merged.{json,md}
"""
import json, numpy as np
from pathlib import Path


def main():
    base = Path(__file__).parent.parent

    with open(base / "analysis/contrastive_multiseed_qwen3-8b_scenarios_merged.json") as f:
        data = json.load(f)

    results = data["results"]
    two_form = {}
    three_plus = {}

    for effect, tool_data in results.items():
        n_forms = len(tool_data)
        means = [r["post_fnr_mean"] for r in tool_data.values()]
        stds = [r["post_fnr_std"] for r in tool_data.values()]
        entry = {
            "n_forms": n_forms,
            "tools": list(tool_data.keys()),
            "worst_post_fnr_mean": round(float(np.max(means)), 4) if means else 0,
            "effect_average_post_fnr_mean": round(float(np.mean(means)), 4) if means else 0,
            "effect_average_post_fnr_std": round(float(np.mean(stds)), 4) if stds else 0,
            "per_tool": tool_data,
        }
        if n_forms == 2:
            two_form[effect] = entry
        else:
            three_plus[effect] = entry

    strict = {
        "two_form_effects": {
            **{e: {"status": "not_evaluable", "reason": "Only two surface forms; leaving out the target pair removes all cross-form positive training pairs.", **v}
               for e, v in two_form.items()}
        },
        "three_plus_form_effects": {
            **{e: {"status": "evaluable", "reason": "At least three surface forms; transitive alignment testable through intermediate forms.", **v}
               for e, v in three_plus.items()}
        },
    }

    out_json = base / "analysis/contrastive_strict_split_qwen3-8b_scenarios_merged.json"
    out_json.write_text(json.dumps(strict, indent=2))
    print(f"Saved to {out_json}")

    # MD
    lines = [
        "# Contrastive Strict Leave-One-Pair-Out Split",
        "",
        "## Two-Form Effects (Not Evaluable in Strict Setting)",
        "",
        "These effects have only 2 surface forms. Leaving one pair out removes ALL cross-form training data.",
        "",
        "| Effect | Forms | Worst post-FNR (full) | Effect-Avg post-FNR (full) |",
        "|---|---:|---:|---:|",
    ]
    for e, v in sorted(two_form.items()):
        lines.append(f"| {e} | {', '.join(v['tools'])} | {v['worst_post_fnr_mean']:.4f} | {v['effect_average_post_fnr_mean']:.4f} |")

    lines += [
        "",
        "## Three-Plus-Form Effects (Evaluable in Strict Setting)",
        "",
        "These effects have ≥3 surface forms. Transitive alignment through intermediate forms is testable.",
        "",
        "| Effect | Forms | Worst post-FNR (full) | Effect-Avg post-FNR (full) |",
        "|---|---:|---:|---:|",
    ]
    for e, v in sorted(three_plus.items()):
        lines.append(f"| {e} | {', '.join(v['tools'])} | {v['worst_post_fnr_mean']:.4f} | {v['effect_average_post_fnr_mean']:.4f} |")

    out_md = base / "analysis/contrastive_strict_split_qwen3-8b_scenarios_merged.md"
    out_md.write_text("\n".join(lines))
    print(f"Saved to {out_md}")
    print(f"Two-form: {list(two_form.keys())}")
    print(f"Three-plus: {list(three_plus.keys())}")


if __name__ == "__main__":
    main()
