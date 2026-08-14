from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
SCRIPT = ROOT / "scripts/run_toolsandbox_concrete_atom_authorizer.py"
CONTEXTS = ROOT / "experiments/human-authority-and-causal-validation/evaluation/heldout-toolsandbox-effect-binding-validation/heldout-contexts.jsonl"


def load_module():
    spec = importlib.util.spec_from_file_location("concrete_atom_authorizer", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_multiset_authorization_preserves_occurrence_counts() -> None:
    module = load_module()
    atom = {"effect": "write", "resource_id": "r"}
    assert module.multiset_subset([atom], [atom, atom]) is True
    assert module.multiset_subset([atom, atom], [atom]) is False


def test_frozen_full_domain_has_232_ordered_queries() -> None:
    module = load_module()
    rows = module.load_jsonl(CONTEXTS)
    queries = module.build_queries(rows)
    assert len(rows) == 32
    assert len(queries) == 232
    assert {row["ideal_decision"] for row in queries} == {"ALLOW", "DENY"}


def test_concrete_atoms_match_source_authorization_relation() -> None:
    module = load_module()
    rows = module.load_jsonl(CONTEXTS)
    queries = module.build_queries(rows)
    summary = module.summarize_method(queries, "concrete_effect_atoms")
    assert summary["unsafe_pre_allow"]["successes"] == 0
    assert summary["safe_false_deny"]["successes"] == 0
    assert summary["decision_accuracy"]["rate"] == 1.0


def test_coarse_and_raw_views_expose_distinct_failure_modes() -> None:
    module = load_module()
    rows = module.load_jsonl(CONTEXTS)
    queries = module.build_queries(rows)
    whole = module.summarize_method(queries, "whole_call_tool_name")
    raw = module.summarize_method(queries, "raw_arguments_exact")
    assert whole["unsafe_pre_allow"]["successes"] > 0
    assert raw["safe_false_deny"]["successes"] > 0


def test_smoke_emits_traceable_artifacts(tmp_path: Path) -> None:
    module = load_module()
    payload = module.run("smoke", tmp_path)
    assert payload["status"] == "passed"
    assert payload["n_contexts"] == 10
    assert payload["n_queries"] == 20
    assert all(payload["gates"].values())
    for name in (
        "authorization-decisions.jsonl",
        "concrete-atom-authorizer-report.json",
        "concrete-atom-authorizer-report.md",
        "authorizer-metrics.csv",
        "table_concrete_atom_authorizer.tex",
    ):
        assert (tmp_path / name).is_file()
    report = json.loads((tmp_path / "concrete-atom-authorizer-report.json").read_text())
    assert report["mode"] == "smoke"
