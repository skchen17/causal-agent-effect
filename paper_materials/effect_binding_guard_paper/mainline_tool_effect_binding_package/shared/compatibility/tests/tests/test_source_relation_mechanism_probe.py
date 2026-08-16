from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCE = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/source/"
    "headline-benign-utility-pathway-audit/run_source_relation_probe.py"
)
spec = importlib.util.spec_from_file_location(
    "source_relation_mechanism_probe", SOURCE
)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)


def test_source_relation_probe_is_fail_closed_and_diagnostic() -> None:
    report = probe.run_probe(ROOT)
    assert report["status"] == "passed"
    assert (
        report["cases"]["correct_source_unconstrained_fields"]["decision"]
        == "ALLOW"
    )
    assert report["cases"]["correct_source_semantic_fields"]["decision"] == "ALLOW"
    assert report["cases"]["wrong_source_name"]["decision"] == "NEEDS_REPLAN"
    assert (
        report["cases"]["ambiguous_prior_result"]["decision"]
        == "NEEDS_REPLAN"
    )
    assert report["model_calls"] == 0
    assert report["tool_executions"] == 0
