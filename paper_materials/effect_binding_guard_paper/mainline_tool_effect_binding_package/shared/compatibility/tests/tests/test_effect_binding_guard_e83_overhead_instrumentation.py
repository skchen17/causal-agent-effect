from __future__ import annotations

import json
from pathlib import Path

from src.experiments.effect_binding_guard.e83_overhead_instrumentation import EventRecorder, summarize_events


def test_recorder_writes_success_and_failure_events(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    recorder = EventRecorder(path, "run-1")
    with recorder.timed("precommit_check", case_id="c1", tool_name="send", trajectory_index=2) as event:
        event["atom_count"] = 3
        event["decision"] = "ALLOW"
    try:
        with recorder.timed("precommit_check", case_id="c2"):
            raise ValueError("expected")
    except ValueError:
        pass
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 2
    assert rows[0]["attributes"]["atom_count"] == 3
    assert rows[0]["outcome"] == "returned"
    assert rows[1]["outcome"] == "raised" and rows[1]["error_type"] == "ValueError"
    assert all(row["wall_ns"] >= 0 and row["cpu_ns"] >= 0 for row in rows)


def test_summary_reports_required_quantiles() -> None:
    rows = [{"event": "guard", "wall_ns": value * 1_000_000} for value in range(1, 101)]
    summary = summarize_events(rows)["guard"]
    assert summary["n"] == 100
    assert summary["median_ms"] == 50.5
    assert summary["p90_ms"] == 90
    assert summary["p95_ms"] == 95


def test_summary_rejects_malformed_events() -> None:
    import pytest

    with pytest.raises(ValueError):
        summarize_events([{"event": "guard", "wall_ns": -1}])
