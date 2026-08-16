#!/usr/bin/env python3
"""Repository-level entry point for active USENIX claim reproduction."""

from __future__ import annotations

import runpy
from pathlib import Path


def find_repository_root() -> Path:
    """Resolve the logical repository root even when ``scripts`` is a symlink."""
    candidates = [Path.cwd().resolve(), *Path(__file__).resolve().parents]
    for candidate in candidates:
        target = candidate / "paper/current-usenix/reproduction/reproduce_main_claims.py"
        if target.is_file():
            return candidate
    raise FileNotFoundError("cannot locate the active USENIX reproduction entry point")


ROOT = find_repository_root()
raw_support = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl",
    ROOT
    / "experiments/human-authority-and-causal-validation/results/causal-effect-projection-validation/agentdojo-projection-intervention-report.json",
)
snapshot = ROOT / "paper/current-usenix/reproduction/sanitized_fixed_support.json"
if all(path.is_file() for path in raw_support):
    extractor = runpy.run_path(
        str(ROOT / "paper/current-usenix/reproduction/extract_sanitized_fixed_support.py")
    )
    if extractor["main"]() != 0:
        raise SystemExit("sanitized fixed-support extraction failed")
elif not snapshot.is_file():
    raise FileNotFoundError("missing both raw fixed-support reports and their sanitized snapshot")
runpy.run_path(
    str(ROOT / "paper/current-usenix/reproduction/reproduce_main_claims.py"),
    run_name="__main__",
)
