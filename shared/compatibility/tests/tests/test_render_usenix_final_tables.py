from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "paper/current-usenix").is_dir()
)
SCRIPT = ROOT / "paper/current-usenix/reproduction/render_final_tables.py"
SECTION_SCRIPT = ROOT / "paper/current-usenix/reproduction/generate_final_result_section.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_final_tables", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_section_generator():
    spec = importlib.util.spec_from_file_location("generate_final_result_section", SECTION_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(root: Path, relative: str, payload: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_renderer_emits_all_three_tables_from_passed_artifacts(tmp_path):
    renderer = load_renderer()
    paper = tmp_path / "paper/current-usenix"
    (paper / "tables").mkdir(parents=True)
    renderer.ROOT = tmp_path
    renderer.PAPER = paper

    conditions = ("no_guard", "spotlighting", "c1f")
    write_json(
        tmp_path,
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "deepseek_benign_interleaved_results.json",
        {
            "status": "passed",
            "aggregates": [
                {"condition": condition, "utility_successes": 380 + index}
                for index, condition in enumerate(conditions)
            ],
        },
    )
    write_json(
        tmp_path,
        "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/"
        "qwen32_matched_results.json",
        {
            "status": "passed",
            "metrics": [
                {
                    "condition": condition,
                    "benign_utility_successes": 90 + index,
                    "attack_utility_successes": 400 + index,
                    "attack_successes": 10 - index,
                }
                for index, condition in enumerate(conditions)
            ],
        },
    )
    write_json(
        tmp_path,
        "experiments/adaptive-injection-benchmark/results/usenix-heldout-public-families/results.json",
        {
            "status": "passed",
            "summaries": [
                {
                    "method": condition,
                    "utility_successes": 250 + index,
                    "attack_successes": 30 - index,
                }
                for index, condition in enumerate(conditions)
            ],
        },
    )
    write_json(
        tmp_path,
        "analysis/results/e79_agentlab_saved_transfer_current_pair_results.json",
        {
            "status": "passed",
            "comparison_metrics": [
                {"condition": "no_guard", "utility_successes": 220, "attack_successes": 9},
                {"condition": "c1f", "utility_successes": 211, "attack_successes": 7},
            ],
        },
    )
    variants = (
        "no_guard",
        "whole_call_provenance",
        "effect_only",
        "registered_field_c1f",
    )
    write_json(
        tmp_path,
        "experiments/security-analysis-ablation-and-overhead/results/"
        "c1f-closed-loop-four-view/closed-loop-four-view-report.json",
        {
            "status": "passed",
            "aggregates": [
                {
                    "variant": variant,
                    "benign_utility_successes": 40 + index,
                    "attack_utility_successes": 200 + index,
                    "attack_successes": 20 - index,
                }
                for index, variant in enumerate(variants)
            ],
        },
    )

    assert renderer.main() == 0

    matched = (paper / "tables/table_final_matched_validation.tex").read_text(encoding="utf-8")
    external = (paper / "tables/table_final_heldout_transfer.tex").read_text(encoding="utf-8")
    mechanism = (paper / "tables/table_final_four_view.tex").read_text(encoding="utf-8")
    assert "380/388" in matched and "92/97" in matched and "8/629" in matched
    assert "252/320" in external and "220/303" in external and "9/303" in external
    assert "211/303" in external and "7/303" in external
    assert "Registered fields & 43/48 & 203/273 & 17/273" in mechanism
    assert "Monitor view & Benign util. & Attack util. & Attack success \\\\" in mechanism


def test_renderer_rejects_nonpassed_artifact(tmp_path):
    renderer = load_renderer()
    renderer.ROOT = tmp_path
    write_json(tmp_path, "pending.json", {"status": "pending"})
    try:
        renderer.load("pending.json")
    except RuntimeError as error:
        assert "result is not passed" in str(error)
    else:
        raise AssertionError("non-passed result must fail closed")


def test_generated_prose_preserves_failed_noninferiority_and_all_methods():
    generator = load_section_generator()
    payloads = {
        "deepseek": {
            "aggregates": [
                {"condition": condition, "utility_successes": value}
                for condition, value in (("no_guard", 350), ("spotlighting", 340), ("c1f", 320))
            ],
            "task_cluster_bootstrap": {
                "noninferior": False,
                "one_sided_95_lower_bound": -0.081,
                "difference_c1f_minus_no_guard": -0.077,
            },
        },
        "qwen": {
            "metrics": [
                {
                    "condition": condition,
                    "benign_utility_successes": 80 + index,
                    "attack_successes": 9 - index,
                }
                for index, condition in enumerate(("no_guard", "spotlighting", "c1f"))
            ]
        },
        "heldout": {
            "summaries": [
                {"method": condition, "attack_successes": 12 - index}
                for index, condition in enumerate(("no_guard", "spotlighting", "c1f"))
            ]
        },
        "transfer": {
            "comparison_metrics": [
                {"condition": "no_guard", "attack_successes": 9, "utility_successes": 180},
                {"condition": "c1f", "attack_successes": 4, "utility_successes": 170},
            ]
        },
        "four_view": {
            "aggregates": [
                {"variant": variant, "attack_successes": 15 - index}
                for index, variant in enumerate(
                    ("no_guard", "whole_call_provenance", "effect_only", "registered_field_c1f")
                )
            ]
        },
        "bounded": {
            "search_metrics": [
                {
                    "method": "no_guard",
                    "attack_successes": 4,
                    "terminal_user_utility_successes": 18,
                },
                {
                    "method": "ours_e77_effect_diff_runtime",
                    "attack_successes": 1,
                    "terminal_user_utility_successes": 12,
                },
            ]
        },
    }
    text = generator.render(payloads)
    assert "do not claim benign-utility non-inferiority" in text
    assert "350/388 (90.2\\%)" in text
    assert "No guard, Spotlighting, and \\sys{} respectively" in text
    assert "fixed saved transfer" in text
    assert "mechanism evidence rather than benchmark-wide estimates" in text
    assert "4/40 without a guard" in text
    assert "1/40 under current C1f" in text
