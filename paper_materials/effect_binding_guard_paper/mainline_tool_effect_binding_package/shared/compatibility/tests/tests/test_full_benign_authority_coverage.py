from __future__ import annotations

import json
from pathlib import Path


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
OUTPUT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "full-benign-authority-coverage"
)


def test_full_denominator_and_label_separation_are_recorded() -> None:
    report = json.loads(
        (OUTPUT / "coverage-report.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "passed"
    assert report["n_tasks"] == 97
    assert report["ground_truth_chain_covered_tasks"] == 59
    assert report["runtime_uses_official_ground_truth"] is False


def test_task_rows_preserve_all_uncovered_cases() -> None:
    rows = [
        json.loads(line)
        for line in (OUTPUT / "task-coverage.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    assert len(rows) == 97
    assert sum(row["ground_truth_chain_covered"] for row in rows) == 59
