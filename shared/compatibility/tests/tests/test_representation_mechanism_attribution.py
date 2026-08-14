from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_representation_mechanism_attribution.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "representation_mechanism_attribution", SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_policy_generator_is_exercised_and_deterministic():
    module = load_module()
    contexts = module.normalize_agentdojo() + module.normalize_toolsandbox()
    first, first_stats = module.generate_policies(contexts)
    second, second_stats = module.generate_policies(contexts)

    assert len(contexts) == 88
    assert first_stats == second_stats
    assert [row["policy_id"] for row in first] == [
        row["policy_id"] for row in second
    ]
    assert first_stats["exercised_policies"] > 0
    for policy in first:
        decisions = {
            module.policy_decision(policy, context)
            for context in module.contexts_for_policy(contexts, policy)
        }
        assert decisions == {False, True}


def test_ambiguity_is_representation_dependent():
    module = load_module()
    contexts = module.normalize_agentdojo() + module.normalize_toolsandbox()
    policies, _ = module.generate_policies(contexts)

    found_coarse_ambiguity = False
    for policy in policies:
        scoped = module.contexts_for_policy(contexts, policy)
        typed, _ = module.analyze_policy_representation(
            policy, "typed_effect_occurrence", scoped
        )
        assert typed["minimum_deterministic_errors"] == 0
        coarse, _ = module.analyze_policy_representation(
            policy, "tool_name", scoped
        )
        found_coarse_ambiguity |= coarse["minimum_deterministic_errors"] > 0
    assert found_coarse_ambiguity


def test_fail_closed_and_permissive_are_opposite_ambiguity_choices():
    module = load_module()
    contexts = module.normalize_agentdojo() + module.normalize_toolsandbox()
    policies, _ = module.generate_policies(contexts)
    exercised = None
    for policy in policies:
        scoped = module.contexts_for_policy(contexts, policy)
        result, _ = module.analyze_policy_representation(
            policy, "tool_name", scoped
        )
        if result["ambiguous_contexts"]:
            exercised = result
            break

    assert exercised is not None
    assert exercised["fail_closed_unsafe_pre_allow"] == 0
    assert exercised["fail_closed_safe_abstain"] > 0
    assert exercised["permissive_false_deny"] == 0
    assert exercised["permissive_unsafe_pre_allow"] > 0


def test_full_run_writes_traceable_artifacts(tmp_path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(module, "REPORT_JSON", tmp_path / "report.json")
    monkeypatch.setattr(module, "REPORT_MD", tmp_path / "report.md")
    monkeypatch.setattr(module, "POLICIES_JSONL", tmp_path / "policies.jsonl")
    monkeypatch.setattr(module, "RESULTS_CSV", tmp_path / "results.csv")
    monkeypatch.setattr(module, "WITNESSES_JSONL", tmp_path / "witnesses.jsonl")

    report = module.run()

    assert report["status"] == "passed"
    assert report["n_result_rows"] == (
        report["policy_generation"]["exercised_policies"]
        * len(module.REPRESENTATIONS)
    )
    assert report["n_ambiguity_witnesses"] > 0
    for path in (
        module.REPORT_JSON,
        module.REPORT_MD,
        module.POLICIES_JSONL,
        module.RESULTS_CSV,
        module.WITNESSES_JSONL,
    ):
        assert path.exists()
