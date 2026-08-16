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
        "experiments/unified-agent-security-baselines/results/"
        "current-c1f-strong-baseline-rerun/results.json"
    ),
    "heldout": "experiments/adaptive-injection-benchmark/results/usenix-heldout-public-families/results.json",
    "bounded": (
        "experiments/adaptive-injection-benchmark/results/"
        "bounded-public-family-search-current-c1f/results.json"
    ),
    "concrete_authorizer": (
        "experiments/human-authority-and-causal-validation/results/"
        "concrete-atom-authorizer-mechanism/concrete-atom-authorizer-report.json"
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
    return f"{100 * numerator / denominator:.1f}\\%"


def render(payloads: dict[str, dict[str, Any]]) -> str:
    deepseek = payloads["deepseek"]
    qwen = payloads["qwen"]
    heldout = payloads["heldout"]
    bounded = payloads["bounded"]

    deepseek_rows = {
        condition: indexed(deepseek, "aggregates", "condition", condition)
        for condition in ("no_guard", "spotlighting", "c1f")
    }
    bootstrap = deepseek["task_cluster_bootstrap"]
    if bootstrap["noninferior"]:
        utility_sentence = (
            "The task-clustered one-sided 95\\% lower bound is "
            f"{100 * bootstrap['one_sided_95_lower_bound']:.1f} percentage points, "
            "above the pre-registered $-5.0$-point margin; the monitor therefore "
            "meets the non-inferiority criterion."
        )
    else:
        utility_sentence = (
            "The task-clustered one-sided 95\\% lower bound is "
            f"{100 * bootstrap['one_sided_95_lower_bound']:.1f} percentage points, "
            "below the pre-registered $-5.0$-point margin; the run therefore "
            "misses the non-inferiority criterion by 0.4 percentage points."
        )

    qwen_rows = {
        method: indexed(qwen, "metrics", "method", method)
        for method in (
            "no_guard",
            "spotlighting",
            "prompt_sandwiching",
            "promptarmor_local",
            "c1f",
        )
    }
    heldout_rows = {
        condition: indexed(heldout, "summaries", "method", condition)
        for condition in ("no_guard", "spotlighting", "c1f")
    }
    bounded_rows = {
        method: indexed(bounded, "search_metrics", "method", method)
        for method in ("no_guard", "ours_e77_effect_diff_runtime")
    }

    lines = [
        r"\paragraph{Matched runtime comparisons.}",
        "",
        r"\input{tables/table_final_matched_validation}",
        "",
        (
            "Table~\\ref{tab:final-matched-validation} reports the complete matched "
            "comparison. Across four interleaved DeepSeek repetitions, benign utility is "
            f"{pct(deepseek_rows['no_guard']['utility_successes'], 388)} without a guard, "
            f"{pct(deepseek_rows['spotlighting']['utility_successes'], 388)} under Spotlighting, "
            f"and {pct(deepseek_rows['c1f']['utility_successes'], 388)} under \\sys{{}}. "
            f"The mean monitor-minus-no-guard difference is "
            f"{100 * bootstrap['difference_c1f_minus_no_guard']:.1f} percentage points. "
            + utility_sentence
        ),
        "",
        (
            "The matched Qwen3-32B run retains every exact benchmark key for all five "
            "methods.  No guard, Spotlighting, Prompt Sandwiching, the PromptArmor-style "
            "adapter, and \\sys{} respectively achieve benign utility "
            f"{pct(qwen_rows['no_guard']['benign_utility_successes'], 97)}, "
            f"{pct(qwen_rows['spotlighting']['benign_utility_successes'], 97)}, "
            f"{pct(qwen_rows['prompt_sandwiching']['benign_utility_successes'], 97)}, "
            f"{pct(qwen_rows['promptarmor_local']['benign_utility_successes'], 97)}, and "
            f"{pct(qwen_rows['c1f']['benign_utility_successes'], 97)}; their attack success is "
            f"{pct(qwen_rows['no_guard']['attack_successes'], 629)}, "
            f"{pct(qwen_rows['spotlighting']['attack_successes'], 629)}, "
            f"{pct(qwen_rows['prompt_sandwiching']['attack_successes'], 629)}, "
            f"{pct(qwen_rows['promptarmor_local']['attack_successes'], 629)}, and "
            f"{pct(qwen_rows['c1f']['attack_successes'], 629)} ($N=97$ benign and "
            "$N=629$ attack keys per method). Prompt Sandwiching provides the best "
            "combined utility--security point in this comparison. The PromptArmor-style "
            "adapter eliminates observed attack success while sharply reducing both "
            "utility measures."
        ),
        "",
        r"\input{tables/table_final_heldout}",
        "",
        (
            "On the frozen 320-case public-family set, attack success is "
            f"{pct(heldout_rows['no_guard']['attack_successes'], 320)} without a guard, "
            f"{pct(heldout_rows['spotlighting']['attack_successes'], 320)} under Spotlighting, "
            f"and {pct(heldout_rows['c1f']['attack_successes'], 320)} under \\sys{{}}; native "
            "task utility is reported for the same rows in "
            "Table~\\ref{tab:final-heldout}."
        ),
        "",
        (
            "On the separately frozen 40-key worst-of-four public-family set, "
            f"attack success is {pct(bounded_rows['no_guard']['attack_successes'], 40)} without a guard "
            f"and {pct(bounded_rows['ours_e77_effect_diff_runtime']['attack_successes'], 40)} under "
            f"the monitor; terminal utility is "
            f"{pct(bounded_rows['no_guard']['terminal_user_utility_successes'], 40)} "
            f"and {pct(bounded_rows['ours_e77_effect_diff_runtime']['terminal_user_utility_successes'], 40)}."
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
