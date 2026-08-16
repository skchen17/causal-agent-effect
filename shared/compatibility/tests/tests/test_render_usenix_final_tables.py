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


def test_renderer_emits_nonduplicated_final_tables_from_passed_artifacts(tmp_path):
    renderer = load_renderer()
    paper = tmp_path / "paper/current-usenix"
    (paper / "tables").mkdir(parents=True)
    renderer.ROOT = tmp_path
    renderer.PAPER = paper

    conditions = ("no_guard", "spotlighting", "c1f")
    qwen_methods = (
        "no_guard",
        "spotlighting",
        "prompt_sandwiching",
        "promptarmor_local",
        "c1f",
    )
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
        "experiments/human-authority-and-causal-validation/results/"
        "concrete-atom-authorizer-mechanism/concrete-atom-authorizer-report.json",
        {
            "status": "passed",
            "metrics": [
                {
                    "method": method,
                    "unsafe_pre_allow": {"rate": 0.1 * index},
                    "safe_false_deny": {"rate": 0.05 * index},
                    "coverage": {"rate": 1.0},
                    "decision_accuracy": {"rate": 1.0 - 0.1 * index},
                }
                for index, method in enumerate(
                    (
                        "whole_call_tool_name",
                        "raw_arguments_exact",
                        "common_effect_atoms",
                        "concrete_effect_atoms",
                        "source_effect_oracle",
                    )
                )
            ],
        },
    )
    write_json(
        tmp_path,
        "experiments/unified-agent-security-baselines/results/"
        "current-c1f-strong-baseline-rerun/results.json",
        {
            "status": "passed",
            "metrics": [
                {
                    "method": method,
                    "benign_utility_successes": 90 + index,
                    "attack_utility_successes": 400 + index,
                    "attack_successes": 10 - index,
                }
                for index, method in enumerate(qwen_methods)
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
    assert renderer.main() == 0

    matched = (paper / "tables/table_final_matched_validation.tex").read_text(encoding="utf-8")
    external = (paper / "tables/table_final_heldout.tex").read_text(encoding="utf-8")
    authorizer = (paper / "tables/table_concrete_atom_authorizer.tex").read_text(encoding="utf-8")
    assert "97.9\\%" in matched and "96.9\\%" in matched and "1.0\\%" in matched
    assert "Prompt Sandwiching" in matched and "PromptArmor-style" in matched
    assert "78.8\\%" in external
    assert "AgentLAB" not in external
    assert not (paper / "tables/table_final_four_view.tex").exists()
    assert "Exact raw args" in authorizer and "Concrete atoms" in authorizer


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
                    "method": method,
                    "benign_utility_successes": 80 + index,
                    "attack_utility_successes": 300 + index,
                    "attack_successes": 9 - index,
                }
                for index, method in enumerate(
                    (
                        "no_guard",
                        "spotlighting",
                        "prompt_sandwiching",
                        "promptarmor_local",
                        "c1f",
                    )
                )
            ]
        },
        "heldout": {
            "summaries": [
                {"method": condition, "attack_successes": 12 - index}
                for index, condition in enumerate(("no_guard", "spotlighting", "c1f"))
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
                    "attack_successes": 2,
                    "terminal_user_utility_successes": 17,
                },
            ]
        },
        "concrete_authorizer": {
            "metrics": [
                {
                    "method": "concrete_effect_atoms",
                    "unsafe_pre_allow": {"successes": 0},
                    "safe_false_deny": {"successes": 0},
                }
            ]
        },
    }
    text = generator.render(payloads)
    assert "misses the non-inferiority criterion" in text
    assert "90.2\\% without a guard" in text
    assert "all five methods" in text
    assert "Prompt Sandwiching" in text and "PromptArmor-style" in text
    assert "AgentLAB" not in text
    assert "closed-loop four-view" not in text
    assert "10.0\\% without a guard" in text
    assert "5.0\\% under the monitor" in text
