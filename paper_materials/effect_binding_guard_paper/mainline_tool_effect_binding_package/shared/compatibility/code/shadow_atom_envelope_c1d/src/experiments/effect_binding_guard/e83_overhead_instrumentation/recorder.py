"""Append-only timing events and deterministic distribution summaries."""

from __future__ import annotations

import fcntl
import json
import math
import os
import resource
import time
from contextlib import contextmanager
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterator, Mapping


class EventRecorder:
    def __init__(self, path: str | Path, run_id: str) -> None:
        self.path = Path(path)
        self.run_id = run_id

    def append(self, row: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"run_id": self.run_id, **dict(row)}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @contextmanager
    def timed(
        self,
        event: str,
        *,
        case_id: str,
        tool_name: str | None = None,
        trajectory_index: int | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        start_wall = time.perf_counter_ns()
        start_cpu = time.process_time_ns()
        start_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        dynamic: dict[str, Any] = {}
        outcome = "returned"
        error_type = None
        try:
            yield dynamic
        except Exception as exc:
            outcome = "raised"
            error_type = type(exc).__name__
            raise
        finally:
            end_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            self.append({
                "event": event,
                "case_id": case_id,
                "tool_name": tool_name,
                "trajectory_index": trajectory_index,
                "wall_ns": time.perf_counter_ns() - start_wall,
                "cpu_ns": time.process_time_ns() - start_cpu,
                "max_rss_kib_before": start_rss,
                "max_rss_kib_after": end_rss,
                "outcome": outcome,
                "error_type": error_type,
                "attributes": {**dict(attributes or {}), **dynamic},
            })


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires values")
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return ordered[rank]


def summarize_events(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        if not isinstance(row.get("event"), str) or not isinstance(row.get("wall_ns"), int):
            raise ValueError("every overhead row requires event:string and wall_ns:int")
        if row["wall_ns"] < 0:
            raise ValueError("negative wall time")
        groups.setdefault(row["event"], []).append(row["wall_ns"] / 1_000_000)
    return {
        event: {
            "n": len(values),
            "mean_ms": mean(values),
            "median_ms": median(values),
            "p90_ms": _percentile(values, 0.90),
            "p95_ms": _percentile(values, 0.95),
            "max_ms": max(values),
        }
        for event, values in sorted(groups.items())
    }
