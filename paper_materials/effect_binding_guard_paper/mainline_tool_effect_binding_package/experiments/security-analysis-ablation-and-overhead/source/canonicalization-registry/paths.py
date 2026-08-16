"""Shared path resolution for the effect-preserving canonicalization framework.

ROOT is the repository root (parents[4] of this file):
  .../experiments/security-analysis-ablation-and-overhead/source/
      canonicalization-registry/paths.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

FINITE_CONTEXTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "finite-domain-effect-binding-validation/finite-contexts.jsonl"
)
FINITE_BASELINE_REPORT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "finite-domain-effect-binding-validation/finite-domain-validation-report.json"
)
E2_REPORT = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "policy-family-sensitivity/policy-family-sensitivity-report.json"
)
RESULTS_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "canonicalization-registry"
)

PREREG_FILE = SRC_DIR / "preregistered_control_set.json"
PREREG_SHA_FILE = SRC_DIR / "preregistered_control_set.sha256.txt"
FAILURE_CASES_FILE = SRC_DIR / "failure_cases_m3.jsonl"

CONTROL_REPORT_JSON = RESULTS_DIR / "control-validation-report.json"
CONTROL_REPORT_MD = RESULTS_DIR / "control-validation-report.md"
CEGAR_REPORT_JSON = RESULTS_DIR / "cegar-replay-report.json"
CEGAR_REPORT_MD = RESULTS_DIR / "cegar-replay-report.md"
REGISTRY_FROZEN_JSON = RESULTS_DIR / "registry.frozen.json"

EXPECTED_FINITE_CONTEXTS = 56
