#!/usr/bin/env python3
"""Generate bounded final-result prose after every frozen artifact passes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
OUTPUT = PAPER / "sections/generated_final_validation_results.tex"
MANIFEST = PAPER / "reproduction/generated_final_validation_manifest.json"
RENDERER_PATH = PAPER / "reproduction/render_final_tables.py"

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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_renderer():
    spec = importlib.util.spec_from_file_location("final_table_renderer", RENDERER_PATH)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load final table renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_all() -> dict[str, dict[str, Any]]:
    payloads = {}
    for name, relative in SOURCES.items():
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "passed":
            raise RuntimeError(f"final result is not passed: {relative}")
        payloads[name] = payload
    return payloads


def indexed(payload: dict[str, Any], outer: str, field: str, value: str) -> dict[str, Any]:
    for row in payload[outer]:
        if row[field] == value:
            return row
    raise KeyError(f"{outer}[{field}={value}]")


def pct(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}\\%)"


def render(payloads: dict[str, dict[str, Any]]) -> str:
    deepseek = payloads["deepseek"]
    qwen = payloads["qwen"]
    heldout = payloads["heldout"]
    transfer = payloads["transfer"]
    four_view = payloads["four_view"]
    bounded = payloads["bounded"]

    deepseek_rows = {
        condition: indexed(deepseek, "aggregates", "condition", condition)
        for condition in ("no_guard", "spotlighting", "c1f")
    }
    bootstrap = deepseek["task_cluster_bootstrap"]
    if bootstrap["noninferior"]:
        utility_sentence = (
            "The task-clustered one-sided 95\\% lower bound is "
            f"{bootstrap['one_sided_95_lower_bound']:.3f}, above the pre-registered "
            "$-0.05$ margin; C1f therefore meets this bounded non-inferiority criterion."
        )
    else:
        utility_sentence = (
            "The task-clustered one-sided 95\\% lower bound is "
            f"{bootstrap['one_sided_95_lower_bound']:.3f}, which does not exceed the "
            "pre-registered $-0.05$ margin; we therefore do not claim benign-utility "
            "non-inferiority."
        )

    qwen_rows = {
        condition: indexed(qwen, "metrics", "condition", condition)
        for condition in ("no_guard", "spotlighting", "c1f")
    }
    heldout_rows = {
        condition: indexed(heldout, "summaries", "method", condition)
        for condition in ("no_guard", "spotlighting", "c1f")
    }
    tm = {
        row["condition"]: row for row in transfer["comparison_metrics"]
    }
    four_rows = {
        variant: indexed(four_view, "aggregates", "variant", variant)
        for variant in (
            "no_guard",
            "whole_call_provenance",
            "effect_only",
            "registered_field_c1f",
        )
    }
    bounded_rows = {
        method: indexed(bounded, "search_metrics", "method", method)
        for method in ("no_guard", "ours_e77_effect_diff_runtime")
    }

    lines = [
        r"\subsection{Frozen Generalization and Utility Checks}",
        r"\label{sec:final-validation}",
        "",
        r"\input{tables/table_final_matched_validation}",
        "",
        (
            "Across four interleaved DeepSeek repetitions, benign utility is "
            f"{pct(deepseek_rows['no_guard']['utility_successes'], 388)} without a guard, "
            f"{pct(deepseek_rows['spotlighting']['utility_successes'], 388)} under Spotlighting, "
            f"and {pct(deepseek_rows['c1f']['utility_successes'], 388)} under \\sys{{}}. "
            f"The mean C1f-minus-no-guard difference is {bootstrap['difference_c1f_minus_no_guard']:.3f}. "
            + utility_sentence
        ),
        "",
        (
            "The matched Qwen3-32B run retains every exact benchmark key.  No guard, "
            "Spotlighting, and \\sys{} respectively achieve benign utility "
            f"{qwen_rows['no_guard']['benign_utility_successes']}/97, "
            f"{qwen_rows['spotlighting']['benign_utility_successes']}/97, and "
            f"{qwen_rows['c1f']['benign_utility_successes']}/97; their attack success is "
            f"{qwen_rows['no_guard']['attack_successes']}/629, "
            f"{qwen_rows['spotlighting']['attack_successes']}/629, and "
            f"{qwen_rows['c1f']['attack_successes']}/629.  This is a second-checkpoint "
            "test under the same benchmark protocol, not a claim about arbitrary models."
        ),
        "",
        r"\input{tables/table_final_heldout_transfer}",
        "",
        (
            "On the frozen 320-case public-family set, attack success is "
            f"{heldout_rows['no_guard']['attack_successes']}/320 without a guard, "
            f"{heldout_rows['spotlighting']['attack_successes']}/320 under Spotlighting, "
            f"and {heldout_rows['c1f']['attack_successes']}/320 under \\sys{{}}; native "
            "task utility is reported for the same rows in Table~\\ref{tab:final-heldout-transfer}. "
            "The matched current-profile AgentLAB saved replay changes attack success from "
            f"{tm['no_guard']['attack_successes']}/303 without a guard to "
            f"{tm['c1f']['attack_successes']}/303 under C1f, and task utility from "
            f"{tm['no_guard']['utility_successes']}/303 to {tm['c1f']['utility_successes']}/303, "
            "with exact checked/executed signature reconciliation.  This "
            "is fixed saved transfer, not regeneration of adaptive AgentLAB attacks."
        ),
        "",
        (
            "On the separately frozen 40-key worst-of-four public-family diagnostic, "
            f"attack success is {bounded_rows['no_guard']['attack_successes']}/40 without a guard "
            f"and {bounded_rows['ours_e77_effect_diff_runtime']['attack_successes']}/40 under "
            f"current C1f; terminal utility is {bounded_rows['no_guard']['terminal_user_utility_successes']}/40 "
            f"and {bounded_rows['ours_e77_effect_diff_runtime']['terminal_user_utility_successes']}/40. "
            "This small bounded search is reported as sensitivity evidence, not unrestricted adaptation."
        ),
        "",
        r"\input{tables/table_final_four_view}",
        "",
        (
            "The closed-loop four-view comparison isolates monitor granularity on its frozen "
            "applicability subset.  Attack success is "
            f"{four_rows['no_guard']['attack_successes']}/273 without blocking, "
            f"{four_rows['whole_call_provenance']['attack_successes']}/273 for whole-call "
            "provenance, "
            f"{four_rows['effect_only']['attack_successes']}/273 for effect-only checking, "
            f"and {four_rows['registered_field_c1f']['attack_successes']}/273 for registered "
            "fields.  The table reports benign and attack-task utility alongside security; "
            "because selection required field-level applicability, these rates are mechanism "
            "evidence rather than benchmark-wide estimates."
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    payloads = load_all()
    renderer = load_renderer()
    if renderer.main() != 0:
        raise RuntimeError("final table renderer failed")
    content = render(payloads)
    OUTPUT.write_text(content, encoding="utf-8")
    manifest = {
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256(OUTPUT),
        "sources": {
            name: {"path": relative, "sha256": sha256(ROOT / relative)}
            for name, relative in SOURCES.items()
        },
        "claim_boundary": (
            "Generated only from strict-passed frozen artifacts; negative outcomes are retained."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "output": manifest["output"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
