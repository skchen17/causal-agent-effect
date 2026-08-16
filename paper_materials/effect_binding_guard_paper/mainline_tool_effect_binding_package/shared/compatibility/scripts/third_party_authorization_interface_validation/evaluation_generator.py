"""Descriptor-blind post-freeze contexts with disjoint values and state."""

from __future__ import annotations

from .scenario_data import TOOL_SOURCES, make_case


def generate_evaluation_rows(phase: str = "evaluation") -> list[dict]:
    if phase not in {"evaluation", "confirmatory"}:
        raise ValueError(phase)
    return [make_case(tool, phase, pair, side)
            for tool in TOOL_SOURCES for pair in range(12) for side in (0, 1)]

